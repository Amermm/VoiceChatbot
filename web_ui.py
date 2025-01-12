from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from voice_core_v1 import VoiceChatBot
import logging

# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize VoiceChatBot
chatbot = VoiceChatBot()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/")
def index():
    """Render the homepage."""
    return render_template("index.html")

@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    logger.info("Client connected.")
    emit("message", {"data": "Connected to VoiceChatBot!"})

@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected.")

@socketio.on("audio")
def handle_audio(data):
    """Handle audio data sent from the client."""
    logger.info("Audio data received.")
    try:
        response = chatbot.process_audio(data)
        emit("response", {"data": response})
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        emit("error", {"data": "Failed to process audio."})

if __name__ == "__main__":
    # Run the app with SocketIO
    socketio.run(app, host="0.0.0.0", port=8080)
