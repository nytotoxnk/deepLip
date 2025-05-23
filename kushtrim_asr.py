from gradio_client import Client, handle_file
import os
audio_path = 'extracted_audios\\20250403_161711.wav'

# kushtrim asr model api
# Works great for now, but will need to be tested more thoroughly.
# Takes a long time to transcribe, but the accuracy is great.

"""
# This is the original code for the transcription.

client = Client("Kushtrim/whisper-large-v3-turbo-shqip")
result = client.predict(
		inputs=handle_file(audio_path),
		api_name="/predict_1"
)
transcription = result['text']
print(transcription)

"""

# Going through all the files in folder, transcribing them and writing to file.
for file in os.listdir('prepared_dataset_audio'):
	
	file_path = os.path.join('prepared_dataset_audio', file)

	client = Client("Kushtrim/whisper-large-v3-turbo-shqip")
	result = client.predict(
		inputs=handle_file(file_path),
		api_name="/predict_1"
	)
	print("Transcription: " + result)
	
	# Append transcription to file
	with open('transcription_alb.txt', 'a', encoding="utf-8") as f:
		f.write(f"{file}:{result}\n")