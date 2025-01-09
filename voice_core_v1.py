import os
import openai
import pandas as pd
from google.cloud import speech
import logging
import json
from datetime import datetime
import tempfile

class VoiceChatBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load environment variables
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.google_credentials_json = os.environ.get("GOOGLE_CREDENTIALS")
        self.database_excel_path = os.environ.get("DATABASE_EXCEL_PATH")
        self.robot_name = os.environ.get("ROBOTNAME", "VoiceBot")
        
        # Initialize components
        openai.api_key = self.openai_api_key
        self.setup_google_credentials()
        self.df = self._load_excel_data()
        self.speech_client = speech.SpeechClient()
        
        # Audio settings for Google Speech-to-Text
        self.RATE = 16000
        self.CHANNELS = 1

    def setup_google_credentials(self):
        """Setup Google Cloud credentials from environment variable."""
        try:
            # Create temporary credentials file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
                temp_file.write(self.google_credentials_json)
                temp_file_path = temp_file.name
            
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file_path
            self.logger.info("Google credentials setup successfully")
        except Exception as e:
            self.logger.error(f"Error setting up Google credentials: {e}")
            raise

    def _load_excel_data(self):
        """Load and preprocess Excel data."""
        try:
            df = pd.read_excel(self.database_excel_path)
            
            # Handle different column types appropriately
            for column in df.columns:
                if df[column].dtype in ['float64', 'int64']:
                    df[column] = df[column].fillna(0)
                else:
                    df[column] = df[column].fillna('')
            
            # Pre-process context data for GPT
            self.context_data = df.astype(str).to_string(index=False, header=True)
            self.logger.info("Excel data loaded successfully")
            return df
        except Exception as e:
            self.logger.error(f"Error loading Excel data: {e}")
            return pd.DataFrame()

    def process_audio_data(self, audio_data):
        """Process audio data and return transcript."""
        if not audio_data:
            return None

        try:
            # Create audio configuration
            audio = speech.RecognitionAudio(content=audio_data)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.RATE,
                language_code="en-US",
                enable_automatic_punctuation=True,
                use_enhanced=True
            )

            # Perform the transcription
            response = self.speech_client.recognize(config=config, audio=audio)

            # Process the response
            for result in response.results:
                transcript = result.alternatives[0].transcript.strip()
                self.logger.info(f"Transcribed text: {transcript}")
                return transcript

            return None

        except Exception as e:
            self.logger.error(f"Error in speech recognition: {e}")
            return None

    def get_gpt_response(self, query):
        """Get response from GPT based on the query and context."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are {self.robot_name}, a helpful data assistant. "
                                 "Provide concise and accurate responses based on the data provided."
                    },
                    {
                        "role": "system",
                        "content": f"Context data:\n{self.context_data}"
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                max_tokens=150,
                temperature=0
            )
            
            gpt_response = response.choices[0].message['content'].strip()
            self.logger.info(f"GPT Response: {gpt_response}")
            return gpt_response
            
        except Exception as e:
            self.logger.error(f"Error getting GPT response: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"

    def validate_audio_data(self, audio_data):
        """Validate the received audio data."""
        try:
            # Check if audio data is not empty
            if not audio_data or len(audio_data) == 0:
                return False

            # Check if size is within reasonable limits (e.g., 10MB)
            if len(audio_data) > 10 * 1024 * 1024:
                return False

            return True
        except Exception as e:
            self.logger.error(f"Error validating audio data: {e}")
            return False

    def cleanup(self):
        """Cleanup temporary files and resources."""
        try:
            # Remove temporary credentials file if it exists
            creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if creds_path and os.path.exists(creds_path):
                os.remove(creds_path)
                self.logger.info("Cleaned up temporary credentials file")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
