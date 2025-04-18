from transformers import WhisperForConditionalGeneration, WhisperProcessor, WhisperTokenizer
import torch
import librosa
import numpy as np

# Load processor and tokenizer from the original Whisper model
processor = WhisperProcessor.from_pretrained("openai/whisper-large-v2")
tokenizer = WhisperTokenizer.from_pretrained("openai/whisper-large-v2")

# Load the peshperima model weights
model = WhisperForConditionalGeneration.from_pretrained("niv-al/peshperima-large-v2-merged")

# Load audio file
audio_path = "output/audio.wav"
audio, sampling_rate = librosa.load(audio_path, sr=16000)

input_features = processor.feature_extractor(audio, sampling_rate=sampling_rate, return_tensors="pt")
attention_mask = torch.ones_like(input_features.input_features[:, :, 0])

inputs = {
    "input_features": input_features.input_features,
    "attention_mask": attention_mask
}

# Get the forced decoder IDs for Albanian language and transcription task
forced_decoder_ids = processor.get_decoder_prompt_ids(language="sq", task="transcribe")

# Generate transcription using forced_decoder_ids
predicted_ids = model.generate(
    **inputs,
    forced_decoder_ids=forced_decoder_ids,
    max_length=448
)

transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)
print("Transcription:", transcription[0])