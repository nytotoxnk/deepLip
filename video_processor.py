import os
import subprocess
# whisper import moved to legacy functions where it's actually needed
# translate import moved to legacy functions where it's actually needed
import sys
from pathlib import Path

def create_directories():
    """Create necessary directories for the processing workflow"""
    directories = [
        "testing_video",
        "testing_audios/extracted", 
        "testing_translations"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created/verified directory: {directory}")

def get_video_files(video_folder="testing_videos"):
    """Get all video files from the specified folder"""
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v')
    
    if not os.path.exists(video_folder):
        print(f"Video folder '{video_folder}' not found. Creating it...")
        os.makedirs(video_folder, exist_ok=True)
        return []
    
    video_files = []
    for file in os.listdir(video_folder):
        if file.lower().endswith(video_extensions):
            video_files.append(os.path.join(video_folder, file))
    
    return sorted(video_files)

def extract_audio_from_video(video_path, output_folder="testing_audios/extracted"):
    """
    Extract audio from video using FFmpeg and save to specified folder
    """
    try:
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Get video filename without extension
        video_filename = os.path.basename(video_path)
        video_name = os.path.splitext(video_filename)[0]
        
        # Create output audio path
        audio_filename = f"{video_name}.wav"
        output_path = os.path.join(output_folder, audio_filename)
        
        # Normalize paths for the operating system
        video_path = os.path.normpath(video_path)
        output_path = os.path.normpath(output_path)
        
        # Skip if audio already exists
        if os.path.exists(output_path):
            print(f"Audio already exists: {output_path}")
            return output_path
        
        print(f"Extracting audio from: {video_filename}")
        print(f"Output: {output_path}")
        
        command = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # Audio codec
            '-ar', '16000',  # Sample rate
            '-ac', '1',  # Number of channels
            '-y',  # Overwrite output files
            output_path
        ]
        
        # Run ffmpeg with minimal output
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"[OK] Audio extracted successfully: {audio_filename}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error extracting audio from {video_path}: {e}")
        print(f"FFmpeg stderr: {e.stderr}")
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected error extracting audio from {video_path}: {e}")
        return None

def run_neura_transcription(audio_folder="testing_audios/extracted", output_file="testing_transcribe.txt"):
    """
    Run neura_ASR.py to transcribe audio files
    """
    try:
        print(f"\n{'='*70}")
        print("RUNNING NEURA ASR TRANSCRIPTION")
        print('='*70)
        
        # Import and run neura_ASR functionality
        sys.path.append('neura')
        
        # Set environment for neura_ASR to use our folders and files
        original_cwd = os.getcwd()
        
        # Create a custom neura_ASR command
        neura_command = [
            sys.executable, 
            'neura/neura_ASR.py', 
            '--folder', audio_folder,
            '--auto'
        ]
        
        print(f"Running command: {' '.join(neura_command)}")
        
        # Temporarily set environment variables for custom output
        env = os.environ.copy()
        env['NEURA_OUTPUT_FILE'] = output_file
        
        result = subprocess.run(neura_command, check=True, text=True, capture_output=True, env=env)
        print("[OK] Neura ASR transcription completed")
        print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error running Neura ASR: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error running Neura ASR: {e}")
        return False

def run_translation(input_file="testing_transcribe.txt", output_folder="testing_translations"):
    """
    Run translation on the transcribed file
    """
    try:
        print(f"\n{'='*70}")
        print("RUNNING TRANSLATION")
        print('='*70)
        
        # Create output folder
        os.makedirs(output_folder, exist_ok=True)
        
        # Check if input file exists
        if not os.path.exists(input_file):
            print(f"[ERROR] Transcription file not found: {input_file}")
            return False
        
        # Import translation functionality
        sys.path.append('translations')
        
        # Import the translation module
        import importlib.util
        spec = importlib.util.spec_from_file_location("translate", "translations/translate.py")
        translate_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(translate_module)
        
        print(f"Translating {input_file}...")
        
        # Translate to each target language
        languages = translate_module.languages
        translate_file_func = translate_module.translate_file
        
        for lang_code, lang_name in languages.items():
            output_file = os.path.join(output_folder, f"{lang_code}_translation.txt")
            print(f"  Translating to {lang_name}...")
            
            try:
                # Use the translation function directly
                result_file = translate_file_func(input_file, lang_code, lang_name, output_file)
                if result_file:
                    print(f"  [OK] Created {result_file}")
                else:
                    print(f"  [ERROR] Failed to create {output_file}")
            except Exception as e:
                print(f"  [ERROR] Error translating to {lang_name}: {e}")
        
        print("[OK] Translation process completed")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error in translation process: {e}")
        return False

