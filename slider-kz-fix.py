import os
import re
from mutagen.easyid3 import EasyID3 #pip3 install mutagen

# Path to the folder containing MP3 files
folder_path = '/Users/geoff/Downloads/'

# Regex pattern to extract artist and title
pattern = re.compile(r'(.+?) - (.+?) \[www\.slider\.kz\]\.mp3')

# Iterate over each file in the folder
for filename in os.listdir(folder_path):
    # Check if the file matches the pattern
    match = pattern.match(filename)
    if match:
        artist = match.group(1)
        title = match.group(2)
        
        # New filename without the [www.slider.kz] suffix
        new_filename = f"{artist} - {title}.mp3"
        old_filepath = os.path.join(folder_path, filename)
        new_filepath = os.path.join(folder_path, new_filename)
        
        # Rename the file
        os.rename(old_filepath, new_filepath)
        print(f"Renamed: {filename} -> {new_filename}")
        
        # Set ID3 tags (artist and title)
        try:
            audio = EasyID3(new_filepath)
        except mutagen.id3.ID3NoHeaderError:
            audio = EasyID3()
        
        audio['artist'] = artist
        audio['title'] = title
        audio.save()
        
        print(f"ID3 tags set for: {new_filename}")

print("All files processed.")
