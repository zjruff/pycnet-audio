"""Build an inventory of files with a .wav extension under the target
directory and write it to a comma-separated text file. Information
includes the subfolder (relative to the target directory), size of each
file in bytes, and duration of each file in seconds.
"""

import os
import pathlib
import sys

import pycnet

def main():
    target_dir= sys.argv[1]
    
    if not os.path.isdir(target_dir):
        print("\nNo valid target directory provided.\nExiting...\n")
        exit()
    else:
        dir_name = os.path.basename(target_dir)
        inv_file = os.path.join(target_dir, "{0}_wav_inventory.csv".format(dir_name))

        wav_paths = pycnet.file.findFiles(target_dir, ".wav")
        wav_inventory = pycnet.file.makeFileInventory(wav_paths, target_dir)
        wav_inventory.to_csv(inv_file, index=False)
        
        n_wav_files = len(wav_paths)
        wav_lengths = wav_inventory["Duration"]
        wav_sizes = wav_inventory["Size"]
        total_dur, total_gb = sum(wav_lengths) / 3600., sum(wav_sizes) / 1024.**3

        print("\nFound {0} wav files.\nTotal duration: {1:.1f} h\nTotal size: {2:.1f} GB\n".format(n_wav_files, total_dur, total_gb))
        
        print("File information written to {0}.\n".format(inv_file))

if __name__ == "__main__":
    main()