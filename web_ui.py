from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
from voice_core_v1 import VoiceChatBot
import json
import os
import secrets
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(16)

# Initialize SocketIO with gevent
socketio = SocketIO(app, 
                   async_mode='gevent',
                   cors_allowed_origins="*",
                   logger=True,
                   engineio_logger=True)

# Initialize the chatbot
chatbot = None

@app.before_first_request
def initialize_chatbot():
    global chatbot
    if chatbot is None:
        chatbot = VoiceChatBot()

@app.route('/')
def index():
    robot_name = os.environ.get('ROBOTNAME', 'Royal')
    return render_template('index.html', robot_name=robot_name)

@socketio.on('connect')
def handle_connect():
    global chatbot
    if chatbot is None:
        chatbot = VoiceChatBot()
    logger.info('Client connected')
    emit('status', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('start_listening')
def handle_start_listening():
    logger.info('Started listening')
    emit('listening_status', {'status': 'started'})

@socketio.on('stop_listening')
def handle_stop_listening():
    logger.info('Stopped listening')
    emit('listening_status', {'status': 'stopped'})

@socketio.on('audio_data')
def handle_audio_data(data):
    logger.info('Received audio data')
    try:
        if chatbot is None:
            initialize_chatbot()
        
        if isinstance(data, dict) and 'audio' in data:
            audio_data = data['audio']
        else:
            audio_data = data
            
        results = chatbot.process_audio_chunk(audio_data)
        logger.info(f'Audio processing results: {results}')
        
        if results:
            if 'error' in results:
                emit('error', {'error': results['error']})
            else:
                emit('bot_response', {
                    'transcript': results.get('transcript', ''),
                    'response': results.get('response', '')
                })
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}", exc_info=True)
        emit('error', {'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, 
                host='0.0.0.0',
                port=port,
                debug=False)
