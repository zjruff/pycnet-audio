"""A script to generate spectrograms representing 12-second segments of
audio in the frequency range [0, 4000 Hz]. Splits up the spectrogram 
generation across multiple folders for neater parallel processing.
"""

import os 
import pandas as pd
import sys
import time
import multiprocessing as mp
from multiprocessing import JoinableQueue, Queue

import pycnet

n_cores = min(mp.cpu_count(), 10)

def main():
    target_dir= sys.argv[1]
    try:
        output_dir = sys.argv[2]
        image_dir = os.path.join(output_dir, os.path.basename(target_dir), "images")
    except:
        output_dir = target_dir
        image_dir = os.path.join(output_dir, "Temp", "images")

    inv_file = os.path.join(target_dir, "{0}_wav_inventory.csv".format(os.path.basename(target_dir)))
    if not os.path.exists(inv_file):
        wav_inventory = pycnet.file.inventoryFolder(target_dir)
    else:
        wav_inventory = pd.read_csv(inv_file)
        pycnet.file.summarizeInventory(wav_inventory)
    
    n_wav_files = len(wav_inventory)

    if n_wav_files == 0:
        print("\nExiting...")
        exit()

    print("\nGenerating spectrograms using {0} cores starting at {1}...".format(n_cores, time.strftime("%H:%M:%S")))
    
    proc_queue = pycnet.process.buildProcQueue(target_dir, image_dir)

    pycnet.process.generateSpectrograms(proc_queue, n_cores)

    pngs = pycnet.file.findFiles(image_dir, "png")
    print("\nFinished at {0}.\n{1} spectrograms generated.\n".format(time.strftime("%H:%M:%S"), len(pngs)))

if __name__ == "__main__":
    main()
