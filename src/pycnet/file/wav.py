"""Defines functions and classes for processing audio files.

Functions:

    getWavLength
        Measure the duration of a .wav file.

    getFlacLength
        Measure the duration of a .flac file.

    getAudioFileInfo
        Get general audio file information from SoX.

    makeSoxCmds
        Build a set of commands to be executed by SoX to generate 
        spectrograms from a .wav file.

    makeSpectroDirList 
        Map a set of audio files to a set of temporary output 
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
import re
import subprocess
import wave

from functools import reduce
from multiprocessing import JoinableQueue, Process, Queue
from pathlib import Path


def _to_int_be(data):
    """Convert a big-endian sequence of bytes to a numeric value.
    
    Copied from ``mutagen.flac``:
    https://github.com/quodlibet/mutagen/blob/main/mutagen/flac.py
    """

    return reduce(lambda a, b: (a << 8) + b, bytearray(data), 0)


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
    
    wav_path = str(wav_path) # wave.open chokes on pathlib.Path input

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


def getFlacLength(flac_path, mode='h'):
    """Return the duration of a .flac file in hours or seconds.

    First 38 bytes of any FLAC file contain a FLAC signature (b'fLaC')
    and a "stream info" metadata block listing number of channels, 
    sample rate, etc. Unfortunately some of these values are encoded
    in strings of bits that do not divide nicely into bytes, which 
    necessitates some clever bitwise calculations to convert them into
    numeric values. The calculations seen here are copied from 
    the ``flac`` submodule of the ``mutagen`` package:
    https://github.com/quodlibet/mutagen/blob/main/mutagen/flac.py

    Args:

        flac_path (str): Path to the .flac file.

        mode (str): Units for the return value. Default is 'h' (hours).
            Set mode='s' to return duration in seconds.

    Returns:

        float: Duration of the .flac file in hours or seconds, or 0 if
        the file's duration could not be determined.
    """

    try:
        with open(flac_path, 'rb') as infile: 
            data = infile.read(38)
            flac_sig, stream_info = data[0:4], data[4:]

        if flac_sig != b'fLaC':
            raise
        # first 16 bits of sample rate
        sample_first = _to_int_be(stream_info[14:16])
        # last 4 bits of sample rate, 3 of channels, first 1 of bits/sample
        sample_channels_bps = _to_int_be(stream_info[16:17])
        # last 4 of bits/sample, 36 of total samples
        bps_total = _to_int_be(stream_info[17:22])
        total_samples = bps_total & 0xFFFFFFFFF

        sample_tail = sample_channels_bps >> 4
        sample_rate = int((sample_first << 4) + sample_tail)

        dur_s = total_samples / float(sample_rate)
    except:
        dur_s = 0

    if mode == 'h':
        return dur_s / 3600. 
    else:
        return dur_s


def getAudioFileInfo(file_path):
    """Return a string containing information about an audio file.

    This function just runs `sox --i [file_path]`, captures the output 
    from stdout and converts it from a bytestring to UTF-8 text for 
    parsing by other functions.

    Args:

        file_path (str): Path to the audio file.

    Returns:

        str: String containing SoX output. 
    """

    b_wav_info = subprocess.run("sox --i ""{0}""".format(file_path), capture_output=True).stdout
    if len(b_wav_info) == 0:
        return
    else:
        return b_wav_info.decode("utf-8")


def makeSoxCmds(file_path, output_dir, clip_length=12):
    """Generate SoX commands to create spectrograms from an audio file.

    Generates a list of SoX commands to create spectrograms 
    representing segments of audio from the file provided.

    Args:

        file_path (str): Path to an audio (.wav or .flac) file.

        output_dir (str): Path to the folder where spectrogram files 
            will be generated.

    Returns:

        list[str]: A list of commands to be executed by SoX.
    """

    p = Path(file_path)
    filename, ext = p.name, p.suffix

    if ext.lower() == ".wav":
        duration = getWavLength(file_path, 's')
    elif ext.lower() == ".flac":
        duration = getFlacLength(file_path, 's')
    else:
        duration = 0

    n_segments = int(duration / 12) + 1
    n_digits = max(len(str(n_segments)), 3)

    in_paths = [file_path for i in range(n_segments)]
    offsets = [clip_length * i for i in range(n_segments)]
    durs = [min(clip_length, duration - i) for i in offsets]
    str_parts = [f"_part_{j:0{n_digits}}.png" for j in range(1, n_segments+1)]
    out_paths = [Path(output_dir, filename.replace(ext, k)) for k in str_parts]

    sox_vals = zip(in_paths, offsets, durs, out_paths)

    stop = n_segments - 1 if durs[-1] < 8 else n_segments

    sox_cmds = ['sox "{0}" -V1 -n trim {1} {2} remix 1 rate 8k spectrogram -x 1000 -y 257 -z 90 -m -r -o "{3}"'.format(*vals) for vals in sox_vals][:stop]

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

