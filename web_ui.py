from flask import Flask, render_template, jsonify, request
from voice_core_v2 import VoiceChatBot
import logging
import asyncio
from functools import wraps

app = Flask(__name__)
chatbot = VoiceChatBot()

# Configure Flask logging
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

def async_route(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapped

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_audio', methods=['POST'])
@async_route
async def process_audio():
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
        result = await chatbot.process_audio_data(audio_data)
        
        # Log result summary
        if "error" in result:
            app.logger.error(f"Processing error: {result['error']}")
            return jsonify(result), 400
            
        app.logger.info("Audio processing successful")
        app.logger.debug(f"Result: {result}")
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Unexpected error in process_audio: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/start_listening', methods=['POST'])
async def start_listening():
    try:
        result = chatbot.start_listening()
        app.logger.info("Started listening session")
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error starting listening: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/stop_listening', methods=['POST'])
async def stop_listening():
    try:
        result = chatbot.stop_listening()
        app.logger.info("Stopped listening session")
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error stopping listening: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
