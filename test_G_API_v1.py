# Import the Speech-to-Text client library
from google.cloud import speech
from google.protobuf import wrappers_pb2

# Instantiates a client
client=speech.SpeechClient()

# The name of the audio file to transcribe
gcs_uri="gs://speech-to-text-albanian/audio-files/20250403_161711.wav"

def transcribe_speech():
  audio=speech.RecognitionAudio(uri=gcs_uri)

  config=speech.RecognitionConfig(
  encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
  sample_rate_hertz=16000,
  language_code="sq-AL",
  model="long",
  audio_channel_count=2,
  enable_word_confidence=True,
  enable_word_time_offsets=True,
  )

  # Detects speech in the audio file
  operation=client.long_running_recognize(config=config, audio=audio)

  print("Waiting for operation to complete...")
  response=operation.result(timeout=90)

  for result in response.results:
    print("Transcript: {}".format(result.alternatives[0].transcript))

transcribe_speech()