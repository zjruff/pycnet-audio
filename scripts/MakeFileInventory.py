import os
import pathlib
import sys

PACKAGEDIR = pathlib.Path(__file__).parents[1].absolute()
sys.path.append(str(PACKAGEDIR))

from pycnet import file

def main():
    target_dir= sys.argv[1]

    wav_paths = file.findFiles(target_dir, ".wav")
    wav_inventory = file.makeFileInventory(wav_paths, target_dir)
    inv_file = os.path.join(target_dir, "Wav_Inventory.csv")
    wav_inventory.to_csv(inv_file, index=False)
    
    n_wav_files = len(wav_paths)
    wav_lengths = wav_inventory["Duration"]
    wav_sizes = wav_inventory["Size"]
    total_dur, total_gb = sum(wav_lengths) / 3600., sum(wav_sizes) / 1024.**3

    print("\nFound {0} wav files.\nTotal duration: {1:.1f} h\nTotal size: {2:.1f} GB\n".format(n_wav_files, total_dur, total_gb))

if __name__ == "__main__":
    main()