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

YOUR_LOCAL_AUDIO_FOLDER = r"extracted_audios"

YOUR_GCS_UPLOAD_FOLDER = "audio-files/batch_uploads"

YOUR_GCS_OUTPUT_PARENT_FOLDER = f"gs://{YOUR_BUCKET_NAME}/transcripts/batch_output"

OUTPUT_TEXT_FILE = "transcription_alb.txt"

# Recognizer and Operation settings
RECOGNIZER_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/{RECOGNIZER_ID}"

OPERATION_TIMEOUT_SECS = 6 * 60 * 60 # 6 hours

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

        results_json_str = blob.download_as_text(client=storage_client, encoding='utf-8')
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


def main():
    print("--- Starting Batch Audio Transcription Process ---")

    # 1. Identify audio files in the local folder
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
    
    print(f"Found {len(audio_files_to_upload)} audio files to process.")

    # 2. Upload all audio files to GCS
    # uploaded_file_info_map: GCS URI -> original_base_name
    uploaded_file_info_map = {}
    gcs_uris_for_batch_request = []

    print("\n--- Uploading Audio Files to GCS ---")
    for local_file_path in audio_files_to_upload:
        gcs_uri = upload_audio_to_gcs(
            YOUR_BUCKET_NAME,
            local_file_path,
            YOUR_GCS_UPLOAD_FOLDER
        )
        if gcs_uri:
            base_name = os.path.basename(local_file_path)
            uploaded_file_info_map[gcs_uri] = base_name
            gcs_uris_for_batch_request.append(gcs_uri)
        else:
            print(f"Skipping {local_file_path} due to upload failure.")

    if not gcs_uris_for_batch_request:
        print("No files were successfully uploaded. Cannot proceed with transcription.")
        return
    print(f"\nSuccessfully uploaded {len(gcs_uris_for_batch_request)} files to GCS.")

    # 3. Prepare and run the batch transcription request
    print("\n--- Preparing Batch Transcription Request ---")
    all_file_metadata = [cloud_speech.BatchRecognizeFileMetadata(uri=uri) for uri in gcs_uris_for_batch_request]

    # Define RecognitionConfig (ensure these settings are correct for your audio)
    recognition_config = cloud_speech.RecognitionConfig(
        explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
            encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16, # Assuming WAV/LINEAR16
            sample_rate_hertz=16000, # Adjust if your audio has a different sample rate
            audio_channel_count=2    # Adjust if mono or different channel count
        ),
        features=cloud_speech.RecognitionFeatures(
            enable_word_confidence=True,
            enable_word_time_offsets=True,
            # enable_automatic_punctuation=True, # Consider adding
            # diarization_config=cloud_speech.SpeakerDiarizationConfig( # Optional: if you need speaker labels
            #     min_speaker_count=1,
            # ),
        ),
        model="chirp_2", # Using the Chirp model
        language_codes=["sq-AL"], # Albanian
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

    print(f"Submitting batch transcription request for {len(all_file_metadata)} files to recognizer {RECOGNIZER_NAME}.")
    print(f"Output will be stored under GCS path: {YOUR_GCS_OUTPUT_PARENT_FOLDER}")

    try:
        operation = speech_client.batch_recognize(request=batch_request)
        print(f"Waiting for batch operation to complete (timeout: {OPERATION_TIMEOUT_SECS} seconds)...")
        response = operation.result(timeout=OPERATION_TIMEOUT_SECS) # This is a BatchRecognizeResponse
        print("Batch transcription operation completed.")

        # 4. Process results and save to text file
        print(f"\n--- Processing Transcription Results and Saving to {OUTPUT_TEXT_FILE} ---")
        with open(OUTPUT_TEXT_FILE, 'w', encoding='utf-8') as outfile:
            if response and response.results:
                processed_files_count = 0
                for input_audio_gcs_uri, file_result in response.results.items():
                    original_base_name = uploaded_file_info_map.get(input_audio_gcs_uri, os.path.basename(input_audio_gcs_uri))

                    if file_result.error and file_result.error.message:
                        print(f"Error for '{original_base_name}': {file_result.error.message} (Code: {file_result.error.code})")
                        outfile.write(f"{original_base_name}:ERROR_API:{file_result.error.message}\n")
                        continue

                    result_json_gcs_uri = file_result.uri
                    if not result_json_gcs_uri:
                        print(f"No result URI found for '{original_base_name}', though no explicit API error reported.")
                        outfile.write(f"{original_base_name}:ERROR_NO_URI:Transcription result URI missing\n")
                        continue

                    print(f"Fetching transcript for '{original_base_name}' from: {result_json_gcs_uri}")
                    transcript_text, confidence = get_transcript_from_specific_json_uri(
                        result_json_gcs_uri,
                        storage_client
                    )

                    if transcript_text is not None:
                        confidence_str = f"{confidence:.4f}" if isinstance(confidence, float) else str(confidence if confidence is not None else "N/A")
                        output_line = f"{original_base_name}:{confidence_str}:{transcript_text}\n"
                        outfile.write(output_line)
                        print(f"Saved transcription for '{original_base_name}'")
                        processed_files_count +=1
                    else:
                        print(f"Failed to retrieve or parse transcription for '{original_base_name}' from {result_json_gcs_uri}.")
                        outfile.write(f"{original_base_name}:ERROR_PARSING:Failed to process transcript JSON\n")
                print(f"Successfully processed and saved results for {processed_files_count} files.")
            else:
                print("Batch operation completed, but no results found in the response object.")
                if response:
                     print(f"Response object details: {response}")


    except DeadlineExceeded:
        print(f"CRITICAL ERROR: Batch operation did not complete within the timeout of {OPERATION_TIMEOUT_SECS} seconds.")
        print("The operation might still be running in the background. Check the Google Cloud Console for its status.")
        print(f"Partial results (if any) might not be available. Consider increasing OPERATION_TIMEOUT_SECS if this persists for large batches.")
    except NotFound:
        print(f"CRITICAL ERROR: Recognizer not found at {RECOGNIZER_NAME}. Please check your PROJECT_ID, LOCATION, and RECOGNIZER_ID.")
    except GoogleAPIError as e:
        print(f"CRITICAL Google Cloud API error during batch transcription: {e}")
    except Exception as e:
        print(f"CRITICAL An unexpected error occurred during batch transcription: {e}")

    print(f"\n--- Batch Transcription Process Finished. Check '{OUTPUT_TEXT_FILE}' for results. ---")

if __name__ == "__main__":
    main()