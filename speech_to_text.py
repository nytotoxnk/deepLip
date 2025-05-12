

"""
DOES NOT WORK AT ALL, VERY BAD TRANSCRIPTION QUALITY DO NOT USE

"""

import os

from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

PROJECT_ID = "890676014334"
LOCATION = "europe-west4"
MAX_AUDIO_LENGTH_SECS = 8 * 60 * 60
# Chirp 2 is only available in certain locations
client_options_var = ClientOptions(api_endpoint="europe-west4-speech.googleapis.com")

# Initialize the client
client = SpeechClient(client_options=client_options_var)
recogniser = f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/albanian-recogniser"

def transcribe_audio_file(audio_path, client, recogniser, base_name):
    # Read file as bytes to send to Google API
    try:
        with open(audio_path, "rb") as f:
            audio_content = f.read()
    except Exception as e:
        print(f"Error reading file {audio_path}: {e}")
        return
    
    try:
        config = cloud_speech.RecognitionConfig(
            explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                audio_channel_count=2
            ),
            features=cloud_speech.RecognitionFeatures(
                enable_word_confidence=True,
                enable_word_time_offsets=True,
            ),
            model="chirp_2",
            language_codes=["sq-AL"],
        )
                
        request = cloud_speech.RecognizeRequest(
            recognizer=recogniser,
            config=config,
            content=audio_content
        )
                
        # Transcribes the audio into text
        operation = client.long_running_recognize(request=request)
        #print(operation)

        response = operation.result(timeout=3 * MAX_AUDIO_LENGTH_SECS)
        print(response)


        if response.results:
           top_alternative = response.results[0].alternatives[0]
           confidence = top_alternative.confidence
           transcript = top_alternative.transcript

           print(f"Transcript: {transcript}")
           print(f"Confidence: {confidence}")

        #   with open(base_name, "a", encoding="utf-8") as f:
        #       f.write(f"{audio_path}:{confidence}:{transcript}\n")
        else:
            print(f"No transcription results for {audio_path}")

    except Exception as e:
        print(f"Error transcribing {audio_path}: {e}")

transcribe_audio_file("extracted_audios\\20250403_161711.wav", client, recogniser, "transcription_alb_test.txt")