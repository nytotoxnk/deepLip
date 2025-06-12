from transformers import pipeline
import os
import torch # Required for PyTorch backend

# --- Configuration ---
# Path to the folder containing your audio files
AUDIO_FOLDER = "full_length_extracted_audio"
# Output file name for transcriptions
OUTPUT_FILE = "whisper_transcription_hf.txt"

WHISPER_MODEL = "openai/whisper-large-v3" 

if torch.cuda.is_available():
    DEVICE = "cuda:0" 
    print("Using CUDA (GPU) for inference.")
else:
    DEVICE = "cpu"
    print("Using CPU for inference. Transcription might be slow for large models.")


def transcribe_audio_with_hf_whisper(audio_file_path, transcriber_pipeline):
    """
    Transcribes an audio file using a Hugging Face Whisper ASR model.
    """
    try:
        # Let the pipeline handle audio loading and preprocessing automatically
        # This is more robust and handles various audio formats better
        result = transcriber_pipeline(audio_file_path)
        return result["text"]
    except Exception as e:
        print(f"Error transcribing {audio_file_path}: {e}")
        print(f"  This could be due to a corrupted audio file or unsupported format.")
        return None

def main():
    if not os.path.exists(AUDIO_FOLDER):
        print(f"Error: Audio folder '{AUDIO_FOLDER}' not found. Please create it and place your audio files inside.")
        return

    # Initialize the Whisper pipeline
    print(f"Loading Whisper model '{WHISPER_MODEL}' to {DEVICE}...")
    transcriber = pipeline(
        "automatic-speech-recognition",
        model=WHISPER_MODEL,
        torch_dtype=torch.float16 if DEVICE == "cuda:0" else torch.float32, # Use float16 for GPU memory efficiency
        device=DEVICE,
        return_timestamps=True,  # Enable long-form transcription for audio > 30 seconds
        generate_kwargs={"language": "albanian", "task": "transcribe"}
    )
    print("Model loaded.")

    transcriptions = []
    
    audio_files = [f for f in os.listdir(AUDIO_FOLDER) if f.lower().endswith(('.wav', '.mp3', '.flac', '.m4a'))] 
    
    if not audio_files:
        print(f"No audio files found in '{AUDIO_FOLDER}'. Supported formats: .wav, .mp3, .flac, .m4a")
        return

    print(f"Starting transcription of {len(audio_files)} files from '{AUDIO_FOLDER}'...")

    for i, audio_file_name in enumerate(audio_files):
        # The output format requires 'video_id.wav', so we'll construct it even if source isn't WAV.
        video_id = os.path.splitext(audio_file_name)[0] 
        audio_file_path = os.path.join(AUDIO_FOLDER, audio_file_name)

        print(f"({i+1}/{len(audio_files)}) Transcribing '{audio_file_name}'...")
        text_transcription = transcribe_audio_with_hf_whisper(audio_file_path, transcriber)

        if text_transcription is not None:
            # Ensure the output format is `video_id.wav:text_transcription` as requested
            formatted_line = f"{video_id}.wav:{text_transcription.strip()}\n" 
            transcriptions.append(formatted_line)
            print(f"  -> Transcribed. Length: {len(text_transcription.strip())} chars.")
        else:
            print(f"  -> Failed to transcribe '{audio_file_name}'. Skipping.")

    # Write all transcriptions to the output file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(transcriptions)

    print(f"\nTranscription complete. Results saved to '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    main()