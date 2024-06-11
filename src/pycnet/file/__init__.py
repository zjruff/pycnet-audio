"""Defines functions for various file handling tasks. 

Functions:

    buildFilename
        Construct a filename using a prefix and a timestamp.

    findFiles
        List all paths with a given extension in a directory 
        tree.

    getFileSize
        Return the size of a file in human-readable units.

    getFolder
        Return the location of a file relative to a higher-level
        folder.

    inventoryFolder
        Inventory .wav files in a folder and write the info to a file.

    makeFileInventory
        Build a table of basic attributes for a list of files.

    massRenameFiles
        Rename files with a given extension in a directory tree (or 
        undo this operation if previously performed).

    removeSpectroDir
        Recursively remove temporary files and folders.

    renameFiles
        Rename files based on values in a DataFrame.

    summarizeInventory
        Summarize a table of info on .wav files in human-readable form.

"""

import datetime as dt
import os
import wave
import pandas as pd
from pathlib import Path

from . import image
from . import wav


def findFiles(top_dir, file_ext):
    """List all files with a given extension in a directory tree.

    Args:

        top_dir (str): Path to the root of the directory tree to be 
            searched.

        file_ext (str): File extension of files to look for. A leading 
            dot (.) is not necessary but will not hurt anything.

    Returns:

        list[str]: A sorted list of paths to files with extension 
        file_ext in the directory tree rooted at top_dir.
    """

    files_found = []
    for root, dirs, files in os.walk(top_dir):
        for file in files:
            if file.split('.')[-1] == file_ext.replace('.', ''):
                files_found.append(os.path.join(root, file))
    return sorted(files_found)


def getFileSize(file_path, units='gb'):
    """Return the size of a file in human-readable units. 

    By default the file size will be returned in GB (gibibytes); other 
    options include MB, KB, and plain bytes.

    Args:

        file_path (str): path to the target file.

        units (str): units to use when reporting file size ('gb' for 
            gibibytes, 'mb' for mebibytes, 'kb' for kibibytes, and 'b'
            for bytes).

    Returns:

        float: The size of the target file in the units specified.
    """
    
    unit_key = {'gb':-3, 'mb':-2, 'kb':-1, 'b':0}
    convert_exp = unit_key.get(units, -3)
    conversion = 1024**convert_exp
    file_size = os.path.getsize(file_path) * conversion
    return file_size


def getFolder(file_path, top_dir):
    """Return the location of a file relative to a higher-level folder.

    Args:

        file_path (str): Path to the target file.

        top_dir (str): Path to the folder relative to which the file's 
            location will be reported.

    Returns:
        str: Path to the folder containing file_path relative to 
        top_dir.
    """

    file_dir = Path(file_path).parent
    top_dir_path = Path(top_dir)
    file_folder = file_dir.relative_to(top_dir_path)
    return file_folder


