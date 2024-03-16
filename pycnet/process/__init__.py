"""Functions to provide a higher-level interface for typical processing 
tasks. Common processing workflows should be accessible as simple CLI
commands using console_scripts entry points from the top-level pycnet 
package.
Functions:
1. makeFileInventory: Build an inventory of .wav files in the target 
folder.
2. generateSpectrograms: Generate a set of spectrograms representing 
segments of the audio.
3. generateClassScores: Process an existing set of spectrograms using
the PNW-Cnet model.
4. makeReviewTable: Filter raw class scores to get a set of apparent 
detections of one or more target classes. (Put this in pycnet.review)
5. processFolder: Do all of the above in one go.
"""

import datetime as dt
import math
import multiprocessing as mp
import os
import pandas as pd
import pycnet
import tensorflow as tf

from pycnet.cnet import v4_class_names, v5_class_names, v4_model_path, v5_model_path
from pycnet.process import CLArgParser


def getWavPaths(wav_inventory, top_dir):
    """Reconstruct full paths for wav files listed in the inventory."""
    wi = wav_inventory
    if os.path.exists(wi["Folder"][0]):
        wav_paths = [os.path.join(wi["Folder"][i], wi["Filename"][i]) for i in range(len(wi))]
    else:
        wav_paths = [os.path.join(top_dir, wi["Folder"][i], wi["Filename"][i]) for i in range(len(wi))]
    return wav_paths


def buildProcQueue(input_dir, image_dir):
    """Return a queue of input file paths mapped to output folders."""
    dir_name = os.path.basename(input_dir)
    inv_file = os.path.join(input_dir, "{0}_wav_inventory.csv".format(dir_name))
    
    wav_inventory = pd.read_csv(inv_file) # Raises FileNotFoundError if inv_file doesn't exist - build it first
    wav_paths = getWavPaths(wav_inventory, input_dir)

    total_dur = sum(wav_inventory["Duration"]) / 3600.
    n_images = total_dur * 300
    n_chunks = int(n_images / 50000) + min(n_images % 50000, 1)

    todo = pycnet.file.wav.makeSpectroDirList(wav_paths, image_dir, n_chunks)
    spectro_dirs = list(set([k[1] for k in todo]))

    proc_queue = mp.JoinableQueue()
    for wav in todo:
        proc_queue.put(wav)

    return {"queue":proc_queue, "dirs":spectro_dirs}


def generateSpectrograms(proc_queue, n_workers, show_prog=True):
    """Generate spectrograms using a number of worker processes."""
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

    print(pycnet.prog.makeProgBar(n_wav_files, n_wav_files), end = '\n')

    return


def generateClassScores(target_dir, model_path, show_prog=True):
    """Generate class scores for a set of spectrograms using PNW-Cnet. 

    Returns a Pandas DataFrame, which R can handle more or less natively. The
    DataFrame has one column Filename for the names of the image files and 
    either 51 (PNW-Cnet v4) or 135 (PNW-Cnet v5) columns for class scores.
    
    Arguments:
    <target_dir>: directory containing spectrograms in the form of .png
    image files; these images will be classified by the PNW-Cnet model
    <model_path>: path to either PNW-Cnet_v4_TF.h5 or PNW-Cnet_v5_TF.h5
    <show_prog>: whether to show a text-based progress bar as the model
    makes predictions on batches of images
    """

    # Find all the PNG files in the directory tree
    image_paths = pycnet.file.findFiles(target_dir, ".png")
    image_df = pd.DataFrame(data=image_paths, columns=["Filename"])

    # The generator uses the dataframe of image paths to feed batches of image
    # data to the neural net after rescaling the 8-bit integer pixel values to 
    # floating-point in the range [0,1].
    image_generator = tf.keras.preprocessing.image.ImageDataGenerator(
        rescale = 1./255)
    
    predict_gen = image_generator.flow_from_dataframe(
        dataframe = image_df,
        directory = None,
        x_col = "Filename",
        y_col = None,
        target_size = (257, 1000),
        color_mode = 'grayscale',
        batch_size = 16,
        class_mode = None,
        shuffle = False)

    # Spits out a few informational and warning messages which can be safely ignored.
    pnw_cnet_model = tf.keras.models.load_model(model_path)

    # Progress bar is kind of obnoxious when running in RStudio (prints a separate
    # line for each step) but still probably helpful on balance. 
    class_scores = pnw_cnet_model.predict(predict_gen, verbose = 1 if show_prog else 0)

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
        score_cols = ["Class_%s" % str(i).zfill(int(math.log10(n_cols))+1) for i in range(1, n_cols + 1)]

    predictions = pd.DataFrame(data=class_scores, columns=score_cols).round(decimals = 5)
    predictions.insert(loc=0, column="Filename", 
        value=[os.path.basename(path) for path in image_paths])

    return predictions


