"""Provides an interface for command-line processing of audio data.

This interface can be accessed by calling "python -m pycnet [args]" or 
simply "pycnet [args]"
"""

import pycnet

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
    valid_modes = ["process", "spectro", "predict", "review", "inventory", "rename", "cleanup"]

    args = pycnet.process.CLArgParser.parsePycnetArgs()

    if not args.mode in valid_modes:
        print("\nMode '{0}' not recognized. Please use one of the following options:".format(args.mode))
        print('\n'.join(valid_modes))

    else:
        if args.mode == "process":
            proc_args = [args.mode, args.target_dir, args.cnet_version, args.image_dir, args.n_workers, args.review_settings]
            pycnet.process.processFolder(*proc_args)

        elif args.mode == "spectro":
            spectro_args = [args.mode, args.target_dir, args.cnet_version, args.image_dir, args.n_workers]
            pycnet.process.processFolder(*spectro_args, cleanup=False)

        elif args.mode == "predict":
            predict_args = [args.mode, args.target_dir, args.cnet_version, args.image_dir]
            pycnet.process.processFolder(*predict_args, cleanup=False)

        elif args.mode == "review":
            review_args = [args.mode, args.target_dir, args.cnet_version]
            pycnet.process.processFolder(*review_args, cleanup=False)

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