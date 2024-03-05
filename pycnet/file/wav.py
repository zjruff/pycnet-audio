"""Defines functions for processing .wav audio files."""

import datetime as dt
import math
import multiprocessing as mp
import os
import wave
from multiprocessing import JoinableQueue, Process, Queue


def getWavLength(wav_path, mode='h'):
    """Return the duration of the file at <wav_path> in hours or seconds. 
    
    By default the duration will be expressed in hours; specify mode='s' to
    return duration in seconds instead.
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


def makeSoxCmds(wav_path, sox_path, output_dir):
    """Generate SoX commands to create a set of spectrograms from <wav_file>.
    
    Generate a list of SoX commands to create spectrograms for each 12 s
    of audio in file at <wav_path>. Output files (PNG images) will be generated
    in <output_dir>.
    Can make this more flexible to allow for shorter and/or overlapping
    audio segments.
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
    
    Facilitates parallel processing by breaking up the list of .wav files to 
    be processed into <n_chunks> lists and enumerating a set of corresponding
    output directories, then associating each .wav file with one output 
    directory. Does not actually create the output folders. Return value is a 
    list of tuples.
    """
    chunk_size = int(len(wav_list) / n_chunks) + 1
    n_digits = int(math.log10(n_chunks)) + 1
    wav_chunks = [int(i / chunk_size) + 1 for i in range(len(wav_list))]
    dst_dirs = [os.path.join(image_dir, "part_{0}".format(str(j).zfill(n_digits))) for j in wav_chunks]
    wav_key = list(zip(wav_list, dst_dirs))
    return wav_key


class WaveWorker(Process):
    """ Worker process to generate spectrograms from wave files.
    
    <in_queue> contains tuples in the format (wav_path, spectro_dir).
    <done_queue> contains paths of wav files that have already been processed;
    size of <done_queue> is compared to the total number of wavs to build the
    progress bar.
    <sox_path> is constant but is hardcoded at the top of the package for ease
    of making changes if needed.
    <output_dir> is the top level of the directory where spectrograms will be
    generated; this will typically be split into chunks to be handled by 
    parallel processes.
    """
    def __init__(self, in_queue, done_queue, sox_path, output_dir):
        Process.__init__(self)
        self.in_queue = in_queue
        self.done_queue = done_queue
        self.sox_path = sox_path
        self.output_dir = output_dir
    
    def run(self):
        while True:
            wav_path, spectro_dir = self.in_queue.get()
            sox_cmds = makeSoxCmds(wav_path, self.sox_path, spectro_dir)
            for i in sox_cmds:
                os.system(i)
            self.in_queue.task_done()
            self.done_queue.put(wav_path)