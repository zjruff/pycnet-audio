"""Defines functions for generating a set of apparent detections of one
or more target classes based on a set of PNW-Cnet class scores.
See target_classes.csv for a complete list of sonotypes detected by
PNW-Cnet v4 and v5 and their respective codes / labels.

Functions:

    buildClipDataFrame
        Produce a table listing when each clip was recorded.

    getApparentDetections
        Find apparent detections of one class at one score threshold 
        within a set of class scores.

    getClipInfo
        Infer information about a file from its filename.

    getDefaultReviewSettings
        Decide which score threshold to use for each target class when 
        no review_settings file was provided.
        
    getSourceFile
        Return the name of the .wav file from which a clip was taken.
    
    getSourceFolders
        Get locations of a set of files within a directory tree.

    makeKscopeReviewTable
        Produce a table of apparent detections, formatted to be 
        exported as a CSV file and browsed / tagged in Kaleidoscope.
    
    makeReviewTable
        Produce a table of apparent detections of one or more target 
        classes for manual review.

    parseStrReviewCriteria
        Read a mapping of target classes to score thresholds from a
        string provided by the user.

    readPredFile
        Read a table of PNW-Cnet class scores from a CSV file.

    readReviewSettings
        Read a mapping of target classes to score thresholds from a CSV
        file.

    summarizeRecordingEffort
        Summarize the number of clips and amount of recording time by 
        site, station and date.

    summarizeDetections
        Tally up apparent detections of all target classes from a set 
        of class scores across a range of score thresholds.

    tallyDetections
        Tally up the number of apparent detections for all classes in a
        set of class scores at a single threshold.
"""

from datetime import datetime, timedelta
import multiprocessing as mp
import os
import pycnet
import re
import sys
import pandas as pd

from pathlib import Path
from pycnet.cnet import v4_class_names, v5_class_names


def readPredFile(pred_file_path):
    """Read a table of PNW-Cnet class scores from a CSV file.

    Args:

        pred_file_path (str): Path to the file containing the class 
            scores.

    Returns:

         Pandas.DataFrame: DataFrame containing PNW-Cnet class scores
         indexed by image filename.
    """
    
    pred_df = pd.read_csv(pred_file_path)
    
    return pred_df


def getClipInfo(clip_name):
    """Extract information from the name of a spectrogram image file.

    Clip names will be in the form 

    [Area]_[Site]-[Stn]_[Date]_[Time]_part_[part].png

    e.g. 

    COA_23459-C_20230316_081502_part_001.png

    Args:

        clip_name (str): The name of a spectrogram image file.

    Returns:

        dict: Dictionary of values inferred from the image filename.
    """

    stamp_patt = re.compile("_[0-9]{8}_[0-9]{6}_part_[0-9]+\\.png")
    part_patt = re.compile("part_[0-9]+")

    try:
        clip_stamp = stamp_patt.findall(clip_name)[0]
        clip_prefix = clip_name.replace(clip_stamp, "")

        site_vals = re.split(pattern="[-._]", string=clip_prefix)
        if len(site_vals) == 3:
            clip_dict = dict(zip(["Area", "Site", "Stn"], site_vals))
        else:
            clip_dict = {"Area": '', "Site": '', "Stn": clip_prefix}

        clip_str_datetime = clip_stamp[1:16]
        clip_dict["Timestamp"] = datetime.strptime(clip_str_datetime, "%Y%m%d_%H%M%S")
        clip_dict["Date"] = clip_dict["Timestamp"].date()

        clip_part = part_patt.findall(clip_name)[0].replace("part_", "")
        clip_dict["Part"] = clip_part

    except:
        clip_dict = {"Area":None, "Site":None, "Stn":None, "Timestamp":None, "Date":None}

    return clip_dict


