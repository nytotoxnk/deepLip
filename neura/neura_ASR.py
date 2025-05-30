import os
import requests
import time
import json
from pathlib import Path

api_prefix = os.environ['NEURA_API_PREFIX']
api_key = os.environ['NEURA_API_KEY']  

# Audio folder path
audio_folder = 'full_length_extracted_audio'

# Check if folder exists
if not os.path.exists(audio_folder):
    print(f"Error: Audio folder not found at {audio_folder}")
    exit(1)

# Create necessary directories
Path("neura_json").mkdir(exist_ok=True)
Path("SRT").mkdir(exist_ok=True)

# File to track processed files and callback IDs
callback_tracking_file = 'neura_callback_tracking.json'
transcript_file = 'neura_transcript.txt'

# Load existing callback tracking
pending_callbacks = {}
processed_files = set()

if os.path.exists(callback_tracking_file):
    with open(callback_tracking_file, 'r', encoding='utf-8') as f:
        tracking_data = json.load(f)
        pending_callbacks = tracking_data.get('pending_callbacks', {})
        processed_files = set(tracking_data.get('processed_files', []))

# Check what files are already in transcript file
if os.path.exists(transcript_file):
    with open(transcript_file, 'r', encoding='utf-8') as f:
        for line in f:
            if ':' in line:
                filename = line.split(':', 1)[0]
                processed_files.add(filename)

print(f"Found {len(processed_files)} already processed files")
print(f"Found {len(pending_callbacks)} pending callbacks")

# URL for the API endpoint
url = f'{api_prefix}/stt'

# Optional: any other data you want to send along with the audio
other_data = {
    'word_timestamps': 'true'
}

def save_tracking_data():
    """Save tracking data to file"""
    tracking_data = {
        'pending_callbacks': pending_callbacks,
        'processed_files': list(processed_files)
    }
    with open(callback_tracking_file, 'w', encoding='utf-8') as f:
        json.dump(tracking_data, f, indent=2)

def send_audio_file(audio_file_path):
    """
    Send audio file to API and return callback ID
    """
    try:
        with open(audio_file_path, 'rb') as audio_file:
            files = {
                'audio': (os.path.basename(audio_file_path), audio_file, 'audio/wav')
            }

            headers = {
                'Authorization': f'Bearer {api_key}'
            }

            print(f"Sending audio file: {audio_file_path}")
            print(f"File size: {os.path.getsize(audio_file_path)} bytes")
            
            response = requests.post(url, files=files, data=other_data, headers=headers)
            response.raise_for_status()
            
            print("File uploaded successfully!")
            
            initial_response = response.json()
            print("Server response:", json.dumps(initial_response, indent=2))
            
            # Extract callback ID from response
            callback_id = None
            if 'callbackID' in initial_response:
                callback_id = initial_response['callbackID']
            elif 'callback_id' in initial_response:
                callback_id = initial_response['callback_id']
            elif 'id' in initial_response:
                callback_id = initial_response['id']
            
            return callback_id, initial_response
            
    except Exception as e:
        print(f"Error sending file {audio_file_path}: {e}")
        return None, None

def get_transcription_status(callback_id, result_format="json", max_attempts=30, wait_time=2):
    """
    Poll the callback status endpoint to get transcription results
    """
    status_url = f'{api_prefix}/callback/status?callbackId={callback_id}&result_as={result_format}'
    
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    
    for attempt in range(max_attempts):
        try:
            print(f"Polling attempt {attempt + 1}/{max_attempts} for format '{result_format}'...")
            response = requests.get(status_url, headers=headers)
            response.raise_for_status()
            
            # Handle different response formats
            if result_format == "json":
                result = response.json()
                print(f"Status response: {json.dumps(result, indent=2)}")
                
                # Check if transcription is complete
                if 'status' in result:
                    if result['status'] == 'completed' or result['status'] == 'success':
                        print(f"Transcription completed for format '{result_format}'!")
                        return result
                    elif result['status'] == 'failed' or result['status'] == 'error':
                        print(f"Transcription failed for format '{result_format}'!")
                        return result
                    elif result['status'] == 'processing' or result['status'] == 'pending':
                        print(f"Still processing... waiting {wait_time} seconds")
                        time.sleep(wait_time)
                        continue
                
                # If no status field, check for transcription data directly
                if 'transcription' in result or 'text' in result:
                    print(f"Transcription completed for format '{result_format}'!")
                    return result
            else:
                # For txt, srt, srt_words formats, response is text
                result_text = response.text
                print(f"Received {result_format} response (length: {len(result_text)} characters)")
                
                # Check if we got actual content (not an error message)
                if len(result_text) > 0 and not result_text.startswith('{"status"'):
                    print(f"Transcription completed for format '{result_format}'!")
                    return result_text
                elif result_text.startswith('{"status"'):
                    # Parse JSON status message
                    try:
                        status_data = json.loads(result_text)
                        if status_data.get('status') in ['processing', 'pending']:
                            print(f"Still processing... waiting {wait_time} seconds")
                            time.sleep(wait_time)
                            continue
                        elif status_data.get('status') in ['failed', 'error']:
                            print(f"Transcription failed for format '{result_format}'!")
                            return result_text
                    except json.JSONDecodeError:
                        pass
                
            # Continue polling if status is unclear
            print(f"Status unclear, continuing to poll... waiting {wait_time} seconds")
            time.sleep(wait_time)
            
        except requests.exceptions.RequestException as e:
            print(f"Error polling status: {e}")
            time.sleep(wait_time)
    
    print(f"Maximum polling attempts ({max_attempts}) reached for format '{result_format}'. Transcription may still be processing.")
    return None

