import os
from deep_translator import GoogleTranslator

# Define target languages with their codes and file suffixes
languages = {
    'en': 'English',
    'de': 'German', 
    'es': 'Spanish',
    'ja': 'Japanese',
    'zh': 'Chinese',
    'it': 'Italian'
}

# Input file to process
input_file = 'neura/transcriptions_neura.txt'

def translate_file(input_file, target_lang, lang_name):
    """
    Translate a transcription file to the target language
    """
    try:
        # Read the input file
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Create translator instance
        translator = GoogleTranslator(source='sq', target=target_lang)  # sq = Albanian
        
        # Prepare translated lines
        translated_lines = []
        
        print(f"Translating {input_file} to {lang_name}...")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if ':' in line:
                # Split at the first colon to separate filename from text
                filename_part, text_part = line.split(':', 1)
                
                # Translate the text part
                try:
                    translated_text = translator.translate(text_part.strip())
                    translated_line = f"{filename_part}:{translated_text}"
                    translated_lines.append(translated_line)
                    
                    # Progress indicator
                    if (i + 1) % 10 == 0:
                        print(f"  Processed {i + 1}/{len(lines)} lines")
                        
                except Exception as e:
                    print(f"  Error translating line {i + 1}: {e}")
                    # Keep original line if translation fails
                    translated_lines.append(line)
            else:
                # Keep lines without colon as-is
                translated_lines.append(line)
        
        # Determine output filename based on input file
        if 'neura' in input_file:
            output_file = f"neura/{target_lang}_translation.txt"
            # Create neura directory if it doesn't exist
            os.makedirs('neura', exist_ok=True)
        else:
            output_file = f"{target_lang}_translation.txt"
        
        # Write translated content to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in translated_lines:
                f.write(line + '\n')
        
        print(f"  ✓ Created {output_file}")
        
    except FileNotFoundError:
        print(f"  ✗ Input file {input_file} not found")
    except Exception as e:
        print(f"  ✗ Error processing {input_file}: {e}")

def main():
    """
    Main function to process the input file for all target languages
    """
    print("Starting translation process...")
    print("=" * 50)
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Input file not found: {input_file}")
        print("Please ensure the input file is present.")
        return
    
    # Process the input file for each target language
    print(f"Processing: {input_file}")
    print("-" * 30)
    
    for lang_code, lang_name in languages.items():
        translate_file(input_file, lang_code, lang_name)
    
    print("\n" + "=" * 50)
    print("Translation process completed!")
    print("\nCreated files:")
    
    # List all created translation files
    for lang_code in languages.keys():
        if 'neura' in input_file:
            output_file = f"neura/{lang_code}_translation.txt"
        else:
            output_file = f"{lang_code}_translation.txt"
        
        if os.path.exists(output_file):
            print(f"  ✓ {output_file}")

if __name__ == "__main__":
    main()
