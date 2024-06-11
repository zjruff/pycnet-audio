"""Defines functions to provide a higher-level interface for processing
audio data using PNW-Cnet.

Functions:

    buildProcQueue
        Create a JoinableQueue defining .wav files to be processed and 
        the directories where temporary spectrogram image files will be
        stored.

    generateClassScores
        Generate class scores for a set of images using the PNW-Cnet 
        model.

    generateEmbeddings
        Generate embeddings for a set of images using PNW-Cnet.

    generateSpectrograms
        Generate a set of spectrograms representing segments of the 
        audio data.

    getWavPaths
        Reconstruct absolute paths to .wav files listed in a DataFrame 
        containing filenames and relative paths.

    logMessage
        Print a message and optionally write it to a log file.

    makeFileInventory
        Build an inventory of .wav files in the target folder.

    parsePycnetArgs
        Define command-line options for the 'pycnet' console script.

    processFolder
        Perform one or more processing operations on a folder.
"""

import argparse
import datetime as dt
import multiprocessing as mp
import os
import pandas as pd
import pycnet
import tensorflow as tf

from pycnet.cnet import v4_class_names, v5_class_names, v4_model_path, v5_model_path


def getWavPaths(wav_inventory, top_dir):
    """Reconstruct full paths for wav files listed in the inventory.
    
    Args:
        
        wav_inventory (Pandas.DataFrame): DataFrame listing the folder 
            (relative to top_dir), filename, size, and duration of each            
            .wav file.
        
        top_dir (str): Path of the root of the directory tree 
            containing the .wav files listed in wav_inventory.
        
    Returns:
        
        list[str]: A list of absolute paths for the .wav files listed in 
        wav_inventory.
    """
    
    wi = wav_inventory
    if os.path.exists(wi["Folder"][0]):
        wav_paths = [os.path.join(wi["Folder"][i], wi["Filename"][i]) for i in range(len(wi))]
    else:
        wav_paths = [os.path.join(top_dir, wi["Folder"][i], wi["Filename"][i]) for i in range(len(wi))]
    return wav_paths


def buildProcQueue(input_dir, image_dir, n_chunks=0):
    """Return a queue of input file paths mapped to output folders.
    
    If n_chunks is not supplied, the function will try to avoid 
    generating >50,000 image files in any one folder.
    
    Arguments:
        
        input_dir (str): Root of the directory tree containing .wav 
            files.
        
        image_dir (str): Path to the directory where spectrograms 
            should be generated (in subfolders as needed).
        
        n_chunks (int): Number of subfolders to create for the 
            spectrograms.
    
    Returns:
        
        dict: A dictionary containing "queue" (the queue itself) and 
        "spectro_dirs", a list of folders where spectrograms will be 
        generated.
    """
    
    dir_name = os.path.basename(input_dir)
    inv_file = os.path.join(input_dir, "{0}_wav_inventory.csv".format(dir_name))
    
    wav_inventory = pd.read_csv(inv_file)
    wav_paths = getWavPaths(wav_inventory, input_dir)

    total_dur = sum(wav_inventory["Duration"]) / 3600.
    n_images = total_dur * 300
    
    if n_chunks == 0:
        n_chunks = int(n_images / 50000) + min(n_images % 50000, 1)

    todo = pycnet.file.wav.makeSpectroDirList(wav_paths, image_dir, n_chunks)
    spectro_dirs = list(set([k[1] for k in todo]))

    proc_queue = mp.JoinableQueue()
    for wav in todo:
        proc_queue.put(wav)

    return {"queue":proc_queue, "dirs":spectro_dirs}


