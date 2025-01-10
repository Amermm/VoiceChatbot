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
import base64
import io
import tempfile

class VoiceChatBot:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        
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

        # Create temp directory for audio files
        self.temp_dir = tempfile.mkdtemp()

    def setup_environment(self):
        # Set OpenAI API key
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        # Setup Google Cloud credentials
        google_creds = os.environ.get('GOOGLE_CREDENTIALS')
        if google_creds:
            fd, path = tempfile.mkstemp()
            with os.fdopen(fd, 'w') as temp:
                temp.write(google_creds)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path

    def _load_excel_data(self):
        try:
            excel_path = os.environ.get('DATABASE_EXCEL_PATH', '/app/SCADA TestData.xlsx')
            df = pd.read_excel(excel_path)
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

    def process_audio_chunk(self, audio_data):
        """Process base64 encoded audio data."""
        try:
            self.logger.debug("Starting audio processing")
            
            # Decode base64 string
            audio_bytes = base64.b64decode(audio_data)
            
            # Save as temporary WAV file
            temp_wav = os.path.join(self.temp_dir, f'temp_{datetime.now().strftime("%Y%m%d_%H%M%S")}.wav')
            
            with wave.open(temp_wav, 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(self.RATE)
                wf.writeframes(audio_bytes)
            
            self.logger.debug("Created temporary WAV file")

            # Read the file for Google Speech-to-Text
            with open(temp_wav, 'rb') as audio_file:
                content = audio_file.read()

            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.RATE,
                language_code="en-US",
                enable_automatic_punctuation=True,
                use_enhanced=True
            )

            self.logger.debug("Sending to Google Speech-to-Text")
            response = self.speech_client.recognize(config=config, audio=audio)
            self.logger.debug(f"Received response: {response}")

            # Clean up temporary file
            try:
                os.remove(temp_wav)
            except:
                pass

            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                self.logger.info(f"Transcribed text: {transcript}")
                
                # Get GPT response
                gpt_response = self.get_gpt_response(transcript)
                return {
                    "transcript": transcript,
                    "response": gpt_response
                }
                
            self.logger.debug("No speech recognized")
            return None

        except Exception as e:
            self.logger.error(f"Error processing audio chunk: {str(e)}", exc_info=True)
            return {"error": str(e)}

    def get_gpt_response(self, query):
        try:
            robot_name = os.environ.get('ROBOTNAME', 'Royal')
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are {robot_name}, a helpful data assistant. Provide concise responses."},
                    {"role": "system", "content": f"Context data:\n{self.context_data}"},
                    {"role": "user", "content": query}
                ],
                max_tokens=100,
                temperature=0
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            self.logger.error(f"GPT Error: {str(e)}")
            return "Sorry, I couldn't process your request."

    def speak_response(self, response):
        """Convert text to speech using pyttsx3."""
        def tts_worker(response_text):
            try:
                engine = pyttsx3.init()
                engine.say(response_text)
                engine.runAndWait()
            except Exception as e:
                self.logger.error(f"TTS Error: {str(e)}")

        tts_thread = threading.Thread(target=tts_worker, args=(response,))
        tts_thread.daemon = True
        tts_thread.start()

    def __del__(self):
        """Cleanup temp directory on shutdown."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except:
            pass
