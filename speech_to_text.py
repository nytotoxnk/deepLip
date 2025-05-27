import os
import json
import datetime # Keep for potential future use, not directly used in this version's GCS result fetching

from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError, NotFound, DeadlineExceeded
from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

# --- Configuration (Update these as needed) ---
PROJECT_ID = "meta-triode-456910-n9"  # Google Cloud Project ID
LOCATION = "europe-west4"             # Sevice server region
RECOGNIZER_ID = "albanian-recogniser" # The recogniser ID

# GCS Configuration
YOUR_BUCKET_NAME = "speech-to-text-albanian"

YOUR_LOCAL_AUDIO_FOLDER = r"full_length_extracted_audio"

YOUR_GCS_UPLOAD_FOLDER = "audio-files"

YOUR_GCS_OUTPUT_PARENT_FOLDER = f"gs://{YOUR_BUCKET_NAME}/transcripts"

OUTPUT_TEXT_FILE = "google_transcription_alb.txt"

# Local folder for downloading JSON transcription files
TRANSCRIPTIONS_JSON_FOLDER = "transcriptions_json"

# Batch processing settings
BATCH_SIZE = 5  # Process 5 files at a time

# Recognizer and Operation settings
RECOGNIZER_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/{RECOGNIZER_ID}"

OPERATION_TIMEOUT_SECS = 2 * 60 * 60 # 2 hours (reduced for smaller batches)

# --- Client Initialization ---
try:
    client_options_var = ClientOptions(api_endpoint=f"{LOCATION}-speech.googleapis.com")
    speech_client = SpeechClient(client_options=client_options_var)
    storage_client = storage.Client()
except Exception as e:
    print(f"Error initializing Google Cloud clients: {e}")
    exit()

# --- GCS Upload Function ---
def upload_audio_to_gcs(bucket_name, local_file_path, gcs_destination_prefix):
    """Uploads a file from local storage to a GCS bucket."""
    try:
        bucket = storage_client.bucket(bucket_name)
        file_name = os.path.basename(local_file_path)

        if gcs_destination_prefix and gcs_destination_prefix.strip('/'):
            destination_blob_name = f"{gcs_destination_prefix.strip('/')}/{file_name}"
        else:
            destination_blob_name = file_name

        blob = bucket.blob(destination_blob_name)

        # Check if file already exists
        if blob.exists():
            print(f"File already exists at gs://{bucket_name}/{destination_blob_name}, skipping upload")
            return f"gs://{bucket_name}/{destination_blob_name}"

        print(f"Uploading {local_file_path} to gs://{bucket_name}/{destination_blob_name}")
        blob.upload_from_filename(local_file_path)
        gcs_uri = f"gs://{bucket_name}/{destination_blob_name}"
        print(f"File uploaded successfully to {gcs_uri}")
        return gcs_uri
    except FileNotFoundError:
        print(f"Error: Local file not found at {local_file_path}")
        return None
    except GoogleAPIError as e:
        print(f"Google Cloud API error during upload for {local_file_path}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during upload for {local_file_path}: {e}")
        return None

