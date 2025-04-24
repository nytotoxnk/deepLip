from pydub import AudioSegment, silence
import os
import subprocess
import json

def split_video_on_silence(video_path, output_dir, max_chunk_length=15000, silence_thresh=-40):
    # Ensure directories exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract audio for silence detection
    temp_audio_path = "temp_audio.wav"
    extract_audio(video_path, temp_audio_path)
    
    # Load audio with pydub
    audio = AudioSegment.from_wav(temp_audio_path)
    
    # Detect silent chunks longer than 1s
    silence_ranges = silence.detect_silence(audio, min_silence_len=1000, silence_thresh=silence_thresh)
    silence_ranges = [(start, stop) for start, stop in silence_ranges if (stop - start) >= 1000]
    
    # Add boundaries for full coverage
    cuts = [0]
    for start, stop in silence_ranges:
        if stop - cuts[-1] >= max_chunk_length:
            cuts.append(stop)
    if cuts[-1] < len(audio):
        cuts.append(len(audio))
    
    print(f"Cutting video at timestamps (ms): {cuts}")
    
    # Use ffmpeg directly to split the video
    for i in range(len(cuts) - 1):
        start_ms = cuts[i]
        end_ms = cuts[i+1]
        
        if end_ms - start_ms > max_chunk_length:
            end_ms = start_ms + max_chunk_length
        
        start_sec = start_ms / 1000
        end_sec = end_ms / 1000
        duration = end_sec - start_sec
        
        out_path = os.path.join(output_dir, f"chunk_{i+1:03d}.mp4")
        print(f"Creating chunk {i+1}: {start_sec:.2f}s to {end_sec:.2f}s (duration: {duration:.2f}s)")
        
        # Direct ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(start_sec),
            '-t', str(duration),
            '-c:v', 'libx264',  # Video codec
            '-c:a', 'aac',      # Audio codec
            '-strict', 'experimental',
            '-b:a', '192k',     # Audio bitrate
            '-y',               # Overwrite output files
            out_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"Successfully created {out_path}")
            
            # Verify the output has audio
            probe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', out_path]
            result = subprocess.run(probe_cmd, check=True, capture_output=True, text=True)
            streams = json.loads(result.stdout)['streams']
            
            has_audio = any(stream['codec_type'] == 'audio' for stream in streams)
            if has_audio:
                print(f"✓ Verified {out_path} has audio")
            else:
                print(f"✗ Warning: {out_path} has no audio!")
                
        except subprocess.CalledProcessError as e:
            print(f"Error creating chunk {i+1}: {e}")
            print(f"Error output: {e.stderr}")
    
    # Clean up temp files
    os.remove(temp_audio_path)
    print("Done splitting the video")

def extract_audio(video_path, output_path):
    """Extract audio from video using FFmpeg"""
    try:
        command = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # Audio codec
            '-ar', '16000',  # Sample rate
            '-ac', '1',  # Number of channels
            '-y',  # Overwrite output
            output_path
        ]
        
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Audio extracted successfully to {output_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        print(f"FFmpeg error output: {e.stderr}")
        raise

if __name__ == "__main__":
    video_path = os.path.normpath('downloads/')
    output_dir = 'prepared_dataset'
    
    # Check if ffmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg is not installed or not in PATH. Please install ffmpeg first.")
        exit(1)
    
    # Check if input file exists
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        exit(1)
    
    print(f"Found video file, proceeding with splitting")
    split_video_on_silence(video_path, output_dir)