def generateSpectrograms(proc_queue, n_workers, show_prog=True):
    """Generate spectrogram image files from a queue of .wav files.

    Arguments:

        proc_queue (Multiprocessing.JoinableQueue): A joinable queue 
            containing tuples mapping paths of .wav audio files to 
            folders where the spectrograms generated from each .wav 
            file should be saved.

        n_workers (int): Number of worker processes to use for 
            spectrogram generation.

        show_prog (bool): Whether to display a text-based progress bar
            as spectrograms are generated.

    Returns:

        Nothing.
    """

    wav_queue = proc_queue["queue"]
    n_wav_files = wav_queue.qsize()
    
    spectro_dirs = proc_queue["dirs"]
    for dir in spectro_dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)

    image_dir = os.path.commonpath(spectro_dirs)
    done_queue = mp.Queue()

    for i in range(n_workers):
        worker = pycnet.file.wav.WaveWorker(wav_queue, done_queue, image_dir)
        worker.daemon = True
        worker.start()

    if show_prog:
        prog_worker = pycnet.prog.ProgBarWorker(done_queue, n_wav_files)
        prog_worker.daemon = True
        prog_worker.start()

    wav_queue.join()

    return


def batchImageData(target_dir, batch_size=16):
    """Supply batches of image data from a folder for classification.

    This function searches the target directory for image files with a
    .png file extension and chunks them up into batches to be supplied
    to the PNW-Cnet model. Images are loaded in batches and converted 
    to NumPy arrays with pixel values rescaled to floating-point values
    in the range [0,1].

    Args:

        target_dir (str): Path to the folder containing the images.

        batch_size (int): Number of images to process in each batch. 
            Larger batches may allow faster processing at the cost of
            increased memory usage.

    Returns:
    
        dict: A dict containing "image_paths", a list of the full paths
        of all .png images in the target directory; "image_names", a 
        list of the filenames of the same files; and "image_batches", 
        a Keras DataFrameIterator.
    """

    image_paths = pycnet.file.findFiles(target_dir, ".png")
    image_names = [os.path.basename(path) for path in image_paths]
    image_df = pd.DataFrame(data=image_paths, columns=["Filename"])

    image_generator = tf.keras.preprocessing.image.ImageDataGenerator(
        rescale = 1./255)

    image_batches = image_generator.flow_from_dataframe(
        dataframe = image_df,
        directory = None,
        x_col = "Filename",
        y_col = None,
        target_size = (257, 1000),
        color_mode = 'grayscale',
        batch_size = batch_size,
        class_mode = None,
        shuffle = False)

    return {"image_paths": image_paths, "image_names": image_names, "image_batches": image_batches}


def generateClassScores(target_dir, model_path, show_prog=True):
    """Generate class scores for a set of spectrograms using PNW-Cnet.

    The DataFrame returned contains one column Filename for the names 
    of the image files and either 51 (PNW-Cnet v4) or 135 (PNW-Cnet v5)
    columns for class scores.

    Args:

        target_dir (str): Directory containing spectrograms in the form
            of .png image files to be be classified using the PNW-Cnet 
            model.

        model_path (str): Path to either the PNW-Cnet v4 or v5 trained 
            model file.

        show_prog (bool): Whether to show a text-based progress bar as 
            the model processes batches of images.

    Returns:

        Pandas.DataFrame: A DataFrame containing the class scores for
        each image file.
    """

    i = batchImageData(target_dir)
    image_paths = i["image_paths"]
    image_names = i["image_names"]
    image_batches = i["image_batches"]

    # Spits out a few informational and warning messages which can be safely ignored.
    pnw_cnet_model = tf.keras.models.load_model(model_path)

    class_scores = pnw_cnet_model.predict(image_batches, verbose = 1 if show_prog else 0)

    # Function applies different column labels depending on the number of columns
    # (i.e., target classes) in the class_scores dataframe. If it gets an unexpected
    # number of columns (neither 51 nor 135) it just labels them sequentially.
    n_cols = class_scores.shape[1]
    if n_cols == 51:
        score_cols = v4_class_names
    elif n_cols == 135:
        score_cols = v5_class_names
    else:
        print("Warning: Prediction dataframe has unexpected number of columns. Cannot determine class names.")
        score_cols = ["Class_{0:03d}".format(i) for i in range(1, n_cols + 1)]

    predictions = pd.DataFrame(data=class_scores, columns=score_cols).round(decimals=5)
    predictions.insert(loc=0, column="Filename", value=image_names)

    return predictions


