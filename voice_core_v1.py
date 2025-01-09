import os
import openai
import pandas as pd
from google.cloud import speech
import pyaudio
import wave
import threading
import queue
import time
from datetime import datetime
import logging
import numpy as np
import pyttsx3
import json

class VoiceChatBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Load environment variables
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.google_credentials_json = os.environ.get("GOOGLE_CREDENTIALS")
        self.database_excel_path = os.environ.get("DATABASE_EXCEL_PATH")
        self.robot_name = os.environ.get("ROBOTNAME", "VoiceBot")

        # Initialize OpenAI API key
        openai.api_key = self.openai_api_key

        # Set up Google credentials
        self.setup_google_credentials()

        # Audio settings
        self.RATE = 16000
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1

        # Initialize components
        self.df = self._load_excel_data()
        self.speech_client = speech.SpeechClient()

        # Streaming components
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.p = None
        self.stream = None

    def setup_google_credentials(self):
        try:
            credentials_path = "google_credentials.json"
            with open(credentials_path, "w") as f:
                f.write(self.google_credentials_json)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        except Exception as e:
            self.logger.error(f"Error setting up Google credentials: {e}")

    def _load_excel_data(self):
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
        if not audio_data:
            return None

        # Convert audio data to wav file
        temp_filename = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        with wave.open(temp_filename, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(audio_data))

        try:
            with open(temp_filename, 'rb') as f:
                content = f.read()

            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.RATE,
                language_code="en-US",
                enable_automatic_punctuation=True,
                use_enhanced=True
            )

            response = self.speech_client.recognize(config=config, audio=audio)

            for result in response.results:
                return result.alternatives[0].transcript

        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

        return None

    def get_gpt_response(self, query):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful data assistant. Provide concise responses."},
                    {"role": "system", "content": f"Context data:\n{self.context_data}"},
                    {"role": "user", "content": query}
                ],
                max_tokens=100,
                temperature=0
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            self.logger.error(f"GPT Error: {e}")
            return "Sorry, I couldn't process your request."

    def speak_response(self, response):
        """Convert text to speech using pyttsx3."""
        def tts_worker(response_text):
            try:
                engine = pyttsx3.init()
                engine.say(response_text)
                engine.runAndWait()
            except Exception as e:
                self.logger.error(f"TTS Error: {e}")

        tts_thread = threading.Thread(target=tts_worker, args=(response,))
        tts_thread.daemon = True
        tts_thread.start()
