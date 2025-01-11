from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from voice_core_v1 import VoiceChatBot
import base64
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')
chatbot = VoiceChatBot()

@app.route('/')
def index():
    robot_name = "Royal"  # Replace with dynamic environment variable if needed
    return render_template('index.html', robot_name=robot_name)

@socketio.on('connect')
def handle_connect():
    logger.info("Client connected")
    emit('connection_status', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected")

@socketio.on('audio_data')
def handle_audio_data(data):
    try:
        logger.info("Received audio data")
        audio_bytes = base64.b64decode(data)
        transcript = chatbot.process_audio_data(audio_bytes)
        if transcript:
            response = chatbot.get_gpt_response(transcript)
            emit('bot_response', {'transcript': transcript, 'response': response})
    except Exception as e:
        logger.error(f"Error processing audio data: {e}")
        emit('error', {'error': str(e)})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port)
