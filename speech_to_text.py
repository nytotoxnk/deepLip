import os
import json

from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError, NotFound, DeadlineExceeded
import datetime # Import datetime for timestamp comparison

# ... (Keep imports for SpeechClient, cloud_speech, ClientOptions, etc.) ...
from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

PROJECT_ID = "meta-triode-456910-n9"
LOCATION = "europe-west4"
MAX_AUDIO_LENGTH_SECS = 8 * 60 * 60
OPERATION_TIMEOUT_SECS = 3 * MAX_AUDIO_LENGTH_SECS

client_options_var = ClientOptions(api_endpoint=f"{LOCATION}-speech.googleapis.com")
speech_client = SpeechClient(client_options=client_options_var)
recognizer_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/albanian-recogniser"
storage_client = storage.Client()

# --- GCS Upload Function (same as before) ---
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
         print(f"Google Cloud API error during upload: {e}")
         return None
    except Exception as e:
        print(f"An unexpected error occurred during upload: {e}")
        return None

# --- Batch Transcription Function (same as before) ---
def run_gcs_batch_transcribe(audio_gcs_uri, speech_client, recognizer_name, gcs_output_folder):
    """Starts a batch transcription job for a file in GCS and waits for completion."""
    print(f"\nStarting batch transcription for {audio_gcs_uri}...")
    try:
        config = cloud_speech.RecognitionConfig(
            explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                audio_channel_count=2
            ),
            features=cloud_speech.RecognitionFeatures(
                enable_word_confidence=True,
                enable_word_time_offsets=True,
            ),
            model="chirp_2",
            language_codes=["sq-AL"],
        )

        output_config = cloud_speech.RecognitionOutputConfig(
            gcs_output_config=cloud_speech.GcsOutputConfig(uri=gcs_output_folder),
        )

        files = [cloud_speech.BatchRecognizeFileMetadata(uri=audio_gcs_uri)]

        request = cloud_speech.BatchRecognizeRequest(
            recognizer=recognizer_name,
            config=config,
            files=files,
            recognition_output_config=output_config,
        )

        operation = speech_client.batch_recognize(request=request)

        print("Waiting for batch operation to complete...")
        response = operation.result(timeout=OPERATION_TIMEOUT_SECS)

        print("Batch operation completed.")
        return response

    except NotFound:
        print(f"Error: Recognizer not found at {recognizer_name}")
        return None
    except DeadlineExceeded:
        print(f"Error: Batch operation did not complete within the timeout of {OPERATION_TIMEOUT_SECS} seconds.")
        print("The operation might still be running in the background. Check the Cloud Console.")
        return operation
    except GoogleAPIError as e:
         print(f"Google Cloud API error during transcription: {e}")
         return None
    except Exception as e:
        print(f"An unexpected error occurred during transcription: {e}")
        return None

