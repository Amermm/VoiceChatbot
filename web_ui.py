from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from voice_core_v1 import VoiceChatBot
import base64
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')
chatbot = VoiceChatBot()

@app.route('/')
def index():
    robot_name = os.environ.get('ROBOTNAME', 'Royal')
    return render_template('index.html', robot_name=robot_name)

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('audio_data')
def handle_audio_data(data):
    try:
        audio_bytes = base64.b64decode(data)
        transcript = chatbot.process_audio_data(audio_bytes)
        if transcript:
            response = chatbot.get_gpt_response(transcript)
            emit('bot_response', {'transcript': transcript, 'response': response})
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        emit('error', {'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
