# Example code (specifics depend on the model)
import torch
import soundfile as sf
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import librosa
from datasets import load_dataset
from video_to_sound import extract_audio

# Load pre-trained processor and model
processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")

#librispeech_samples_ds = load_dataset("patrickvonplaten/librispeech_asr_dummy", "clean", split="validation")

#Loading audio file from dataset
#audio_input, sample_rate = sf.read(librispeech_samples_ds[0]["file"])

# Extract audio from video
#extract_audio("videos/20250403_161711.mp4", "output/audio.wav")

# Load audio
audio, rate = librosa.load("output/audio.wav", sr=16000)

# Process audio
input_values = processor(audio, sampling_rate=rate, return_tensors="pt").input_values

# Perform inference
with torch.no_grad():
    logits = model(input_values).logits

# Decode the prediction
predicted_ids = torch.argmax(logits, dim=-1)
transcription = processor.batch_decode(predicted_ids)[0]

print(transcription)