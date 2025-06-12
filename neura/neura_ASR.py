import os
import requests
import time
import json
from pathlib import Path
import argparse
import sys

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Neura ASR - Automatic Speech Recognition Processing Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python neura_ASR.py                    # Interactive mode - asks for confirmation
  python neura_ASR.py --auto             # Automatic mode - processes new files without confirmation
  python neura_ASR.py -a                 # Same as --auto (short form)
  python neura_ASR.py --check-only       # Only check for new files, don't process
  python neura_ASR.py --status           # Show current processing status
  python neura_ASR.py --retrieve-results # Only retrieve pending transcription results
  python neura_ASR.py --folder /path/to/audio --status    # Check status for specific folder
  python neura_ASR.py --folder /path/to/audio --retrieve-results  # Get results for specific folder

This script automatically detects new audio files in the specified folder and
avoids processing duplicates by maintaining folder-specific tracking files.

WORKFLOW:
  1. Send files: python neura_ASR.py --folder /your/folder --auto
  2. Retrieve results: python neura_ASR.py --folder /your/folder --retrieve-results
        """
    )
    
    parser.add_argument('--auto', '-a', 
                       action='store_true',
                       help='Automatically process new files without user confirmation')
    
    parser.add_argument('--check-only', 
                       action='store_true',
                       help='Only check for new files and show status, do not process')
    
    parser.add_argument('--status', 
                       action='store_true',
                       help='Show current processing status and exit')
    
    parser.add_argument('--retrieve-results', 
                       action='store_true',
                       help='Retrieve and save pending transcription results only')
    
    parser.add_argument('--folder', 
                       default='full_length_extracted_audio',
                       help='Audio folder path (default: full_length_extracted_audio)')
    
    return parser.parse_args()

# Parse command line arguments
args = parse_arguments()

api_prefix = os.environ.get('NEURA_API_PREFIX')
api_key = os.environ.get('NEURA_API_KEY')

# Check environment variables
if not api_prefix or not api_key:
    print("Error: Required environment variables not set:")
    if not api_prefix:
        print("  - NEURA_API_PREFIX")
    if not api_key:
        print("  - NEURA_API_KEY")
    print("\nPlease set these environment variables and try again.")
    exit(1)

# Audio folder path
audio_folder = args.folder

# Check if folder exists
if not os.path.exists(audio_folder):
    print(f"Error: Audio folder not found at {audio_folder}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Make sure the audio folder exists or use --folder to specify a different path.")
    exit(1)

# Create folder-specific tracking file names
folder_name = os.path.basename(os.path.normpath(audio_folder))
safe_folder_name = "".join(c for c in folder_name if c.isalnum() or c in ('-', '_')).rstrip()
if not safe_folder_name:
    safe_folder_name = "default"

# File to track processed files and callback IDs
callback_tracking_file = f'neura_callback_tracking_{safe_folder_name}.json'

# Check for custom output files from environment variables
custom_output = os.environ.get('NEURA_OUTPUT_FILE')
if custom_output:
    # Use custom output file names based on the provided file
    base_name = os.path.splitext(custom_output)[0]
    transcript_file = custom_output
    srt_file = f'{base_name}_srt.txt'
    callback_tracking_file = f'{base_name}_callback_tracking.json'
    print(f"Using custom output files: {transcript_file}, {srt_file}")
else:
    # Use folder-specific file names
    transcript_file = f'hard_script_transcriptions_neura_{safe_folder_name}.txt'
    srt_file = f'hard_script_srt_neura_{safe_folder_name}.txt'

print(f"Using tracking file: {callback_tracking_file}")
print(f"Output files: {transcript_file}, {srt_file}")

def load_tracking_data():
    """Load existing callback tracking and processed files"""
    pending_callbacks = {}
    processed_files = set()
    
    # Load from tracking file
    if os.path.exists(callback_tracking_file):
        try:
            with open(callback_tracking_file, 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)
                pending_callbacks = tracking_data.get('pending_callbacks', {})
                processed_files = set(tracking_data.get('processed_files', []))
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Error reading tracking file: {e}")
            print("Starting with empty tracking data...")
    
    # Cross-check with transcript file to ensure consistency
    if os.path.exists(transcript_file):
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if ':' in line:
                        filename = line.split(':', 1)[0].strip()
                        if filename:  # Only add non-empty filenames
                            processed_files.add(filename)
        except Exception as e:
            print(f"Warning: Error reading transcript file: {e}")
    
    return pending_callbacks, processed_files

def get_audio_files():
    """Get all audio files from the audio folder"""
    supported_extensions = ('.wav', '.mp3', '.m4a', '.flac', '.aac', '.ogg', '.wma')
    try:
        audio_files = [f for f in os.listdir(audio_folder) 
                      if f.lower().endswith(supported_extensions) and os.path.isfile(os.path.join(audio_folder, f))]
        return sorted(audio_files)  # Sort for consistent processing order
    except Exception as e:
        print(f"Error reading audio folder: {e}")
        return []

def find_new_files(audio_files, processed_files, pending_callbacks):
    """Find new files that haven't been processed or are pending"""
    all_tracked_files = processed_files.union(set(pending_callbacks.keys()))
    new_files = [f for f in audio_files if f not in all_tracked_files]
    return sorted(new_files)

