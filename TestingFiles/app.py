from flask import Flask, render_template, request, jsonify
import azure.cognitiveservices.speech as speechsdk
import pandas as pd

app = Flask(__name__)

# Load Config from Excel
config = pd.read_excel('VCB_Config.xlsx', sheet_name='Settings')
config_dict = dict(zip(config['Key'], config['Value']))

speech_key = config_dict['speech_key']
service_region = config_dict['service_region']
language = config_dict['language']
database_excel_path = config_dict['DatabaseExcel_path']

# Azure STT Setup
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_recognition_language = language
audio_config = speechsdk.AudioConfig(use_default_microphone=True)

data = pd.read_excel(database_excel_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/voice', methods=['POST'])
def voice_recognition():
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    result = speech_recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        question = result.text
        print(f"User asked: {question}")
        response = handle_question(question)
        return jsonify({'response': response})
    else:
        return jsonify({'response': "تعذر التعرف على الصوت"})

def handle_question(question):
    # Step 1: Search for direct matches
    match = data[data['Question'].str.contains(question, case=False, na=False)]
    
    if not match.empty:
        return match['Answer'].values[0]
    
    # Step 2: Handle ambiguity (PIT case example)
    if "PIT" in question:
        return "ماهو رقم ال PIT المقصود؟"
    
    return "عذرًا، لم أفهم السؤال"

if __name__ == '__main__':
    app.run(debug=True)
