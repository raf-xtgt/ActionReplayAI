from flask import Blueprint, jsonify, request, Response
import json

msg_bp = Blueprint('msg_bp', __name__)

@msg_bp.route('/send', methods=['POST'])
def send_msg():
    print("send message endpoint")