from flask import Flask, render_template, jsonify, request
from voice_core_v1 import VoiceChatBot  # Changed from v2 to v1
import logging

app = Flask(__name__)
chatbot = VoiceChatBot()

# Configure Flask logging
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_audio', methods=['POST'])
def process_audio():
    try:
        # Log request details
        app.logger.info("Received audio processing request")
        app.logger.debug(f"Request content type: {request.content_type}")
        app.logger.debug(f"Request size: {request.content_length} bytes")
        
        # Validate request
        if not request.is_json:
            app.logger.error("Request is not JSON")
            return jsonify({"error": "Request must be JSON"}), 400
            
        audio_data = request.json.get('audio')
        if not audio_data:
            app.logger.error("No audio data in request")
            return jsonify({"error": "No audio data provided"}), 400
        
        # Process audio
        app.logger.info("Processing audio data...")
        result = chatbot.process_audio_data(audio_data)
        
        # Log result summary
        if result is None or (isinstance(result, dict) and "error" in result):
            error_msg = result.get("error", "Unknown processing error") if isinstance(result, dict) else "Processing failed"
            app.logger.error(f"Processing error: {error_msg}")
            return jsonify({"error": error_msg}), 400
            
        app.logger.info("Audio processing successful")
        app.logger.debug(f"Result: {result}")
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Unexpected error in process_audio: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/start_listening', methods=['POST'])
def start_listening():
    try:
        result = chatbot.start_listening()
        app.logger.info("Started listening session")
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error starting listening: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/stop_listening', methods=['POST'])
def stop_listening():
    try:
        result = chatbot.stop_listening()
        app.logger.info("Stopped listening session")
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error stopping listening: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Use the port from environment variable if available
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