# Load existing callback tracking
pending_callbacks, processed_files = load_tracking_data()

print(f"Found {len(processed_files)} already processed files")
print(f"Found {len(pending_callbacks)} pending callbacks")

# Handle retrieve-results-only request
if args.retrieve_results:
    if not pending_callbacks:
        print("No pending callbacks found. Nothing to retrieve.")
        exit(0)
    
    print(f"\n" + "="*70)
    print("RETRIEVING PENDING RESULTS ONLY")
    print("="*70)
    print(f"Pending callbacks to process: {len(pending_callbacks)}")
    
    for filename in sorted(pending_callbacks.keys()):
        print(f"  ⏳ {filename} (ID: {pending_callbacks[filename]})")
    
    print(f"\nProceed with retrieving {len(pending_callbacks)} pending results? (Y/N): ", end="")
    user_input = input().strip().upper()
    
    if user_input != 'Y':
        print("Retrieval cancelled.")
        exit(0)
    
    # Process pending callbacks only
    print("\n" + "="*70)
    print("PROCESSING PENDING CALLBACKS")
    print("="*70)

    for filename, callback_id in list(pending_callbacks.items()):
        print(f"\nProcessing pending callback for {filename} (ID: {callback_id})")
        
        try:
            all_results = save_results(callback_id, filename)
            
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
    
    print(f"\n" + "="*70)
    print("RETRIEVAL COMPLETED!")
    print("="*70)
    print(f"Successfully retrieved: {len([f for f in processed_files if f not in pending_callbacks])}")
    print(f"Still pending: {len(pending_callbacks)}")
    exit(0)

# Handle status-only request
if args.status:
    audio_files = get_audio_files()
    new_files = find_new_files(audio_files, processed_files, pending_callbacks)
    
    print(f"\n" + "="*70)
    print("CURRENT STATUS")
    print("="*70)
    print(f"Audio folder: {audio_folder}")
    print(f"Total audio files: {len(audio_files)}")
    print(f"Processed files: {len(processed_files)}")
    print(f"Pending callbacks: {len(pending_callbacks)}")
    print(f"New files to process: {len(new_files)}")
    
    if new_files:
        print(f"\nNew files found:")
        for filename in new_files[:10]:  # Show first 10
            print(f"  + {filename}")
        if len(new_files) > 10:
            print(f"  ... and {len(new_files) - 10} more")
    
    if pending_callbacks:
        print(f"\nPending callbacks:")
        for filename in sorted(pending_callbacks.keys()):
            print(f"  ⏳ {filename}")
    
    exit(0)

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
    try:
        with open(callback_tracking_file, 'w', encoding='utf-8') as f:
            json.dump(tracking_data, f, indent=2)
    except Exception as e:
        print(f"Error saving tracking data: {e}")

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

