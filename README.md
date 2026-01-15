# MMIF Inspector

> This repository used to be the repository for the summarizer and associated code. The summerizer proper now lives in [https://github.com/clamsproject/mmif-python](https://github.com/clamsproject/mmif-python) and the remaining code is repurposed as an inspector. At the moment everything in this repository, including the documentation, is eminently unstable.

Code to create a summary of an MMIF file, only keeping those annotations that are useful metadata (and reducing the size of the file by one or two orders of magnitude), and making some implicit relations between annotations and anchors in the source explicit.

This code requries Python 3.10 or higher and the clams-python module:

```bash
$ pip install clams-python>=1.3.3
```

The inspector runs on a summary of a MMIF file created by the `mmif summarize` CLI command and it generates a mini website from the summary. See [docs/output/index.md](docs/output/index.md) for a description of the output. One of the perks of the summarizer is that errors in the MMIF file are made more obvious, the output description has an example of that. 

To run properly it requires MMIF files from version 1.0.0 or higher. There are no plans to make older MMIF files palatable to the summarizer.


## Usage

The inspector is implemented as a Python package. If you have installed the package you have access to the inspect command utility, but the package also comes with the `run_inspector.py` script which calls the package.

```bash
$ inspect -i MMIF_FILE -o JSON_FILE
```

For development you can run the code from this repository using the run script:

```bash
$ cd code
$ python run_inspector.py -i MMIF_FILE -o JSON_FILE
```


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
