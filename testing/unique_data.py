import pandas as pd
import os
import shutil
import hashlib

def merge_metadata_files(csv_file1, csv_file2, output_file):
    """
    Merge two metadata CSV files and remove duplicates, using the first column
    as the filename identifier.
    
    Args:
        csv_file1: Path to the first CSV file
        csv_file2: Path to the second CSV file
        output_file: Path to the output merged CSV file
    
    Returns:
        DataFrame with unique entries and a set of unique filenames
    """
    print(f"Reading {csv_file1}...")
    df1 = pd.read_csv(csv_file1, delimiter='|', header=None)
    print(f"Found {len(df1)} entries in first file")
    
    print(f"Reading {csv_file2}...")
    df2 = pd.read_csv(csv_file2, delimiter='|', header=None)
    print(f"Found {len(df2)} entries in second file")
    
    # Get the name of the first column (which contains filenames)
    filename_column = df1.columns[0]
    print(f"Using '{filename_column}' as the filename identifier column")
    
    # Combine both dataframes
    combined_df = pd.concat([df1, df2], ignore_index=True)
    print(f"Combined entries: {len(combined_df)}")
    
    # Drop duplicates based on all columns
    unique_df = combined_df.drop_duplicates()
    print(f"Unique entries after removing duplicates: {len(unique_df)}")
    
    # Get the set of unique filenames from the first column
    unique_filenames = set(unique_df[filename_column])
    print(f"Identified {len(unique_filenames)} unique audio files")
    
    # Save the merged and deduplicated dataframe
    unique_df.to_csv(output_file, index=False)
    print(f"Saved deduplicated metadata to {output_file}")
    
    return unique_df, unique_filenames

def copy_unique_audio_files(source_dir1, source_dir2, dest_dir, unique_filenames):
    """
    Copy unique audio files from source directories to destination directory.
    
    Args:
        source_dir1: First directory containing audio files
        source_dir2: Second directory containing audio files
        dest_dir: Destination directory for unique audio files
        unique_filenames: Set of unique filenames from metadata
    """
    # Create destination directory if it doesn't exist
    os.makedirs(dest_dir, exist_ok=True)
    
    # Track how many files we found and copied
    found_count = 0
    copied_count = 0
    missing_files = set(unique_filenames)  # Track files we couldn't find
    
    # Process source directories
    for source_dir in [source_dir1, source_dir2]:
        print(f"Processing audio files in {source_dir}...")
        
        for filename in os.listdir(source_dir):
            # Check if this file is in our unique filenames
            if filename in unique_filenames:
                found_count += 1
                missing_files.discard(filename)  # Remove from missing set
                
                source_path = os.path.join(source_dir, filename)
                dest_path = os.path.join(dest_dir, filename)
                
                # Only copy if the file doesn't already exist in destination
                if not os.path.exists(dest_path):
                    shutil.copy2(source_path, dest_path)
                    copied_count += 1
    
    print(f"Found {found_count} unique audio files in source directories")
    print(f"Copied {copied_count} files to {dest_dir}")
    
    if missing_files:
        print(f"Warning: Could not find {len(missing_files)} audio files mentioned in metadata")
        print("First 10 missing files:", list(missing_files)[:10])

def calculate_file_hash(filepath):
    """Calculate MD5 hash of a file to identify duplicates by content."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)  # Read in 64k chunks
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def find_duplicate_audio_files(audio_dir):
    """
    Find duplicate audio files based on their content hash.
    
    Args:
        audio_dir: Directory containing audio files
    
    Returns:
        Dictionary mapping hashes to lists of files with that hash
    """
    print(f"Scanning for duplicate audio files in {audio_dir}...")
    hash_map = {}
    
    # Go through all files in the directory
    for filename in os.listdir(audio_dir):
        filepath = os.path.join(audio_dir, filename)
        if os.path.isfile(filepath):
            file_hash = calculate_file_hash(filepath)
            if file_hash in hash_map:
                hash_map[file_hash].append(filename)
            else:
                hash_map[file_hash] = [filename]
    
    # Filter to only hashes with multiple files (duplicates)
    duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}
    
    print(f"Found {sum(len(files) - 1 for files in duplicates.values())} duplicate audio files")
    return duplicates

if __name__ == "__main__":
    # Configuration - update these paths
    csv_file1 = "metadata.csv"
    csv_file2 = "models/metadata.csv"
    output_csv = "datasets/merged_metadata.csv"
    
    audio_dir1 = "clips"
    audio_dir2 = "dataset_2023-03-30_17/clips"
    output_audio_dir = "datasets"
    
    # Process metadata files
    merged_df, unique_filenames = merge_metadata_files(csv_file1, csv_file2, output_csv)
    
    # Copy unique audio files
    copy_unique_audio_files(audio_dir1, audio_dir2, output_audio_dir, unique_filenames)
    
    # Optional: Find any duplicate audio files based on content
    duplicates = find_duplicate_audio_files(output_audio_dir)
    
    if duplicates:
        print("Found the following duplicate audio files by content:")
        for hash_val, files in duplicates.items():
            print(f"  Duplicates: {', '.join(files)}")