def get_transcription_result(callback_id, result_format="txt", max_attempts=30, wait_time=2):
    """
    Poll the callback status endpoint to get transcription results
    Returns the data content when status is "done"
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
            
            # All responses are JSON format
            result = response.json()
            print(f"Status response: {json.dumps(result, indent=2)}")
            
            # Check if transcription is complete
            if result.get('status') == 'done':
                print(f"Transcription completed for format '{result_format}'!")
                return result.get('data', '')
            elif result.get('status') in ['failed', 'error']:
                print(f"Transcription failed for format '{result_format}'!")
                return None
            elif result.get('status') in ['processing', 'pending']:
                print(f"Still processing... waiting {wait_time} seconds")
                time.sleep(wait_time)
                continue
            else:
                print(f"Unknown status: {result.get('status')}, continuing to poll...")
                time.sleep(wait_time)
                continue
            
        except requests.exceptions.RequestException as e:
            print(f"Error polling status: {e}")
            time.sleep(wait_time)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            time.sleep(wait_time)
    
    print(f"Maximum polling attempts ({max_attempts}) reached for format '{result_format}'. Transcription may still be processing.")
    return None

def save_results(callback_id, audio_filename):
    """
    Get and save transcription results
    """
    results = {}
    
    # Get TXT result
    print("\n" + "="*50)
    print("Getting TXT transcription...")
    txt_result = get_transcription_result(callback_id, "txt")
    if txt_result:
        results['txt'] = txt_result
        # Append to transcript file
        with open(transcript_file, 'a', encoding='utf-8') as f:
            f.write(f"{audio_filename}:{txt_result}\n")
        print(f"TXT transcription saved to: {transcript_file}")
    
    # Get SRT result
    print("\n" + "="*50)
    print("Getting SRT transcription...")
    srt_result = get_transcription_result(callback_id, "srt")
    if srt_result:
        results['srt'] = srt_result
        # Append to SRT file with readable formatting
        with open(srt_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"FILE: {audio_filename}\n")
            f.write(f"CALLBACK ID: {callback_id}\n")
            f.write(f"{'='*60}\n")
            f.write(srt_result)
            f.write(f"\n{'='*60}\n\n")
        print(f"SRT transcription saved to: {srt_file}")
    
    return results

# Get all audio files and find new ones
audio_files = get_audio_files()
new_files = find_new_files(audio_files, processed_files, pending_callbacks)

print(f"\n" + "="*70)
print("FILE PROCESSING SUMMARY")
print("="*70)
print(f"Total audio files found: {len(audio_files)}")
print(f"Already processed: {len(processed_files)}")
print(f"Pending callbacks: {len(pending_callbacks)}")
print(f"New files to process: {len(new_files)}")

if processed_files:
    print(f"\nAlready processed files (showing last 5):")
    for filename in sorted(list(processed_files))[-5:]:
        print(f"  [OK] {filename}")
    if len(processed_files) > 5:
        print(f"  ... and {len(processed_files) - 5} more")

if pending_callbacks:
    print(f"\nPending callbacks:")
    for filename in sorted(pending_callbacks.keys()):
        print(f"  [PENDING] {filename}")

if new_files:
    print(f"\nNew files found:")
    for filename in new_files:
        print(f"  [NEW] {filename}")
    
    # Handle different processing modes
    auto_process = False
    
    if args.check_only:
        print(f"\nCheck-only mode: Found {len(new_files)} new files to process.")
        print("Run without --check-only to process these files.")
        exit(0)
    elif args.auto:
        auto_process = True
        print(f"\nAuto-processing mode enabled. Processing {len(new_files)} new files...")
    else:
        print(f"\nDo you want to send {len(new_files)} new files for transcription? (Y/N): ", end="")
        user_input = input().strip().upper()
        auto_process = (user_input == 'Y')
    
    if not auto_process:
        print("Processing cancelled.")
        if len(new_files) > 0:
            print("To automatically process new files, run with --auto flag:")
            print("python neura_ASR.py --auto")
        exit()
else:
    print("\nNo new files to process.")
    if len(pending_callbacks) == 0:
        print("All files are up to date!")
    else:
        print("Will check pending callbacks for completed transcriptions.")
    
    if args.check_only:
        exit(0)
    
    # If no new files but there are pending callbacks, continue to process them
    if len(pending_callbacks) == 0:
        exit()

# Process new files
print("\n" + "="*70)
print("SENDING NEW FILES FOR TRANSCRIPTION")
print("="*70)

wait_between_files = 5  # seconds to wait between file uploads

for i, filename in enumerate(new_files):
    audio_file_path = os.path.join(audio_folder, filename)
    
    print(f"\n[{i+1}/{len(new_files)}] Processing: {filename}")
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
    if i < len(new_files) - 1:
        print(f"Waiting {wait_between_files} seconds before sending next file...")
        time.sleep(wait_between_files)

print("\n" + "="*70)
print("ALL NEW FILES SENT!")
print("="*70)
print(f"Files sent for processing: {len(new_files)}")
print(f"Total pending callbacks: {len(pending_callbacks)}")
print(f"\nResults will be saved to:")
print(f"  - Transcriptions: {transcript_file}")
print(f"  - SRT subtitles: {srt_file}")
print("\nTo retrieve results, run this script again. It will automatically")
print("process any pending callbacks and retrieve transcriptions.")
print("\nPending files:")
for filename in pending_callbacks.keys():
    print(f"  - {filename}")