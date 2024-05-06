"""Defines functions for processing .wav audio files."""

import datetime as dt
import math
import multiprocessing as mp
import os
import wave
from multiprocessing import JoinableQueue, Process, Queue


def getWavLength(wav_path, mode='h'):
    """Return the duration of a .wav file in hours or seconds. 
    
    Arguments:
    - wav_path: path to the .wav file.
    - mode: units for the return value. Default is 'h' (hours). Set
    mode='s' to return length in seconds.
    
    Returns:
    Duration of the .wav file in hours or seconds.
    """
    try:
        with wave.open(wav_path) as w:
            nframes, framerate = w.getnframes(), w.getframerate()
        wav_length_s = float(nframes) / framerate
    except:
        wav_length_s = 0
    if mode == 'h':
        wav_length_h = wav_length_s / 3600.
        return wav_length_h
    else:
        return wav_length_s


def makeSoxCmds(wav_path, output_dir):
    """Generate SoX commands to create spectrograms from a .wav file.
    
    Generate a list of SoX commands to create spectrograms representing
    non-overlapping 12-s segments of audio from the .wav file provided.
    
    Arguments:
    - wav_path: path to the .wav file.
    - output_dir: folder where spectrogram files will be generated.
    
    Returns:
    A list of commands to be executed by SoX.
    """
    wav_name = os.path.basename(wav_path)
    wav_length = getWavLength(wav_path, 's')
    n_segments = int(wav_length / 12) + 1
    n_digits = max(len(str(n_segments)), 3)
    sox_cmds = []
    for i in range(1, n_segments+1):
        offs = 12 * (i - 1)
        if offs + 12 > wav_length:
            dur = wav_length - offs
            if dur < 8:
                continue
        else:
            dur = 12
        png_name = wav_name.replace(wav_name[-4:], "_part_{0}.png".format(str(i).zfill(n_digits)))
        png_path = os.path.join(output_dir, png_name)
        sox_cmd = 'sox "{0}" -V1 -n trim {1} {2} remix 1 rate 8k spectrogram -x 1000 -y 257 -z 90 -m -r -o {3}'.format(wav_path, offs, dur, png_path)
        sox_cmds.append(sox_cmd)
    return sox_cmds


def makeSpectroDirList(wav_list, image_dir, n_chunks):
    """Map input .wav files to multiple output directories.
    
    Divides the full list of .wav files to be processed into several
    chunks and designates a folder to hold spectrograms from each chunk 
    to facilitate parallel processing.
    
    Arguments:
    - wav_list: a list of .wav files from which spectrograms will be 
    generated.
    - image_dir: the directory where spectrograms will be generated (in
    subfolders as needed).
    - n_chunks: the number of subfolders to create.
    
    Returns:
    A list of tuples each containing the path to a .wav file and the
    folder where spectrograms from that file will be generated.
    """
    chunk_size = int(len(wav_list) / n_chunks) + 1
    n_digits = int(math.log10(n_chunks)) + 1
    wav_chunks = [int(i / chunk_size) + 1 for i in range(len(wav_list))]
    dst_dirs = [os.path.join(image_dir, "part_{0}".format(str(j).zfill(n_digits))) for j in wav_chunks]
    wav_key = list(zip(wav_list, dst_dirs))
    return wav_key


class WaveWorker(Process):
    """ Worker process to generate spectrograms from wave files.
    
    Arguments:
    - in_queue: a Multiprocessing.JoinableQueue containing tuples in 
    the format (wav_path, spectro_dir).
    - done_queue: a Multiprocessing.Queue to hold paths of wav files 
    that have already been processed, used to build a progress bar.
    
    Methods:
    - run: get the next available item from in_queue, consisting of a
    .wav file and an output directory. Generate a set of sox commands
    to generate a set of spectrograms from the .wav file in the output
    directory, then execute those commands. When finished, put the path
    to the .wav file in done_queue.
    """
    def __init__(self, in_queue, done_queue, output_dir):
        Process.__init__(self)
        self.in_queue = in_queue
        self.done_queue = done_queue
        self.output_dir = output_dir
    
    def run(self):
        while True:
            wav_path, spectro_dir = self.in_queue.get()
            sox_cmds = makeSoxCmds(wav_path, spectro_dir)
            for i in sox_cmds:
                os.system(i)
            self.in_queue.task_done()
            self.done_queue.put(wav_path)