"""Defines functions for various file handling tasks. 

Functions:

    buildFilename
        Construct a filename using a prefix and a timestamp.

    buildFilePrefix
        Construct a prefix for a file using one or more wildcards
        based on its location in a directory.

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

    readInventoryFile
        Read a .wav file inventory from a CSV file.

    removeSpectroDir
        Recursively remove temporary files and folders.

    renameFiles
        Rename files based on values in a DataFrame.

    summarizeInventory
        Summarize a table of info on .wav files in human-readable form.

"""

import datetime as dt
import multiprocessing as mp
import os
import re
import wave
import pandas as pd
from pathlib import Path

from . import image
from . import wav


def findFiles(top_dir, file_ext, ignore_case=True):
    """List all files with a given extension in a directory tree.

    Args:

        top_dir (str): Path to the root of the directory tree to be 
            searched.

        file_ext (str): File extension of files to look for. A leading 
            dot (.) is not necessary but will not hurt anything.

        ignore_case (bool): Treat upper- and lowercase file extensions 
            the same. (File paths are case-sensitive on Unix-based 
            systems but not on Windows.)

    Returns:

        list: A sorted list of strings representing paths of files with
        extension file_ext in the directory tree rooted at top_dir.
    """

    ext_no_dot = file_ext.replace('.', '')

    if ignore_case:	
        patt = ''.join(["[{0}{1}]".format(c.lower(), c.upper()) for c in ext_no_dot])
    else:
        patt = ext_no_dot

    glob_patt = "*.{0}".format(patt)

    file_list = sorted([str(x) for x in Path(top_dir).rglob(glob_patt)])

    return file_list


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
    if file_dir == Path(top_dir):
        file_folder = ''
    else:
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
    paths = [Path(p) for p in path_list]

    file_dict = {"Folder":[], "Filename":[], "Size":[], "Duration":[]}

    for p in paths:
        file_dict["Folder"].append(p.parent if use_abs_path else getFolder(p, top_dir))
        file_dict["Filename"].append(p.name)
        file_dict["Size"].append(getFileSize(p, 'b'))
        if p.suffix.lower() == ".wav":
            file_dict["Duration"].append(wav.getWavLength(p, 's'))
        elif p.suffix.lower() == ".flac":
            file_dict["Duration"].append(wav.getFlacLength(p, 's'))
        else:
            file_dict["Duration"].append("NA")

    file_df = pd.DataFrame(data = file_dict)

    return file_df


def buildAudioFileDF(top_dir, file_types=["wav", "flac"], n_workers=None):
    """Get information from a set of audio files in a directory tree.

    Officially the only supported file types are WAV and FLAC. This 
    function uses ``sox --i`` to get information on each file, so it 
    should work with any audio file format that includes a 
    self-describing header.
    
    This is not currently used for anything specific in pycnet; it 
    returns slightly more information than makeFileInventory but is
    much slower. We may try to make it more efficient / useful in 
    future, but don't hold your breath.

    Args:

        top_dir (str): Root of the directory tree to be searched.

        file_types (list): List of file extensions to search for.

        n_workers (int): Number of worker processes to use.

    Returns:

        pandas.DataFrame: DataFrame containing basic info on each file.
    """

    files = []
    for ext in file_types:
        files.extend(findFiles(top_dir, ext))
    files.sort()
    
    n_files = len(files)

    if n_workers is None:
        n_workers = min(n_files, mp.cpu_count())

    with mp.Pool(n_workers) as p:
        file_info_all = ''.join(p.map(wav.getAudioFileInfo, files))

    path_listings = re.findall("Input File[ :]+[\S]+", file_info_all)
    channel_listings = re.findall("Channels[ :]*[0-9]+", file_info_all)
    sample_rate_listings = re.findall("Sample Rate[ :]*[0-9]+", file_info_all)
    n_sample_listings = re.findall("[0-9]+ samples", file_info_all)
    bit_depth_listings = re.findall("Precision[ :]+[0-9]+-bit", file_info_all)

    path_list = [x.split(' ')[-1].replace("'", "") for x in path_listings]
    channels_list = [int(x.split(' ')[-1]) for x in channel_listings]
    sample_rate_list = [int(x.split(' ')[-1]) for x in sample_rate_listings]
    n_samples_list = [int(x.split(' ')[0]) for x in n_sample_listings]
    bit_depth_list = [int(x.split(' ')[-1].replace("-bit", "")) for x in bit_depth_listings]

    duration_list = [n_samples_list[i] / sample_rate_list[i] for i in range(n_files)]
    file_size_list = [os.path.getsize(x) for x in files]
    filename_list = [Path(x).name for x in path_list]
    folder_list = [Path(x).parent.relative_to(top_dir) for x in path_list]

    file_info_df = pd.DataFrame(data = {"Path": path_list,
        "Folder": folder_list,
        "Filename": filename_list,    
        "Channels": channels_list, 
        "Sample_Rate": sample_rate_list, 
        "Samples": n_samples_list,
        "Duration": duration_list,
        "Bit_Depth": bit_depth_list,
        "Size": file_size_list})

    return file_info_df


def readInventoryFile(inventory_path):
    """Read a .wav file inventory dataframe from a CSV file.

    Args:

        inventory_path (str): Path to a CSV file containing information
            on audio files within a folder.

    Returns:

        pandas.DataFrame: DataFrame with one row for each .wav file 
        listing its folder (absolute or relative to top_dir), filename,
        size in bytes, and duration in seconds.
    """

    wav_inventory = pd.read_csv(inventory_path, 
                                converters={"Folder": str, 
                                            "Filename": str, 
                                            "Size": int, 
                                            "Duration": float})

    return wav_inventory


