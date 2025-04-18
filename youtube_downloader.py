import os
import sys
import subprocess
import json

def download_video(url, output_path='downloads', resolution='best', format='mp4', max_retries=3):
    """
    Download a YouTube video using yt-dlp
    
    Args:
        url (str): The YouTube video URL
        output_path (str): Directory to save the downloaded video
        resolution (str): Video resolution ('best', '720p', '480p', etc.)
        format (str): File format ('mp4', 'webm', etc.)
        max_retries (int): Maximum number of retry attempts
    
    Returns:
        str: Path to the downloaded video file or None if download failed
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    # Get video info to display before downloading
    try:
        print(f"Fetching video information from: {url}")
        info_cmd = ['yt-dlp', '--dump-json', url]
        info_result = subprocess.run(info_cmd, capture_output=True, text=True, check=True)
        video_info = json.loads(info_result.stdout)
        
        # Display video information
        print(f"Title: {video_info.get('title', 'Unknown')}")
        print(f"Channel: {video_info.get('uploader', 'Unknown')}")
        print(f"Duration: {video_info.get('duration', 0)} seconds")
        print(f"Views: {video_info.get('view_count', 'Unknown')}")
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Warning: Could not fetch video info - {e}")
        # Continue with download anyway
    
    # Build download command
    cmd = [
        'yt-dlp',
        '--no-warnings',
        '-R', str(max_retries),
        '--no-playlist',
    ]
    
    # Set output format
    if resolution == 'best':
        if format == 'mp4':
            # Best mp4 format
            cmd.extend(['-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'])
        else:
            # Best format in any container
            cmd.extend(['-f', 'bestvideo+bestaudio/best'])
    else:
        # Specific resolution
        if resolution == '720p':
            cmd.extend(['-f', f'bestvideo[height<=720][ext={format}]+bestaudio/best[height<=720][ext={format}]/best'])
        elif resolution == '480p':
            cmd.extend(['-f', f'bestvideo[height<=480][ext={format}]+bestaudio/best[height<=480][ext={format}]/best'])
        elif resolution == '360p':
            cmd.extend(['-f', f'bestvideo[height<=360][ext={format}]+bestaudio/best[height<=360][ext={format}]/best'])
        else:
            # Default to best if resolution not recognized
            cmd.extend(['-f', 'bestvideo+bestaudio/best'])
    
    # Set output path and filename template
    output_template = os.path.join(output_path, '%(title)s.%(ext)s')
    cmd.extend(['-o', output_template])
    
    # Add the URL
    cmd.append(url)
    
    # Execute the command
    print(f"Starting download with command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print(f"Download complete to {output_path} directory")
        return output_path  # Return the directory since we can't know the exact filename
    except subprocess.CalledProcessError as e:
        print(f"Error during download: {e}")
        return None

def download_audio(url, output_path='downloads', audio_format='mp3', max_retries=3):
    """
    Download only the audio from a YouTube video
    
    Args:
        url (str): The YouTube video URL
        output_path (str): Directory to save the downloaded audio
        audio_format (str): Audio format ('mp3', 'm4a', etc.)
        max_retries (int): Maximum number of retry attempts
    
    Returns:
        str: Path to the downloaded audio file or None if download failed
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    # Build download command
    cmd = [
        'yt-dlp',
        '--no-warnings',
        '-R', str(max_retries),
        '--no-playlist',
        '--extract-audio',
        f'--audio-format={audio_format}',
        '--audio-quality=0',  # Best quality
    ]
    
    # Set output path and filename template
    output_template = os.path.join(output_path, '%(title)s.%(ext)s')
    cmd.extend(['-o', output_template])
    
    # Add the URL
    cmd.append(url)
    
    # Execute the command
    print(f"Starting audio download with command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print(f"Audio download complete to {output_path} directory")
        return output_path  # Return the directory since we can't know the exact filename
    except subprocess.CalledProcessError as e:
        print(f"Error during audio download: {e}")
        return None

def main():
    """
    Main function to handle command line arguments
    """
    # Check if URL is provided
    if len(sys.argv) < 2:
        print("Usage: python youtube_downloader.py <youtube_url> [--audio-only] [--resolution=720p] [--format=mp4] [--output=downloads] [--retries=3]")
        return
    
    url = sys.argv[1]
    audio_only = "--audio-only" in sys.argv
    output_path = "downloads"
    resolution = "best"
    file_format = "mp4"
    audio_format = "mp3"
    max_retries = 3
    
    # Parse command line arguments
    for arg in sys.argv:
        if arg.startswith("--output="):
            output_path = arg.split("=")[1]
        elif arg.startswith("--resolution="):
            resolution = arg.split("=")[1]
        elif arg.startswith("--format="):
            file_format = arg.split("=")[1]
        elif arg.startswith("--audio-format="):
            audio_format = arg.split("=")[1]
        elif arg.startswith("--retries="):
            try:
                max_retries = int(arg.split("=")[1])
            except ValueError:
                print("Invalid retries value, using default of 3")
                max_retries = 3
    
    if audio_only:
        download_audio(url, output_path, audio_format, max_retries)
    else:
        download_video(url, output_path, resolution, file_format, max_retries)

if __name__ == "__main__":
    main() 