def save_results(callback_id, audio_filename):
    """
    Get and save all transcription formats
    """
    results = {}
    
    # Get JSON result
    print("\n" + "="*50)
    print("Getting JSON result...")
    json_result = get_transcription_status(callback_id, "json")
    if json_result:
        results['json'] = json_result
        # Save JSON file
        json_filename = f"neura_json/{audio_filename}_{callback_id}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_result, f, indent=2, ensure_ascii=False)
        print(f"JSON result saved to: {json_filename}")
    
    # Get TXT result
    print("\n" + "="*50)
    print("Getting TXT result...")
    txt_result = get_transcription_status(callback_id, "txt")
    if txt_result:
        results['txt'] = txt_result
        # Append to transcript file
        with open(transcript_file, 'a', encoding='utf-8') as f:
            f.write(f"{audio_filename}:{txt_result}\n")
        print(f"TXT result appended to: {transcript_file}")
    
    # Get SRT result
    print("\n" + "="*50)
    print("Getting SRT result...")
    srt_result = get_transcription_status(callback_id, "srt")
    if srt_result:
        results['srt'] = srt_result
        # Save SRT file
        srt_filename = f"SRT/{audio_filename}_{callback_id}.srt"
        with open(srt_filename, 'w', encoding='utf-8') as f:
            f.write(srt_result)
        print(f"SRT result saved to: {srt_filename}")
    
    # Get SRT_WORDS result
    print("\n" + "="*50)
    print("Getting SRT_WORDS result...")
    srt_words_result = get_transcription_status(callback_id, "srt_words")
    if srt_words_result:
        results['srt_words'] = srt_words_result
        # Save SRT_WORDS file
        srt_words_filename = f"SRT/{audio_filename}_{callback_id}_words.srt"
        with open(srt_words_filename, 'w', encoding='utf-8') as f:
            f.write(srt_words_result)
        print(f"SRT_WORDS result saved to: {srt_words_filename}")
    
    return results

# Process pending callbacks first
print("\n" + "="*70)
print("PROCESSING PENDING CALLBACKS")
print("="*70)

for filename, callback_id in list(pending_callbacks.items()):
    print(f"\nProcessing pending callback for {filename} (ID: {callback_id})")
    
    try:
        all_results = save_results(callback_id, Path(filename).stem)
        
        if all_results and any(all_results.values()):
            print(f"Successfully processed pending callback for {filename}")
            processed_files.add(filename)
            del pending_callbacks[filename]
        else:
            print(f"Failed to get results for {filename}, keeping in pending")
            
    except Exception as e:
        print(f"Error processing pending callback for {filename}: {e}")

# Save updated tracking data
save_tracking_data()

# Get all audio files
audio_files = [f for f in os.listdir(audio_folder) 
               if f.lower().endswith(('.wav', '.mp3', '.m4a', '.flac', '.aac'))]

unprocessed_files = [f for f in audio_files if f not in processed_files]

print(f"\n" + "="*70)
print("FILE PROCESSING SUMMARY")
print("="*70)
print(f"Total audio files found: {len(audio_files)}")
print(f"Already processed: {len(processed_files)}")
print(f"Pending callbacks: {len(pending_callbacks)}")
print(f"Files to process: {len(unprocessed_files)}")

if unprocessed_files:
    print("\nFiles to be processed:")
    for file in unprocessed_files:
        print(f"  - {file}")
    
    print(f"\nDo you want to send {len(unprocessed_files)} files for transcription? (Y/N): ", end="")
    user_input = input().strip().upper()
    
    if user_input != 'Y':
        print("Processing cancelled.")
        exit()

# Process unprocessed files
print("\n" + "="*70)
print("SENDING NEW FILES FOR TRANSCRIPTION")
print("="*70)

wait_between_files = 5  # seconds to wait between file uploads

for i, filename in enumerate(unprocessed_files):
    audio_file_path = os.path.join(audio_folder, filename)
    
    print(f"\n[{i+1}/{len(unprocessed_files)}] Processing: {filename}")
    print("-" * 50)
    
    callback_id, response = send_audio_file(audio_file_path)
    
    if callback_id:
        print(f"Received callback ID: {callback_id}")
        pending_callbacks[filename] = callback_id
        save_tracking_data()
        print(f"Callback ID saved for {filename}")
    else:
        print(f"Failed to get callback ID for {filename}")
        continue
    
    # Wait before sending next file (except for the last one)
    if i < len(unprocessed_files) - 1:
        print(f"Waiting {wait_between_files} seconds before sending next file...")
        time.sleep(wait_between_files)

print("\n" + "="*70)
print("ALL FILES SENT!")
print("="*70)
print(f"Files sent for processing: {len(unprocessed_files)}")
print(f"Total pending callbacks: {len(pending_callbacks)}")
print("\nTo retrieve results, run this script again. It will automatically")
print("process any pending callbacks and retrieve transcriptions.")
print("\nPending files:")
for filename in pending_callbacks.keys():
    print(f"  - {filename}")