from flask import Flask, render_template, jsonify, request, Response
from voice_core_v1 import VoiceChatBot
import json
import os

app = Flask(__name__)
chatbot = VoiceChatBot()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_listening', methods=['POST'])
def start_listening():
    chatbot.start_listening()
    return jsonify({"status": "started"})

@app.route('/stop_listening', methods=['POST'])
def stop_listening():
    chatbot.stop_listening()
    return jsonify({"status": "stopped"})

@app.route('/stream')
def stream():
    def generate():
        for result in chatbot.process_continuous_audio():
            yield f"data: {json.dumps(result)}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    # Use the port provided by Render's environment, defaulting to 5000 locally
    port = int(os.environ.get('PORT', 5000))
    # Bind to 0.0.0.0 to ensure the app is accessible in Render's environment
    app.run(host='0.0.0.0', port=port, threaded=True)
