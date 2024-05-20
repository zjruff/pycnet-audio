"""Defines functions for processing image files (spectrograms).

Functions:

    checkImageFile
        Verify that an image file can be loaded.

    checkImages
        Use a set of worker processes to check all the image files in a
        directory tree.
    
Classes:

    ImageChecker
        Worker process that checks whether image files can be loaded.
"""

import multiprocessing as mp
import os
import pycnet
import sys
from tensorflow.keras.preprocessing.image import load_img


def checkImageFile(image_path):
    """Verify that TensorFlow can load an image file.

    Args:

        image_path (str): Path to the image file that will be loaded.

    Returns:

        bool: True if the image loaded successfully, otherwise False.
    """

    try:
        img = load_img(image_path)
        return True
    except:
        return False


def checkImages(top_dir, n_workers=0):
    """Check all the .png images in a folder.
    
    Arguments:
        
        top_dir (str): Path to the root of the directory tree 
            containing image files to be checked.
        
        n_workers (int): Number of worker processes to use. Defaults to
            the number of logical CPU cores.
    
    Returns:
        
        list: A sorted list of paths to image files that could not be 
        loaded for any reason.
    """
    
    if n_workers == 0:
        n_workers = mp.cpu_count()
    else:
        n_workers = min(mp.cpu_count, n_workers)

    pngs = pycnet.file.findFiles(top_dir, ".png")
    print("\nFound {0} PNG files under {1}.\n".format(len(pngs), top_dir))
    print("Checking images... ")
    
    img_queue, bad_img_queue = mp.JoinableQueue(), mp.Queue()
    for i in pngs:
        img_queue.put(i)
        
    for j in range(n_workers):
        worker = ImageChecker(img_queue, bad_img_queue)
        worker.daemon = True
        worker.start()
        
    img_queue.join()
    
    print("done.")
    
    n_bad_imgs = bad_img_queue.qsize()
    bad_imgs = []

    if n_bad_imgs > 0:
        print("\n{0} images could not be loaded.".format(n_bad_imgs))        
        while bad_img_queue.qsize() > 0:
            bad_imgs.append(bad_img_queue.get())
        with open(os.path.join(top_dir, "Bad_Images.csv"), 'w') as outfile:
            outfile.write("Path\n")
            outfile.write('\n'.join(sorted(bad_imgs)))
    else:
        print("\nAll images loaded successfully. No errors detected.")
    
    return sorted(bad_imgs)


class ImageChecker(mp.Process):
    """Worker that checks for bad image files.
    
    Fetches image paths from self.in_queue and checks them using 
    checkImageFiles(). Paths of image files that could not be loaded 
    are placed in self.bad_queue. Process will run until its in_queue
    is empty.
    
    Attributes:
        
        in_queue (multiprocessing.JoinableQueue): Queue containing 
            paths to image files to be checked.
        
        bad_queue (multiprocessing.Queue): Queue to hold paths to image
            files that could not be loaded.
    """

    def __init__(self, in_queue, bad_queue):
        """Initializes the instance with input and output queues.
        
        Args:
            
            in_queue (multiprocessing.JoinableQueue): Queue listing 
                image files to check.
            
            bad_queue (multiprocessing.Queue): Queue where paths to bad
                image files should go.
        """
        mp.Process.__init__(self)
        self.in_queue = in_queue
        self.bad_queue = bad_queue

    
    def run(self):
        while True:
            img_path = self.in_queue.get()
            img_loads = checkImageFile(img_path)
            if not img_loads:
                self.bad_queue.put(img_path)
            self.in_queue.task_done()