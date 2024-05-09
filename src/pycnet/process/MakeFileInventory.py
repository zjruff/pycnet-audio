"""Build an inventory of files with a .wav extension under the target
directory and write it to a comma-separated text file. Information
includes the subfolder (relative to the target directory), size of each
file in bytes, and duration of each file in seconds.
Designed to be run as a standalone console script. For more general use,
see pycnet.process.__init__:inventoryFolder
"""

import os
import sys

from pycnet.file import inventoryFolder

def main():
    help_message = "\nUsage:\ninventory_folder <path to target directory>\n"
    if len(sys.argv) < 2:
        print(help_message)
    else:
        try:
            target_dir= sys.argv[1]
            inventoryFolder(target_dir)
        except:
            print("\nInvalid target directory.")
            print(help_message)

if __name__ == "__main__":
    main()