def summarizeInventory(inventory_df, ext=".wav"):
    """Summarize a table of info on audio files in human-readable form.

    Args:

        inventory_df (Pandas.DataFrame): DataFrame containing 
            information on audio files in a directory tree, as produced 
            by makeFileInventory.

        ext (str): Extension of the audio files to be summarized.

    Returns:

        str: A human-readable summary of the audio dataset.
    """

    n_audio_files = len(inventory_df)
    durs = inventory_df["Duration"]
    sizes = inventory_df["Size"]
    total_dur, total_gb = sum(durs) / 3600., sum(sizes) / 1024.**3
    summary = "Directory contains {0} {1} files.\nTotal duration: {2:.1f} h\nTotal size: {3:.1f} GB".format(n_audio_files, ext, total_dur, total_gb)
    return summary


def inventoryFolder(target_dir, write_file=True, print_summary=True, flac_mode=False):
    """Inventory audio files in a folder and write the info to a file.

    Args:

        target_dir (str): Path of the top-level directory containing 
            .wav files.

        write_file (bool): Whether to write the inventory table to a 
            CSV file.

        print_summary (bool): whether to use summarizeInventory to 
            print a human-readable summary of the .wav files that were
            found.

        flac_mode (bool): Inventory .flac files rather than .wav files.

    Returns:

        Pandas.DataFrame: DataFrame listing each audio file in the 
        directory tree, its path relative to target_dir, the size of 
        the file, and its duration in seconds.
    """

    if not os.path.isdir(target_dir):
        print("\nNo valid target directory provided.\n")
        return
    else:
        target_ext = ".flac" if flac_mode else ".wav"
        paths = findFiles(target_dir, target_ext)

        inventory_df = makeFileInventory(paths, target_dir)

        if print_summary:
            print('\n' + summarizeInventory(inventory_df, target_ext) + '\n')

        if write_file:
            dir_name = os.path.basename(target_dir)
            inv_file = os.path.join(target_dir, "{0}_{1}_inventory.csv".format(dir_name, target_ext.replace(".", "")))
            inventory_df.to_csv(inv_file, index=False)

    return inventory_df


def buildFilePrefix(file_path, prefix_string):
    """Create a prefix for a file which may be based on its location.

    Valid wildcards include: ``%p``, the name of the file's parent 
    folder; ``%g``, the name of the file's "grandparent" folder (the 
    parent folder of the parent folder), ``%c``, the partial parent
    folder, i.e. the last component of the parent folder's name split 
    up by underscores, and ``%h``, the partial grandparent folder, i.e.
    the last component of the grandparent folder's name split up by
    underscores.

    Args:

        file_path (str): Full path to the file for which a prefix will
            be generated.

        prefix_string (str): Prefix to use, which may include one or
            more wildcards that will be replaced with components of the
            file's path.

    Returns:
        str: The prefix created by substituting the appropriate path
        components for their corresponding wildcards in the prefix
        string provided.
    """
    file_dir = os.path.dirname(file_path)
    file_dir_comps = file_dir.split(os.sep)
    parent_dir, grandparent_dir = file_dir_comps[-1], file_dir_comps[-2]
    partial_parent = parent_dir.split('_')[-1]
    partial_grandparent = grandparent_dir.split('_')[-1]

    replacements = {"%p":parent_dir, 
                    "%g":grandparent_dir, 
                    "%c":partial_parent,
                    "%h":partial_grandparent}

    for patt in replacements:
        prefix_string = re.sub(patt, replacements[patt], prefix_string)

    return(prefix_string)


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
            Can include wildcards, which will be interpreted by 
            buildFilePrefix().

    Returns:

        str: Path to the file following renaming.
    """

    p = Path(file_path)
    file_dir = p.parent

    if prefix == '':
        prefix = "%g-%c"

    new_prefix = buildFilePrefix(file_path, prefix)

    if re.search("%[a-zA-Z]", new_prefix):
        print("\nWarning: One or more unrecognized wildcard options found in prefix string:", end='')
        print(','.join(re.findall("%[a-zA-Z]", new_prefix)))
        print("\nFilenames containing wildcards may behave unpredictably! Use at your own risk.")

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

    If the values in the New_Name column are not unique, the renaming
    operation will be aborted so as not to produce duplicate filenames
    (including duplicate filenames in different folders). This is 
    indicated by a return value of -1.

    Args:

        rename_log_df (Pandas.DataFrame): DataFrame listing the 
            directory, current filenames, and future filenames for a 
            set of files.

        revert (bool): Whether to run in "undo mode" to reverse a 
            previous renaming operation.

    Returns:

        int: The number of files that were successfully renamed, or -1
        if the renaming operation was aborted due to duplicate 
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


def massRenameFiles(top_dir, extension, prefix=None):
    """Rename all files with a given extension in a directory tree.

    Runs in 'undo mode' if a file called [Folder name]_rename_log.csv 
    already exists in the directory provided.

    Args:

        top_dir (str): Path to the root of the directory tree 
            containing files to be renamed.

        extension (str): File extension of files to be found and 
            renamed.

        prefix (str): A prefix to use when constructing filenames.

    Returns:

        Nothing.
    """

    if prefix is None:
        prefix = ''

    folder_name = os.path.basename(top_dir)
    rename_log_path = os.path.join(top_dir, "{0}_rename_log.csv".format(folder_name))

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

            new_path = buildFilename(old_path, prefix)
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