# --- Function to Get Results from GCS (Updated to find latest) ---
def get_transcription_results_from_gcs(audio_gcs_uri, gcs_output_folder, storage_client):
    """Retrieves and parses the most recent transcription results from GCS."""

    print(f"\nAttempting to retrieve results from {gcs_output_folder} for {audio_gcs_uri}...")

    try:
        if not gcs_output_folder.startswith("gs://"):
             print("Error: GCS output folder URI must start with 'gs://'")
             return None, None

        uri_parts = gcs_output_folder[len("gs://"):].split('/', 1)
        output_bucket_name = uri_parts[0]
        output_prefix = uri_parts[1] if len(uri_parts) > 1 else ''

        # Ensure prefix ends with a slash for listing within the folder
        if output_prefix and not output_prefix.endswith('/'):
            output_prefix += '/'

        # Get the base name of the original audio file without extension
        original_file_name = os.path.basename(audio_gcs_uri)
        original_file_base_name = os.path.splitext(original_file_name)[0]

        print(f"Searching for results files starting with '{original_file_base_name}' in gs://{output_bucket_name}/{output_prefix}...")

        bucket = storage_client.bucket(output_bucket_name)
        blobs = bucket.list_blobs(prefix=output_prefix)

        most_recent_blob = None
        latest_timestamp = None

        # Iterate through the listed blobs to find the most recent result file
        for blob in blobs:
            # Check if the blob name is under the correct prefix, starts with the base name, and ends with .json
            # Ensure the name after the prefix starts with the base name
            name_after_prefix = blob.name[len(output_prefix):] if blob.name.startswith(output_prefix) else blob.name # Handle root prefix case
            if name_after_prefix.startswith(original_file_base_name) and name_after_prefix.endswith(".json"):
                 print(f"Found potential results file: {blob.name} (Last Updated: {blob.updated})")
                 # Check if this is the first matching blob found or if it's more recent
                 if most_recent_blob is None or blob.updated > latest_timestamp:
                     most_recent_blob = blob
                     latest_timestamp = blob.updated

        if most_recent_blob:
            print(f"Selected most recent results file: gs://{output_bucket_name}/{most_recent_blob.name}")
            try:
                # Download the content of the found result file
                results_json_str = most_recent_blob.download_as_text(encoding='utf-8')
                print("Results file downloaded.")

                # Parse the JSON content
                results_data = json.loads(results_json_str)

                # Extract the transcript and confidence
                if results_data and 'results' in results_data and results_data['results']:
                    first_result = results_data['results'][0]
                    if 'alternatives' in first_result and first_result['alternatives']:
                        top_alternative = first_result['alternatives'][0]
                        transcript = top_alternative.get('transcript')
                        confidence = top_alternative.get('confidence')

                        if transcript is not None:
                             print("Successfully extracted transcription results.")
                             return transcript, confidence
                        else:
                             print("Error: Could not find transcript in results data.")
                             return None, None
                    else:
                        print("Error: No alternatives found in the first result.")
                        return None, None
                else:
                    print("No transcription results found in the output file data.")
                    return None, None

            except json.JSONDecodeError:
                 print(f"Error: Could not parse JSON from results file gs://{output_bucket_name}/{most_recent_blob.name}.")
                 return None, None
            except Exception as e:
                print(f"An unexpected error occurred when processing results file {most_recent_blob.name}: {e}")
                return None, None
        else:
            print(f"Error: Could not find any results file starting with '{original_file_base_name}' and ending with '.json' in gs://{output_bucket_name}/{output_prefix}")
            print("Ensure the batch job completed successfully and check the contents of the output folder in the Cloud Console.")
            return None, None

    except GoogleAPIError as e:
         print(f"Google Cloud API error during result retrieval: {e}")
         return None, None
    except Exception as e:
        print(f"An unexpected error occurred during result retrieval: {e}")
        return None, None


# --- Main Execution Workflow ---
# Define your file details and bucket info
your_bucket_name = "speech-to-text-albanian" # Your GCS bucket name
your_local_audio_file = r"extracted_audios\\20250408_212848.wav" # Path to your local file
your_gcs_upload_folder = "audio-files/extracted-audios" # Folder inside your bucket to upload to
your_gcs_output_folder = "gs://speech-to-text-albanian/transcripts" # Folder inside your bucket for results

# Variables to store the final transcription results
transcription_results_text = None # Renamed to avoid conflict
confidence_score = None       # Renamed to avoid conflict

# 1. Upload the local audio file to GCS
uploaded_gcs_uri = upload_audio_to_gcs(
    your_bucket_name,
    your_local_audio_file,
    your_gcs_upload_folder
)

# 2. Check if upload was successful and proceed with transcription
if uploaded_gcs_uri:
    print("Upload successful. Proceeding with batch transcription...")
    # Pass the GCS URI of the uploaded file and the output folder to the transcribe function
    transcription_operation_result = run_gcs_batch_transcribe(
        uploaded_gcs_uri,
        speech_client,
        recognizer_name,
        your_gcs_output_folder
    )

    # Check if the transcription operation successfully started/completed without error/timeout
    if transcription_operation_result is not None:
        print("Batch transcription operation finished. Attempting to retrieve results from GCS...")

        # 3. Retrieve and get the transcription results from GCS
        transcription_results_text, confidence_score = get_transcription_results_from_gcs(
            uploaded_gcs_uri,
            your_gcs_output_folder,
            storage_client
        )

        # 4. Print and store the results in variables
        if transcription_results_text is not None:
            print("\n--- Final Transcription Results ---")
            print(f"Transcript: {transcription_results_text}")
            print(f"Confidence: {confidence_score}")

            # The results are now in the variables 'transcription_results_text' and 'confidence_score'
            # You can do further processing here

        else:
            print("\nFailed to retrieve or parse transcription results from GCS.")

    else:
        print("Batch transcription operation failed or did not complete successfully within the timeout.")

else:
    print("Upload failed. Cannot proceed with batch transcription.")