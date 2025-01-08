from flask import Flask, render_template, jsonify, request, Response
from voice_core_v1 import VoiceChatBot
import json
import logging

app = Flask(__name__)
chatbot = VoiceChatBot()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_ui")

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

@app.route('/process_audio', methods=['POST'])
def process_audio():
    try:
        logger.info("Processing audio data")
        audio_data = request.data
        logger.debug(f"Audio data length: {len(audio_data)}")
        
        result = chatbot.process_audio_data([audio_data])
        if result is not None:
            return jsonify(result)
        else:
            logger.error("Audio processing returned None")
            return jsonify({"error": "Audio processing failed"}), 400
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/stream')
def stream():
    def generate():
        for result in chatbot.process_continuous_audio():
            yield f"data: {json.dumps(result)}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
