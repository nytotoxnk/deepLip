from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.client_options import ClientOptions
from google.cloud import speech_v2
import random
import os
from google.api_core.exceptions import NotFound
import editing
from pydub import AudioSegment, silence
from moviepy.editor import VideoFileClip

# Google cloud data
PROJECT_ID = "890676014334"
LOCATION = "europe-west4"

# Chirp 2 is only available in certain locations
client_options_var = ClientOptions(api_endpoint="europe-west4-speech.googleapis.com")

# Initialize the client
client = speech_v2.SpeechClient(client_options=client_options_var)


recogniser = f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/albanian-recogniser"

def speech_to_text(path):

    # Creating a temporary audio file from the video
    audio_path = "temp_audio.wav"
    path.audio.write_audiofile(audio_path, fps=16000, logger=None)

    # Base name for the transcription file
    base_name = audio_path[:-4] + ".txt" # Removing the last 4 letters .mp4 from the video file

    try:
        config = speech_v2.RecognitionConfig(
            auto_decoding_config=speech_v2.AutoDetectDecodingConfig(),
            language_codes=["sq-AL"], 
            model="chirp_2",
            features=cloud_speech.RecognitionFeatures(
                enable_word_time_offsets=True, # this is not tested and good chance it does not work
            ),
        )
            
        request = speech_v2.RecognizeRequest(
            recognizer=recogniser,
            config=config,
            content=audio_path
        )
            
            # Transcribes the audio into text
        response = client.recognize(request=request)

        with open(base_name, "w", encoding="utf-8") as f:
            f.write(f"Transcript: {alternative.transcript}\nConfidence: {alternative.confidence}\n")

            # Going through the response from google speech to text API    
            for result in response.results:
                print(f"Transcript: {result.alternatives[0].transcript}")
                    # have to save the transcript somehow, make the translation and then do a text-to-voice clone
                print("\n Response --->",response)
                print("\n Response.results --->",response.results)
                alternative = result.alternatives[0]
                for word_info in alternative.words:
                    word = word_info.word
                    start = word_info.start_offset
                    end = word_info.end_offset
                    
                    start_time = start.seconds + start.nanos / 1e9
                    end_time = end.seconds + end.nanos / 1e9
                    
                    # wirting the timing for the words into the transcription text file
                    f.write(f"{word}: {start_time:.2f}-{end_time:.2f}\n")



    except Exception as e:
        print(f"Error: {e}")
            
        print("\nRecognizer not found, bad name or something...")
        
        
    # Remove the temp audio file after extracting it from the video
    os.remove(audio_path)


def transcribe_video(path):

    if os.path.isdir(path):
        print(f"Processing all video files in folder: {path}")
        video_files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov'))]
        for video_file in video_files:
            print(f"\n--- Processing video: {video_file} ---")
            speech_to_text(video_file)
    elif os.path.isfile(path) and path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
        print(f"Processing single video file: {path}")
        speech_to_text(path)
    else:
        print(f"Error: Invalid path '{path}'. Please provide a valid video file or a folder containing video files.")
