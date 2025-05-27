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

# Read already processed files from the transcription file
processed_files = set()
transcription_file = 'transcription_alb_long_audio_kushtrim.txt'

if os.path.exists(transcription_file):
	with open(transcription_file, 'r', encoding="utf-8") as f:
		for line in f:
			if ':' in line:
				filename = line.split(':', 1)[0]
				processed_files.add(filename)

print(f"Found {len(processed_files)} already processed files")

# Going through all the files in folder, transcribing them and writing to file.
for file in os.listdir('full_length_extracted_audio'):
	
	# Skip files that have already been processed
	if file in processed_files:
		print(f"Skipping {file} - already processed")
		continue
	
	file_path = os.path.join('full_length_extracted_audio', file)

	print(f"Processing {file}...")
	client = Client("Kushtrim/whisper-large-v3-turbo-shqip")
	result = client.predict(
		inputs=handle_file(file_path),
		api_name="/predict_1"
	)
	print("Transcription: " + result)
	
	# Append transcription to file
	with open(transcription_file, 'a', encoding="utf-8") as f:
		f.write(f"{file}:{result}\n")