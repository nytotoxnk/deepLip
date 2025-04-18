from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.client_options import ClientOptions
from google.cloud import speech_v2
import random
import os
from google.api_core.exceptions import NotFound

# Works as of now.

PROJECT_ID = "890676014334"
LOCATION = "europe-west4"

client_options_var = ClientOptions(api_endpoint="europe-west4-speech.googleapis.com")

# Initialize the client
client = speech_v2.SpeechClient(client_options=client_options_var)

audio_folder = "dataset_2023/clips"
audio_files = [f for f in os.listdir(audio_folder)]

#Choosing a random audio file
if audio_files:
    selected_file = random.choice(audio_files)
    full_path = os.path.join(audio_folder, selected_file)
    print('File: ',full_path)
    # Reads a file as bytes
    with open(full_path, "rb") as f:
        audio_content = f.read()

recogniser = f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/albanian-recogniser"

# Don't check if the recognizer exists - just try to use it directly
# If the recognizer doesn't exist, the recognize call will fail anyway

try:
    config = speech_v2.RecognitionConfig(
        auto_decoding_config=speech_v2.AutoDetectDecodingConfig(),
        language_codes=["sq-AL"], 
        model="chirp_2"
    )
    
    request = speech_v2.RecognizeRequest(
        recognizer=recogniser,
        config=config,
        content=audio_content
    )
    
    # Transcribes the audio into text
    response = client.recognize(request=request)
    
    for result in response.results:
        print(f"Transcript: {result.alternatives[0].transcript}")
        
except Exception as e:
    print(f"Error: {e}")
    
    # If the error is that the recognizer doesn't exist, create it
    if "NOT_FOUND" in str(e) or "not found" in str(e).lower():
        print("Recognizer not found, creating...")
        try:
            parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
            recognizer = speech_v2.Recognizer(
                display_name="Albanian Speech Recognizer",
                default_recognition_config=speech_v2.RecognitionConfig(
                    language_codes=["sq-AL"],
                    model="chirp_2"
                )
            )
            
            operation = client.create_recognizer(
                parent=parent,
                recognizer_id="albanian-recogniser",
                recognizer=recognizer
            )
            
            result = operation.result()
            print(f"Created recognizer: {result.name}")
            print("Please run the script again to use the new recognizer")
        except Exception as create_error:
            print(f"Error creating recognizer: {create_error}")