from flask import Flask, request, jsonify, current_app
import logging
import base64
import time
from google.cloud import speech
import openai
import os
from concurrent.futures import ThreadPoolExecutor

class VoiceChatDebugger:
    def __init__(self):
        self._setup_logging()
        self._setup_apis()
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    def _setup_logging(self):
        """Configure detailed logging"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def _setup_apis(self):
    """Setup API clients with validation"""
    try:
        # Validate OpenAI API key
        self.openai_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_key:
            raise ValueError("OpenAI API key not found!")
        openai.api_key = self.openai_key
        
        # Handle Google credentials
        google_creds_json = os.getenv('GOOGLE_CREDENTIALS')
        if not google_creds_json:
            raise ValueError("Google credentials not found in environment!")
            
        # Write credentials to a temporary file
        import tempfile
        import json
        
        # Parse the JSON string to ensure it's valid
        try:
            json.loads(google_creds_json)
        except json.JSONDecodeError:
            raise ValueError("Invalid Google credentials JSON format")
            
        # Create a temporary file for credentials
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(google_creds_json)
            temp_creds_path = temp_file.name
            
        # Set the environment variable to point to our temporary file
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds_path
        
        # Initialize Speech client
        try:
            self.speech_client = speech.SpeechClient()
            self.logger.info("Successfully initialized Google Speech client")
        except Exception as e:
            self.logger.error(f"Failed to initialize Speech client: {e}")
            raise
            
    except Exception as e:
        self.logger.error(f"Failed to setup APIs: {e}")
        raise

class VoiceChatBot(VoiceChatDebugger):
    def __init__(self):
        super().__init__()
        self.is_listening = False
        
    async def process_audio_data(self, audio_data):
        """Process audio with comprehensive error handling and logging"""
        start_time = time.time()
        self.logger.info("Starting audio processing")
        
        try:
            # Validate and decode audio
            if not audio_data:
                self.logger.error("No audio data received")
                return {"error": "No audio data received"}
                
            try:
                # Extract base64 data after comma
                if ',' in audio_data:
                    audio_data = audio_data.split(',')[1]
                decoded_audio = base64.b64decode(audio_data)
                self.logger.debug(f"Decoded audio size: {len(decoded_audio)} bytes")
                
                # Validate audio size
                if len(decoded_audio) < 10000:
                    self.logger.warning("Audio chunk too small")
                    return {"error": "Audio chunk too small"}
                    
            except Exception as e:
                self.logger.error(f"Audio decoding error: {e}")
                return {"error": f"Audio decode failed: {str(e)}"}

            # Configure speech recognition
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code="en-US",
                enable_automatic_punctuation=True,
                model="default",
                use_enhanced=True,
            )
            
            audio = speech.RecognitionAudio(content=decoded_audio)
            
            # Process with Google Speech-to-Text
            try:
                self.logger.info("Sending request to Google Speech-to-Text")
                response = await self.executor.submit(
                    self.speech_client.recognize,
                    config=config,
                    audio=audio
                )
                self.logger.debug(f"Speech-to-Text response: {response}")
                
                if not response.results:
                    self.logger.warning("No transcription results")
                    return {"error": "No speech detected"}

                transcript = response.results[0].alternatives[0].transcript
                confidence = response.results[0].alternatives[0].confidence

                self.logger.info(f"Transcribed: '{transcript}' with confidence: {confidence}")

                if confidence < 0.6:
                    self.logger.warning(f"Low confidence: {confidence}")
                    return {"error": "Low confidence in transcription"}

                # Get GPT response
                gpt_response = await self.get_gpt_response(transcript)
                
                process_time = time.time() - start_time
                self.logger.info(f"Total processing time: {process_time:.2f} seconds")
                
                return {
                    "transcript": transcript,
                    "response": gpt_response,
                    "confidence": confidence,
                    "process_time": process_time
                }

            except Exception as e:
                self.logger.error(f"Speech-to-Text error: {e}")
                return {"error": f"Speech recognition failed: {str(e)}"}

        except Exception as e:
            self.logger.error(f"Process audio error: {e}")
            return {"error": f"Processing failed: {str(e)}"}

    async def get_gpt_response(self, query):
        """Get GPT response with error handling and logging"""
        try:
            self.logger.info(f"Sending query to GPT: {query}")
            start_time = time.time()
            
            response = await openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant. Keep responses clear and concise."},
                    {"role": "user", "content": query}
                ],
                max_tokens=150,
                temperature=0.7,
                timeout=10  # Add timeout
            )
            
            response_text = response.choices[0].message.content.strip()
            process_time = time.time() - start_time
            
            self.logger.info(f"GPT response time: {process_time:.2f}s")
            self.logger.debug(f"GPT response: {response_text}")
            
            return response_text
            
        except Exception as e:
            self.logger.error(f"GPT Error: {e}")
            return "I apologize, but I'm having trouble generating a response right now. Please try again."

    def start_listening(self):
        self.is_listening = True
        self.logger.info("Started listening")
        return {"status": "started", "timestamp": time.time()}

    def stop_listening(self):
        self.is_listening = False
        self.logger.info("Stopped listening")
        return {"status": "stopped", "timestamp": time.time()}
