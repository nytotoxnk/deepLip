import os
import subprocess
import whisper
import json
from pathlib import Path
import shutil

def create_directories():
    """Create necessary directories for output files"""
    directories = ['output/videos', 'output/audio', 'output/transcripts']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def extract_audio(video_path, output_path):
    """Extract audio from video using FFmpeg"""
    try:
        command = [
            'ffmpeg',
            '-i', video_path,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '2',
            output_path
        ]
        subprocess.run(command, check=True)
        print(f"Audio extracted successfully to {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        raise

def transcribe_audio(audio_path):
    """Transcribe audio using OpenAI Whisper with word-level timestamps"""
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, word_timestamps=True)
        return result
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        raise

def cut_video_segment(input_video, output_video, start_time, end_time):
    """Cut a segment from the video using FFmpeg"""
    try:
        command = [
            'ffmpeg',
            '-i', input_video,
            '-ss', str(start_time),
            '-t', str(end_time - start_time),
            '-c', 'copy',
            output_video
        ]
        subprocess.run(command, check=True)
        print(f"Video segment created: {output_video}")
    except subprocess.CalledProcessError as e:
        print(f"Error cutting video segment: {e}")
        raise

def cut_audio_segment(input_audio, output_audio, start_time, end_time):
    """Cut a segment from the audio using FFmpeg"""
    try:
        command = [
            'ffmpeg',
            '-i', input_audio,
            '-ss', str(start_time),
            '-t', str(end_time - start_time),
            output_audio
        ]
        subprocess.run(command, check=True)
        print(f"Audio segment created: {output_audio}")
    except subprocess.CalledProcessError as e:
        print(f"Error cutting audio segment: {e}")
        raise

def process_video(video_path):
    """Main function to process video and create word-level segments"""
    # Create output directories
    create_directories()
    
    # Extract full audio
    full_audio_path = "output/audio/full_audio.wav"
    extract_audio(video_path, full_audio_path)
    
    # Transcribe audio with word timestamps
    print("Transcribing audio...")
    result = transcribe_audio(full_audio_path)
    
    # Save full transcript
    transcript_path = "output/transcripts/full_transcript.txt"
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(result["text"])
    print(f"Full transcript saved to {transcript_path}")
    
    # Save word-level transcript with timestamps
    word_transcript_path = "output/transcripts/word_transcript.txt"
    with open(word_transcript_path, "w", encoding="utf-8") as f:
        for segment in result["segments"]:
            for word in segment["words"]:
                f.write(f"{word['word']} [{word['start']:.2f} - {word['end']:.2f}]\n")
    print(f"Word-level transcript saved to {word_transcript_path}")
    
    # Process each word
    print("Creating word-level segments...")
    for segment in result["segments"]:
        for word in segment["words"]:
            word_text = word["word"].strip()
            if word_text:  # Skip empty words
                # Create safe filename
                safe_filename = "".join(c for c in word_text if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_filename = safe_filename.replace(' ', '_')
                
                # Create video segment
                video_segment_path = f"output/videos/{safe_filename}.mp4"
                cut_video_segment(video_path, video_segment_path, word["start"], word["end"])
                
                # Create audio segment
                audio_segment_path = f"output/audio/{safe_filename}.wav"
                cut_audio_segment(full_audio_path, audio_segment_path, word["start"], word["end"])
    
    print("Processing complete!")
    print(f"Segments are saved in:")
    print("- output/videos/ (video segments)")
    print("- output/audio/ (audio segments)")
    print("- output/transcripts/ (transcript files)")

if __name__ == "__main__":
    # Example usage
    video_path = "input_video.mp4"  # Replace with your video path
    
    try:
        process_video(video_path)
    except Exception as e:
        print(f"An error occurred: {e}") 