def getClipTimestamp(source_file, offset):
    """Get the timestamp of a clip taken from a longer file.
    
    Args:
        
        source_file (str): Name of a .wav file including a timestamp in
            the format YYYYMMDD_HHMMSS.
        
        offset (numeric): Location of the clip within source_file in 
            seconds from the beginning.
    
    Returns:
        
        tuple: A tuple (clip_date, clip_time) containing two strings 
        representing the date and the time at the start of the clip.
    """

    stamp_patt = re.compile("[0-9]{8}_[0-9]{6}")
    srcfile_str_stamp = stamp_patt.findall(source_file)[0]
    srcfile_stamp = datetime.strptime(srcfile_str_stamp, "%Y%m%d_%H%M%S")
    clip_stamp = srcfile_stamp + timedelta(seconds = offset)
    clip_date, clip_time = clip_stamp.strftime("%m-%d-%Y_%H:%M:%S").split('_')
    return (clip_date, clip_time)


def getReadableOffset(offset):
    """Convert a number of seconds to a more human-readable offset.

    Args:

        offset (numeric): A number of seconds, typically representing a
            position within a long-form .wav file.

    Returns:

        str: A string in format H:MM:SS if offset > 3600 or MM:SS 
        otherwise.
    """

    stamp = datetime(2000, 1, 1) + timedelta(seconds = offset)
    time_format = "%H:%M:%S" if offset >= 3600 else "%M:%S"
    str_offset = datetime.strftime(stamp, time_format)
    return str_offset


def buildClipDataFrame(pred_table):
    """Extract basic information about clips in the predictions table.
    
    Args:
        
        pred_table (Pandas.DataFrame): DataFrame containing PNW-Cnet 
            class scores indexed by image filename.
    
    Returns:
        
        Pandas.DataFrame: DataFrame summarizing information about the 
        audio data that were processed to produce the class scores.
    """
    
    clips = pred_table["Filename"]
    clip_df = pd.DataFrame(data=[getClipInfo(clip) for clip in clips])
    clip_df["Filename"] = clips
    day_1 = min(clip_df["Date"])
    clip_df["Rec_Day"] = [(date - day_1).days + 1 for date in clip_df["Date"]]
    clip_df["Rec_Week"] = [int((day - 1) / 7.) + 1 for day in clip_df["Rec_Day"]]
    return clip_df


def getSourceFile(clip_name, ext=".wav"):
    """Return the name of the audio file from which a clip was taken.

    Args:

        clip_name (str): Filename created by concatenating the name of
            the source file, a string indicating a position within that
            file (e.g. "part_017"), and a file extension (".png").

        ext (str): File extension of the source audio files.

    Returns:

        tuple: A tuple (source_file, str_part) containing the name of 
        the source file and the part_xxx string indicating position 
        within the source file. If the clip name is not formatted as 
        expected, the returned tuple will contain two empty strings.
    """

    part_pattern = re.compile("part_[0-9]+")
    if not part_pattern.search(clip_name):
        return ("", "")
    else:
        base_name = os.path.splitext(clip_name)[0]
        source_file = base_name.split("_part")[0] + ext
        str_part = part_pattern.findall(base_name)[0]
        return (source_file, str_part)


