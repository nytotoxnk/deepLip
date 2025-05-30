from gradio_client import Client, handle_file
import os
import time
import random
import soundfile  # For audio duration
import numpy as np # For selecting files by duration

# Function to get audio duration
def get_audio_duration(file_path):
	try:
		info = soundfile.info(file_path)
		return info.duration
	except Exception as e:
		print(f"Error getting duration for {file_path}: {e}")
		return None

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

	# Ask user if they want to run benchmarks
	print(f"\nDo you want to run benchmarking on a subset of these {len(not_transcribed)} files? (Y/N): ", end="")
	user_input_benchmark = input().strip().upper()

	if user_input_benchmark == 'Y':
		print("\n--- Starting Benchmarking --- ")
		
		# 1. Benchmark 5 random files
		num_random_files_to_benchmark = min(5, len(not_transcribed))
		if num_random_files_to_benchmark > 0:
			print(f"\nBenchmarking {num_random_files_to_benchmark} random files...")
			random_sample_for_benchmark = random.sample(not_transcribed, num_random_files_to_benchmark)
			for file in random_sample_for_benchmark:
				file_path = os.path.join(audio_directory, file)
				audio_duration = get_audio_duration(file_path)
				duration_str = f"{audio_duration:.2f}s" if audio_duration is not None else "N/A"
				print(f"  Benchmarking (Random): {file} (Duration: {duration_str})")
				
				start_time = time.time()
				client = Client("Kushtrim/whisper-large-v3-turbo-shqip")
				result = client.predict(
					inputs=handle_file(file_path),
					api_name="/predict_1"
				)
				end_time = time.time()
				api_time = end_time - start_time
				if isinstance(result, dict) and 'text' in result:
					print(f"    -> API Time: {api_time:.2f}s, Transcription snippet: {result['text'][:50]}...")
				else:
					print(f"    -> API Time: {api_time:.2f}s, Unexpected result format for {file}: {result}")
		else:
			print("\nNot enough files available to benchmark random files.")

		# 2. Benchmark files by audio duration
		print("\nGathering audio durations for benchmark selection...")
		files_with_durations = []
		for file in not_transcribed:
			file_path = os.path.join(audio_directory, file)
			duration = get_audio_duration(file_path)
			if duration is not None:
				files_with_durations.append({'name': file, 'duration': duration})
		
		if len(files_with_durations) > 0:
			files_with_durations.sort(key=lambda x: x['duration'])
			
			num_files_for_duration_benchmark = len(files_with_durations)
			indices_to_benchmark = []
			if num_files_for_duration_benchmark == 1:
				indices_to_benchmark = [0] # Shortest (and only)
			elif num_files_for_duration_benchmark == 2:
				indices_to_benchmark = [0, 1] # Shortest, Longest
			elif num_files_for_duration_benchmark == 3:
				indices_to_benchmark = [0, 1, 2] # Shortest, Middle, Longest
			elif num_files_for_duration_benchmark == 4:
				indices_to_benchmark = [0, 1, 2, 3] # Shortest, Q1, Q3, Longest (approx)
			elif num_files_for_duration_benchmark >= 5:
				indices_to_benchmark = [
					0,  # Shortest
					int(num_files_for_duration_benchmark * 0.25), # Not so short (25th percentile)
					int(num_files_for_duration_benchmark * 0.50), # Average (50th percentile)
					int(num_files_for_duration_benchmark * 0.75), # A bit longer (75th percentile)
					num_files_for_duration_benchmark - 1   # Longest
				]
				# Ensure unique indices, especially for small N
				indices_to_benchmark = sorted(list(set(indices_to_benchmark)))

			if indices_to_benchmark:
				print(f"\nBenchmarking {len(indices_to_benchmark)} files based on audio duration...")
				files_for_duration_benchmark = [files_with_durations[i] for i in indices_to_benchmark]

				for file_info in files_for_duration_benchmark:
					file = file_info['name']
					file_path = os.path.join(audio_directory, file)
					audio_duration = file_info['duration']
					print(f"  Benchmarking (Duration-based): {file} (Duration: {audio_duration:.2f}s)")

					start_time = time.time()
					client = Client("Kushtrim/whisper-large-v3-turbo-shqip")
					result = client.predict(
						inputs=handle_file(file_path),
						api_name="/predict_1"
					)
					end_time = time.time()
					api_time = end_time - start_time
					if isinstance(result, dict) and 'text' in result:
						print(f"    -> API Time: {api_time:.2f}s, Transcription snippet: {result['text'][:50]}...")
					else:
						print(f"    -> API Time: {api_time:.2f}s, Unexpected result format for {file}: {result}")
			else:
				print("\nNot enough files with valid durations to benchmark by duration.")
		else:
			print("\nCould not get durations for any files, skipping duration-based benchmark.")
		print("--- End Benchmarking ---")
	
	# Ask user if they want to proceed with full transcription
	print(f"\nDo you want to transcribe the remaining {len(not_transcribed)} files and save to file? (Y/N): ", end="")
	user_input_transcribe_all = input().strip().upper()
	
	if user_input_transcribe_all != 'Y':
		print("Transcription cancelled.")
		exit()
	
	print("\nStarting transcription of remaining files...")
else:
	print("\nAll files have been transcribed!")
	exit()

# Initialize the client once here, assuming the endpoint doesn't change.
# If different models/endpoints are needed, this might need to be re-evaluated.
client = Client("Kushtrim/whisper-large-v3-turbo-shqip")

# Going through the remaining files, transcribing them and writing to file.
for file in not_transcribed:
	file_path = os.path.join(audio_directory, file)

	print(f"Processing {file}...")
	start_transcribe_time = time.time() 
	result = client.predict(
		inputs=handle_file(file_path),
		api_name="/predict_1"
	)
	end_transcribe_time = time.time() 
	transcription_duration = end_transcribe_time - start_transcribe_time
	
	if isinstance(result, dict) and 'text' in result:
		transcription_text = result['text']
		print(f"Transcription: {transcription_text} (Took {transcription_duration:.2f}s)")
		
		# Append transcription to file
		with open(transcription_file, 'a', encoding="utf-8") as f:
			f.write(f"{file}:{transcription_text}\n")
	else:
		print(f"Error in transcription for {file}: Unexpected result format: {result} (Took {transcription_duration:.2f}s)")
		# Optionally, write an error marker to the file or skip writing
		with open(transcription_file, 'a', encoding="utf-8") as f:
			f.write(f"{file}:ERROR_UNEXPECTED_RESULT_FORMAT\n")