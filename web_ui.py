from flask import Flask, render_template, jsonify
from flask_sockets import Sockets
import json
import os
from voice_core_v1 import VoiceChatBot
import base64
import threading

app = Flask(__name__)
sockets = Sockets(app)

# Initialize the chatbot
chatbot = VoiceChatBot()

def get_env_variable(var_name):
    try:
        return os.environ[var_name]
    except KeyError:
        raise RuntimeError(f"Environment variable '{var_name}' is not set.")

# Load environment variables
GOOGLE_CREDENTIALS = get_env_variable("GOOGLE_CREDENTIALS")
DATABASE_EXCEL_PATH = get_env_variable("DATABASE_EXCEL_PATH")
OPENAI_API_KEY = get_env_variable("OPENAI_API_KEY")
ROBOTNAME = get_env_variable("ROBOTNAME")

chatbot.setup_environment()

@app.route('/')
def index():
    return render_template('index.html')

@sockets.route('/audio')
def audio(ws):
    """WebSocket endpoint to handle real-time audio streaming."""
    audio_buffer = []
    silence_threshold = 500
    silence_frames = 0
    max_silence_frames = 20

    def process_and_respond():
        nonlocal audio_buffer
        transcript = chatbot.process_audio_data(audio_buffer)
        if transcript:
            response = chatbot.get_gpt_response(transcript)
            ws.send(json.dumps({"transcript": transcript, "response": response}))
            chatbot.speak_response(response)
        audio_buffer = []

    while not ws.closed:
        try:
            message = ws.receive()
            if not message:
                continue

            audio_data = base64.b64decode(message)
            audio_buffer.append(audio_data)

            # Process silence detection
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            if np.abs(audio_array).mean() < silence_threshold:
                silence_frames += 1
            else:
                silence_frames = 0

            if silence_frames >= max_silence_frames and audio_buffer:
                process_and_respond()
        except Exception as e:
            ws.send(json.dumps({"error": str(e)}))

if __name__ == '__main__':
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler

    app.debug = True
    server = pywsgi.WSGIServer(('0.0.0.0', 5000), app, handler_class=WebSocketHandler)
    server.serve_forever()
