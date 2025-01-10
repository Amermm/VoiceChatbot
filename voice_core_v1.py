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
        
        # Load configuration from environment variables
        self.config = {
            'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
            'DATABASE_EXCEL_PATH': os.environ.get('DATABASE_EXCEL_PATH', 'SCADA TestData.xlsx'),
            'GOOGLE_CREDENTIALS': os.environ.get('GOOGLE_CREDENTIALS'),
            'ROBOTNAME': os.environ.get('ROBOTNAME', 'Royal'),
        }
        
        # Setup environment
        self.setup_environment()
        
        # Initialize components
        self.df = self._load_excel_data()
        self.speech_client = speech.SpeechClient()

    def setup_environment(self):
        openai.api_key = self.config['OPENAI_API_KEY']
        
        # Setup Google Cloud credentials
        if self.config['GOOGLE_CREDENTIALS']:
            try:
                fd, path = tempfile.mkstemp()
                with os.fdopen(fd, 'w') as temp:
                    temp.write(self.config['GOOGLE_CREDENTIALS'])
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
                self.logger.info("Google credentials successfully loaded")
            except Exception as e:
                self.logger.error(f"Failed to load Google credentials: {e}")
    

    def _load_excel_data(self):
        try:
            df = pd.read_excel(self.config['DATABASE_EXCEL_PATH'])
            for column in df.columns:
                if df[column].dtype in ['float64', 'int64']:
                    df[column] = df[column].fillna(0)
                else:
                    df[column] = df[column].fillna('')
            self.context_data = df.astype(str).to_string(index=False, header=True)
            return df
        except Exception as e:
            self.logger.error(f"Error loading Excel: {e}")
            return pd.DataFrame()

    def process_audio_data(self, audio_bytes):
        try:
            audio = speech.RecognitionAudio(content=audio_bytes)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,  # Browser audio encoding
                language_code="en-US",
                sample_rate_hertz=16000,  # Explicit sample rate
                enable_automatic_punctuation=True
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
                    {"role": "system", "content": f"Context data:\n{self.context_data}"},
                    {"role": "user", "content": query}
                ],
                max_tokens=100,
                temperature=0
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            self.logger.error(f"GPT Error: {e}")
            return "I'm sorry, I couldn't process your request."
