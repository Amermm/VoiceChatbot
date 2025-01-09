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

class VoiceChatBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Environment-based configuration
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.google_credentials = os.getenv('GOOGLE_CREDENTIALS')
        self.database_excel_path = os.getenv('DATABASE_EXCEL_PATH')
        self.robot_name = os.getenv('ROBOTNAME', 'Royal')

        # Validate critical configurations
        if not all([self.openai_key, self.google_credentials, self.database_excel_path]):
            raise ValueError("Environment variables are missing or incomplete")

        self.setup_environment()

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

    def setup_environment(self):
        openai.api_key = self.openai_key
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.google_credentials

    def _load_excel_data(self):
        try:
            df = pd.read_excel(self.database_excel_path)
            # Handle missing values
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
