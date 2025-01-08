import os
import openai
import pandas as pd
import speech_recognition as sr
from google.cloud import speech
import logging
import threading
import pyttsx3


class VoiceChatBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Load configuration from environment variables
        self.setup_environment()

        # Initialize components
        self.df = self._load_excel_data()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.speech_client = speech.SpeechClient()
        self.is_listening = False

    def setup_environment(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.google_credentials = os.getenv('GOOGLE_CREDENTIALS')
        self.database_excel_path = os.getenv('DATABASE_EXCEL_PATH')
        self.robot_name = os.getenv('ROBOTNAME', 'AI Assistant')

        # Write GOOGLE_CREDENTIALS to a file
        credentials_path = "/tmp/google_credentials.json"
        with open(credentials_path, "w") as cred_file:
            cred_file.write(self.google_credentials)

        # Set Google Application Credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

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

    def start_listening(self):
        """Start listening for audio."""
        if self.is_listening:
            self.logger.warning("Already listening.")
            return

        self.is_listening = True
        self.logger.info("Listening started.")
        threading.Thread(target=self.listen_and_process, daemon=True).start()

    def stop_listening(self):
        """Stop listening for audio."""
        self.is_listening = False
        self.logger.info("Listening stopped.")

    def listen_and_process(self):
        """Continuously listen to the microphone and process audio."""
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            self.logger.info("Microphone ready for input.")

            while self.is_listening:
                try:
                    self.logger.info("Listening for speech...")
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    transcript = self.recognizer.recognize_google(audio)
                    self.logger.info(f"Transcribed: {transcript}")

                    # Generate a response using GPT
                    response = self.get_gpt_response(transcript)
                    self.logger.info(f"Response: {response}")

                    # Speak the response
                    self.speak_response(response)
                except sr.WaitTimeoutError:
                    self.logger.warning("Listening timed out, no speech detected.")
                except sr.UnknownValueError:
                    self.logger.error("Could not understand the audio.")
                except sr.RequestError as e:
                    self.logger.error(f"SpeechRecognition API error: {e}")
                except Exception as e:
                    self.logger.error(f"Error during audio processing: {e}")

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

    def speak_response(self, response):
        """Convert text to speech using pyttsx3."""
        def tts_worker(response_text):
            try:
                engine = pyttsx3.init()
                engine.say(response_text)
                engine.runAndWait()
            except Exception as e:
                self.logger.error(f"TTS Error: {e}")

        threading.Thread(target=tts_worker, args=(response,), daemon=True).start()
