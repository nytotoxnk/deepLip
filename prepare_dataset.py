import os
import pandas as pd
from datasets import Dataset, Audio, load_dataset
import json
from tqdm import tqdm

def prepare_dataset_from_custom_metadata(
    metadata_path, 
    audio_folder, 
    output_path, 
    split_ratio=None
):
    """
    Convert a custom-formatted metadata file and audio folder into a Hugging Face Dataset format.
    The metadata format is expected to be: filename|transcript|validation
    with no header row and pipe as delimiter.
    
    Args:
        metadata_path: Path to the custom metadata file
        audio_folder: Path to the folder containing audio files
        output_path: Path to save the prepared dataset
        split_ratio: Optional dict with train/validation/test split ratios (e.g., {"train": 0.8, "validation": 0.1, "test": 0.1})
    """
    print(f"Loading metadata from {metadata_path}")
    
    # Read the custom-formatted file with no header and pipe delimiter
    df = pd.read_csv(metadata_path, header=None, sep='|')
    
    # Assign column names based on expected format
    column_names = ['filename', 'transcript', 'validation']
    
    # If there are only two columns, adjust accordingly
    if len(df.columns) == 2:
        column_names = ['filename', 'transcript']
    
    # Rename columns
    df.columns = column_names[:len(df.columns)]
    
    print(f"Loaded metadata with {len(df)} entries and {len(df.columns)} columns")
    
    # Check if we have audio file extensions in the filename column
    # If not, we'll need to append them when looking for the files
    sample_filename = df['filename'].iloc[0]
    has_extension = os.path.splitext(sample_filename)[1] != ''
    
    # Prepare the dataset
    data_dict = {
        "audio": [],
        "text": []
    }
    
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    # Track missing files
    missing_files = []
    
    # Get all files in the audio folder for matching
    audio_files = set(os.listdir(audio_folder))
    
    print("Processing audio files...")
    for _, row in tqdm(df.iterrows(), total=len(df)):
        filename = row['filename']
        
        # Try to find the audio file (with or without extension)
        audio_path = None
        
        if has_extension:
            # Direct match if filename includes extension
            if filename in audio_files:
                audio_path = os.path.join(audio_folder, filename)
        else:
            # Try common audio extensions if filename doesn't include one
            for ext in ['.wav', '.mp3', '.flac', '.m4a', '.ogg']:
                potential_filename = filename + ext
                if potential_filename in audio_files:
                    audio_path = os.path.join(audio_folder, potential_filename)
                    break
            
            # If still not found, check if any file starts with this name
            if audio_path is None:
                matches = [f for f in audio_files if f.startswith(filename)]
                if matches:
                    audio_path = os.path.join(audio_folder, matches[0])
        
        if audio_path is None or not os.path.exists(audio_path):
            missing_files.append(filename)
            continue
        
        # Add to dataset
        data_dict["audio"].append(audio_path)
        data_dict["text"].append(row['transcript'])
    
    print(f"Found {len(data_dict['audio'])} valid audio files with transcripts")
    if missing_files:
        print(f"Warning: {len(missing_files)} audio files were missing")
        print(f"First 5 missing files: {missing_files[:5]}")
    
    # Create the dataset
    dataset = Dataset.from_dict(data_dict)
    
    # Add audio feature
    dataset = dataset.cast_column("audio", Audio())
    
    # Split the dataset if needed
    if split_ratio:
        splits = dataset.train_test_split(
            train_size=split_ratio.get("train", 0.8),
            test_size=split_ratio.get("test", 0.2)
        )
        
        # Further split train into train/validation if specified
        if "validation" in split_ratio and split_ratio["validation"] > 0:
            val_size = split_ratio["validation"] / (split_ratio["train"] + split_ratio["validation"])
            train_val = splits["train"].train_test_split(test_size=val_size)
            dataset_dict = {
                "train": train_val["train"],
                "validation": train_val["test"],
                "test": splits["test"]
            }
        else:
            dataset_dict = splits
            
        # Save each split
        for split_name, split_data in dataset_dict.items():
            split_path = os.path.join(output_path, split_name)
            os.makedirs(split_path, exist_ok=True)
            
            # Save metadata for this split
            split_data.to_json(os.path.join(split_path, "metadata.jsonl"), orient="records", lines=True)
            print(f"Saved {split_name} split with {len(split_data)} examples")
    else:
        # Save metadata
        dataset.to_json(os.path.join(output_path, "metadata.jsonl"), orient="records", lines=True)
        print(f"Saved dataset with {len(dataset)} examples")
    
    # Create the dataset_info.json file
    dataset_info = {
        "description": "Speech recognition dataset",
        "citation": "",
        "homepage": "",
        "license": "",
        "features": {
            "audio": {
                "dtype": "audio",
                "_type": "Audio"
            },
            "text": {
                "dtype": "string",
                "_type": "Value"
            }
        }
    }
    
    with open(os.path.join(output_path, "dataset_info.json"), "w") as f:
        json.dump(dataset_info, f, indent=2)
    
    print(f"\nDataset prepared and saved to {output_path}")
    print("You can now load it with: dataset = load_dataset('path', data_dir='" + output_path + "')")
    
    return dataset

