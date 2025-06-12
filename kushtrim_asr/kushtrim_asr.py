from gradio_client import Client, handle_file
import os

# kushtrim asr model api
# Simplified version - processes all audio files in folder

# Get all files in the audio directory
audio_directory = 'full_length_extracted_audio'
if not os.path.exists(audio_directory):
	print(f"Audio directory '{audio_directory}' not found!")
	exit()

all_audio_files = [f for f in os.listdir(audio_directory) if f.endswith(('.wav', '.mp3', '.m4a', '.flac'))]

print(f"Total audio files in directory: {len(all_audio_files)}")

if len(all_audio_files) == 0:
	print("No audio files found in directory!")
	exit()

print(f"\nFound {len(all_audio_files)} audio files to transcribe:")
for file in all_audio_files:
	print(f"  - {file}")

# Ask user confirmation
print(f"\nProceed with transcription of {len(all_audio_files)} files? (Y/N): ", end="")
user_input = input().strip().upper()

if user_input != 'Y':
	print("Transcription cancelled.")
	exit()

# Initialize the client
client = Client("Kushtrim/whisper-large-v3-turbo-shqip")

# Transcribe files
transcription_file = '300h_transcription.txt'
print(f"\nStarting transcription...")
print("=" * 80)

for i, file in enumerate(all_audio_files, 1):
	file_path = os.path.join(audio_directory, file)
	
	# Extract video_id (filename without extension)
	video_id = os.path.splitext(file)[0]

	print(f"\n[{i}/{len(all_audio_files)}] Processing: {file}")
	
	try:
		result = client.predict(
			inputs=handle_file(file_path),
			api_name="/predict_1"
		)
		
		# Handle different result formats
		transcription_text = None
		if isinstance(result, dict) and 'text' in result:
			transcription_text = result['text']
		elif isinstance(result, str):
			transcription_text = result
		else:
			print(f"Error in transcription: Unexpected result format: {result}")
			with open(transcription_file, 'a', encoding="utf-8") as f:
				f.write(f"{video_id}:ERROR_UNEXPECTED_RESULT_FORMAT\n")
			continue
		
		print(f"Transcription: {transcription_text[:100]}{'...' if len(transcription_text) > 100 else ''}")
		
		# Write transcription to file in requested format: video_id:text_transcription
		with open(transcription_file, 'a', encoding="utf-8") as f:
			f.write(f"{video_id}:{transcription_text}\n")
				
	except Exception as e:
		print(f"Error processing {file}: {e}")
		with open(transcription_file, 'a', encoding="utf-8") as f:
			f.write(f"{video_id}:ERROR_PROCESSING_FILE\n")
	
	print("-" * 40)

print(f"\nTranscription completed! Results saved to: {transcription_file}")