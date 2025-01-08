from flask import Flask, render_template, jsonify, request, Response
from voice_core_v1 import VoiceChatBot
import json
import logging

app = Flask(__name__)
chatbot = VoiceChatBot()

# Configure Flask logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            logger.error("No audio data received")
            return jsonify({"error": "No audio data received"}), 400

        logger.info("Processing audio data")
        result = chatbot.process_audio_data(audio_data)
        
        if result:
            logger.info(f"Audio processing result: {result}")
            return jsonify(result)
        
        return jsonify({"error": "Could not process audio"}), 400
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/start_listening', methods=['POST'])
def start_listening():
    return jsonify(chatbot.start_listening())

@app.route('/stop_listening', methods=['POST'])
def stop_listening():
    return jsonify(chatbot.stop_listening())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
