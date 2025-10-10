# Publishing the summarizer with mmif-python

These are preperatory notes on how to add the summarizer to the mmif-python package.


## Publishing mmif-python as it is now

First tried to do `$ python -m build`, but that was clearly not the way to go. Keigh said the following:

- He usually does `$ pip install -e .` (the -e option installs a project in editable mode from a local project path)
- There is no proper documentation,the closest is the Makefile.

Since the first fails on a missing VERSION file I did the following:

```bash
$ make version
$ pip install -e .
```

Nothing needed to be installed for this to run, except for pip itself and `make version` requires `jq` to be installed. 

The proposed default for creating a new version number is by increasing the patch level of themost recent git tags, at the time of this writing the most recent tag was 1.1.2 so the proposed default was 1.1.3. What is not clear to me is why the `docs` directory does not have 1.1.1 and 1.1.2 versions.

The pip-install command printed the following (edited to remove all details about collecting packages):

```
Obtaining file:///Users/marc/Desktop/projects/clams/code/clamsproject/mmif-python
  Installing build dependencies ... done
  Checking if build backend supports build_editable ... done
  Getting requirements to build editable ... done
  Preparing editable metadata (pyproject.toml) ... done
Collecting deepdiff>5 (from mmif-python==1.1.3)
Collecting orderly-set==5.3.* (from mmif-python==1.1.3)
Collecting jsonschema (from mmif-python==1.1.3)
Collecting deepdiff>5 (from mmif-python==1.1.3)
Collecting attrs>=22.2.0 (from jsonschema->mmif-python==1.1.3)
Collecting jsonschema-specifications>=2023.03.6 (from jsonschema->mmif-python==1.1.3)
Collecting referencing>=0.28.4 (from jsonschema->mmif-python==1.1.3)
Collecting rpds-py>=0.7.1 (from jsonschema->mmif-python==1.1.3)
Collecting typing-extensions>=4.4.0 (from referencing>=0.28.4->jsonschema->mmif-python==1.1.3)
Using cached orderly_set-5.3.2-py3-none-any.whl (12 kB)
Using cached deepdiff-8.4.2-py3-none-any.whl (87 kB)
Using cached jsonschema-4.25.1-py3-none-any.whl (90 kB)
Using cached attrs-25.3.0-py3-none-any.whl (63 kB)
Using cached jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
Using cached referencing-0.36.2-py3-none-any.whl (26 kB)
Using cached rpds_py-0.27.1-cp311-cp311-macosx_10_12_x86_64.whl (371 kB)
Using cached typing_extensions-4.15.0-py3-none-any.whl (44 kB)
Building wheels for collected packages: mmif-python
  Building editable for mmif-python (pyproject.toml) ... done
  Created wheel for mmif-python: filename=mmif_python-1.1.3-0.editable-py3-none-any.whl size=8062 sha256=7b54c4486f66e3203ac8ddee77595bb7fdd7413ebd87c2a9d9dd6b3b0f8e8531
  Stored in directory: /private/var/folders/6t/b3yp90vs0wq1fqwrqzxrsq8w0000gn/T/pip-ephem-wheel-cache-un6bzxs3/wheels/c3/af/5f/f3f20b83287609fc8fb94b9826053871b452cc71e1c220e25c
Successfully built mmif-python
Installing collected packages: typing-extensions, rpds-py, orderly-set, attrs, referencing, deepdiff, jsonschema-specifications, jsonschema, mmif-python
Successfully installed attrs-25.3.0 deepdiff-8.4.2 jsonschema-4.25.1 jsonschema-specifications-2025.9.1 mmif-python-1.1.3 orderly-set-5.3.2 referencing-0.36.2 rpds-py-0.27.1 typing-extensions-4.15.0
```

That wheel file in `/private/var` does not appear to exist. What has happend is that you now have packages loaded into the environment:

