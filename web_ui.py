from flask import Flask, render_template, jsonify
from flask_sockets import Sockets
import json
import os
from voice_core_v1 import VoiceChatBot
import base64

app = Flask(__name__)
sockets = Sockets(app)
chatbot = VoiceChatBot()

@app.route('/')
def index():
    return render_template('index.html')

@sockets.route('/audio')
def audio(ws):
    """WebSocket endpoint to handle real-time audio streaming."""
    while not ws.closed:
        try:
            message = ws.receive()
            if not message:
                continue
            
            # Process the audio data received from client
            audio_data = base64.b64decode(message)
            transcript = chatbot.process_audio_data(audio_data)
            
            if transcript:
                response = chatbot.get_gpt_response(transcript)
                ws.send(json.dumps({
                    "transcript": transcript,
                    "response": response
                }))
        except Exception as e:
            ws.send(json.dumps({"error": str(e)}))

if __name__ == '__main__':
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    port = int(os.environ.get('PORT', 5000))
    server = pywsgi.WSGIServer(('0.0.0.0', port), app, handler_class=WebSocketHandler)
    server.serve_forever()
