import os
import openai
import pandas as pd
from google.cloud import speech
import logging
import json
import base64

class VoiceChatBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.setup_environment()
        self.df = self._load_excel_data()
        self.speech_client = speech.SpeechClient()
        self.is_listening = False

    def setup_environment(self):
        """Load environment variables."""
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        google_creds_json = os.getenv('GOOGLE_CREDENTIALS')
        self.database_excel_path = os.getenv('DATABASE_EXCEL_PATH')

        # Set API keys
        openai.api_key = self.openai_api_key
        
        # Handle Google credentials
        if google_creds_json:
            temp_creds_path = '/tmp/google_creds_temp.json'
            with open(temp_creds_path, 'w') as f:
                f.write(google_creds_json)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds_path

    def _load_excel_data(self):
        """Load data from the Excel file."""
        try:
            df = pd.read_excel(self.database_excel_path)
            for column in df.columns:
                if df[column].dtype in ['float64', 'int64']:
                    df[column] = df[column].fillna(0)
                else:
                    df[column] = df[column].fillna('')
            # Pre-process context data
            self.context_data = df.astype(str).to_string(index=False, header=True)
            return df
        except Exception as e:
            self.logger.error(f"Error loading Excel: {e}")
            return pd.DataFrame()

    def process_audio_data(self, audio_data):
        """Process audio data from client"""
        try:
            # Decode base64 audio data
            decoded_audio = base64.b64decode(audio_data.split(',')[1])
            
            audio = speech.RecognitionAudio(content=decoded_audio)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code="en-US",
                enable_automatic_punctuation=True
            )

            response = self.speech_client.recognize(config=config, audio=audio)
            
            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                gpt_response = self.get_gpt_response(transcript)
                return {"transcript": transcript, "response": gpt_response}
            
            return None
        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
            return None

    def get_gpt_response(self, query):
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful data assistant. Provide concise responses."},
                    {"role": "system", "content": f"Context data:\n{self.context_data}"},
                    {"role": "user", "content": query}
                ],
                max_tokens=100,
                temperature=0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"GPT Error: {e}")
            return "Sorry, I couldn't process your request."

    def start_listening(self):
        """Start listening"""
        self.is_listening = True
        return {"status": "started"}

    def stop_listening(self):
        """Stop listening"""
        self.is_listening = False
        return {"status": "stopped"}