def makeFileInventory(path_list, top_dir, use_abs_path=False):
    """Build a table of basic attributes for a list of files.

    Args:

        path_list (list): List of paths of files to be examined.

        top_dir (str): Path to the folder that will be used to create 
            relative paths.

        use_abs_path (bool): Whether to list the full path of the 
            folder containing each file in the Folder column of the 
            resulting DataFrame.

    Returns:

        Pandas.DataFrame: DataFrame with one row for each .wav file 
        listing its folder (absolute or relative to top_dir), filename,
        size in bytes, and duration in seconds.
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


def summarizeInventory(wav_inventory):
    """Summarize a table of info on .wav files in human-readable form.

    Args:

        wav_inventory (Pandas.DataFrame): DataFrame containing 
            information on .wav files in a directory tree, as produced 
            by makeFileInventory.

    Returns:

        str: A human-readable summary of the audio dataset.
    """

    n_wav_files = len(wav_inventory)
    wav_lengths = wav_inventory["Duration"]
    wav_sizes = wav_inventory["Size"]
    total_dur, total_gb = sum(wav_lengths) / 3600., sum(wav_sizes) / 1024.**3
    summary = "Directory contains {0} .wav files.\nTotal duration: {1:.1f} h\nTotal size: {2:.1f} GB".format(n_wav_files, total_dur, total_gb)
    return summary


def inventoryFolder(target_dir, write_file=True, print_summary=True):
    """Inventory .wav files in a folder and write the info to a file.

    Args:

        target_dir (str): Path of the top-level directory containing 
            .wav files.

        write_file (bool): Whether to write the inventory table to a 
            CSV file.

        print_summary (bool): whether to use summarizeInventory to 
            print a human-readable summary of the .wav files that were
            found.

    Returns:
        Pandas.DataFrame: DataFrame listing each .wav file in the 
        directory tree, its path relative to target_dir, the size of 
        the file, and its duration in seconds.
    """

    if not os.path.isdir(target_dir):
        print("\nNo valid target directory provided.\n")
        return
    else:
        dir_name = os.path.basename(target_dir)
        inv_file = os.path.join(target_dir, "{0}_wav_inventory.csv".format(dir_name))

        wav_paths = findFiles(target_dir, ".wav")
        wav_inventory = makeFileInventory(wav_paths, target_dir)

        if print_summary:
            summarizeInventory(wav_inventory)
        
        if write_file:
            wav_inventory.to_csv(inv_file, index=False)
    
    return wav_inventory


def buildFilename(file_path, prefix=''):
    """Construct a filename using a prefix and a timestamp.

    If no prefix is provided, a prefix will be constructed based on the
    two lowest-level directories containing the file (i.e., the file's 
    grandparent and parent directories).

    If the filename does not already have a timestamp in the right
    format, it will be generated based on the file's modification time.

    Args:

        file_path (str): Full path to the file to be renamed.

        prefix (str): Prefix component of the filename to be generated.

    Returns:

        str: Path to the file following renaming.
    """

    p = Path(file_path)
    file_dir = p.parent
    
    if prefix == '':
        site_name, stn_dir_name = p.parts[-3], p.parts[-2]
        stn_id = stn_dir_name.split('_')[-1]
        new_prefix = "{0}-{1}".format(site_name, stn_id)
    else:
        new_prefix = prefix
    
    old_name, file_ext = p.stem, p.suffix
    
    stamp_fmt = "%Y%m%d_%H%M%S"
    str_stamp = '_'.join(old_name.split('_')[-2:])
    try:
        stamp = dt.datetime.strptime(str_stamp, stamp_fmt)
        new_stamp = str_stamp
    except:
        stamp = dt.datetime.fromtimestamp(os.path.getmtime(file_path))
        new_stamp = stamp.strftime(stamp_fmt)
    
    new_filename = "{0}_{1}{2}".format(new_prefix, new_stamp, file_ext)
    new_path = os.path.join(file_dir, new_filename)
    
    return new_path


def renameFiles(rename_log_df, revert=False):
    """Rename files based on values in a DataFrame.

    Args:

        rename_log_df (Pandas.DataFrame): DataFrame listing the 
            directory, current filenames, and future filenames for a 
            set of files.

        revert (bool): Whether to run in "undo mode" to reverse a 
            previous renaming operation.

    Returns:

        int: The number of files that were successfully renamed, or -1
        if the renaming operation would have resulted in duplicate 
        filenames.
    """

    n_files = len(rename_log_df)
    dirs = rename_log_df["Folder"]
    old_names = rename_log_df["Old_Name"]
    new_names = rename_log_df["New_Name"]
    
    old_paths, new_paths = [], []
    
    for i in range(n_files):
        old_paths.append(os.path.join(dirs[i], old_names[i]))
        new_paths.append(os.path.join(dirs[i], new_names[i]))
    
    rename_from = new_paths if revert else old_paths
    rename_to = old_paths if revert else new_paths
    
    if len(set(new_names)) < n_files:
        return -1
    else:
        rename_count = 0
        for i in range(n_files):
            if rename_from[i] != rename_to[i]:
                os.rename(rename_from[i], rename_to[i])
                rename_count += 1
            else:
                continue
        return rename_count


def massRenameFiles(top_dir, extension, prefix=''):
    """Rename all files with a given extension in a directory tree.

    Runs in 'undo mode' if a file called Rename_Log.csv already exists 
    in the directory provided.

    Args:

        top_dir (str): Path to the root of the directory tree 
            containing files to be renamed.

        extension (str): File extension of files to be found and 
            renamed.

        prefix (str): A prefix to use when constructing filenames.

    Returns:

        Nothing.
    """
    
    rename_log_path = os.path.join(top_dir, "Rename_Log.csv")
    
    if os.path.exists(rename_log_path):
        rename_log_df = pd.read_csv(rename_log_path)
        print("\nRename_Log.csv already exists. Reverting previously renamed files...\n")
        renameFiles(rename_log_df, revert=True)
        print("Filenames reverted. Rename_Log.csv removed.\n")
        os.remove(rename_log_path)
    else:
        to_rename = findFiles(top_dir, extension)
        n_files = len(to_rename)
        folders, old_names, new_names, changed = [], [], [], []
        
        print("\nFound {0} files with extension {1} in target directory.".format(n_files, extension))
        print("Attempting to standardize filenames...")
        
        for i in range(n_files):
            old_path = to_rename[i]
            file_dir, old_name = os.path.split(old_path)
            
            new_path = buildFilename(old_path)
            new_name = os.path.basename(new_path)
            
            folders.append(file_dir)
            old_names.append(old_name)
            new_names.append(new_name)
            
            if old_path != new_path:
                changed.append('Y')
            else:
                changed.append('N')
    
        rename_log_df = pd.DataFrame(data={"Folder":folders, "Old_Name":old_names, "New_Name":new_names, "Changed":changed})
        
        rename_count = renameFiles(rename_log_df, revert=False)
        
        if rename_count == -1:
            print("\nRenaming would result in duplicate filenames!\n")
            print("Renaming operation canceled.\n")
        elif rename_count == 0:
            print("\nAll filenames are correct. No files were renamed.\n")
        else:
            print("\n{0} of {1} {2} files were renamed.\n".format(rename_count, n_files, extension))
            rename_log_df.to_csv(rename_log_path, index=False)
            print("Results written to {0}.\n".format(rename_log_path))

    return


def removeSpectroDir(target_dir, spectro_dir=None):
    """Recursively remove temporary files and folders.

    Args:

        target_dir (str): Path to the folder containing audio data from
            which spectrograms were generated.

        spectro_dir (str): Path to the folder where the temporary 
            spectrogram folder was created (defaults to target_dir).

    Returns:

        Nothing.
    """
    
    folder_name = os.path.basename(target_dir)
    
    if not spectro_dir:
        image_dir = os.path.join(target_dir, "Temp", "images")
    else:
        image_dir = os.path.join(spectro_dir, folder_name, "images")
    
    if not os.path.exists(image_dir):
        print("Temporary folder not found.")
    else:
        print("Removing temporary folders...", end='')
        if os.name == "nt":
            os.system("rmdir /s /q {0}".format(os.path.dirname(image_dir)))
        else: 
            # os.name should be 'posix' on both Linux and MacOS 
            os.system("rm -rf {0}".format(os.path.dirname(image_dir)))
        print(" done.\n")
    
    return