def getSourceFolders(clip_list, mode="from_source_files", top_dir="", 
                    prefix="", flac_mode=False):
    """Get locations of a set of files within a directory tree.

    This function will attempt to associate each spectrogram image
    with an existing source file in the directory tree rooted at 
    top_dir, based on the filename. Images for which a source file
    cannot be found, or for which there are multiple possible source
    files, will cause the function to return nothing.

    Args:

        clip_list (list): A list of names of spectrogram image files.

        mode (str): Either "from_source_files" or "from_clip_names". If
            "from_source_files", source folders will be inferred by 
            joining the source filename with the .wav inventory table
            under top_dir, which will be created if it does not already
            exist. If "from_clip_names", the source folders will be
            constructed by combining the station code in the filename
            of each clip with an optional prefix.

        top_dir (str): Path to the root of the directory tree 
            containing the source .wav files. Values in the FOLDER 
            field will be generated relative to this directory. Used if
            mode == "from_source_files".

        prefix (str): Prefix to be combined with the stn
            ID code inferred from the name of each clip in order to 
            construct the source folder. Used if mode == 
            "from_clip_names".

        flac_mode (bool): Assume audio files are .flac fomat rather
            than .wav.

    Returns:

        Pandas.DataFrame: DataFrame listing the folder (relative to 
        top_dir), source filename, "part_xxx" string, and image 
        filename for each clip.
    """
    
    file_ext = ".flac" if flac_mode else ".wav"
    
    source_file_list, part_list = zip(*[getSourceFile(clip, file_ext) for clip in clip_list])
    source_file_df = pd.DataFrame(data={"Filename": clip_list, 
                                        "Stem": [Path(x).stem for x in source_file_list], 
                                        "PART": part_list})

    if mode == "from_source_files":
        inv_file_path = Path(top_dir, f"{Path(top_dir).name}_{file_ext[1:]}_inventory.csv")
        if not os.path.exists(inv_file_path):
            inv_df = pycnet.file.inventoryFolder(top_dir, print_summary=False, flac_mode=flac_mode)
        else:
            inv_df = pd.read_csv(inv_file_path)

        inv_df.rename(columns={"Folder": "FOLDER", "Filename": "IN_FILE"}, inplace=True)
        inv_df["Stem"] = [Path(x).stem for x in inv_df["IN_FILE"]]

        joined_df = source_file_df.merge(inv_df, how="left", on="Stem")

        if joined_df.shape[0] != source_file_df.shape[0]:
            print("Warning! Either source files could not be located for all clips or some clips are associated with duplicate filenames.")
            return
        else:
            return joined_df[["FOLDER", "IN_FILE", "PART", "Filename"]]
    
    elif mode == "from_clip_names":
        stn_list = [prefix + getClipInfo(clip)["Stn"] for clip in clip_list]

        source_file_df.insert(loc=0, column="FOLDER", value=stn_list)

        return source_file_df[["FOLDER", "IN_FILE", "PART", "Filename"]]


def readReviewSettings(review_settings_file):
    """Read a mapping of target class to score threshold from a file.

    Args:
        
        review_settings_file (str): Path to a CSV file with a "Class"
            column listing the classes to be included in the review 
            file and a "Threshold" column listing the score threshold
            used to define apparent detections for each class.

    Returns:

        dict: A dictionary of score thresholds indexed by class code.
    """

    try:
        df = pd.read_csv(review_settings_file)
        settings_dict = dict(zip(df["Class"], df["Threshold"]))
        return settings_dict
    except:
        print("Could not determine intended settings.")
        return


def parseStrReviewCriteria(crit_string):
    """Map target classes to score thresholds based on a string.

    The crit_string argument should include class codes or groups of 
    class codes alternating with the score threshold to use for each
    class or group of classes, e.g.
    
    ``"BRMA1 0.5 STVA_8Note STVA_Series 0.95"``

    Args:
    
        crit_string (str): A string listing classes (singly or in
            groups) alternating with the score threshold to use for 
            each class or group.

    Returns:
    
        dict: A dictionary of score thresholds indexed by class code.
    """

    crit_list = []

    thresh_patt = re.compile("[0]*?\\.[0-9]+")
    class_patt = re.compile("[A-Za-z0-9_]+")
    class_groups = list(filter(lambda x: x != '', re.split(thresh_patt, crit_string)))
    thresholds = re.findall(thresh_patt, crit_string)

    if len(class_groups) != len(thresholds):
        settings_dict = None

    else:
        for i in range(len(class_groups)):
            add_classes = re.findall(class_patt, class_groups[i])
            thresh = float(thresholds[i])
            add_crit = [(j, thresh) for j in add_classes]
            crit_list.extend(add_crit)

        settings_dict = dict(crit_list)

    return settings_dict