def generateEmbeddings(target_dir, cnet_version, show_prog=True):
    """Generate embeddings for a set of images using PNW-Cnet.

    Embeddings are the activation of the penultimate fully-connected 
    layer of the model. They are not directly interpretable in the same
    way as the class scores but might yield useful information via 
    cluster analysis or other forms of dimensionality reduction, and 
    can also be used to train linear classifiers.

    Args:

        target_dir (str): Directory containing spectrograms in the form
            of .png image files to be be classified using the PNW-Cnet 
            model.

        cnet_version (str): Which version of the PNW-Cnet model ("v4"
            or "v5") to use for generating embeddings.

        show_prog (bool): Whether to show a text-based progress bar as
            the model processes batches of images.

    Returns:

        dict: A dictionary containing two Pandas DataFrames. 
        "predictions" contains the class scores for each image file.
        "embeddings" contains the embeddings for each image file.
    """

    i = batchImageData(target_dir)
    image_paths = i["image_paths"]
    image_names = i["image_names"]
    image_batches = i["image_batches"]

    if cnet_version == "v5":
        model_path, class_names, embed_layer_name, embed_nodes = v5_model_path, v5_class_names, "dense", 512
    elif cnet_version == "v4":
        model_path, class_names, embed_layer_name, embed_nodes = v4_model_path, v4_class_names, "dense_1", 256
    else:
        return
    
    cnet_model = tf.keras.models.load_model(model_path)
    embed_model = tf.keras.models.Model(inputs = cnet_model.input,
                                outputs = {"class_scores": cnet_model.output,
                                            "embeddings": cnet_model.get_layer(embed_layer_name).output})

    embed_cols = ["Node_{0:03d}".format(j) for j in range(embed_nodes)]

    model_output = embed_model.predict(image_batches, verbose = 1 if show_prog else 0)
    
    predictions = pd.DataFrame(data=model_output["class_scores"], columns=class_names).round(decimals=5)
    predictions.insert(loc=0, column="Filename", value=image_names)
    
    embeddings = pd.DataFrame(data=model_output["embeddings"], columns=embed_cols).round(decimals=5)
    embeddings.insert(loc=0, column="Filename", value=image_names)

    return {"predictions": predictions, "embeddings": embeddings}


def logMessage(message, log_file_path=None):
    """Print a message and optionally write it to a log file.
    
    Args:
        
        message (str): Message to be printed and written to file.
        
        log_file_path (str): Path to the log file, or None.
        
    Returns:
    
        Nothing.
    """
    if log_file_path is not None:
        with open(log_file_path, 'a') as log_file:
            log_file.write(message)
            
    print(message)
    
    return


