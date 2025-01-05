import os
import pyaudio
from google.cloud import speech
import openai  # OpenAI integration

# Set Google and OpenAI API keys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\MahmoudAmer\OneDrive - AIGC\AIGC Projects\RCJY\VoiceChatbot Project\intense-crow-445809-h2-5687324de8f9.json"
openai.api_key = "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"

# PyAudio settings
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms chunks

# Google Speech client
client = speech.SpeechClient()

def chat_with_gpt(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use your model (gpt-4 if needed)
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        print("GPT Error: ", e)
        return "Sorry, I couldn't process that."

def listen_and_transcribe():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("Listening... Speak into the microphone.")

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
        interim_results=False
    )

    responses = client.streaming_recognize(streaming_config, generate_audio())

    try:
        for response in responses:
            for result in response.results:
                transcript = result.alternatives[0].transcript
                print(f"You said: {transcript}")
                
                # Send to GPT and get a response
                gpt_response = chat_with_gpt(transcript)
                print(f"GPT: {gpt_response}")
    except Exception as e:
        print("Error: ", e)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    listen_and_transcribe()