# --- Function to Get Transcript from a Specific GCS JSON URI ---
def get_transcript_from_specific_json_uri(json_gcs_uri, storage_client):
    """Downloads and parses a specific transcription result JSON file from GCS."""
    print(f"Attempting to retrieve and parse results from {json_gcs_uri}...")
    try:
        if not json_gcs_uri.startswith("gs://"):
            print(f"Error: GCS JSON URI '{json_gcs_uri}' must start with 'gs://'")
            return None, None

        uri_parts = json_gcs_uri[len("gs://"):].split('/', 1)
        if len(uri_parts) < 2:
            print(f"Error: Invalid GCS URI format '{json_gcs_uri}'")
            return None, None
        bucket_name = uri_parts[0]
        blob_name = uri_parts[1]

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if not blob.exists(storage_client): # Pass client for blob.exists()
            print(f"Error: Results JSON file not found at {json_gcs_uri}")
            return None, None

        # Create transcriptions_json folder if it doesn't exist
        os.makedirs(TRANSCRIPTIONS_JSON_FOLDER, exist_ok=True)
        
        # Download JSON file to local folder
        json_filename = os.path.basename(blob_name)
        local_json_path = os.path.join(TRANSCRIPTIONS_JSON_FOLDER, json_filename)
        
        print(f"Downloading JSON file to: {local_json_path}")
        blob.download_to_filename(local_json_path)
        
        # Read and parse the downloaded JSON file
        with open(local_json_path, 'r', encoding='utf-8') as f:
            results_json_str = f.read()
        results_data = json.loads(results_json_str)

        full_transcript_parts = []
        overall_confidence = None # We'll take confidence from the first result's first alternative

        if results_data and 'results' in results_data and results_data['results']:
            # Set overall_confidence from the first result's first alternative if available
            first_result = results_data['results'][0]
            if 'alternatives' in first_result and first_result['alternatives']:
                overall_confidence = first_result['alternatives'][0].get('confidence')

            for result_entry in results_data['results']:
                if 'alternatives' in result_entry and result_entry['alternatives']:
                    top_alternative = result_entry['alternatives'][0]
                    transcript_segment = top_alternative.get('transcript')
                    if transcript_segment:
                        full_transcript_parts.append(transcript_segment)
                else:
                    print(f"Warning: No alternatives found in a result entry within {json_gcs_uri}")

            if not full_transcript_parts:
                print(f"Error: No transcript segments found in {json_gcs_uri}")
                return None, overall_confidence # Return confidence even if transcript is empty

            final_transcript = " ".join(full_transcript_parts).strip()
            print(f"Successfully extracted transcription from {json_gcs_uri}.")
            return final_transcript, overall_confidence
        else:
            print(f"No 'results' field or no actual results found in the output file data from {json_gcs_uri}.")
            return None, None

    # --- Exception Handling ---
    except json.JSONDecodeError:
        print(f"Error: Could not parse JSON from results file {json_gcs_uri}.")
        return None, None
    except NotFound:
        print(f"Error: GCS blob not found at {json_gcs_uri} during download.")
        return None, None
    except GoogleAPIError as e:
        print(f"Google Cloud API error during result download/parse from {json_gcs_uri}: {e}")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred when processing results file {json_gcs_uri}: {e}")
        return None, None

# --- Function to list files in GCS bucket ---
def list_gcs_files(bucket_name, prefix=""):
    """List files in GCS bucket with optional prefix."""
    try:
        bucket = storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        return [f"gs://{bucket_name}/{blob.name}" for blob in blobs if not blob.name.endswith('/')]
    except Exception as e:
        print(f"Error listing GCS files: {e}")
        return []

# --- Function to upload files only ---
def upload_files_only():
    """Upload audio files to GCS without transcription."""
    print("--- Uploading Audio Files to GCS Only ---")
    
    audio_files_to_upload = []
    try:
        print(f"Scanning for audio files in: {YOUR_LOCAL_AUDIO_FOLDER}")
        for item in os.listdir(YOUR_LOCAL_AUDIO_FOLDER):
            if item.lower().endswith((".wav")):
                local_file_path = os.path.join(YOUR_LOCAL_AUDIO_FOLDER, item)
                if os.path.isfile(local_file_path):
                    audio_files_to_upload.append(local_file_path)
    except FileNotFoundError:
        print(f"Error: Local audio folder not found at {YOUR_LOCAL_AUDIO_FOLDER}")
        return
    except Exception as e:
        print(f"Error listing audio files in {YOUR_LOCAL_AUDIO_FOLDER}: {e}")
        return

    if not audio_files_to_upload:
        print(f"No audio files found in {YOUR_LOCAL_AUDIO_FOLDER} to process.")
        return
    
    print(f"Found {len(audio_files_to_upload)} audio files to upload.")

    uploaded_count = 0
    for local_file_path in audio_files_to_upload:
        gcs_uri = upload_audio_to_gcs(
            YOUR_BUCKET_NAME,
            local_file_path,
            YOUR_GCS_UPLOAD_FOLDER
        )
        if gcs_uri:
            uploaded_count += 1

    print(f"Upload completed. {uploaded_count} files processed.")