def getDefaultReviewSettings(cnet_version):
    """Define default thresholds for classes to include in review file.

    If the user does not provide a review_settings file listing the
    classes and score thresholds they would like to use, by default
    a threshold of 0.25 (v4) or 0.50 (v5) will be used for northern 
    spotted owl classes and a threshold of 0.95 will be used for all
    other target classes. Spotted owl classes will be selected first,
    followed by all other classes in alphabetical order by class code.
    This corresponds to the thresholds used historically by the 
    northern spotted owl monitoring program to select clips for review.

    We recommend tailoring your review criteria more narrowly, 
    especially when using PNW-Cnet v5, as the large number of target 
    classes can result in a large and unwieldy review table full of 
    species you don't care about.

    Args:

        cnet_version (str): Version of the PNW-Cnet model being used, 
            either "v4" or "v5".

    Returns:

        dict: A dictionary of score thresholds indexed by class code.
    """

    stoc_classes = ["STOC", "STOC_IRREG", "STOC_4Note", "STOC_Series"]
    class_names = v4_class_names if cnet_version == "v4" else v5_class_names
    class_names.sort(key=lambda x: x in stoc_classes, reverse=True)
    settings_dict = {}
    for i in class_names:
        if cnet_version == "v5":
            settings_dict[i] = 0.50 if i in stoc_classes else 0.95
        else:
            settings_dict[i] = 0.25 if i in stoc_classes else 0.95
    return settings_dict


def summarizeRecordingEffort(pred_table):
    """Summarize recording effort by area, site, station, day and week.

    Args:

        pred_table (Pandas.DataFrame): DataFrame containing PNW-Cnet 
            class scores indexed by image filename.

    Returns:

        Pandas.DataFrame: DataFrame with a row for each combination of
        area, site, station, and date listing the number of hours of 
        recording time based on the number of 12-second clips that were
        processed to generate the class scores.
    """

    clip_df = buildClipDataFrame(pred_table)
    grouping_vars = ["Area", "Site", "Stn", "Date", "Rec_Day", "Rec_Week"]
    rec_effort = clip_df[grouping_vars+["Filename"]].groupby(grouping_vars, as_index=False).aggregate("count")
    rec_effort["Effort"] = rec_effort["Filename"] / 300. # hours of recordings
    rec_effort = rec_effort.rename(columns={"Filename":"Clips"}).round({"Effort": 2})
    return rec_effort


def getApparentDetections(pred_table, class_code, score_threshold):
    """Filter PNW-Cnet class scores to apparent detections of one class.

    Args:

        pred_table (Pandas.DataFrame): DataFrame containing PNW-Cnet 
            class scores indexed by image filename.

        class_code (str): The abbreviation for the target class of 
            interest. Note that class codes are specific to the version 
            of PNW-Cnet used.

        score_threshold (float): A number between 0 and 1 defining the
            minimum score at which a clip will be treated as an 
            apparent detection of the chosen class.

    Returns:
        
        Pandas.DataFrame: DataFrame containing rows from pred_table 
        where the score for class_code was greater than or equal to 
        score_threshold.
    """
    
    class_names = list(pred_table.keys())[1:]
    if not class_code in class_names:
        dets = pd.DataFrame()
    elif not 0 < score_threshold <= 1:
        dets = pd.DataFrame()
    else:
        dets = pred_table[pred_table[class_code] >= score_threshold]
    return dets


def tallyDetections(pred_table, score_threshold):
    """Tally apparent detections of all classes at one threshold.

    Args:

        pred_table (Pandas.DataFrame): DataFrame containing PNW-Cnet 
            class scores indexed by image filename.

        score_threshold (float): Minimum score for a clip to be 
            considered an apparent detection for any class.

    Returns:

        Pandas.DataFrame: DataFrame listing the number of apparent 
        detections of all target classes at the score threshold 
        specified, grouped by area, site, station and date. 
    """

    group_fields = ["Area", "Site", "Stn", "Date"]
    clip_info = buildClipDataFrame(pred_table)

    class_names = pred_table.columns[1:]
    class_scores = pred_table[class_names]
    dets_tf = class_scores.apply(lambda x: x >= score_threshold)
    dets_tf = pd.concat([clip_info, dets_tf], axis=1)

    dets_aggregated = dets_tf.groupby(group_fields).aggregate(dict([(code, "sum") for code in class_names]))
    n_rows = dets_aggregated.shape[0]
    dets_aggregated.insert(loc=0, column="Threshold", value=[score_threshold for i in range(n_rows)])

    return dets_aggregated


