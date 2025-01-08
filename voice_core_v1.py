import os
import openai
import pandas as pd
from google.cloud import speech
import sounddevice as sd
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
        
        # Load configuration from environment variables
        self.setup_environment()
        
        # Audio settings
        self.RATE = 16000
        self.CHANNELS = 1
        self.audio_queue = queue.Queue()
        self.is_listening = False

        # Initialize components
        self.df = self._load_excel_data()
        self.speech_client = speech.SpeechClient()

    def setup_environment(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.google_credentials = os.getenv('GOOGLE_CREDENTIALS')
        self.database_excel_path = os.getenv('DATABASE_EXCEL_PATH')
        self.robot_name = os.getenv('ROBOTNAME', 'AI Assistant')

        # Set Google Application Credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.google_credentials

        self.logger.info("Environment variables loaded successfully.")

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

    def audio_callback(self, indata, frames, time, status):
        if self.is_listening:
            self.audio_queue.put(indata.copy())

    def start_listening(self):
        self.is_listening = True
        self.stream = sd.InputStream(
            samplerate=self.RATE,
            channels=self.CHANNELS,
            callback=self.audio_callback
        )
        self.stream.start()
        self.logger.info("Started listening.")

    def stop_listening(self):
        self.is_listening = False
        if hasattr(self, 'stream') and self.stream.active:
            self.stream.stop()
        self.logger.info("Stopped listening.")

    def process_audio_data(self, audio_data):
        if not audio_data:
            return None

        try:
            audio = speech.RecognitionAudio(content=audio_data.tobytes())
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.RATE,
                language_code="en-US",
                enable_automatic_punctuation=True,
                use_enhanced=True
            )

            response = self.speech_client.recognize(config=config, audio=audio)
            
            if not response.results:
                self.logger.info("No transcription results")
                return None

            transcript = response.results[0].alternatives[0].transcript
            confidence = response.results[0].alternatives[0].confidence

            self.logger.info(f"Transcribed: '{transcript}' with confidence: {confidence}")

            if confidence < 0.6:
                self.logger.info("Low confidence, skipping.")
                return None

            gpt_response = self.get_gpt_response(transcript)

            return {
                "transcript": transcript,
                "response": gpt_response,
                "confidence": confidence
            }

        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
            return None

    def get_gpt_response(self, query):
        try:
            openai.api_key = self.openai_api_key
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are {self.robot_name}, a helpful AI assistant. Provide clear, concise responses."
                    },
                    {
                        "role": "system",
                        "content": f"Available data context:\n{self.context_data}"
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            self.logger.error(f"GPT Error: {e}")
            return "Sorry, I couldn't process your request."

    def process_continuous_audio(self):
        audio_data = []
        silence_threshold = 500
        silence_frames = 0
        max_silence_frames = 20

        while self.is_listening:
            try:
                if not self.audio_queue.empty():
                    data = self.audio_queue.get()
                    audio_data.append(data)

                    audio_array = np.frombuffer(data, dtype=np.int16)
                    if np.abs(audio_array).mean() < silence_threshold:
                        silence_frames += 1
                    else:
                        silence_frames = 0

                    if silence_frames >= max_silence_frames and len(audio_data) > 0:
                        audio_chunk = np.concatenate(audio_data, axis=0)
                        transcript = self.process_audio_data(audio_chunk)
                        if transcript:
                            yield {"transcript": transcript["transcript"], "response": transcript["response"]}
                        audio_data = []
                        silence_frames = 0

                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error in continuous processing: {e}")
                yield {"error": str(e)}
