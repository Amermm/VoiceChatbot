import os
import openai
import pandas as pd
from google.cloud import speech
import logging
import json
import base64
import tempfile
from datetime import datetime

class VoiceChatBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Setup environment and APIs
        self.setup_environment()
        
        # Initialize components
        self.df = self._load_excel_data()
        self.speech_client = self._setup_speech_client()
        self.is_listening = False
        
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

    def start_listening(self):
        """Start listening session"""
        self.is_listening = True
        self.logger.info("Started listening")
        return {"status": "started"}

    def stop_listening(self):
        """Stop listening session"""
        self.is_listening = False
        self.logger.info("Stopped listening")
        return {"status": "stopped"}

    def process_audio_data(self, audio_data):
        """Process audio data from the browser"""
        if not audio_data:
            return None
            
        try:
            # Decode base64 audio data
            try:
                audio_content = base64.b64decode(audio_data.split(',')[1])
            except Exception as e:
                self.logger.error(f"Error decoding audio data: {e}")
                return None

            # Process with Google Speech-to-Text
            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code="en-US",
                enable_automatic_punctuation=True,
                use_enhanced=True
            )

            response = self.speech_client.recognize(config=config, audio=audio)
            
            if not response.results:
                return None
                
            transcript = response.results[0].alternatives[0].transcript
            self.logger.info(f"Transcribed: {transcript}")
            
            # Get GPT response
            gpt_response = self.get_gpt_response(transcript)
            
            return {
                "transcript": transcript,
                "response": gpt_response
            }

        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
            return None

async def get_gpt_response(self, query):
    """Get GPT response with error handling"""
    try:
        self.logger.info(f"Sending query to GPT: {query}")
        response = await openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"You are {self.robot_name}, a helpful data assistant. Provide concise responses."},
                {"role": "system", "content": f"Context data:\n{self.context_data}"},
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
        return "Sorry, I couldn't process your request."

def process_continuous_audio(self):
    """
    Generator function for processing continuous audio
    Each client will get their own instance of this generator
    """
    while self.is_listening:
        try:
            # Return empty result to keep connection alive
            yield "data: {}\n\n"
        except Exception as e:
            self.logger.error(f"Error in continuous processing: {e}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
