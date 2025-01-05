import os
import pyaudio
import openai
import pandas as pd
from google.cloud import speech

# Set Google and OpenAI API keys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\MahmoudAmer\OneDrive - AIGC\AIGC Projects\RCJY\VoiceChatbot Project\intense-crow-445809-h2-5687324de8f9.json"
openai.api_key = "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"

# PyAudio settings
RATE = 16000  # Sample rate
CHUNK = int(RATE / 10)  # 100ms chunks for audio input

# Load Excel Data (Your Excel file contains a table, not questions/answers)
# Make sure the Excel file path is correct
excel_file_path = r"C:\Users\MahmoudAmer\OneDrive - AIGC\AIGC Projects\RCJY\VoiceChatbot Project\TestDataBase.xlsx"
df = pd.read_excel(excel_file_path)

# Google Speech client
client = speech.SpeechClient()

def search_excel_for_answer(query):
    """Search the Excel file for relevant data based on the query."""
    # Split the query into words to look for specific information
    query_words = query.lower().split()

    # Search for matching rows in the entire DataFrame
    matching_rows = []
    for index, row in df.iterrows():
        row_data = " ".join(str(cell).lower() for cell in row)
        if any(word in row_data for word in query_words):
            matching_rows.append(row)

    # If matching rows are found, try to return the relevant data
    if matching_rows:
        # Let's assume the user is asking for a specific field, like "job", "age", etc.
        # We'll check if specific keywords are in the query to narrow down the response.
        for row in matching_rows:
            # Check for specific keywords like "job", "age", etc.
            if 'job' in query.lower():
                return row['Job'] if 'Job' in row else "Job information not found."
            elif 'age' in query.lower():
                return row['Age'] if 'Age' in row else "Age information not found."
            elif 'location' in query.lower():
                return row['Location'] if 'Location' in row else "Location information not found."
            elif 'experience' in query.lower():
                return row['Years of Experience'] if 'Years of Experience' in row else "Experience information not found."
            else:
                # Return a general answer if no specific keyword is found
                return str(row.to_dict())
    else:
        return "Sorry, I couldn't find relevant information in the database."

def listen_and_transcribe():
    """Listen to microphone input and transcribe using Google Speech API."""
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("Listening... Speak into the microphone.")

    # Streaming audio from microphone
    def generate_audio():
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            yield speech.StreamingRecognizeRequest(audio_content=data)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="en-US"
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=False  # No interim results, waits for final transcription
    )

    try:
        responses = client.streaming_recognize(streaming_config, generate_audio())
        for response in responses:
            for result in response.results:
                transcript = result.alternatives[0].transcript
                print(f"You said: {transcript}")
                
                # Send the transcribed text to search in the Excel file for a response
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
