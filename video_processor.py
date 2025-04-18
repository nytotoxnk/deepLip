import os
import subprocess
import whisper
from translate import Translator
from dotenv import load_dotenv

def extract_audio(video_path, output_path):
    """
    Extract audio from video using FFmpeg
    """
    try:
        # Ensure paths are properly formatted for the operating system
        video_path = os.path.normpath(video_path)
        output_path = os.path.normpath(output_path)
        
        command = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # Audio codec
            '-ar', '16000',  # Sample rate
            '-ac', '1',  # Number of channels
            output_path
        ]
        subprocess.run(command, check=True)
        print(f"Audio extracted successfully to {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        raise

def transcribe_audio(audio_path, target_lang='sq'):
    """
    Transcribe audio using OpenAI Whisper
    Need to update this, as a final product it should be a good model that has a low WER score
    till I am able to do that I cannot go to the next step. 
    """
    try:
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
        translator = Translator(to_lang=target_lang)
        translation = translator.translate(text)
        return translation
    except Exception as e:
        print(f"Error translating text: {e}")
        raise

def process_video(video_path, target_lang='sq'):
    """
    Main function to process video: extract audio, transcribe, and translate
    """
    # Create output directory if it doesn't exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Ensure video path exists
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Extract audio
    audio_path = os.path.join(output_dir, "extracted_audio.wav")
    extract_audio(video_path, audio_path)
    
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

if __name__ == "__main__":
    # Example usage
    video_path = os.path.join("videos", "20250403_161711.mp4")
    # Available language codes for translation (ISO 639-1 codes)
    # See full list at: https://cloud.google.com/translate/docs/languages
    target_language = "sq"
    transcript, translation = process_video(video_path, target_language)
    print("\nTranscript:", transcript)
    print("\n")
    
    try:
        transcript, translation = process_video(video_path, target_language)
        print("\nOriginal transcript:")
        print(transcript)
        
    except Exception as e:
        print(f"An error occurred: {e}") 