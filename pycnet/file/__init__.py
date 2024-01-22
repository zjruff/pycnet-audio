""" Contains various file-handling functions. """

import os
import wave
import pandas as pd
from pathlib import Path

from . import image, wav


def findFiles(top_dir, ext):
    """List all paths with extension <ext> under <top_dir>."""
    files_found = []
    for root, dirs, files in os.walk(top_dir):
        for file in files:
            if file.split('.')[-1] == ext.replace('.', ''):
                files_found.append(os.path.join(root, file))
    return sorted(files_found)


def getFileSize(file_path, mode='gb'):
    """Return the size of the file at <file_path> in human-readable units. 
    
    By default the file size will be returned in GB (gibibytes); other options
    include MB, KB, and plain bytes. 
    """
    mode_key = {'gb':-3, 'mb':-2, 'kb':-1, 'b':0}
    convert_exp = mode_key.get(mode, -3)
    conversion = 1024**convert_exp
    file_size = os.path.getsize(file_path) * conversion
    return file_size


def getFolder(file_path, top_dir):
    """Return the folder of <file_path> relative to <top_dir>."""
    file_dir = Path(file_path).parent
    top_dir_path = Path(top_dir)
    file_folder = file_dir.relative_to(top_dir_path)
    return file_folder


def makeFileInventory(path_list, top_dir, use_abs_path=False):
    """Build a table of basic attributes for a list of files.
    
    Returns a Pandas DataFrame with one row for each file, listing the
    directory (absolute or relative to <top_dir>), filename, size in 
    bytes, and duration in seconds. Duration is obviously only relevant
    to .wav files.
    """
    top_path = Path(top_dir)

    file_dict = {"Folder":[], "Filename":[], "Size":[], "Duration":[]}

    for path in path_list:
        file_path = Path(path)
        if use_abs_path:
            file_dict["Folder"].append(file_path.parent)
        else:
            file_dict["Folder"].append(getFolder(path, top_dir))
        file_dict["Filename"].append(os.path.basename(path))
        file_dict["Size"].append(getFileSize(path, 'b'))
        if file_path.suffix == ".wav":
            file_dict["Duration"].append(wav.getWavLength(path, 's'))
        else:
            file_dict["Duration"].append("NA")

    file_df = pd.DataFrame(data = file_dict)

    return file_df
