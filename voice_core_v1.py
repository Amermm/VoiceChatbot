import os
import openai
import pandas as pd
from google.cloud import speech
import base64
import tempfile
import logging

class VoiceChatBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = {
            'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
            'GOOGLE_CREDENTIALS': os.environ.get('GOOGLE_CREDENTIALS'),
        }
        self.setup_environment()
        self.speech_client = speech.SpeechClient()

    def setup_environment(self):
        openai.api_key = self.config['OPENAI_API_KEY']
        if self.config['GOOGLE_CREDENTIALS']:
            try:
                fd, path = tempfile.mkstemp()
                with os.fdopen(fd, 'w') as temp:
                    temp.write(self.config['GOOGLE_CREDENTIALS'])
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
                self.logger.info("Google credentials loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load Google credentials: {e}")

    def process_audio_data(self, audio_bytes):
        try:
            self.logger.info("Starting Google Speech-to-Text processing")
            audio = speech.RecognitionAudio(content=audio_bytes)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code="en-US",
                enable_automatic_punctuation=True,
            )
    
            response = self.speech_client.recognize(config=config, audio=audio)
            self.logger.info("Google Speech-to-Text response received")
            for result in response.results:
                return result.alternatives[0].transcript
        except Exception as e:
            self.logger.error(f"Speech Recognition Error: {e}")
            return None


    def get_gpt_response(self, query):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": query}],
                max_tokens=100,
                temperature=0.7,
            )
            return response.choices[0].message['content']
        except Exception as e:
            self.logger.error(f"GPT Error: {e}")
            return "Sorry, I couldn't process your request."
