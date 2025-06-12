# main.py
import re
import argparse
from collections import defaultdict

def preprocess_text(text):
    "Changing numbers to letters if there are any"
    num_to_words_albanian = {
        '0': 'zero', '1': 'një', '2': 'dy', '3': 'tre', '4': 'katër',
        '5': 'pesë', '6': 'gjashtë', '7': 'shtatë', '8': 'tetë', '9': 'nëntë'
    }

    def replace_numbers(s):
    
        words = s.split()
        new_words = []
        for word in words:
            if word.isdigit():
                 new_words.extend([num_to_words_albanian.get(char, char) for char in word])
            else:
                 new_words.append(word)
        return ' '.join(new_words)

    text = text.lower()
    text = re.sub(r'[^\w\s\']', '', text) 
    text = replace_numbers(text)
    return text.split()

def calculate_wer(reference, hypothesis):

    ref_len = len(reference)
    hyp_len = len(hypothesis)
    
    # Using a 1D array for space optimization is possible, but for clarity and 
    # backtracking to count S/D/I, a 2D matrix is simpler to understand.
    dp = [[0] * (hyp_len + 1) for _ in range(ref_len + 1)]

    for i in range(ref_len + 1):
        for j in range(hyp_len + 1):
            if i == 0:
                dp[i][j] = j  # Deletions to match an empty reference
            elif j == 0:
                dp[i][j] = i  # Insertions to match an empty hypothesis
            else:
                cost = 0 if reference[i-1] == hypothesis[j-1] else 1
                dp[i][j] = min(dp[i-1][j] + 1,        # Deletion
                               dp[i][j-1] + 1,        # Insertion
                               dp[i-1][j-1] + cost)  # Substitution

    # Backtrack to count S, D, I
    substitutions = deletions = insertions = 0
    i, j = ref_len, hyp_len
    while i > 0 or j > 0:
        if i > 0 and j > 0 and reference[i-1] == hypothesis[j-1]:
            i, j = i-1, j-1
            continue

        if i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
            substitutions += 1
            i, j = i-1, j-1
        elif j > 0 and dp[i][j] == dp[i][j-1] + 1:
            insertions += 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i-1][j] + 1:
            deletions += 1
            i -= 1
        else: # This case handles moving from (0,0)
            break
            
    if ref_len == 0:
        wer = float('inf') if hyp_len > 0 else 0
    else:
        wer = (substitutions + deletions + insertions) / ref_len
        
    return wer, substitutions, deletions, insertions

def parse_transcript_file(file_path):
    """
    Parses a file with the format 'video_id:text' into a dictionary.
    
    Args:
        file_path (str): The path to the transcript file.
        
    Returns:
        dict: A dictionary mapping video_id to its transcript.
    """
    transcripts = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if ':' in line:
                    # Split only on the first colon to handle colons in the text
                    video_id, text = line.split(':', 1)
                    transcripts[video_id.strip()] = text.strip()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred while reading {file_path}: {e}")
        return None
        
    return transcripts

def main(ref_file_path, hyp_file_path):
    # Parse both files into dictionaries
    reference_transcripts = parse_transcript_file(ref_file_path)
    hypothesis_transcripts = parse_transcript_file(hyp_file_path)

    if reference_transcripts is None or hypothesis_transcripts is None:
        print("Could not proceed due to file reading errors.")
        return

    total_substitutions = 0
    total_deletions = 0
    total_insertions = 0
    total_reference_words = 0
    matched_files_count = 0

    print("-" * 50)
    print("Individual File WER Calculation:")
    print("-" * 50)

    # Iterate through the ground truth file to find matches
    for video_id, ref_text in reference_transcripts.items():
        if video_id in hypothesis_transcripts:
            hyp_text = hypothesis_transcripts[video_id]
            matched_files_count += 1

            # Preprocess both texts
            reference_words = preprocess_text(ref_text)
            hypothesis_words = preprocess_text(hyp_text)
            
            # Calculate WER for the current pair
            wer, s, d, i = calculate_wer(reference_words, hypothesis_words)
            
            # Aggregate totals for overall calculation
            total_substitutions += s
            total_deletions += d
            total_insertions += i
            total_reference_words += len(reference_words)
            
            print(f"File: {video_id}")
            print(f"  - WER: {wer:.2%}, S: {s}, D: {d}, I: {i}\n")
        else:
            print(f"File: {video_id} (Not found in hypothesis file, skipping)\n")

    # Calculate overall WER
    if total_reference_words > 0:
        overall_wer = (total_substitutions + total_deletions + total_insertions) / total_reference_words
    else:
        overall_wer = 0.0

    print("-" * 50)
    print("Overall Summary:")
    print("-" * 50)
    print(f"Total files matched: {matched_files_count}")
    print(f"Total words in reference: {total_reference_words}")
    print(f"Total Substitutions: {total_substitutions}")
    print(f"Total Deletions: {total_deletions}")
    print(f"Total Insertions: {total_insertions}")
    print(f"Overall Word Error Rate (WER): {overall_wer:.2%}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate Word Error Rate (WER) for transcript files keyed by video_id.")
    parser.add_argument("reference_file", help="The path to the ground truth reference file (format: video_id:text).")
    parser.add_argument("hypothesis_file", help="The path to the hypothesis file to be checked (format: video_id:text).")
    args = parser.parse_args()
    
    main(args.reference_file, args.hypothesis_file)