def processFolder(mode, target_dir, cnet_version="v5", spectro_dir=None, n_workers=None, review_settings=None, output_file=None, log_to_file=False, show_prog=True, cleanup=False):
    """Perform one or more processing operations on data in a folder.

    Basically runs through the functions above in a logical sequence to
    produce a set of apparent target species detections from a set of 
    .wav files. Narrates progress and marks the time at the beginning 
    and end of each step to give the user a reasonable sense of 
    processing speed.

    Depending on the processing mode, this may create one or more 
    comma-separated text output files within the target directory.

    Args:

        mode (str): Processing mode, i.e., which operation(s) to 
            perform.

        target_dir (str): Path to the folder containing audio data to
            be processed.

        cnet_version (str): Which version of the PNW-Cnet model to use
            when generating class scores ("v4" or "v5").

        spectro_dir (str): Path to the folder where spectrograms should
            be stored.

        n_workers (int): How many worker processes to use when 
            generating spectrograms.

        review_settings (str): Path to a CSV file with one column 
            "Class" listing classes to include in the review file and
            one column "Threshold" listing the score threshold to use 
            for each class -OR- a string containing class codes or
            groups of class codes followed by the score threshold to be
            used for each class or group.
        
        output_file (str): Name of the review file to be generated.
        
        log_to_file (bool): Whether to copy console messages to a log 
            file (does not include progress bars).

        show_prog (bool): Whether to show progress bars when generating
            spectrograms and classifying images with PNW-Cnet.

        cleanup (bool): Whether to delete spectrograms and temporary 
            folders when processing is complete.

    Returns:

        Nothing.
    """

    ### Preliminary housekeeping ###
    time_fmt = "%b %d at %H:%M:%S"

    folder_name = os.path.basename(target_dir)
    output_prefix = "{0}_{1}".format(folder_name, cnet_version)

    wav_inv_file = os.path.join(target_dir, "{0}_wav_inventory.csv".format(folder_name))
    class_score_file = os.path.join(target_dir, "{0}_class_scores.csv".format(output_prefix))
    det_sum_file = os.path.join(target_dir, "{0}_detection_summary.csv".format(output_prefix))

    if output_file is not None:
        review_file = os.path.join(target_dir, output_file)
    else:
        review_file = os.path.join(target_dir, "{0}_review.csv".format(output_prefix))
    kscope_file = review_file.replace("review", "review_kscope")

    output_files = []

    proc_start = dt.datetime.now()

    if log_to_file:
        proc_log_file = os.path.join(target_dir, "{0}_processing_log_{1}.txt".format(folder_name, proc_start.strftime("%d_%b_%H%M")))
        output_files.append(proc_log_file)
    else:
        proc_log_file = None

    ### Inventory .wav files and set up processing directories ###
    if not os.path.exists(wav_inv_file):
        logMessage("Creating .wav inventory file...", proc_log_file)
        wav_inventory = pycnet.file.inventoryFolder(target_dir, print_summary=False)
        output_files.append(wav_inv_file)
    else:
        logMessage("Using preexisting .wav inventory file...", proc_log_file)
        wav_inventory = pd.read_csv(wav_inv_file)
    
    logMessage('\n' + pycnet.file.summarizeInventory(wav_inventory) + '\n', proc_log_file)

    if spectro_dir is None:
        image_dir = os.path.join(target_dir, "Temp", "images")
    else:
        image_dir = os.path.join(spectro_dir, folder_name, "images")
    
    ### Generate the spectrograms ###
    if mode in ["process", "spectro"]:

        # Check if it's possible to generate spectrograms
        try:
            os.makedirs(image_dir)
        except:
            logMessage("\nCould not create temporary directory in the location requested!", proc_log_file)
            logMessage("Aborting operation.\n", proc_log_file)
            exit()
        
        proc_queue = buildProcQueue(target_dir, image_dir)
        logMessage("\nSpectrograms will be generated in the following folders:\n", proc_log_file)
        logMessage('\n'.join(sorted(proc_queue["dirs"])), proc_log_file)
        
        n_cores = mp.cpu_count()
        if n_workers is None:
            n_workers_corr = n_cores
        else:
            int_workers = int(n_workers)
            if not 1 <= int_workers <= n_cores:
                n_workers_corr = n_cores
                logMessage("Cannot use {0} worker processes. Using {1} processes.".format(n_workers, n_workers_corr), proc_log_file)
            else:
                n_workers_corr = int_workers
        
        logMessage("\nGenerating spectrograms starting {0}...\n".format(proc_start.strftime(time_fmt)), proc_log_file)
        generateSpectrograms(proc_queue, n_workers_corr, show_prog)
        
        spectro_end = dt.datetime.now()
        logMessage("\nFinished {0}.".format(spectro_end.strftime(time_fmt)), proc_log_file)
    
    ### Generate class scores for each image ###
    if mode in ["process", "predict"]:
        
        predict_start = dt.datetime.now()
        if mode == "predict":
            logMessage("\nGenerating class scores using PNW-Cnet {0} starting {1}...\n".format(cnet_version, predict_start.strftime(time_fmt)), proc_log_file)
        else:
            logMessage("\nGenerating class scores using PNW-Cnet {0}...\n".format(cnet_version), proc_log_file)
        
        model_path = v4_model_path if cnet_version == "v4" else v5_model_path
        
        class_scores = generateClassScores(image_dir, model_path, show_prog)
        
        class_scores.to_csv(class_score_file, index = False)
        
        predict_end = dt.datetime.now()
        logMessage("\nFinished {0}.".format(predict_end.strftime(time_fmt)), proc_log_file)
        output_files.append(class_score_file)

    ### Summarize apparent detections and create review file ###
    if mode in ["process", "predict", "review"]:
        try:
            class_scores
        except:
            class_scores = pycnet.review.readPredFile(class_score_file)

        if not os.path.exists(det_sum_file):
            logMessage("\nSummarizing apparent detections...", proc_log_file)
            detection_summary = pycnet.review.summarizeDetections(class_scores)
            logMessage(" done.\n", proc_log_file)

            detection_summary.to_csv(det_sum_file, index=False)
            output_files.append(det_sum_file)

        logMessage("\nGenerating review file...", proc_log_file)

        if review_settings is not None:
            if os.path.exists(review_settings):
                review_settings = pycnet.review.readReviewSettings(review_settings)
            else:
                review_settings =  pycnet.review.parseStrReviewCriteria(review_settings)

        review_df = pycnet.review.makeKscopeReviewTable(class_scores, target_dir, cnet_version, review_settings)
        logMessage(" done. {0} apparent detections found.\n".format(review_df.shape[0]), proc_log_file)

        review_df.to_csv(kscope_file, index=False)
        output_files.append(kscope_file)

    ### Clean up temporary files and folders ###
    if any([mode == "cleanup", cleanup]):
        pycnet.file.removeSpectroDir(target_dir, spectro_dir)

    proc_end = dt.datetime.now()

    ### Report output files and processing speed ###    
    if len(output_files) > 0:
        logMessage("\nCreated the following output files in {0}: ".format(target_dir), proc_log_file)
        logMessage('\n'.join([os.path.basename(f) for f in output_files]) + '\n', proc_log_file)

    if mode == "process":
        d_hours = sum(wav_inventory["Duration"]) / 3600.
        p_hours = (proc_end - proc_start).seconds / 3600.
        dp_ratio = d_hours / p_hours
        logMessage("\nProcessed {0:.1f} h of audio in {1:.1f} h (data:processing ratio = {2:.1f})\n".format(d_hours, p_hours, dp_ratio), proc_log_file)

    return


