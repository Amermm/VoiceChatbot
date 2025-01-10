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
import tempfile

class VoiceChatBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load configuration from environment variables
        self.config = {
            'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
            'DATABASE_EXCEL_PATH': os.environ.get('DATABASE_EXCEL_PATH', '/app/SCADA TestData.xlsx'),
            'GOOGLE_CREDENTIALS': os.environ.get('GOOGLE_CREDENTIALS'),
            'ROBOTNAME': os.environ.get('ROBOTNAME', 'Royal')
        }
        
        # Setup environment
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
        openai.api_key = self.config['OPENAI_API_KEY']
        
        # Setup Google Cloud credentials
        if self.config['GOOGLE_CREDENTIALS']:
            fd, path = tempfile.mkstemp()
            with os.fdopen(fd, 'w') as temp:
                temp.write(self.config['GOOGLE_CREDENTIALS'])
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path

    def _load_excel_data(self):
        try:
            df = pd.read_excel(self.config['DATABASE_EXCEL_PATH'])
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

    def audio_callback(self, in_data, frame_count, time_info, status):
        if self.is_listening:
            self.audio_queue.put(in_data)
        return (in_data, pyaudio.paContinue)

    def start_listening(self):
        self.is_listening = True
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
            stream_callback=self.audio_callback
        )
        self.stream.start_stream()

    def stop_listening(self):
        self.is_listening = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
        self.p = None
        self.stream = None

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
                    {"role": "system", "content": f"You are {self.config['ROBOTNAME']}, a helpful data assistant. Provide concise responses."},
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

    def process_continuous_audio(self):
        audio_data = []
        silence_threshold = 500
        silence_frames = 0
        max_silence_frames = 20

        while self.is_listening:
            try:
                if self.audio_queue.qsize() > 0:
                    data = self.audio_queue.get()
                    audio_data.append(data)
                    
                    # Check for silence
                    audio_array = np.frombuffer(data, dtype=np.int16)
                    if np.abs(audio_array).mean() < silence_threshold:
                        silence_frames += 1
                    else:
                        silence_frames = 0

                    if silence_frames >= max_silence_frames and len(audio_data) > 0:
                        transcript = self.process_audio_data(audio_data)
                        if transcript:
                            response = self.get_gpt_response(transcript)
                            yield {"transcript": transcript, "response": response}
                            self.speak_response(response)
                        audio_data = []
                        silence_frames = 0
                else:
                    time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error in continuous processing: {e}")
                yield {"error": str(e)}
