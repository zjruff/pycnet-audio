"""Tools for displaying nice text-based progress bars while processing
audio data.

functions: 
- makeProgBar: generates a text-based progress bar.

classes:
- ProgBarWorker: monitors progress and displays it with a text-based 
progress bar.
"""

import time
from multiprocessing import Process, Queue


def makeProgBar(done, total, width=30):
    """Create a nicely formatted text-based progress bar.
    
    Progress bar expresses <done> as a proportion of <total>. 
    <width> is the total number of characters comprising the inner (filled)
    portion of the progress bar; 30 seems to work well.
    
    Arguments:
    - done: how many items from the to-do list have been completed
    - total: how many items were in the to-do list to begin with
    - width: total number of characters comprising the fillable portion
    of the progress bar.
    
    Returns:
    - prog_bar: a nicely formatted text-based progress bar.
    """
    prop_done = done / total
    n_fill = int(prop_done * width)
    pct_done = "{0:.1f}".format(prop_done * 100)
    sep_char = '=' if done == total else '>'
    prog_bar = "  [{0}{1}{2}] {3}/{4} ({5}%)".format("="*n_fill, sep_char, "."*(width-n_fill), done, total, pct_done)
    return prog_bar


class ProgBarWorker(Process):
    """A worker process that prints a text-based progress bar.
    
    """
    def __init__(self, done_queue, total_size):
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