# --- Function to process batch transcription ---
def process_batch_transcription(gcs_uris_batch, uploaded_file_info_map):
    """Process a batch of files for transcription."""
    print(f"\n--- Processing batch of {len(gcs_uris_batch)} files ---")
    
    all_file_metadata = [cloud_speech.BatchRecognizeFileMetadata(uri=uri) for uri in gcs_uris_batch]

    # Define RecognitionConfig
    recognition_config = cloud_speech.RecognitionConfig(
        explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
            encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            audio_channel_count=2
        ),
        features=cloud_speech.RecognitionFeatures(
            enable_word_confidence=True,
            enable_word_time_offsets=True,
            enable_automatic_punctuation=True,
        ),
        model="chirp_2",
        language_codes=["sq-AL"],
    )

    recognition_output_config = cloud_speech.RecognitionOutputConfig(
        gcs_output_config=cloud_speech.GcsOutputConfig(uri=YOUR_GCS_OUTPUT_PARENT_FOLDER)
    )

    batch_request = cloud_speech.BatchRecognizeRequest(
        recognizer=RECOGNIZER_NAME,
        config=recognition_config,
        files=all_file_metadata,
        recognition_output_config=recognition_output_config,
    )

    print(f"Submitting batch transcription request for {len(all_file_metadata)} files.")

    try:
        operation = speech_client.batch_recognize(request=batch_request)
        print(f"Waiting for batch operation to complete (timeout: {OPERATION_TIMEOUT_SECS} seconds)...")
        response = operation.result(timeout=OPERATION_TIMEOUT_SECS)
        print("Batch transcription operation completed.")

        # Process results and save to text file
        print(f"--- Processing Transcription Results ---")
        processed_files_count = 0
        
        with open(OUTPUT_TEXT_FILE, 'a', encoding='utf-8') as outfile:
            if response and response.results:
                for input_audio_gcs_uri, file_result in response.results.items():
                    original_base_name = uploaded_file_info_map.get(input_audio_gcs_uri, os.path.basename(input_audio_gcs_uri))

                    if file_result.error and file_result.error.message:
                        print(f"Error for '{original_base_name}': {file_result.error.message}")
                        outfile.write(f"{original_base_name}:ERROR_API:{file_result.error.message}\n")
                        continue

                    result_json_gcs_uri = file_result.uri
                    if not result_json_gcs_uri:
                        print(f"No result URI found for '{original_base_name}'")
                        outfile.write(f"{original_base_name}:ERROR_NO_URI:Transcription result URI missing\n")
                        continue

                    print(f"Fetching transcript for '{original_base_name}' from: {result_json_gcs_uri}")
                    transcript_text, confidence = get_transcript_from_specific_json_uri(
                        result_json_gcs_uri,
                        storage_client
                    )

                    if transcript_text is not None:
                        output_line = f"{original_base_name}:{transcript_text}\n"
                        outfile.write(output_line)
                        print(f"Saved transcription for '{original_base_name}'")
                        processed_files_count += 1
                    else:
                        print(f"Failed to retrieve transcription for '{original_base_name}'")
                        outfile.write(f"{original_base_name}:ERROR_PARSING:Failed to process transcript JSON\n")
            else:
                print("No results found in the response object.")

        print(f"Batch completed. Processed {processed_files_count} files.")
        return processed_files_count

    except Exception as e:
        print(f"Error during batch transcription: {e}")
        return 0

