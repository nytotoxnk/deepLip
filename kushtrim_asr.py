from gradio_client import Client, handle_file

audio_path = 'extracted_audios\\20250403_161711.wav'

# kushtrim asr model api
# Works great for now, but will need to be tested more thoroughly.
# Takes a long time to transcribe, but the accuracy is great.


client = Client("Kushtrim/whisper-large-v3-turbo-shqip")
result = client.predict(
		inputs=handle_file(audio_path),
		api_name="/predict_1"
)
transcription = result['text']
print(transcription)

# technicaly should save the transcription to a file
# and then the transcription should be translated to target language.

"""
# voice cloning model api
# from testing this does not work, but also even the UI interface does not clone the voice 
# to the level that I want it to be.
# Will only be used if there are not better models available.

voice_client = Client("maitrix-org/Voila-demo")

reference_processing_result = voice_client.predict(
    ref_audio=handle_file(audio_path),
    api_name="/get_ref_embs"
)

tts_result = voice_client.predict(
		text="There is something I do not want to say to you who is someone not even related to me",
		api_name="/run_tts"
)
print(tts_result)
"""