from gradio_client import Client, handle_file


audio_path = 'extracted_audios\\20250403_161711.wav'

client = Client("Kushtrim/whisper-large-v3-turbo-shqip")
result = client.predict(
		inputs=handle_file(audio_path),
		api_name="/predict_1"
)
transcription = result['text']
print(transcription)

# technicaly should save the transcription to a file

voice_client = Client("maitrix-org/Voila-demo")

reference_processing_result = voice_client.predict(
    ref_audio=handle_file(audio_path),
    api_name="/get_ref_embs" # Or potentially "/get_ref_embs_1" - check the app details
)

tts_result = voice_client.predict(
		text=transcription,
		ref_embs=reference_processing_result,
		api_name="/run_tts"
)
print(tts_result)