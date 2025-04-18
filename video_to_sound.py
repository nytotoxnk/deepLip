import os
import subprocess

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