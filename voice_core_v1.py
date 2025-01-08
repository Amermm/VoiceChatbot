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

    def start_listening(self):
        """Start listening for audio"""
        self.is_listening = True
        self.logger.info("Started listening")
        return {"status": "started"}

    def stop_listening(self):
        """Stop listening for audio"""
        self.is_listening = False
        self.logger.info("Stopped listening")
        return {"status": "stopped"}

    def process_audio_data(self, audio_data):
        """Process audio data from client"""
        try:
            self.logger.info("Starting audio processing")
            if not audio_data:
                self.logger.error("No audio data received")
                return None
                
            # Decode base64 audio data
            try:
                decoded_audio = base64.b64decode(audio_data.split(',')[1])
                self.logger.info(f"Audio data decoded, size: {len(decoded_audio)}")
                
                # Skip processing if audio is too small
                if len(decoded_audio) < 10000:  # Skip very short audio
                    self.logger.info("Audio chunk too small, skipping")
                    return None
                    
            except Exception as e:
                self.logger.error(f"Error decoding audio: {e}")
                return None

            # Configure speech recognition
            audio = speech.RecognitionAudio(content=decoded_audio)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code="en-US",
                enable_automatic_punctuation=True,
                model="default",
                use_enhanced=True,
                enable_word_time_offsets=True,  # Get timing information
                speech_contexts=[{
                    "phrases": ["Royal", "help", "question", "thanks"],
                    "boost": 20.0
                }]
            )

            # Process with Google Speech-to-Text
            try:
                self.logger.info("Sending request to Google Speech-to-Text")
                response = self.speech_client.recognize(config=config, audio=audio)
                self.logger.info(f"Received response from Google Speech-to-Text: {response}")
                
                if not response.results:
                    self.logger.warning("No transcription results")
                    return None

                transcript = response.results[0].alternatives[0].transcript
                confidence = response.results[0].alternatives[0].confidence

                # Only process if confidence is high enough
                if confidence < 0.6:
                    self.logger.warning(f"Low confidence ({confidence}), skipping")
                    return None

                self.logger.info(f"Transcribed text: {transcript} (confidence: {confidence})")
                
                # Get GPT response
                gpt_response = self.get_gpt_response(transcript)
                return {"transcript": transcript, "response": gpt_response}

            except Exception as e:
                self.logger.error(f"Speech-to-Text error: {e}")
                return None

        except Exception as e:
            self.logger.error(f"Error in process_audio_data: {e}")
            return None

    def get_gpt_response(self, query):
        try:
            self.logger.info(f"Sending query to GPT: {query}")
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant named Royal. You provide concise, helpful responses."},
                    {"role": "user", "content": query}
                ],
                max_tokens=150,
                temperature=0.7
            )
            response_text = response.choices[0].message.content.strip()
            self.logger.info(f"GPT response: {response_text}")
            return response_text
        except Exception as e:
            self.logger.error(f"GPT Error: {e}")
            return "I apologize, but I'm having trouble processing your request right now."
