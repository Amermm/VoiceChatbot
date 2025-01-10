from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
from voice_core_v1 import VoiceChatBot
import json
import os
import logging
import base64

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
    chatbot.start_listening()

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')
    chatbot.stop_listening()

@socketio.on('start_listening')
def handle_start_listening():
    chatbot.start_listening()
    emit('listening_status', {'status': 'started'})
    logger.info('Started listening')

@socketio.on('stop_listening')
def handle_stop_listening():
    chatbot.stop_listening()
    emit('listening_status', {'status': 'stopped'})
    logger.info('Stopped listening')

@socketio.on('audio_data')
def handle_audio_data(data):
    try:
        if isinstance(data, str):
            audio_bytes = base64.b64decode(data)
            chatbot.audio_queue.put(audio_bytes)
            for result in chatbot.process_continuous_audio():
                if result and 'transcript' in result:
                    logger.info(f'Got result: {result}')
                    emit('bot_response', result)
    except Exception as e:
        logger.error(f'Error: {str(e)}')
        emit('error', {'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
