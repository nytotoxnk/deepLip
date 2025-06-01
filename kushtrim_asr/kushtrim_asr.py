from gradio_client import Client, handle_file
import os
import time
import random
import subprocess  # For ffmpeg duration detection
import json  # For parsing ffmpeg output
import numpy as np # For selecting files by duration

# Function to get audio duration using ffmpeg
def get_audio_duration(file_path):
	try:
		# Use ffprobe (part of ffmpeg) to get duration
		result = subprocess.run([
			'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format',
			file_path
		], capture_output=True, text=True, check=True)
		
		data = json.loads(result.stdout)
		duration = float(data['format']['duration'])
		return duration
	except (subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError) as e:
		print(f"Error getting duration for {file_path}: {e}")
		return None

# kushtrim asr model api
# Works great for now, but will need to be tested more thoroughly.
# Takes a long time to transcribe, but the accuracy is great.

# Get all files in the audio directory
audio_directory = 'full_length_extracted_audio'
if not os.path.exists(audio_directory):
	print(f"Audio directory '{audio_directory}' not found!")
	exit()

all_audio_files = [f for f in os.listdir(audio_directory) if f.endswith(('.wav', '.mp3', '.m4a', '.flac'))]

print(f"Total audio files in directory: {len(all_audio_files)}")

if len(all_audio_files) < 10:
	print(f"Not enough files to select 10 total (7 random + 3 specific). Found only {len(all_audio_files)} files.")
	exit()

# Get durations for all files
print("Getting audio durations for all files...")
files_with_durations = []
for file in all_audio_files:
	file_path = os.path.join(audio_directory, file)
	duration = get_audio_duration(file_path)
	if duration is not None:
		files_with_durations.append({'name': file, 'duration': duration})

if len(files_with_durations) < 10:
	print(f"Not enough files with valid durations. Found only {len(files_with_durations)} files with valid durations.")
	exit()

# Sort by duration for selecting shortest, average, longest
files_with_durations.sort(key=lambda x: x['duration'])

# Select 3 specific files based on duration
shortest_file = files_with_durations[0]
longest_file = files_with_durations[-1]
average_index = len(files_with_durations) // 2
average_file = files_with_durations[average_index]

specific_files = [shortest_file, average_file, longest_file]
specific_file_names = [f['name'] for f in specific_files]

# Select 7 random files (excluding the 3 specific ones)
available_for_random = [f for f in files_with_durations if f['name'] not in specific_file_names]
random_files = random.sample(available_for_random, min(7, len(available_for_random)))

# Combine all files to transcribe
files_to_transcribe = specific_files + random_files

print(f"\nSelected files for transcription:")
print(f"Specific files based on duration:")
print(f"  - Shortest: {shortest_file['name']} ({shortest_file['duration']:.2f}s)")
print(f"  - Average: {average_file['name']} ({average_file['duration']:.2f}s)")
print(f"  - Longest: {longest_file['name']} ({longest_file['duration']:.2f}s)")
print(f"Random files ({len(random_files)}):")
for file_info in random_files:
	print(f"  - {file_info['name']} ({file_info['duration']:.2f}s)")

print(f"\nTotal files to transcribe: {len(files_to_transcribe)}")

# Ask user confirmation
print(f"\nProceed with transcription of {len(files_to_transcribe)} files? (Y/N): ", end="")
user_input = input().strip().upper()

if user_input != 'Y':
	print("Transcription cancelled.")
	exit()

# Initialize the client
client = Client("Kushtrim/whisper-large-v3-turbo-shqip")

# Transcribe files
transcription_file = 'retranscription_results.txt'
print(f"\nStarting transcription...")
print("=" * 80)

for i, file_info in enumerate(files_to_transcribe, 1):
	file = file_info['name']
	audio_duration = file_info['duration']
	file_path = os.path.join(audio_directory, file)

	print(f"\n[{i}/{len(files_to_transcribe)}] Processing: {file}")
	print(f"Audio Length: {audio_duration:.2f}s")
	
	start_transcribe_time = time.time() 
	result = client.predict(
		inputs=handle_file(file_path),
		api_name="/predict_1"
	)
	end_transcribe_time = time.time() 
	transcription_duration = end_transcribe_time - start_transcribe_time
	
	print(f"Transcription Time: {transcription_duration:.2f}s")
	
	if isinstance(result, dict) and 'text' in result:
		transcription_text = result['text']
		print(f"Transcription: {transcription_text[:100]}{'...' if len(transcription_text) > 100 else ''}")
		
		# Append transcription to file
		with open(transcription_file, 'a', encoding="utf-8") as f:
			f.write(f"{file} (Duration: {audio_duration:.2f}s, Transcription Time: {transcription_duration:.2f}s): {transcription_text}\n")
	else:
		print(f"Error in transcription: Unexpected result format: {result}")
		with open(transcription_file, 'a', encoding="utf-8") as f:
			f.write(f"{file} (Duration: {audio_duration:.2f}s, Transcription Time: {transcription_duration:.2f}s): ERROR_UNEXPECTED_RESULT_FORMAT\n")
	
	print("-" * 40)

print(f"\nTranscription completed! Results saved to: {transcription_file}")