def processFolder(mode, target_dir, cnet_version="v5", spectro_dir=None, n_workers=None, review_settings=None, cleanup=True):
    """Generate spectrograms, generate class scores, build review file.
    
    Basically runs through the functions above in a logical sequence
    to produce a set of apparent target species detections from a set
    of .wav files. Narrates progress and marks the time at the beginning
    and end of each step to give the user a reasonable sense of
    processing speed.
    
    Accepts a processing mode as an argument which will determine which
    of these steps are actually performed.
    """
    time_fmt = "%b %d at %H:%M:%S"
    
    folder_name = os.path.basename(target_dir)
    output_prefix = "{0}_{1}".format(folder_name, cnet_version)
    
    wav_inv_file = os.path.join(target_dir, "{0}_wav_inventory.csv".format(folder_name))
    class_score_file = os.path.join(target_dir, "{0}_class_scores.csv".format(output_prefix))
    det_sum_file = os.path.join(target_dir, "{0}_detection_summary.csv".format(output_prefix))
    review_file = os.path.join(target_dir, "{0}_review.csv".format(output_prefix))
    kscope_file = review_file.replace("review", "review_kscope")
    
    ### Inventory .wav files and set up processing directories ###
    if not os.path.exists(wav_inv_file):
        print("Creating inventory file {0}.".format(wav_inv_file))
        wav_inventory = pycnet.file.inventoryFolder(target_dir)
    else:
        print("Using inventory file {0}.".format(wav_inv_file))
        wav_inventory = pd.read_csv(wav_inv_file)
        pycnet.file.summarizeInventory(wav_inventory)
    
    if not spectro_dir:
        image_dir = os.path.join(target_dir, "Temp", "images")
    else:
        image_dir = os.path.join(spectro_dir, folder_name, "images")
    
    proc_start = dt.datetime.now()
    
    ### Generate the spectrograms ###
    if mode in ["process", "spectro"]:
    
        proc_queue = buildProcQueue(target_dir, image_dir)
        print("Spectrograms will be generated in the following folders:")
        print('\n'.join(sorted(proc_queue["dirs"])) + '\n')
        
        print("Generating spectrograms starting {0}...\n".format(proc_start.strftime(time_fmt)))
        
        n_workers = n_workers if n_workers else mp.cpu_count()
        generateSpectrograms(proc_queue, n_workers)
        
        spectro_end = dt.datetime.now()
        print("\nFinished {0}.".format(spectro_end.strftime(time_fmt)))
    
    ### Generate class scores for each image and summarize apparent detections ###
    if mode in ["process", "predict"]:
        
        predict_start = dt.datetime.now()
        if mode == "predict":
            print("\nGenerating class scores using PNW-Cnet {0} starting {1}...\n".format(cnet_version, predict_start.strftime(time_fmt)))
        else:
            print("\nGenerating class scores using PNW-Cnet {0}...\n".format(cnet_version))
        
        model_path = v4_model_path if cnet_version == "v4" else v5_model_path
        
        class_scores = generateClassScores(image_dir, model_path)
        
        class_scores.to_csv(class_score_file, index = False)
        
        predict_end = dt.datetime.now()
        print("\nFinished {0}.".format(predict_end.strftime(time_fmt)))
        print("\nClass scores written to {0}.\n".format(class_score_file))
    
        ### Generate review files and summarize apparent detections ###
        print("Summarizing apparent detections...", end='')
        detection_summary = pycnet.review.summarizeDetections(class_scores)
        print(" done.")
        
        detection_summary.to_csv(det_sum_file, index=False)
        print("Detection summary written to {0}.\n".format(det_sum_file))
    
    ### Generate review files containing apparent detections ###
    if mode in ["process", "review"]:
        print("Generating review file...", end='')
        
        try:
            class_scores
        except:
            class_scores = pycnet.review.readPredFile(class_score_file)
            
        review_df = pycnet.review.makeReviewTable(class_scores)
        review_df.to_csv(review_file, index=False)
        print(" done.")
    
    ### Clean up temporary files and folders ###
    if cleanup:
        pycnet.file.removeSpectroDir(target_dir, spectro_dir)
    
    proc_end = dt.datetime.now()
    
    ### Calculate processing speed ###
    if mode == "process":
        d_hours = sum(wav_inventory["Duration"]) / 3600.
        p_hours = (proc_end - proc_start).seconds / 3600.
        dp_ratio = d_hours / p_hours
        print("Processed {0:.1f} h of audio in {1:.1f} h (data:processing ratio = {2:.1f})".format(d_hours, p_hours, dp_ratio))

    return


def main():
    """Perform one or more processing operations on a folder.
    
    Intended to be run as a command-line script with behavior determined
    by one or more arguments. At a minimum, arguments should include a 
    mode (determines what the script actually does) and a target 
    directory containing the data you want to work with.
    
    usage:
    pycnet [mode] [target dir] [optional arguments]
    
    Run with the -h (help) flag, e.g. 'pycnet -h', to see all options.
    """
    # valid_modes = ["rename", "inventory", "spectro", "predict", "review", "process", "cleanup", "config"]
    valid_modes = ["process", "spectro", "predict", "inventory", "rename", "cleanup"]

    args = CLArgParser.parsePycnetArgs()

    if not args.mode in valid_modes:
        print("\nMode '{0}' not recognized. Please use one of the following options:".format(args.mode))
        print('\n'.join(valid_modes))

    else:
        if args.mode == "process":
            proc_args = [args.mode, args.target_dir, args.cnet_version, args.image_dir, args.n_workers, args.review_settings]
            processFolder(*proc_args)

        elif args.mode == "spectro":
            spectro_args = [args.mode, args.target_dir, args.cnet_version, args.image_dir, args.n_workers]
            processFolder(*spectro_args, cleanup=False)

        elif args.mode == "predict":
            predict_args = [args.mode, args.target_dir, args.cnet_version, args.image_dir]
            processFolder(*predict_args, cleanup=False)

        elif args.mode == "inventory":
            inv_args = [args.target_dir]
            pycnet.file.inventoryFolder(*inv_args)

        elif args.mode == "rename":
            rename_args = [args.target_dir, "wav"]
            pycnet.file.massRenameFiles(*rename_args)
            
        elif args.mode == "cleanup":
            cleanup_args = [args.target_dir, args.image_dir]
            pycnet.file.removeSpectroDir(*cleanup_args)

        else:
            pass

if __name__ == "__main__":
    main()

