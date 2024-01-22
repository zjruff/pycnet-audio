"""A script to generate spectrograms representing 12-second segments of
audio in the frequency range [0, 4000 Hz]. Splits up the spectrogram 
generation across multiple folders for neater parallel processing.
"""

import math
import os 
import pathlib
import subprocess
import sys
import time
import wave
import multiprocessing as mp
from multiprocessing import JoinableQueue, Process, Queue

PACKAGEDIR = pathlib.Path(__file__).parents[1].absolute()
sys.path.append(str(PACKAGEDIR))

import pycnet

# Adjust this if necessary
sox_path = pycnet.sox_path


def main():
    n_cores = min(mp.cpu_count(), 10)

    target_dir= sys.argv[1]
    try:
        output_dir = sys.argv[2]
        image_dir = os.path.join(output_dir, os.path.basename(target_dir), "images")
    except:
        output_dir = target_dir
        image_dir = os.path.join(output_dir, "Temp", "images")

    wav_paths = pycnet.file.findFiles(target_dir, ".wav")
    wav_inventory = pycnet.file.makeFileInventory(wav_paths, target_dir)
    inv_file = os.path.join(target_dir, "Wav_Inventory.csv")
    wav_inventory.to_csv(inv_file, index=False)
    
    n_wav_files = len(wav_paths)

    wav_lengths = wav_inventory["Duration"]
    wav_sizes = wav_inventory["Size"]
    total_dur, total_gb = sum(wav_lengths) / 3600., sum(wav_sizes) / 1024.**3

    print("\nFound {0} wav files.\nTotal duration: {1:.1f} h\nTotal size: {2:.1f} GB".format(n_wav_files, total_dur, total_gb))

    if n_wav_files == 0:
        print("\nExiting.")
        exit()

    n_images = total_dur * 300
    n_chunks = int(n_images / 50000) + min(n_images % 50000, 1)

    todo = pycnet.file.wav.makeSpectroDirList(wav_paths, image_dir, n_chunks)
    spectro_dirs = list(set([k[1] for k in todo]))
    for l in spectro_dirs:
        if not os.path.exists(l):
            os.makedirs(l)

    wav_queue, done_queue = JoinableQueue(), Queue()
    for i in todo:
        wav_queue.put(i)

    print("\nGenerating spectrograms using {0} cores starting at {1}...".format(n_cores, time.strftime("%H:%M:%S")))

    for j in range(n_cores):
        worker = pycnet.file.wav.WaveWorker(wav_queue, done_queue, sox_path, image_dir)
        worker.daemon = True
        worker.start()

    prog_worker = pycnet.prog.ProgBarWorker(done_queue, n_wav_files)
    prog_worker.daemon = True
    prog_worker.start()

    wav_queue.join()

    pngs = pycnet.file.findFiles(image_dir, "png")

    print(pycnet.prog.makeProgBar(n_wav_files, n_wav_files), end = '\n')
    print("\nFinished at {0}.\n{1} spectrograms generated.\n".format(time.strftime("%H:%M:%S"), len(pngs)))

if __name__ == "__main__":
    main()
