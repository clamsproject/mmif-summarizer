# MMIF Inspector

The inspector runs on a summary of a MMIF file created by the `mmif summarize` CLI command and it generates a mini website from the summary. See [docs/input-example.md](docs/input-example.md) for an example input file.

This code requries Python 3.10 or higher and the Jinja module:

```bash
$ pip install jinja2>=3.1.6
```

Note that this repository used to be the repository for the summarizer and associated code. The summerizer proper now lives in [https://github.com/clamsproject/mmif-python](https://github.com/clamsproject/mmif-python) and the remaining code is repurposed as an inspector. At the moment everything in this repository, including the documentation, is eminently unstable.


## Usage

The inspector is implemented as a Python package and comes with the `inspect` command utility. If you have installed the package you use:

```bash
$ inspect -i SUMMARY_FILE -o DIRECTORY
```

You can also use the  `run_inspector.py` script:

```bash
$ cd code
$ python run_inspector.py -i MMIF_FILE -o JSON_FILE
```

Usage within Python code:

```python
>>> from inspector.inspect import create_www
>>> create_www('path_to_summary_file', 'output_directory')
```


## Publishing

It is best to use a clean virtual environment with recent versions of build and twine:

```bash
$ pip install build==1.3.0 twine==6.2.0
```

Then build from the `code` directory:

```bash
$ python -m build
```

To upload to TextPyPI (you will need a PyPI token):

```bash
$ twine upload --repository testpypi dist/*
```

You can see this package at [https://test.pypi.org/project/inspector-mv/](https://test.pypi.org/project/inspector-mv/).

For more details and background see [docs/publishing.md](docs/publishing.md).
