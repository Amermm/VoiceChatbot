import os
import pyaudio
import openai
import pandas as pd
from google.cloud import speech
import time

# Load configuration from VCB_Config.xlsx
config_path = 'VCB_Config.xlsx'
config = pd.read_excel(config_path, index_col=0, header=None).iloc[:, 0].to_dict()

# Extract dynamic values
excel_file_path = config.get('DatabaseExcel_path', 'default_path.xlsx')
openai.api_key = config.get('OpenAI_key', 'default_openai_key')
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.get('GoogleSST_Key_path', '')
robot_name = config.get('RobotName', 'Assistant')

# PyAudio settings
RATE = 16000
CHUNK = int(RATE / 10)

# Load and preprocess Excel Data
try:
    df = pd.read_excel(excel_file_path)
    df.fillna("", inplace=True)  # Fill empty cells with empty strings
    df = df.astype(str)  # Ensure all data is string for consistent matching
except Exception as e:
    print(f"Error loading Excel file: {e}")
    df = pd.DataFrame()  # Fallback to empty DataFrame if loading fails

# Google Speech client
client = speech.SpeechClient()

def ask_gpt4(query, context_data):
    """Send the query to GPT-4 for intelligent parsing."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Use GPT-4 for smarter language understanding
            messages=[
                {"role": "system", "content": f"You are a data assistant. Use the provided data and answer queries accurately and concisely."},
                {"role": "system", "content": f"Here is the data:\n{context_data}"},
                {"role": "user", "content": query}
            ],
            max_tokens=150,
            temperature=0
        )
        gpt_response = response.choices[0].message['content'].strip()
        return gpt_response
    except Exception as e:
        print(f"GPT-4 Error: {e}")
        return "Error communicating with GPT-4."

def preprocess_context_data(df):
    """Convert DataFrame to a string for GPT-4 context."""
    context_data = df.to_string(index=False, header=True)
    return context_data

def search_excel_for_answer(query):
    """Search the Excel file dynamically based on the query."""
    # Preprocess data into a format GPT-4 can understand
    context_data = preprocess_context_data(df)

    # Use GPT-4 to process the query and infer the intent
    gpt_response = ask_gpt4(query, context_data)
    if gpt_response:
        print(f"[DEBUG] GPT-4 Response: {gpt_response}")
        return f"{robot_name}: {gpt_response}"
    return f"{robot_name}: Sorry, I couldn't process your request."

def listen_and_transcribe():
    """Listen to microphone input and transcribe using Google Speech API."""
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print(f"{robot_name} is listening... Speak into the microphone.")

    silence_duration = 3  # Seconds of silence before processing
    max_silence_frames = int((silence_duration * RATE) / CHUNK)
    silence_counter = 0

    def generate_audio():
        """Stream audio data from the microphone to the API."""
        nonlocal silence_counter
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            if is_silent(data):
                silence_counter += 1
                if silence_counter > max_silence_frames:
                    break  # Stop listening after enough silence
            else:
                silence_counter = 0  # Reset counter if speech detected
            yield speech.StreamingRecognizeRequest(audio_content=data)

    def is_silent(audio_chunk):
        """Check if the audio chunk contains silence."""
        return max(audio_chunk) < 100  # Adjust this threshold if needed

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="en-US"
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=False  # Wait for final transcription
    )

    try:
        while True:
            responses = client.streaming_recognize(streaming_config, generate_audio())
            for response in responses:
                for result in response.results:
                    transcript = result.alternatives[0].transcript.strip().lower()
                    print(f"You said: {transcript}")
                    
                    # Check for the exit command
                    if "exit" in transcript:
                        print(f"{robot_name}: Exiting the program. Goodbye!")
                        return  # Stop the function and exit
                    
                    # Process the query
                    excel_response = search_excel_for_answer(transcript)
                    print(f"Response: {excel_response}")
    except Exception as e:
        print("Error: ", e)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    listen_and_transcribe()