```bash
$ pip list
```
```
Package                   Version  Editable project location
------------------------- -------- ----------------------------------------------------------------
attrs                     25.3.0
deepdiff                  8.4.2
jsonschema                4.25.1
jsonschema-specifications 2025.9.1
mmif-python               1.1.3    /Users/marc/Desktop/projects/clams/code/clamsproject/mmif-python
orderly-set               5.3.2
pip                       23.2.1
referencing               0.36.2
rpds-py                   0.27.1
setuptools                68.2.2
typing_extensions         4.15.0
```

Note that mmif-python has a special status, unlike the others, it is not in the `lib/python3.11/site-packages/` directory of the virtual environment I used. There is a directory `mmif_python-1.1.3.dist-info/` within `site-packages`.

However, when I import mmif from the Python prompt I get the following error:

```
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/Users/marc/Desktop/projects/clams/code/clamsproject/mmif-python/mmif/__init__.py", line 11, in <module>
    from mmif.vocabulary import *
ModuleNotFoundError: No module named 'mmif.vocabulary'
```

And the same error happens when you try to run the `mmif` command line script.

Ah, found it in the Makefile. Need to generate some code first before doing the pip-install.

```makefile
generatedcode = $(packagename)/ver $(packagename)/res $(packagename)/vocabulary 

$(generatedcode): dist/$(sdistname)*.tar.gz
```

I only needed to do `make mmif/vocabulary`, which does the following:

1. Create a `mmif/ver` directory which makes available `__version__` and `__specver__`.
2. Create a `mmif/res` directory which makes available `mmif.json` (the MMIF JSON schema) and `clams.vocabulary.yaml` (the CLAMS vocabulary definition file from [https://github.com/clamsproject/mmif/](https://github.com/clamsproject/mmif/blob/develop/vocabulary/clams.vocabulary.yaml)).
3. Create a `mmif/vocabulary` directory which implements the CLAMS doxcument types and annotation types.
4. Edit `/documentation/target-versions.csv` by adding the new version.
5. Create a directory `mmif_python.egg-info/` with package information. It is not clear to me why this is created at this step.

And then `make package` creates `dist/mmif_python-1.1.3.tar.gz`. As a side-effect it install about a hundred modules, so you want this in a separate environment.

> However, it looks like `make mmif/vocabulary` also creates `dist/mmif_python-1.1.3.tar.gz`. Should probably just use `make all`.

Finally:

```bash
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install dist/mmif_python-1.1.3.tar.gz
$ mmif
```
```
usage: mmif [-h] [-v] {rewind,source} ...

options:
  -h, --help       show this help message and exit
  -v, --version    show program's version number and exit

sub-command:
  {rewind,source}
    rewind         provides CLI to rewind a MMIF from a CLAMS pipeline.
    source         provides CLI to create a "source" MMIF json.
```

To sum it all up, from scratch (in progress)

```bash
$ git clone https://github.com/clamsproject/mmif-python
$ cd mmif-python
$ make version
$ make mmif/vocabulary
$ python -m venv .venv
$ source .venv/bin/activate
...
```


## Adding the summarizer

The mmif-python package has a way to deal with utility scripts, in particular cli scripts. They all live in the `mmif/utils` directory and the cli utilities in `mmif/utils/cli`. The `mmif/utils/c__init__.py` has some code in a `cli()` that does the following:

```python
for cli_module in find_all_modules('mmif.utils.cli'):
    cli_module_name = cli_module.__name__.rsplit('.')[-1]
    cli_modules[cli_module_name] = cli_module
    subcmd_parser = cli_module.prep_argparser(add_help=False)
```

This finds modules in the top-level of the cli directory, but note that it will descend down that directory. It is going to be easiest to just add single module in there and not packages like the summary. The single script would then import the summary utility that will live in the utils directory, together with the helper scripts that are already there.

Notice the use of `prep_argparser()`, the current code requires utility scripts to have that method. As far as I can see at the moment that is the only restriction on what is in the cli script.

In the setup.py script there is this passage at the end of the file:

```python
    entry_points={
        'console_scripts': [
            'mmif = mmif.__init__:cli',
        ],
    },
```

I think this means that for adding cli scripts we do not need to change the setup file, but we do need to do something to the initialization file of the cli package, which now has

```python
from mmif.utils.cli import rewind
from mmif.utils.cli import source
```

