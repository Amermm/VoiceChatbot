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
        logger.info("Received /process_audio request.")
        audio_file = request.files.get('audio_file')
        if not audio_file:
            logger.error("No audio file provided in the request.")
            return jsonify({"error": "No audio file provided"}), 400

        audio_file_path = f"/tmp/{audio_file.filename}"
        audio_file.save(audio_file_path)
        logger.info(f"Audio file saved to {audio_file_path}.")

        result = chatbot.process_audio_data(audio_file_path)
        if "error" in result:
            logger.error(f"Error processing audio: {result['error']}")
            return jsonify(result), 400
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Exception in /process_audio: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/stream')
def stream():
    def generate():
        for result in chatbot.process_continuous_audio():
            yield f"data: {json.dumps(result)}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
