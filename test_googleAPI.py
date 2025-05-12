import os

from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

MAX_AUDIO_LENGTH_SECS = 8 * 60 * 60


def run_batch_recognize():
    # Instantiates a client.
    client = SpeechClient(
        client_options=ClientOptions(
            api_endpoint="europe-west4-speech.googleapis.com",
        ),
    )
    # The output path of the transcription result.
    gcs_output_folder = "gs://speech-to-text-albanian/transcripts"

    # The name of the audio file to transcribe:
    audio_gcs_uri = "gs://speech-to-text-albanian/audio-files/extracted_audios/20250403_161711.wav"

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

    output_config = cloud_speech.RecognitionOutputConfig(
        gcs_output_config=cloud_speech.GcsOutputConfig(uri=gcs_output_folder),
    )

    files = [cloud_speech.BatchRecognizeFileMetadata(uri=audio_gcs_uri)]

    request = cloud_speech.BatchRecognizeRequest(
        recognizer="projects/meta-triode-456910-n9/locations/europe-west4/recognizers/_",
        config=config,
        files=files,
        recognition_output_config=output_config,
    )
    operation = client.batch_recognize(request=request)
 
    print(operation)
    print("Waiting for operation to complete...")
    
    response = operation.result(timeout=3 * MAX_AUDIO_LENGTH_SECS)
    print(response)

run_batch_recognize()