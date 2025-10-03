# Summarizing MMIF

Code to create a summary of an MMIF file, only keeping those annotations that are useful metadata (and reducing the size of the file by one or two orders of magnitude), and making some implicit relations between annotations and anchors in the source explicit.

This code requries Python 3.10 or higher and the clams-python module:

```bash
$ pip install clams-python>=1.1.3
```

To run properly it requires MMIF files from version 1.0.0 or higher. There are no plans to make older MMIF files palatable to the summarizer.

The summarizer can generate a JSON summary as well as a mini website from the summary. See [docs/output/index.md](docs/output/index.md) for a description of the output. One of the perks of the summarizer is that errors in the MMIF file are made more obvious, the output description has an example of that. 



## Usage

The summarizer is implemented as a Python package. If you have installed the package you have access to the summarize and create-html command utilities, but the package also comes with `run_summarizer.py` and `run_html.py` scripts that call the package.

The summarizer creates a JSON summary, which can then be turned into a mini webpage. After installing the module you can run the code as follows:

```bash
$ summarize --full -i MMIF_FILE -o JSON_FILE
$ create-html JSON_FILE HTML_DIR
```

For development you can run the code from this repository using the run scripts:

```bash
$ cd code
$ python run_summarizer.py --full -i MMIF_FILE -o JSON_FILE
$ python run_html.py JSON_FILE HTML_DIR
```


For all options, see `code/summarizer/summary.py` and [code/summarizer/README.md](code/summarizer/README.md). The latter is what is published on PyPI.


## Publishing

This is the short version, for more details see [docs/publishing.md](docs/publishing.md).

It is best to use a clean virtual environment with recent versions of build and twine:

```bash
$ pip install build==1.3.0 twine==6.2.0
```

You build from the `code` directory:

```bash
$ python -m build
```

To upload to TextPyPI (you will need a PyPI token):

```bash
$ twine upload --repository testpypi dist/*
```

You can see this package at [https://test.pypi.org/project/summarizer-mv/](https://test.pypi.org/project/summarizer-mv/).


## Some history

This repository was originally intended for creating a CLAMS summarizer app, but the current thinking is to add a summarize utility to the mmif-python utilities at [https://github.com/clamsproject/mmif-python/tree/develop/mmif/utils](https://github.com/clamsproject/mmif-python/tree/develop/mmif/utils).

As a result, this repository will probably eventually be archived, but for now it will remain until the summarizer code has been ported (and other utilities in here have found a home if appropriate).
