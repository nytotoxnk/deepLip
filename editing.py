from pydub import AudioSegment, silence
import os
import subprocess
import json
"""
1. Split audio from video file.
2. Check for silence of 0.5 seconds on the audio to determine when to cut
3. Cut video based on the time of silence
4. Output is Multiple small videos
"""

import os
import subprocess
import json
from pydub import AudioSegment
from pydub.silence import detect_silence

# Assume extract_audio function exists and works correctly:
# def extract_audio(video_path, audio_path):
#     # Use ffmpeg to extract audio (e.g., to WAV)
#     cmd = ['ffmpeg', '-i', video_path, '-acodec', 'pcm_wav', audio_path]
#     subprocess.run(cmd, check=True)

def split_video_on_silence(video_path, output_dir, max_chunk_length=55000, min_silence_len=500, max_silence_len=1000, silence_thresh=-40):
    """
    Splits a video file into smaller chunks based on detected silence,
    ensuring chunks are less than a maximum length.

    Args:
        video_path (str): Path to the input video file.
        output_dir (str): Directory to save the output video chunks.
        max_chunk_length (int): Maximum duration of a video chunk in milliseconds
                                (default: 55000 ms = 55 seconds).
        min_silence_len (int): Minimum length of silence to consider a break in milliseconds
                               (default: 500 ms).
        max_silence_len (int): Maximum length of silence to consider a preferred break point
                               (default: 1000 ms = 1 second).
        silence_thresh (int): Silence threshold in dBFS (default: -40 dBFS).
    """
    # Ensure directories exist
    os.makedirs(output_dir, exist_ok=True)

    # Extract audio for silence detection
    temp_audio_path = os.path.join(output_dir, "temp_audio.wav") # Save temp file in output dir
    print(f"Extracting audio to {temp_audio_path}...")
    try:
         # Using ffmpeg directly via subprocess for audio extraction
         audio_extract_cmd = [
             'ffmpeg', '-i', video_path, '-vn', # -vn means no video
             '-acodec', 'pcm_wav', # Output as PCM WAV
             '-ar', '16000', # Recommended sample rate for pydub compatibility and smaller file size
             '-ac', '1', # Mono audio
             '-y', # Overwrite output file without asking
             temp_audio_path
         ]
         subprocess.run(audio_extract_cmd, check=True, capture_output=True, text=True)
         print("Audio extracted successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        print(f"Error output: {e.stderr}")
        return # Exit if audio extraction fails

    # Load audio with pydub
    try:
        audio = AudioSegment.from_wav(temp_audio_path)
        print(f"Audio loaded, duration: {len(audio)} ms")
    except Exception as e:
        print(f"Error loading audio file {temp_audio_path}: {e}")
        os.remove(temp_audio_path) # Clean up temp file
        return

    # Detect silent chunks longer than min_silence_len
    print(f"Detecting silence with threshold {silence_thresh} dBFS and min length {min_silence_len} ms...")
    # pydub's detect_silence already filters by min_silence_len
    silence_ranges = detect_silence(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)

    print(f"Detected silence ranges (ms): {silence_ranges}")

    # --- Logic to determine cut points based on silence and max chunk length ---
    cuts = [0] # Start at the beginning
    last_cut_time = 0
    audio_length = len(audio)

    for s_start, s_stop in silence_ranges:
        silence_duration = s_stop - s_start
        time_since_last_cut = s_stop - last_cut_time

        # Condition 1: Is this silence a suitable length for a preferred break?
        is_suitable_silence = min_silence_len <= silence_duration <= max_silence_len

        # Condition 2: Would cutting here keep the current segment within max length?
        is_within_max_length = time_since_last_cut <= max_chunk_length

        # If it's a suitable silence AND cutting here keeps the segment within max length, use it
        if is_suitable_silence and is_within_max_length:
            cuts.append(s_stop)
            last_cut_time = s_stop
            print(f"Adding cut at end of suitable silence: {s_stop} ms")
        elif time_since_last_cut > max_chunk_length:
             # The segment leading up to *this* silence is already too long.
             # We need to force a cut *before* this silence.
             # The forced cut point is max_chunk_length from the last cut.
             forced_cut_point = last_cut_time + max_chunk_length

             # Ensure the forced cut point doesn't go past the start of the *current* silence
             # This handles cases where max_chunk_length might land inside the silence
             # We prefer cutting just before the silence starts if the forced point is beyond s_start
             # But more simply, if the segment up to s_stop is too long, we must cut at max_chunk_length from last_cut_time
             # Let's add the forced cut point.
             if forced_cut_point > last_cut_time and forced_cut_point < audio_length: # Avoid adding duplicate cuts or cuts past the end
                 cuts.append(forced_cut_point)
                 last_cut_time = forced_cut_point
                 print(f"Forcing cut at max length: {forced_cut_point} ms")

                 # After forcing a cut, check if the *current* silence is now viable for the *next* cut
                 # from the *new* last_cut_time.
                 time_since_new_last_cut = s_stop - last_cut_time
                 if is_suitable_silence and time_since_new_last_cut <= max_chunk_length:
                      cuts.append(s_stop)
                      last_cut_time = s_stop
                      print(f"Adding cut at suitable silence after forced cut: {s_stop} ms")


    # Ensure the last cut point is the end of the audio if it hasn't been added yet
    if cuts[-1] < audio_length:
        cuts.append(audio_length)

    # Filter out consecutive identical cut points
    unique_cuts = [cuts[0]]
    for cut in cuts[1:]:
        if cut > unique_cuts[-1]:
            unique_cuts.append(cut)
    cuts = unique_cuts

    print(f"Final cutting timestamps (ms): {cuts}")

    # Use ffmpeg directly to split the video
    for i in range(len(cuts) - 1):
        start_ms = cuts[i]
        end_ms = cuts[i+1]
        duration_ms = end_ms - start_ms

        if duration_ms <= 0:
            print(f"Skipping zero or negative duration chunk at index {i}")
            continue

        start_sec = start_ms / 1000.0
        duration_sec = duration_ms / 1000.0

        out_path = os.path.join(output_dir, f"chunk_{i+1:03d}.mp4")
        print(f"Creating chunk {i+1}: {start_sec:.2f}s to {end_ms/1000.0:.2f}s (duration: {duration_sec:.2f}s)")

        # Direct ffmpeg command for accurate splitting (-ss after -i)
        # Using -c copy to avoid re-encoding where possible
        cmd = [
            'ffmpeg',
            '-i', video_path,       # Input file
            '-ss', str(start_sec),   # Start time
            '-t', str(duration_sec), # Duration
            '-c:v', 'copy',          # Copy video stream
            '-c:a', 'copy',          # Copy audio stream
            '-map', '0',             # Include all streams from input
            '-y',                    # Overwrite output files
            out_path
        ]

        # Fallback if stream copying fails (e.g., problematic codecs)
        # You might need to uncomment and adjust codecs if copy fails often
        # cmd_fallback = [
        #     'ffmpeg',
        #     '-i', video_path,
        #     '-ss', str(start_sec),
        #     '-t', str(duration_sec),
        #     '-c:v', 'libx264',
        #     '-c:a', 'aac',
        #     '-b:a', '192k',
        #     '-map', '0',
        #     '-y',
        #     out_path
        # ]


        try:
            # Try copying streams first
            print("Trying to copy streams...")
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"Successfully created {out_path} by copying streams.")

            # Verify the output has audio (optional but good practice)
            try:
                probe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', out_path]
                result = subprocess.run(probe_cmd, check=True, capture_output=True, text=True)
                streams = json.loads(result.stdout)['streams']

                has_audio = any(stream['codec_type'] == 'audio' for stream in streams)
                if has_audio:
                    print(f"Verified {out_path} has audio stream.")
                else:
                    print(f"Warning: {out_path} has no audio stream!")
            except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as probe_error:
                 print(f"Could not verify audio stream for {out_path} using ffprobe: {probe_error}")


        except subprocess.CalledProcessError as e:
            print(f"Error creating chunk {i+1} by copying streams: {e}")
            print(f"Error output (copy attempt): {e.stderr}")
            print("Retrying chunk creation with re-encoding...")

            # Fallback to re-encoding if copying failed
            cmd_fallback = [
                'ffmpeg',
                '-i', video_path,
                '-ss', str(start_sec),
                '-t', str(duration_sec),
                '-c:v', 'libx264', # You can choose a suitable video codec
                '-c:a', 'aac',     # AAC is a common audio codec
                '-b:a', '192k',    # Audio bitrate
                '-map', '0',       # Include all streams
                '-y',
                out_path
            ]
            try:
                 subprocess.run(cmd_fallback, check=True, capture_output=True, text=True)
                 print(f"Successfully created {out_path} using re-encoding.")
                 # Verify audio stream again after fallback
                 try:
                    probe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', out_path]
                    result = subprocess.run(probe_cmd, check=True, capture_output=True, text=True)
                    streams = json.loads(result.stdout)['streams']
                    has_audio = any(stream['codec_type'] == 'audio' for stream in streams)
                    if has_audio:
                        print(f"Verified {out_path} has audio stream after re-encoding.")
                    else:
                        print(f"Warning: {out_path} has no audio stream after re-encoding!")
                 except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as probe_error:
                    print(f"Could not verify audio stream for {out_path} using ffprobe after re-encoding: {probe_error}")

            except subprocess.CalledProcessError as e_fallback:
                 print(f"Fatal Error: Failed to create chunk {i+1} even with re-encoding: {e_fallback}")
                 print(f"Error output (re-encoding attempt): {e_fallback.stderr}")
                 # Decide if you want to stop or continue with the next chunk
                 continue # Continue to the next chunk


    # Clean up temp files
    if os.path.exists(temp_audio_path):
        os.remove(temp_audio_path)
        print(f"Cleaned up temporary audio file {temp_audio_path}")
    print("Done splitting the video.")

# Example Usage (assuming you have a video file and the extract_audio function)
# if __name__ == "__main__":
#     # You would need to define or import your extract_audio function here
#     def extract_audio(video_path, audio_path):
#          try:
#              cmd = ['ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_wav', '-ar', '16000', '-ac', '1', '-y', audio_path]
#              subprocess.run(cmd, check=True, capture_output=True, text=True)
#              print(f"Extracted audio from {video_path} to {audio_path}")
#          except subprocess.CalledProcessError as e:
#              print(f"Error extracting audio for function test: {e.stderr}")
#              raise # Re-raise the exception

#     # Ensure ffmpeg and ffprobe are in your PATH
#     # Install pydub: pip install pydub
#     # pydub requires ffmpeg installed separately

#     # Replace with your actual video file path
#     input_video = "your_video.mp4"
#     output_directory = "output_chunks"

#     if os.path.exists(input_video):
#          split_video_on_silence(input_video, output_directory)
#     else:
#          print(f"Input video not found: {input_video}")


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
    video_path = os.path.normpath('videos/')
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