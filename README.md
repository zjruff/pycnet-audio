# Welcome to pycnet-audio!

`pycnet-audio` is a Python package which provides a command-line 
interface and a useful Python API for processing audio data using 
PNW-Cnet, a deep learning model developed for bioacoustics research.

## Installation

`pycnet-audio` is available from the
[Python Package Index](https://pypi.org/project/pycnet-audio/) and can be
installed using `pip`. However, you will first need to install a compatible 
version of Python (currently versions 3.8 through 3.11), as well as SoX. 
For ease of use, we recommend setting up a dedicated Conda environment for 
running `pycnet-audio`. We find it is easiest to do so using Miniconda.

[Install Miniconda](https://www.anaconda.com/docs/getting-started/miniconda/main), then open the
Anaconda Prompt program and run the following command:

```
conda create -n pycnet -c conda-forge sox python=3.11
```

This will create a new conda environment called `pycnet` with Python version 
3.11 and will install the required `sox` package from the 
[conda-forge](https://conda-forge.org/) repository.

Next, activate your environment...

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
