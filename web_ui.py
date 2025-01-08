from flask import Flask, render_template, jsonify, request, Response, send_from_directory
from voice_core_v1 import VoiceChatBot
import json
import os

app = Flask(__name__, 
    static_folder='static',
    template_folder='templates'
)
chatbot = VoiceChatBot()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/process_audio', methods=['POST'])
def process_audio():
    try:
        audio_data = request.json.get('audio')
        if not audio_data:
            app.logger.error("No audio data received")
            return jsonify({"error": "No audio data received"}), 400
        
        app.logger.info("Received audio data, processing...")
        result = chatbot.process_audio_data(audio_data)
        
        if result:
            app.logger.info(f"Processing successful: {result}")
            return jsonify(result)
            
        app.logger.error("Could not process audio")
        return jsonify({"error": "Could not process audio"}), 400
    except Exception as e:
        app.logger.error(f"Error processing audio: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/start_listening', methods=['POST'])
def start_listening():
    return jsonify(chatbot.start_listening())

@app.route('/stop_listening', methods=['POST'])
def stop_listening():
    return jsonify(chatbot.stop_listening())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