def parsePycnetArgs():
    """Define command-line options for the 'pycnet' console script.

    Args:

        Nothing (reads arguments from stdin).

    Returns:

        argparse.Namespace: An argparse.Namespace object containing 
        command-line arguments in an accessible form.
    """
    
    n_cores = mp.cpu_count()

    parser = argparse.ArgumentParser(description="Perform one or more processing operations on a folder.")

    parser.add_argument("mode", metavar="MODE", type=str,
        choices=["rename", "inventory", "spectro", "predict", "review", "process", "cleanup", "test"], 
        help="Operation to be performed. Options: 'inventory' (default), 'rename', 'spectro', 'predict', 'review', 'process', 'cleanup'.", default="inventory")

    parser.add_argument("target_dir", metavar="TARGET_DIR", type=str, help="Path to the directory containing .wav files to be processed.")

    parser.add_argument("-c", dest="cnet_version", type=str, choices=["v4", "v5"], default="v5",
        help="Version of PNW-Cnet to use when generating class scores. Options: 'v5' (default) or 'v4'.")

    parser.add_argument("-i", dest="image_dir", type=str,
        help="Path to the directory where spectrogram images will be stored. Will be created if it does not already exist. Default: a folder called Temp under target dir.")

    parser.add_argument("-w", dest="n_workers", type=int,
        help="Number of worker processes to use when generating spectrograms. Default: number of available cores (currently {0}).".format(n_cores))

    parser.add_argument("-r", dest="review_settings", type=str,
        help="Path to file containing settings to use when generating the review file, or a string specifying review criteria directly.")

    parser.add_argument("-o", dest="output_file", type=str,
        help="Manually specify filename for review file.")
        
    parser.add_argument("-l", dest="log_to_file", action="store_true",
        help="Copy output messages to log file.")

    parser.add_argument("-q", dest="quiet_mode", action="store_true",
        help="Quiet mode (suppress progress bars and informational messages).")

    parser.add_argument("-a", dest="auto_cleanup", action="store_true",
        help="Remove spectrogram image files and temporary folders when class scores have been generated.")

    args = parser.parse_args()
    
    return args
