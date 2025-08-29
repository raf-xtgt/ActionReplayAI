from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from controller import *

load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {  # This will apply to all routes
        "origins": "http://localhost:3000",
        "supports_credentials": True
    }
})
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='gevent',  # or 'eventlet' if you prefer
                   logger=True,
                   engineio_logger=True)

app.register_blueprint(msg_bp, url_prefix='/api/msg')
            

@app.route('/test', methods=['POST'])
def test():
    print("Test received:", request.json)
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    socketio.run(app, port=5000, debug=True)