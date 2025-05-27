import os
import subprocess
import sys
from pathlib import Path

def get_audio_duration(file_path):
    """Get the duration of an audio file in seconds using ffprobe."""
    try:
        cmd = [
            'ffprobe', 
            '-v', 'quiet', 
            '-show_entries', 'format=duration', 
            '-of', 'csv=p=0', 
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print(f"Error getting duration for {file_path}: {e}")
        return None
    except ValueError as e:
        print(f"Error parsing duration for {file_path}: {e}")
        return None

def adjust_audio_length(input_file, output_file, target_duration, method='stretch'):
    """
    Adjust audio length to match target duration.
    
    Args:
        input_file: Path to the input audio file
        output_file: Path to save the adjusted audio
        target_duration: Target duration in seconds
        method: 'stretch' (tempo change) or 'trim_pad' (trim/pad with silence)
    """
    try:
        if method == 'stretch':
            # Use atempo filter to stretch/compress audio
            current_duration = get_audio_duration(input_file)
            if current_duration is None:
                return False
            
            tempo_ratio = current_duration / target_duration
            
            # ffmpeg atempo filter has limits (0.5 to 2.0), so we might need multiple filters
            if tempo_ratio > 2.0:
                # Need to compress significantly - use multiple atempo filters
                filters = []
                remaining_ratio = tempo_ratio
                while remaining_ratio > 2.0:
                    filters.append("atempo=2.0")
                    remaining_ratio /= 2.0
                if remaining_ratio > 1.0:
                    filters.append(f"atempo={remaining_ratio}")
                filter_str = ",".join(filters)
            elif tempo_ratio < 0.5:
                # Need to stretch significantly - use multiple atempo filters
                filters = []
                remaining_ratio = tempo_ratio
                while remaining_ratio < 0.5:
                    filters.append("atempo=0.5")
                    remaining_ratio /= 0.5
                if remaining_ratio < 1.0:
                    filters.append(f"atempo={remaining_ratio}")
                filter_str = ",".join(filters)
            else:
                filter_str = f"atempo={tempo_ratio}"
            
            cmd = [
                'ffmpeg', '-y', '-i', input_file,
                '-filter:a', filter_str,
                '-c:a', 'libmp3lame',  # Use MP3 encoding
                output_file
            ]
            
        else:  # trim_pad method
            cmd = [
                'ffmpeg', '-y', '-i', input_file,
                '-t', str(target_duration),  # Trim to target duration
                '-c:a', 'libmp3lame',
                output_file
            ]
            
            # If original is shorter, we'll pad with silence
            current_duration = get_audio_duration(input_file)
            if current_duration < target_duration:
                silence_duration = target_duration - current_duration
                cmd = [
                    'ffmpeg', '-y',
                    '-i', input_file,
                    '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100:duration={silence_duration}',
                    '-filter_complex', '[0:a][1:a]concat=n=2:v=0:a=1',
                    '-c:a', 'libmp3lame',
                    output_file
                ]
        
        print(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error adjusting audio: {e}")
        print(f"Error output: {e.stderr.decode() if e.stderr else 'No error output'}")
        return False

def compare_and_adjust_audio(original_file, cloned_file, output_file=None, tolerance=0.5, method='stretch'):
    """
    Compare two audio files and adjust the cloned one to match the original's length.
    
    Args:
        original_file: Path to the original audio file
        cloned_file: Path to the cloned audio file
        output_file: Path to save the adjusted cloned audio (optional)
        tolerance: Tolerance in seconds (won't adjust if difference is within this)
        method: 'stretch' (tempo change) or 'trim_pad' (trim/pad with silence)
    """
    
    # Check if files exist
    if not os.path.exists(original_file):
        print(f"Error: Original file not found: {original_file}")
        return False
    
    if not os.path.exists(cloned_file):
        print(f"Error: Cloned file not found: {cloned_file}")
        return False
    
    # Get durations
    print("Getting audio durations...")
    original_duration = get_audio_duration(original_file)
    cloned_duration = get_audio_duration(cloned_file)
    
    if original_duration is None or cloned_duration is None:
        print("Error: Could not get audio durations")
        return False
    
    print(f"Original audio duration: {original_duration:.2f} seconds")
    print(f"Cloned audio duration: {cloned_duration:.2f} seconds")
    
    duration_diff = abs(original_duration - cloned_duration)
    print(f"Duration difference: {duration_diff:.2f} seconds")
    
    # Check if adjustment is needed
    if duration_diff <= tolerance:
        print(f"Duration difference ({duration_diff:.2f}s) is within tolerance ({tolerance}s). No adjustment needed.")
        return True
    
    # Generate output filename if not provided
    if output_file is None:
        cloned_path = Path(cloned_file)
        output_file = cloned_path.parent / f"{cloned_path.stem}_adjusted{cloned_path.suffix}"
    
    print(f"Adjusting cloned audio to match original duration...")
    print(f"Target duration: {original_duration:.2f} seconds")
    print(f"Using method: {method}")
    
    success = adjust_audio_length(cloned_file, output_file, original_duration, method)
    
    if success:
        # Verify the result
        adjusted_duration = get_audio_duration(output_file)
        if adjusted_duration:
            print(f"Adjusted audio duration: {adjusted_duration:.2f} seconds")
            final_diff = abs(original_duration - adjusted_duration)
            print(f"Final difference: {final_diff:.2f} seconds")
            print(f"Adjusted audio saved as: {output_file}")
        return True
    else:
        print("Failed to adjust audio length")
        return False

def main():
    """Main function with example usage"""
    
    # Example file paths - modify these to match your files
    original_file = "audio_mp3/original.mp3"  # Replace with your original file path
    cloned_file = "audio_mp3/cloned.mp3"      # Replace with your cloned file path
    
    # You can also specify custom output file and parameters
    output_file = "audio_mp3/cloned_adjusted.mp3"
    
    print("Audio Length Comparison and Adjustment Tool")
    print("=" * 50)
    
    # Method options: 'stretch' (changes tempo) or 'trim_pad' (trims or adds silence)
    method = 'stretch'  # Change to 'trim_pad' if you prefer not to change tempo
    tolerance = 0.5     # Tolerance in seconds
    
    success = compare_and_adjust_audio(
        original_file=original_file,
        cloned_file=cloned_file,
        output_file=output_file,
        tolerance=tolerance,
        method=method
    )
    
    if success:
        print("\nProcess completed successfully!")
    else:
        print("\nProcess failed. Please check the error messages above.")

if __name__ == "__main__":
    # Check if ffmpeg and ffprobe are available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg and ffprobe are required but not found in PATH.")
        print("Please install ffmpeg: https://ffmpeg.org/download.html")
        sys.exit(1)
    
    main()
