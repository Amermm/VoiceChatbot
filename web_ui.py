from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
from voice_core_v1 import VoiceChatBot
import json
import os
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
app.config['DEBUG'] = False
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='gevent',
                   logger=True,
                   engineio_logger=True)
chatbot = VoiceChatBot()

@app.route('/')
def index():
    robot_name = os.environ.get('ROBOTNAME', 'Royal')
    return render_template('index.html', robot_name=robot_name)

@socketio.on('start_listening')
def handle_start_listening():
    chatbot.start_listening()
    emit('listening_status', {'status': 'started'})

@socketio.on('stop_listening')
def handle_stop_listening():
    chatbot.stop_listening()
    emit('listening_status', {'status': 'stopped'})

@socketio.on('audio_data')
def handle_audio_data(data):
    try:
        results = chatbot.process_audio_chunk(data)
        if results:
            emit('bot_response', results)
    except Exception as e:
        emit('error', {'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, 
                host='0.0.0.0', 
                port=port,
                debug=False,
                use_reloader=False)