def summarizeDetections(pred_table, n_workers=None):
    """Tally apparent detections for all classes at various thresholds.
    
    Uses mp.Pool for multiprocessing, so it needs to be used in a 
    main() function, otherwise the worker processes multiply endlessly.
    
    Arguments:
        
        pred_table (Pandas.DataFrame): DataFrame containing PNW-Cnet 
            class scores indexed by image filename.
        
        n_workers (int): Number of worker processes to use for 
            multiprocessing. Defaults to either 10 or the number of 
            logical CPU cores on the host machine, whichever is lower.
    
    Returns:
        
        Pandas.DataFrame: DataFrame listing the number of apparent 
        detections of all target classes over a range of score 
        thresholds [0.05, 0.10, ..., 0.95, 0.98, 0.99], grouped by 
        area, site, station and date.
    """
    
    thresholds = [x / 100. for x in list(range(5, 100, 5)) + [98, 99]]
    
    group_fields = ["Area", "Site", "Stn", "Date"]
    
    n_cores = mp.cpu_count()
    if n_workers is None:
        n_workers = min(n_cores, 10)
    elif n_workers > n_cores:
        n_workers = n_cores

    with mp.Pool(processes = n_workers) as pool:
        pool_args = [(pred_table, i) for i in thresholds]
        thresh_dets = pool.starmap(tallyDetections, pool_args)

    rec_effort = summarizeRecordingEffort(pred_table)

    det_df = pd.concat(thresh_dets, axis=0)
    det_df = rec_effort.merge(det_df, on=group_fields, how="left")
    det_df = det_df.sort_values(by=["Threshold", "Area", "Site", "Stn", "Date"])

    return det_df


def makeReviewTable(pred_table, cnet_version="v5", review_settings=None):
    """Extract apparent detections from a set of class scores.
    
    This function selects clips representing potential detections based
    on review criteria and generates information about those clips. The
    makeKscopeReviewTable function below is designed to format this 
    table for output and human review using Kaleidoscope.
    
    If no review_settings dictionary is provided, the function will use
    the getDefaultReviewSettings function to map classes to score 
    thresholds.
    
    Apparent detections of each class will be extracted in the order 
    that the classes appear in the review_settings dictionary.    
    
    Args:
        
        pred_table (Pandas.DataFrame): DataFrame containing PNW-Cnet 
            class scores indexed by image filename.
        
        review_settings (dict): A dictionary mapping class codes to 
            score thresholds used to define apparent detections for 
            each class.
    
    Returns:
        
        Pandas.DataFrame: DataFrame listing apparent detections for one
        or more classes based on the review criteria provided.
    """
    
    if cnet_version == "v5":
        class_names = v5_class_names
    else:
        class_names = v4_class_names
    
    clip_df = buildClipDataFrame(pred_table)
    
    review_df = pd.DataFrame()
    
    if review_settings is None:
        review_settings = getDefaultReviewSettings(cnet_version)
    
    class_list, dist_list, thresh_list = [], [], []
    review_classes = list(review_settings.keys())
    
    for i in review_settings:
        class_code, class_threshold = i, review_settings[i]
        review_rows = getApparentDetections(pred_table, class_code, class_threshold)
        if not review_rows.empty:
            n_rows = len(review_rows)
            review_df = pd.concat([review_df, review_rows])
            class_list.extend([class_code for j in range(n_rows)])
            dist_list.extend(review_rows[class_code])
            thresh_list.extend([str(class_threshold) for k in range(n_rows)])

    if not review_df.empty:
        review_df = review_df.merge(right=clip_df, how="left", on="Filename")
        review_df["TOP1MATCH"] = class_list
        review_df["TOP1DIST"] = dist_list
        review_df["THRESHOLD"] = thresh_list

        output_cols = ["Filename", "TOP1MATCH", "TOP1DIST", "THRESHOLD", 
                        "PRIORITY", "Area", "Site", "Stn", "Part", 
                        "Rec_Day", "Rec_Week", "AUTO_TAG"] + class_names

        review_df["PRIORITY"] = [review_classes.index(x)+1 for x in review_df["TOP1MATCH"]]
        review_df.sort_values(by=["Filename", "PRIORITY"], inplace=True)
        
        tags_all = review_df.groupby("Filename").agg(AUTO_TAG=pd.NamedAgg(column="TOP1MATCH", aggfunc=lambda x: '+'.join(sorted(list(set(x))))))
        review_df = review_df.merge(tags_all, on="Filename", how="left")
        
        review_df.drop_duplicates(subset="Filename", keep="first", inplace=True)

        review_df = review_df[output_cols].sort_values(by=["TOP1MATCH", "Filename"])

    return review_df


