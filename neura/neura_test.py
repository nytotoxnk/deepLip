import os
import requests
import json

api_prefix = os.environ['NEURA_API_PREFIX']
api_key = os.environ['NEURA_API_KEY']

# Load callback tracking to get a callback ID to test
callback_tracking_file = 'neura_callback_tracking.json'

if not os.path.exists(callback_tracking_file):
    print(f"No callback tracking file found at {callback_tracking_file}")
    exit(1)

with open(callback_tracking_file, 'r', encoding='utf-8') as f:
    tracking_data = json.load(f)
    pending_callbacks = tracking_data.get('pending_callbacks', {})

if not pending_callbacks:
    print("No pending callbacks found in tracking file")
    exit(1)

# Get the first callback ID
first_filename = list(pending_callbacks.keys())[0]
first_callback_id = pending_callbacks[first_filename]

print(f"Testing callback for file: {first_filename}")
print(f"Callback ID: {first_callback_id}")
print("=" * 50)

# Test different formats
formats = ["json", "txt", "srt", "srt_words"]

headers = {
    'Authorization': f'Bearer {api_key}'
}

for format_type in formats:
    print(f"\n--- Testing format: {format_type} ---")
    
    status_url = f'{api_prefix}/callback/status?callbackId={first_callback_id}&result_as={format_type}'
    
    try:
        response = requests.get(status_url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            if format_type == "json":
                try:
                    json_data = response.json()
                    print(f"JSON Response:")
                    print(json.dumps(json_data, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    print(f"Response is not valid JSON:")
                    print(f"Raw response: {response.text}")
            else:
                print(f"Text Response (length: {len(response.text)} chars):")
                print(f"Raw response: {repr(response.text)}")
                if len(response.text) < 1000:  # Only print if not too long
                    print(f"Readable text: {response.text}")
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Error making request: {e}")
    
    print("-" * 30)