# --- Function to transcribe uploaded files ---
def transcribe_uploaded_files():
    """Transcribe files that are already uploaded to GCS."""
    print("--- Transcribing Uploaded Files ---")
    
    # Get list of uploaded audio files
    gcs_audio_files = list_gcs_files(YOUR_BUCKET_NAME, YOUR_GCS_UPLOAD_FOLDER)
    
    if not gcs_audio_files:
        print(f"No audio files found in GCS bucket under {YOUR_GCS_UPLOAD_FOLDER}")
        return
    
    print(f"Found {len(gcs_audio_files)} audio files in GCS to transcribe.")
    
    # Create mapping of GCS URI to filename
    uploaded_file_info_map = {}
    for gcs_uri in gcs_audio_files:
        filename = os.path.basename(gcs_uri)
        uploaded_file_info_map[gcs_uri] = filename
    
    # Clear the output file at the start
    with open(OUTPUT_TEXT_FILE, 'w', encoding='utf-8') as f:
        f.write("")  # Clear the file
    
    # Process files in batches
    total_processed = 0
    for i in range(0, len(gcs_audio_files), BATCH_SIZE):
        batch = gcs_audio_files[i:i + BATCH_SIZE]
        batch_info = {uri: uploaded_file_info_map[uri] for uri in batch}
        
        print(f"\n--- Processing batch {i//BATCH_SIZE + 1} of {(len(gcs_audio_files) + BATCH_SIZE - 1)//BATCH_SIZE} ---")
        processed_count = process_batch_transcription(batch, batch_info)
        total_processed += processed_count
        
        if i + BATCH_SIZE < len(gcs_audio_files):
            print("Waiting 30 seconds before next batch...")
            import time
            time.sleep(30)
    
    print(f"\nTranscription completed. Total files processed: {total_processed}")

# --- Function to download transcription JSONs only ---
def download_transcription_jsons():
    """Download transcription JSON files from GCS."""
    print("--- Downloading Transcription JSON Files ---")
    
    # List JSON files in the transcripts folder
    json_files = list_gcs_files(YOUR_BUCKET_NAME, "transcripts/")
    json_files = [f for f in json_files if f.endswith('.json')]
    
    if not json_files:
        print("No JSON transcription files found in GCS.")
        return
    
    print(f"Found {len(json_files)} JSON files to download.")
    
    os.makedirs(TRANSCRIPTIONS_JSON_FOLDER, exist_ok=True)
    
    downloaded_count = 0
    for json_gcs_uri in json_files:
        try:
            uri_parts = json_gcs_uri[len("gs://"):].split('/', 1)
            bucket_name = uri_parts[0]
            blob_name = uri_parts[1]
            
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            json_filename = os.path.basename(blob_name)
            local_json_path = os.path.join(TRANSCRIPTIONS_JSON_FOLDER, json_filename)
            
            print(f"Downloading {json_filename}...")
            blob.download_to_filename(local_json_path)
            downloaded_count += 1
            
        except Exception as e:
            print(f"Error downloading {json_gcs_uri}: {e}")
    
    print(f"Downloaded {downloaded_count} JSON files to {TRANSCRIPTIONS_JSON_FOLDER}")

def main():
    print("=== Google Cloud Speech-to-Text Batch Processor ===")
    print("Choose an operation:")
    print("1. Upload audio files only")
    print("2. Transcribe uploaded files (batch processing)")
    print("3. Download transcription JSON files only")
    print("4. Full process (upload + transcribe)")
    
    choice = input("Enter your choice (1-4): ").strip()
    
    if choice == "1":
        upload_files_only()
    elif choice == "2":
        transcribe_uploaded_files()
    elif choice == "3":
        download_transcription_jsons()
    elif choice == "4":
        upload_files_only()
        print("\nNow starting transcription process...")
        transcribe_uploaded_files()
    else:
        print("Invalid choice. Please run the script again and choose 1-4.")

if __name__ == "__main__":
    main()