def makeKscopeReviewTable(pred_table, target_dir, cnet_version="v5", 
                        review_settings=None, timescale="weekly", 
                        infer_source_folders=False, 
                        source_folder_prefix="", flac_mode=False):
    """Extract & format apparent detections for review in Kaleidoscope.

    Args:

        pred_table (Pandas.DataFrame): DataFrame listing a set of image
            filenames and the class scores produced by PNW-Cnet for 
            each image.

        target_dir (str): Path to the root of the directory tree 
            containing the audio data.

        cnet_version (str): The version of PNW-Cnet used to generate 
            the class scores (either "v4" or "v5").

        review_settings (dict): Dictionary mapping target classes to 
            score thresholds. See makeReviewTable for details.

        timescale (str): The temporal scale ("daily" or "weekly") at 
            which to tally the apparent detections of each class.

        infer_source_folders (bool): Construct source folders based on
            clip filenames instead of checking a .wav inventory file.

        source_folder_prefix (str): Prefix to combine with the station
            ID code to construct the names of source folders.

        flac_mode (bool): Assume source audio files are .flac instead
            of .wav.

    Returns:

        Pandas.DataFrame: DataFrame listing apparent detections of one 
        or more classes, formatted to be written to a CSV file which 
        will be readable and editable using Wildlife Acoustics' 
        Kaleidoscope software.
    """

    output_cols = ["FOLDER", "IN_FILE", "PART", "CHANNEL", "OFFSET", 
    "DURATION", "DATE", "TIME", "OFFSET_MMSS", "TOP1MATCH", "TOP1DIST", "THRESHOLD", 
    "PRIORITY", "SORT", "AUTO_TAG", "VOCALIZATIONS", "MANUAL_ID"]

    review_df = makeReviewTable(pred_table, cnet_version, review_settings)
    if review_df.empty:
        kscope_df = pd.DataFrame(columns=output_cols)
    else:
        n_clips = review_df.shape[0]

        if infer_source_folders:
            source_df = getSourceFolders(review_df.Filename, mode="from_clip_names", prefix=source_folder_prefix, flac_mode=flac_mode)
        else:
            source_df = getSourceFolders(review_df.Filename, mode="from_source_files", top_dir=target_dir, flac_mode=flac_mode)

        output_df = review_df.merge(source_df, how="inner", on="Filename")

        output_df["OFFSET"] = [12*(int(p)-1) for p in output_df.Part]
        output_df["TOP1DIST"] = round(output_df["TOP1DIST"], 5)
        output_df["DURATION"] = 12
        output_df["CHANNEL"] = 1
        output_df["VOCALIZATIONS"] = 1
        output_df["HOUR"] = ''
        output_df["MANUAL_ID"] = ''

        clip_timestamps = list(map(getClipTimestamp, output_df.IN_FILE, output_df.OFFSET))
        clip_dates, clip_times = zip(*clip_timestamps)
        output_df["DATE"] = clip_dates
        output_df["TIME"] = clip_times

        output_df["OFFSET_MMSS"] = [getReadableOffset(i) for i in output_df.OFFSET]

        if timescale == "weekly":
            output_df["SORT"] = ["{0:03d}_{1}_Stn_{2}_Week_{3:02d}".format(*x) for x in zip(output_df.PRIORITY, output_df.TOP1MATCH, output_df.Stn, output_df.Rec_Week)]
        else:
            output_df["SORT"] = ["{0:03d}_{1}_Stn_{2}_Day_{3:03d}".format(*x) for x in zip(output_df.PRIORITY, output_df.TOP1MATCH, output_df.Stn, output_df.Rec_Day)]

        kscope_df = output_df[output_cols].sort_values(by=["TOP1MATCH", "IN_FILE", "PART"])

    return kscope_df
