import os
import requests
import time
import json
from pathlib import Path

api_prefix = os.environ['NEURA_API_PREFIX']
api_key = os.environ['NEURA_API_KEY']  

# Path to your audio file
audio_file_path = 'full_length_extracted_audio/20250403_161711.wav'

# Check if file exists and is accessible
if not os.path.exists(audio_file_path):
    print(f"Error: Audio file not found at {audio_file_path}")
    exit(1)

# Create necessary directories
Path("neura_json").mkdir(exist_ok=True)
Path("SRT").mkdir(exist_ok=True)

# URL for the API endpoint
url = f'{api_prefix}/stt'

# Optional: any other data you want to send along with the audio
other_data = {
    'word_timestamps': 'true'
}

def get_transcription_status(callback_id, result_format="json", max_attempts=30, wait_time=2):
    """
    Poll the callback status endpoint to get transcription results
    
    Args:
        callback_id: The callback ID returned from the initial request
        result_format: Format for the response ("json", "txt", "srt", "srt_words")
        max_attempts: Maximum number of polling attempts
        wait_time: Time to wait between polling attempts (seconds)
    
    Returns:
        The transcription result or None if failed
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
        with open("neura_transcript.txt", 'a', encoding='utf-8') as f:
            f.write(f"{audio_filename}:{txt_result}\n")
        print(f"TXT result appended to: neura_transcript.txt")
    
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

try:
    with open(audio_file_path, 'rb') as audio_file:
        # 'rb' means read in binary mode, which is crucial for files
        files = {
            'audio': (audio_file_path.split('/')[-1], audio_file, 'audio/wav')
            # 'audio' is the field name the server expects for the file.
            # The tuple contains:
            # 1. The filename (optional, but good practice)
            # 2. The file object itself
            # 3. The MIME type of the file (e.g., 'audio/wav' for wav, 'audio/mpeg' for mp3)
        }

        # Headers for authentication
        headers = {
            'Authorization': f'Bearer {api_key}'
            # Don't set Content-Type manually - let requests handle multipart/form-data
        }

        print(f"Sending audio file: {audio_file_path}")
        print(f"File size: {os.path.getsize(audio_file_path)} bytes")
        
        # Make the POST request
        response = requests.post(url, files=files, data=other_data, headers=headers)

        # Check the response from the server
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
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
        
        if callback_id:
            print(f"\nReceived callback ID: {callback_id}")
            
            # Extract filename without extension for naming files
            audio_filename = Path(audio_file_path).stem
            
            # Get and save all result formats
            all_results = save_results(callback_id, audio_filename)
            
            print("\n" + "="*70)
            print("TRANSCRIPTION PROCESSING COMPLETED!")
            print("="*70)
            print("Files saved:")
            print(f"- JSON: neura_json/{audio_filename}_{callback_id}.json")
            print(f"- TXT: neura_transcript.txt (appended)")
            print(f"- SRT: SRT/{audio_filename}_{callback_id}.srt")
            print(f"- SRT_WORDS: SRT/{audio_filename}_{callback_id}_words.srt")
            
        else:
            print("No callback ID found in response. Response may contain direct results:")
            print(json.dumps(initial_response, indent=2))

except FileNotFoundError:
    print(f"Error: The file '{audio_file_path}' was not found.")
except requests.exceptions.HTTPError as e:
    print(f"HTTP error occurred: {e}")
    print(f"Response status code: {response.status_code}")
    print(f"Response text: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"An error occurred during the request: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")