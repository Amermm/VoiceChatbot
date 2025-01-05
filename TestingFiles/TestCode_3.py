import os
from google.cloud import texttospeech

# Set the path to your JSON key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\MahmoudAmer\OneDrive - AIGC\AIGC Projects\RCJY\VoiceChatbot Project\intense-crow-445809-h2-5687324de8f9.json"

# Function: Text-to-Speech
def text_to_speech(text, output_file="output.mp3"):
    # Initialize Text-to-Speech client
    tts_client = texttospeech.TextToSpeechClient()

    # Configure TTS request
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",  # Specify the language code
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL  # Voice gender
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    # Call the API
    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # Save the audio to a file
    with open(output_file, "wb") as out:
        out.write(response.audio_content)
        print(f"Text-to-Speech audio saved to {output_file}")

# Function to Play Audio
def play_audio(file_path="output.mp3"):
    # Check if the platform supports audio playback
    import platform
    import subprocess

    if platform.system() == "Darwin":  # macOS
        subprocess.call(["afplay", file_path])
    elif platform.system() == "Linux":  # Linux
        subprocess.call(["aplay", file_path])
    elif platform.system() == "Windows":  # Windows
        subprocess.call(["start", file_path], shell=True)
    else:
        print("Audio playback is not supported on this platform.")

# Main Function
if __name__ == "__main__":
    while True:
        # Get user input from the terminal
        text_input = input("Enter the text you want to convert to speech (or type 'exit' to quit): ")

        if text_input.lower() == "exit":
            print("Goodbye!")
            break

        # Convert the text to speech
        text_to_speech(text_input)

        # Play the generated audio
        play_audio("output.mp3")
