import os
import openai
import pandas as pd
from google.cloud import secretmanager
from google.cloud import speech
import tempfile
import logging

class VoiceChatBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Initialize secrets and environment variables
        self.config = {
            'GOOGLE_CREDENTIALS': self.get_secret('GOOGLE_CREDENTIALS'),
            'OPENAI_API_KEY': self.get_secret('OPENAI_API_KEY'),
            'DATABASE_EXCEL_PATH': os.environ.get('DATABASE_EXCEL_PATH'),
            'ROBOTNAME': os.environ.get('ROBOTNAME', 'Royal'),  # Default to 'Royal'
        }

        # Setup API keys and credentials
        self.setup_environment()
        self.speech_client = speech.SpeechClient()

    def get_secret(self, secret_name):
        """
        Retrieve a secret from Google Secret Manager.
        """
        try:
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
            secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(name=secret_path)
            secret_value = response.payload.data.decode("UTF-8")
            self.logger.info(f"Retrieved secret: {secret_name}")
            return secret_value
        except Exception as e:
            self.logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise

    def setup_environment(self):
        """
        Set up API credentials and keys.
        """
        openai.api_key = self.config['OPENAI_API_KEY']
        if self.config['GOOGLE_CREDENTIALS']:
            try:
                fd, path = tempfile.mkstemp()
                with os.fdopen(fd, 'w') as temp:
                    temp.write(self.config['GOOGLE_CREDENTIALS'])
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
                self.logger.info("Google credentials successfully loaded")
            except Exception as e:
                self.logger.error(f"Failed to load Google credentials: {e}")
                raise
        else:
            self.logger.error("GOOGLE_CREDENTIALS secret is not set")
            raise ValueError("GOOGLE_CREDENTIALS secret is missing")

    def process_audio_data(self, audio_bytes):
        try:
            self.logger.info("Processing audio data")
            audio = speech.RecognitionAudio(content=audio_bytes)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code="en-US",
                enable_automatic_punctuation=True,
            )
            response = self.speech_client.recognize(config=config, audio=audio)
            for result in response.results:
                return result.alternatives[0].transcript
        except Exception as e:
            self.logger.error(f"Speech Recognition Error: {e}")
            return None

    def get_gpt_response(self, query):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are {self.config['ROBOTNAME']}, a helpful assistant."},
                    {"role": "user", "content": query}
                ],
                max_tokens=100,
                temperature=0.7,
            )
            return response.choices[0].message['content']
        except Exception as e:
            self.logger.error(f"GPT Error: {e}")
            return "I'm sorry, I couldn't process your request."
