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
processed_files = []
transcription_file = 'transcription_alb_long_audio_kushtrim.txt'

if os.path.exists(transcription_file):
	with open(transcription_file, 'r', encoding="utf-8") as f:
		for line in f:
			if ':' in line:
				filename = line.split(':', 1)[0]
				processed_files.append(filename)

# Check for duplicates
unique_processed_files = set(processed_files)
duplicates = []
for file in unique_processed_files:
	count = processed_files.count(file)
	if count > 1:
		duplicates.append((file, count))

print(f"Found {len(processed_files)} total entries in transcription file")
print(f"Found {len(unique_processed_files)} unique processed files")

if duplicates:
	print("\nDUPLICATE FILES FOUND:")
	for file, count in duplicates:
		print(f"  {file}: appears {count} times")
else:
	print("No duplicates found in transcription file")

# Get all files in the audio directory
audio_directory = 'full_length_extracted_audio'
if not os.path.exists(audio_directory):
	print(f"Audio directory '{audio_directory}' not found!")
	exit()

all_audio_files = [f for f in os.listdir(audio_directory) if f.endswith(('.wav', '.mp3', '.m4a', '.flac'))]
not_transcribed = [f for f in all_audio_files if f not in unique_processed_files]

print(f"\nTotal audio files in directory: {len(all_audio_files)}")
print(f"Files already transcribed: {len(unique_processed_files)}")
print(f"Files not yet transcribed: {len(not_transcribed)}")

if not_transcribed:
	print("\nFiles that have NOT been transcribed:")
	for file in not_transcribed:
		print(f"  - {file}")
	
	# Ask user if they want to proceed
	print(f"\nDo you want to transcribe the remaining {len(not_transcribed)} files? (Y/N): ", end="")
	user_input = input().strip().upper()
	
	if user_input != 'Y':
		print("Transcription cancelled.")
		exit()
	
	print("\nStarting transcription of remaining files...")
else:
	print("\nAll files have been transcribed!")
	exit()

# Going through the remaining files, transcribing them and writing to file.
for file in not_transcribed:
	file_path = os.path.join(audio_directory, file)

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