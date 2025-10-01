# Summarizing MMIF

Code to create a summary of an MMIF file, only keeping those annotations that are useful metadata (and reducing the size of the file by one or two orders of magnitude), and making some implicit relations between annotations and anchors in the source explicit.

This code requries Python 3.10 or higher and the clams-python and graphviz modules:

```bash
$ pip install clams-python==1.0.3
```

To run properly it requires MMIF files from version 1.0.0 or higher.


## Usage

The summarizer is implemented as a Python package, but also comes with a `main.py` script with an example of how to call the package.

To run the summarizer:

```bash
$ cd code
$ python main.py --full -i MMIF_FILE -o JSON_FILE
```

See `code/summarizer/summary.py` for all options.

This repository was originally intended for creating a summarizer app, but the current thinking is to add a summarize utility to the mmif-python utilities at [https://github.com/clamsproject/mmif-python/tree/develop/mmif/utils](https://github.com/clamsproject/mmif-python/tree/develop/mmif/utils).

As a result, this repository will probably be archived, but for now it will remain until the summarizer code has been ported (and other utilities in here have found a home if appropriate).
