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
import tempfile

class VoiceChatBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Setup environment and APIs
        self.setup_environment()
        
        # Audio settings
        self.RATE = 16000
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        
        # Initialize components
        self.df = self._load_excel_data()
        self.speech_client = self._setup_speech_client()
        
        # Streaming components
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.p = None
        self.stream = None
        
        # Get robot name from environment
        self.robot_name = os.getenv('ROBOTNAME', 'Royal')

    def setup_environment(self):
        """Setup environment variables and APIs"""
        try:
            # Setup OpenAI
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not found in environment")
            openai.api_key = self.openai_api_key
            
            # Setup Google credentials
            google_creds_json = os.getenv('GOOGLE_CREDENTIALS')
            if not google_creds_json:
                raise ValueError("Google credentials not found in environment")
                
            # Write Google credentials to temporary file
            try:
                creds_dict = json.loads(google_creds_json)
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
                    json.dump(creds_dict, temp_file)
                    self.google_creds_path = temp_file.name
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.google_creds_path
                self.logger.info("Successfully setup Google credentials")
            except json.JSONDecodeError:
                raise ValueError("Invalid Google credentials JSON format")
                
            # Get database path
            self.database_path = os.getenv('DATABASE_EXCEL_PATH')
            if not self.database_path:
                raise ValueError("Database Excel path not found in environment")
                
        except Exception as e:
            self.logger.error(f"Environment setup error: {e}")
            raise

    def _setup_speech_client(self):
        """Initialize Google Speech client"""
        try:
            return speech.SpeechClient()
        except Exception as e:
            self.logger.error(f"Failed to initialize Speech client: {e}")
            raise

    def _load_excel_data(self):
        """Load Excel data with error handling"""
        try:
            df = pd.read_excel(self.database_path)
            for column in df.columns:
                if pd.api.types.is_numeric_dtype(df[column]):
                    df[column] = df[column].fillna(0)
                else:
                    df[column] = df[column].fillna('')
            self.context_data = df.astype(str).to_string(index=False, header=True)
            return df
        except Exception as e:
            self.logger.error(f"Error loading Excel: {e}")
            return pd.DataFrame()

    def audio_callback(self, in_data, frame_count, time_info, status):
        """Handle audio callback"""
        if self.is_listening:
            self.audio_queue.put(in_data)
        return (in_data, pyaudio.paContinue)

    def start_listening(self):
        """Start audio stream"""
        try:
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
            self.logger.info("Started listening")
            return {"status": "started"}
        except Exception as e:
            self.logger.error(f"Error starting audio stream: {e}")
            raise

    def stop_listening(self):
        """Stop audio stream"""
        try:
            self.is_listening = False
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.p:
                self.p.terminate()
            self.p = None
            self.stream = None
            self.logger.info("Stopped listening")
            return {"status": "stopped"}
        except Exception as e:
            self.logger.error(f"Error stopping audio stream: {e}")
            raise

    def process_audio_data(self, audio_data):
        """Process audio data with error handling"""
        if not audio_data:
            return None
            
        temp_filename = None
        try:
            # Create temporary WAV file
            temp_filename = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
                wf.setframerate(self.RATE)
                wf.writeframes(b''.join(audio_data))

            # Process with Google Speech-to-Text
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

        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
            return None
            
        finally:
            if temp_filename and os.path.exists(temp_filename):
                os.remove(temp_filename)

    def get_gpt_response(self, query):
        """Get GPT response with error handling"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are {self.robot_name}, a helpful data assistant. Provide concise responses."},
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
        """Text to speech with error handling"""
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
        """Process continuous audio stream"""
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

                    # Process after silence
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
