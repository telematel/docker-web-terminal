from flask import Flask, render_template
from flask_sockets import Sockets
from utility.myDocker import ClientHandler, DockerStreamThread
import conf

from cryptography.fernet import Fernet
import base64


app = Flask(__name__)
sockets = Sockets(app)

@app.route('/hello')
def hello_world():
    return 'ping'

@sockets.route('/echo')
def echo_socket(ws):
    token = ws.receive()
    try:
        f = Fernet(base64.b64encode(bytes(conf.SECRET_KEY, 'UTF-8')))
        data = f.decrypt(bytes(token, 'UTF-8'), ttl=60).decode().split(':')
    except:
        data = []
    if (len(data) != 2) or (not data[0] == 'conaiter_name'):
        ws.send("Invalid token\n\r")
        ws.close()
        return

    try:
        dockerCli = ClientHandler(base_url=conf.DOCKER_HOST, timeout=10)
        terminalExecId = dockerCli.creatTerminalExec(data[1])
        terminalStream = dockerCli.startTerminalExec(terminalExecId)._sock

        terminalThread = DockerStreamThread(ws, terminalStream)
        terminalThread.start()
    except Exception as e:
        ws.send("Cannot connect to container\n\rError: %s\n\r" % e)
        ws.close()
        return

    while not ws.closed:
        message = ws.receive()
        if message is not None:
            terminalStream.send(bytes(message, encoding='utf-8'))

if __name__ == '__main__':
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('', 5000), app, handler_class=WebSocketHandler)
    server.serve_forever()