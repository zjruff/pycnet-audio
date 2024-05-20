"""Defines functions and classes for processing .wav audio files.

Functions:

    getWavLength
        Measure the duration of a .wav file.

    makeSoxCmds
        Build a set of commands to be executed by SoX to generate 
        spectrograms from a .wav file.

    makeSpectroDirList 
        Map a set of .wav files to a set of temporary output 
        directories where spectrograms will be generated.

Classes:

    WaveWorker
        Worker process that generates spectrograms from audio files 
        using SoX.
"""

import datetime as dt
import math
import multiprocessing as mp
import os
import wave
from multiprocessing import JoinableQueue, Process, Queue


def getWavLength(wav_path, mode='h'):
    """Return the duration of a .wav file in hours or seconds. 
    
    Args:
    
        wav_path (str): Path to the .wav file.
        
        mode (str): Units for the return value. Default is 'h' (hours).
            Set mode='s' to return duration in seconds.
    
    Returns:
        
        float: Duration of the .wav file in hours or seconds, or 0 if
        the file's duration could not be determined.
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
    
    Generates a list of SoX commands to create spectrograms representing
    segments of audio from the .wav file provided.
    
    Args:
    
        wav_path (str): Path to the .wav file.
        
        output_dir (str): Path to the folder where spectrogram files 
            will be generated.
    
    Returns:
    
        list[str]: A list of commands to be executed by SoX.
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
    
    Args:
    
        wav_list (list): List of paths to .wav files from which 
            spectrograms will be generated.
        
        image_dir (str): Path to the directory where spectrograms will
            be generated (in subfolders as needed).
        
        n_chunks (int): The number of subfolders to create.
    
    Returns:
        
        list: A list of tuples (wav_path, output_dir), each containing 
        the path to a .wav file and the folder where spectrograms from
        that file will be generated.
    """
    
    chunk_size = int(len(wav_list) / n_chunks) + 1
    n_digits = int(math.log10(n_chunks)) + 1
    wav_chunks = [int(i / chunk_size) + 1 for i in range(len(wav_list))]
    dst_dirs = [os.path.join(image_dir, "part_{0}".format(str(j).zfill(n_digits))) for j in wav_chunks]
    wav_key = list(zip(wav_list, dst_dirs))
    return wav_key


class WaveWorker(Process):
    """ Worker process to generate spectrograms from wave files.

    When running, the worker will fetch the next available item from 
    in_queue, consisting of a .wav file and an output directory. 
    It will create a set of sox commands to generate a set of 
    spectrograms from the .wav file in the output directory, then 
    execute those commands sequentially using os.system. When finished,
    the path to the .wav file will be placed in done_queue.
    
    Attributes:
        
        in_queue (Multiprocessing.JoinableQueue): Queue containing 
            tuples in the format (wav_path, output_dir).
        
        done_queue (Multiprocessing.Queue): Queue to hold paths to .wav
            files that have already been processed.
        
        output_dir (str): Path to the directory where spectrograms 
            should be generated.
    """

    def __init__(self, in_queue, done_queue, output_dir):
        """Initializes the instance with input and output queues.
        
        Args:
            
            in_queue (multiprocessing.JoinableQueue): Queue containing
                input data in the form of tuples (wav_path, 
                output_dir). 
            
            done_queue (multiprocessing.Queue: Queue where paths to 
                .wav files that have already been processed should go.
            
            output_dir (str): Path to the directory where spectrograms
                should be generated.
        """

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