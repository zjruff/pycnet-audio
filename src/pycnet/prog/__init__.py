"""Defines functions and classes for displaying text progress bars.

Functions:

    makeProgBar
        Generates a text progress bar.

Classes:

    ProgBarWorker
        Monitors progress and prints a text-based progress bar.
"""

import time
from multiprocessing import Process, Queue


def makeProgBar(done, total, width=30):
    """Create a nicely formatted text-based progress bar.
    
    Arguments:
    
        done (int): How many items from the to-do list have been 
            completed.
    
        total (int): How many items were in the to-do list initially.

        width (int): Number of characters comprising the fillable 
            portion of the progress bar.
    
    Returns:
    
        str: A nicely formatted text-based progress bar.
    """
    
    prop_done = done / total
    n_fill = int(prop_done * width)
    pct_done = "{0:.1f}".format(prop_done * 100)
    sep_char = '=' if done == total else '>'
    prog_bar = "  [{0}{1}{2}] {3}/{4} ({5}%)".format("="*n_fill, sep_char, "."*(width-n_fill), done, total, pct_done)
    return prog_bar


class ProgBarWorker(Process):
    """A worker that prints a text-based progress bar.
    
    When running, the worker will regularly check the number of items
    in done_queue, compute progress as a proportion of total_size, and
    generate and print a text-based progress bar. When the size of 
    done_queue equals total_size (i.e., all tasks are complete), the 
    process stops.
    
    Attributes:

        done_queue (Multiprocessing.Queue): Queue to track completed 
            tasks.

        total_size (int): Number of tasks to be performed.
    """

    def __init__(self, done_queue, total_size):
        """Initializes the instance with a set of tasks to monitor.
        
        Args:
        
            done_queue (Multiprocessing.Queue): Queue listing items 
                that have been completed.
            
            total_size (int): The number of items that were on the 
                to-do list initially.
        """
        
        Process.__init__(self)
        self.done_queue = done_queue
        self.total_size = total_size
        self.done = 0


    def run(self):
        print(makeProgBar(0, self.total_size, 30), end='\r')
        while True:
            n_done = self.done_queue.qsize()
            progbar = makeProgBar(n_done, self.total_size, 30)

            if all([n_done != 0, n_done == self.done]):
                # print('', end='\r')
                continue
            else:
                print(progbar) #, end='\r')
                self.done = n_done

            if n_done == self.total_size:
                break
            else:
                time.sleep(2)