def fine_tune_whisper(dataset_path, model_name="openai/whisper-small", output_dir="./whisper-finetuned"):
    """
    Fine-tune a Whisper model on the prepared dataset.
    
    Args:
        dataset_path: Path to the prepared dataset
        model_name: Name of the Whisper model to fine-tune
        output_dir: Directory to save the fine-tuned model
    """
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    from transformers import Seq2SeqTrainingArguments, Seq2SeqTrainer
    
    # Load the dataset
    dataset = load_dataset("json", data_files=os.path.join(dataset_path, "metadata.jsonl"))
    dataset = dataset["train"]
    
    # Split for training if not already split
    if "validation" not in dataset.column_names:
        splits = dataset.train_test_split(test_size=0.1)
        dataset = {
            "train": splits["train"],
            "validation": splits["test"]
        }
    
    # Load the model and processor
    processor = WhisperProcessor.from_pretrained(model_name)
    model = WhisperForConditionalGeneration.from_pretrained(model_name)
    
    # Enable gradient checkpointing to save memory
    model.gradient_checkpointing_enable()
    
    # Prepare features
    def prepare_dataset(examples):
        # Load and resample audio data
        audio = examples["audio"]
        
        # Process audio
        input_features = processor(
            audio["array"], 
            sampling_rate=audio["sampling_rate"],
            return_tensors="pt"
        ).input_features
        
        # Process text
        labels = processor.tokenizer(examples["text"]).input_ids
        
        examples["input_features"] = input_features[0]
        examples["labels"] = labels
        
        return examples
    
    # Map the prepare function to the dataset
    processed_dataset = {}
    for split in dataset:
        processed_dataset[split] = dataset[split].map(
            prepare_dataset, 
            remove_columns=dataset[split].column_names,
            num_proc=4
        )
    
    # Set up training arguments
    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=8,
        gradient_accumulation_steps=2,
        learning_rate=1e-5,
        warmup_steps=500,
        max_steps=4000,
        evaluation_strategy="steps",
        eval_steps=500,
        save_strategy="steps",
        save_steps=500,
        generation_max_length=225,
        logging_steps=25,
        report_to=["tensorboard"],
        load_best_model_at_end=True,
        metric_for_best_model="wer",
        push_to_hub=False,
        fp16=True,  
    )
    
    # Define the trainer
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=processed_dataset["train"],
        eval_dataset=processed_dataset["validation"],
    )
    
    # Start training
    print("Starting fine-tuning...")
    trainer.train()
    
    # Save the model
    model.save_pretrained(os.path.join(output_dir, "final_model"))
    processor.save_pretrained(os.path.join(output_dir, "final_model"))
    
    print(f"Model fine-tuning completed. Saved to {output_dir}")

if __name__ == "__main__":
    
    prepare_dataset_from_custom_metadata(
        metadata_path="dataset_2023/metadata.csv", 
        audio_folder="dataset_2023/clips",    
        output_path="path/to/prepared_dataset",
        split_ratio={"train": 0.8, "validation": 0.1, "test": 0.1}
    )
    
    # Uncomment to run fine-tuning after dataset preparation
    # fine_tune_whisper(dataset_path="path/to/prepared_dataset")