def process_videos_workflow():
    """
    Main workflow to process videos: extract audio, transcribe, and translate
    """
    print("INTEGRATED VIDEO PROCESSING WORKFLOW")
    print("="*70)
    
    # Step 1: Create necessary directories
    print("\nStep 1: Setting up directories...")
    create_directories()
    
    # Step 2: Get video files
    print("\nStep 2: Finding video files...")
    video_files = get_video_files()
    
    if not video_files:
        print("No video files found in 'testing_video/' folder.")
        print("Please add video files (.mp4, .avi, .mov, etc.) to the 'testing_video/' folder and try again.")
        return False
    
    print(f"Found {len(video_files)} video files:")
    for video in video_files:
        print(f"  - {os.path.basename(video)}")
    
    # Step 3: Extract audio from all videos
    print(f"\nStep 3: Extracting audio from {len(video_files)} videos...")
    extracted_count = 0
    
    for i, video_path in enumerate(video_files, 1):
        print(f"\n[{i}/{len(video_files)}] Processing: {os.path.basename(video_path)}")
        audio_path = extract_audio_from_video(video_path)
        if audio_path:
            extracted_count += 1
    
    print(f"\n[OK] Audio extraction completed: {extracted_count}/{len(video_files)} successful")
    
    if extracted_count == 0:
        print("No audio files were extracted. Stopping workflow.")
        return False
    
    # Step 4: Run Neura ASR transcription
    print(f"\nStep 4: Running transcription...")
    transcription_success = run_neura_transcription()
    
    if not transcription_success:
        print("Transcription failed. Stopping workflow.")
        return False
    
    # Step 5: Run translation
    print(f"\nStep 5: Running translation...")
    translation_success = run_translation()
    
    if translation_success:
        print(f"\n{'='*70}")
        print("WORKFLOW COMPLETED SUCCESSFULLY!")
        print('='*70)
        print(f"Results:")
        print(f"  - Extracted audio: testing_audios/extracted/")
        print(f"  - Transcriptions: testing_transcribe.txt") 
        print(f"  - Translations: testing_translations/")
        return True
    else:
        print("Translation failed.")
        return False

# Legacy functions (keeping for backward compatibility)
def extract_audio(video_path, output_path):
    """Legacy function - use extract_audio_from_video instead"""
    return extract_audio_from_video(video_path, os.path.dirname(output_path))

def transcribe_audio(audio_path, target_lang='sq'):
    """
    Transcribe audio using OpenAI Whisper
    Note: This is the legacy transcription method. 
    The workflow now uses Neura ASR for better accuracy.
    """
    try:
        # Import whisper only when this legacy function is used
        try:
            import whisper
        except ImportError:
            raise ImportError("OpenAI Whisper is not installed. Install it with: pip install openai-whisper")
        
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language=target_lang)
        return result["text"]
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        raise

def translate_text(text, target_lang='en'):
    """
    Translate text to target language using translate package
    """
    try:
        # Import Translator only when this legacy function is used
        try:
            from translate import Translator
        except ImportError:
            raise ImportError("translate package is not installed. Install it with: pip install translate")
        
        translator = Translator(to_lang=target_lang)
        translation = translator.translate(text)
        return translation
    except Exception as e:
        print(f"Error translating text: {e}")
        raise

def process_video(video_path, target_lang='sq'):
    """
    Legacy function to process a single video
    """
    # Create output directory if it doesn't exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Ensure video path exists
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Extract audio
    audio_path = os.path.join(output_dir, "extracted_audio.wav")
    extract_audio_from_video(video_path, output_dir)
    
    # Transcribe audio
    print("Transcribing audio...")
    transcript = transcribe_audio(audio_path)
    
    # Save transcript
    transcript_path = os.path.join(output_dir, "transcript.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript)
    print(f"Transcript saved to {transcript_path}")
    
    # Translate transcript
    print("Translating transcript...")
    translated_text = translate_text(transcript, target_lang)
    
    # Save translation
    translation_path = os.path.join(output_dir, "translation.txt")
    with open(translation_path, "w", encoding="utf-8") as f:
        f.write(translated_text)
    print(f"Translation saved to {translation_path}")
    
    return transcript, translated_text

# if __name__ == "__main__":
#     # Run the integrated workflow
#     success = process_videos_workflow()
    
#     if not success:
#         print("\nWorkflow failed. Please check the errors above.")
#         sys.exit(1)
#     else:
#         print("\nWorkflow completed successfully!")
#         sys.exit(0) 
videos = []
for video in 