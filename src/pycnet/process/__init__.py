"""Functions to provide a higher-level interface for processing audio
data using PNW-Cnet.

Functions:
- getWavPaths: reconstruct absolute paths to .wav files listed in a
DataFrame containing filenames and relative paths.
- buildProcQueue: Create a JoinableQueue defining .wav files to be
processed and the directories where temporary spectrogram image files
will be stored.
- makeFileInventory: Build an inventory of .wav files in the target 
folder.
- generateSpectrograms: Generate a set of spectrograms representing 
segments of the audio data.
- generateClassScores: Process an existing set of spectrograms using
the PNW-Cnet model.
- processFolder: Perform one or more processing operations on a folder.
"""

import datetime as dt
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


def buildProcQueue(input_dir, image_dir, n_chunks=0):
    """Return a queue of input file paths mapped to output folders.
    
    Arguments:
    - input_dir: path to the directory containing audio data
    - image_dir: path to the directory where spectrograms should be
    saved
    - n_chunks: number of segments to split the processing task into. 
    By default the function will try to avoid putting >50,000 images
    into any one folder.
    
    Returns:
    A dictionary containing "queue" (the queue itself) and 
    "spectro_dirs", a list of folders where spectrograms will be saved.
    """
    dir_name = os.path.basename(input_dir)
    inv_file = os.path.join(input_dir, "{0}_wav_inventory.csv".format(dir_name))
    
    wav_inventory = pd.read_csv(inv_file) # Raises FileNotFoundError if inv_file doesn't exist - build it first
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
    """Generate spectrograms from audio files.
    
    Arguments:
    - proc_queue: a Multiprocessing.JoinableQueue containing tuples 
    mapping paths of .wav audio files to folders where spectrograms 
    from each .wav file should be saved
    - n_workers: number of processing nodes to use
    - show_prog: display a text-based progress bar as spectrograms are
    generated
    
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
    
    Arguments:
    - target_dir: path to the folder containing the images
    - batch_size: number of images to process in each batch. Larger
    batches will consume more memory but may allow faster processing.
    
    Returns:
    A dict containing "image_paths", a list of the full paths of all
    PNG images in the target directory; "image_names", a list of the
    filenames for the same files; and "image_batches", a Keras 
    DataFrameIterator.
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

    Returns a Pandas DataFrame, which R can handle more or less natively. The
    DataFrame has one column Filename for the names of the image files and 
    either 51 (PNW-Cnet v4) or 135 (PNW-Cnet v5) columns for class scores.
    
    Arguments:
    - target_dir: directory containing spectrograms in the form of .png
    image files; these images will be classified by the PNW-Cnet model
    - model_path: path to either PNW-Cnet_v4_TF.h5 or PNW-Cnet_v5_TF.h5
    - show_prog: whether to show a text-based progress bar as the model
    makes predictions on batches of images
    
    Returns:
    - predictions: a Pandas DataFrame containing the class scores for
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


def getEmbeddings(target_dir, cnet_version, show_prog=True):
    """Get embeddings from the PNW-Cnet model on a set of images.
    
    Embeddings are the activation of the penultimate fully-connected 
    layer of the model. They are not directly interpretable in the same 
    way as the class scores but might yield useful information via
    cluster analysis or other forms of dimensionality reduction.
    
    Arguments:
    - target_dir: path to a folder containing image files
    - cnet_version: which version of the PNW-Cnet model to use
    - show_prog: show a progress bar
    
    Returns:
    A dictionary containing two Pandas DataFrames. 
    - "predictions" contaings the class scores for each image file. 
    - "embeddings" contains, for each image file, the activations 
    from the model's penultimate layer, which can be interpreted as the
    model's internal representation of the input data, from which 
    the class scores are generated.
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


def processFolder(mode, target_dir, cnet_version="v5", spectro_dir=None, n_workers=None, review_settings=None, show_prog=True, cleanup=False):
    """Perform one or more processing operations on data in a folder.
    
    Basically runs through the functions above in a logical sequence
    to produce a set of apparent target species detections from a set
    of .wav files. Narrates progress and marks the time at the beginning
    and end of each step to give the user a reasonable sense of
    processing speed.
    
    Depending on the processing mode this may create one or more comma- 
    separated text output files within the target directory.
    
    Arguments:
    - mode: processing mode, i.e., which operation(s) to perform
    - target_dir: path to the folder containing data to process
    - cnet_version: which version of the PNW-Cnet model to use
    - spectro_dir: path to the folder where spectrograms should be 
    stored
    - n_workers: how many processing nodes to use to generate 
    spectrograms
    - review_settings: path to a file listing classes to be summarized 
    and the score threshold to use for each
    - show_prog: show text progress bars when generating spectrograms
    and classifying images with PNW-Cnet
    - cleanup: delete spectrograms and temporary folders when finished
    
    Returns:
    Nothing
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
    
    if spectro_dir is None:
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
        generateSpectrograms(proc_queue, n_workers, show_prog)
        
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
        
        class_scores = generateClassScores(image_dir, model_path, show_prog)
        
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
    if mode in ["process", "predict", "review"]:
        print("Generating review file...", end='')
        
        try:
            class_scores
        except:
            class_scores = pycnet.review.readPredFile(class_score_file)
            
        review_df = pycnet.review.makeKscopeReviewTable(class_scores, target_dir, cnet_version)
        n_review_rows = review_df.shape[0]
        
        review_df.to_csv(kscope_file, index=False)
        print(" done.\n")
    
        if n_review_rows == 0:
            print("No apparent detections found with these review criteria.") 
            print("Empty table written to {0}.\n".format(kscope_file))
        else:
            print("{0} apparent detections written to {1}.\n".format(n_review_rows, kscope_file))
    
    ### Clean up temporary files and folders ###
    if any([mode == "cleanup", cleanup]):
        pycnet.file.removeSpectroDir(target_dir, spectro_dir)
    
    proc_end = dt.datetime.now()
    
    ### Calculate processing speed ###
    if mode == "process":
        d_hours = sum(wav_inventory["Duration"]) / 3600.
        p_hours = (proc_end - proc_start).seconds / 3600.
        dp_ratio = d_hours / p_hours
        print("Processed {0:.1f} h of audio in {1:.1f} h (data:processing ratio = {2:.1f})".format(d_hours, p_hours, dp_ratio))

    return
