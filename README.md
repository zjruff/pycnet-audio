# Welcome to pycnet-audio!

`pycnet-audio` is a Python package which provides a command-line 
interface and a useful Python API for processing audio data using 
PNW-Cnet, a deep learning model developed for bioacoustics research.

This software requires Python version 3.8 and SoX. We recommend setting
up a dedicated Conda environment for easier dependency management.

## Installation

`pycnet-audio` is available from 
[the Python Package Index](https://pypi.org/project/pycnet-audio/) and can be
installed using `pip`.

First you will need to set up a compatible conda environment like so:

```
conda create -n pycnet -c conda-forge sox python=3.8
```

Then activate your environment...

```
conda activate pycnet
``` 

Finally, install the package from PyPI:

```
pip install pycnet-audio
```

This will install the package and its dependencies.

## Documentation

Full documentation for this package is hosted by Read The Docs and is 
available [here](https://pycnet-audio.readthedocs.io/en/latest/).

## Issues

Please open an issue on the [issue tracker](https://github.com/zjruff/pycnet-audio/issues).

## Contact

Please direct questions and comments to Zack (zjruff at gmail dot com).
