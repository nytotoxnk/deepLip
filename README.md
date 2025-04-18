# Video Processing and Translation Tool

This tool extracts audio from videos, transcribes the speech to text using OpenAI Whisper, and translates the text to a target language.

## Prerequisites

1. Python 3.8 or higher
2. FFmpeg installed on your system
   - Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html)
   - Linux: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows:
```bash
venv\Scripts\activate
```
- Linux/macOS:
```bash
source venv/bin/activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Place your video file in the project directory
2. Modify the `video_path` and `target_language` variables in `video_processor.py` if needed
3. Run the script:
```bash
python video_processor.py
```

The script will:
1. Extract audio from the video
2. Transcribe the audio to text
3. Translate the text to the target language
4. Save all outputs in the `output` directory

## Output Files

- `output/extracted_audio.wav`: The extracted audio from the video
- `output/transcript.txt`: The transcribed text
- `output/translation.txt`: The translated text

## Language Codes

Common language codes for translation:
- Spanish: 'es'
- French: 'fr'
- German: 'de'
- Italian: 'it'
- Portuguese: 'pt'
- Russian: 'ru'
- Chinese: 'zh-cn'
- Japanese: 'ja'
- Korean: 'ko' 