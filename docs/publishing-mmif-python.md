# Publishing the summarizer with mmif-python

These are preperatory notes on how to add the summarizer to the mmif-python package.


## Developing mmif-python

There is no real documentation, the closest is the Makefile. But to work on mmif-python code the simplest is to do the following:

- Generate a version file and some code
- Use pip to install a local editable mmif-python
- Use and change the mmif package


### Version file and code generation

In order to install and use the package some code needs to be generated (otherwise you get import errors). And code generation requires there to be a `VERSION` file. Create or change it manually. Or create a new one with (this does not overwrite an existing file):

```bash
$ make version
```

Nothing needed to be installed for this to run except for `jq`. The proposed default for creating a new version number is by increasing the patch level of the most recent git tags, at the time of this writing the most recent tag was 1.2.1 so the proposed default was 1.2.2.

Now generate the code needed with

```bash
$ make mmif/vocabulary
```

You may want to do this in a separate build environment because it does install 60+ modules. The following will be done with the above make command:

1. Create a `mmif/ver` directory which makes available `__version__` and `__specver__`.
2. Create a `mmif/res` directory which makes available `mmif.json` (the MMIF JSON schema) and `clams.vocabulary.yaml` (the CLAMS vocabulary definition file from [https://github.com/clamsproject/mmif/](https://github.com/clamsproject/mmif/blob/develop/vocabulary/clams.vocabulary.yaml)).
3. Create a `mmif/vocabulary` directory which implements the CLAMS doxcument types and annotation types.
4. Create a directory `mmif_python.egg-info/` with package information. 
5. Create a directory `dist` with a distribution source archive `mmif_python-VERSION.tar.gz`.

An earlier version of these notes added that the new version will be added to `/documentation/target-versions.csv`. This actually does not appear to happen, find out when it does. Also, the file does not have any versions after 1.2.0 and it is not clear to me why that is.


### Local install

You can now install the mmif package in your environment:

```bash
$ pip install dist/mmif_python-VERSION.tar.gz
```

But you can also totally bypass the distribution and install from local source 

```bash
$ pip install -e .
```

After this, you have packages loaded into the environment:

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


### Using and editing the package

Simply load it into Python or run the command line script:

```bash
$ mmif
```
You should get a help message.

The beauty of the local source install is that you can edit some code and immediately see its effect. For example, you could edit `mmif/__init__.py` and change the name of the options in `prep_argparser_and_subcmds()`. When you then run the mmif command again the help message should be different.


