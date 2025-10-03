Code to create a summary of an MMIF file, only keeping those annotations that are useful metadata (and reducing the size of the file by one or two orders of magnitude), and making some implicit relations between annotations and anchors in the source explicit.

This is a prototype version that will only be offered via TestPyPI.


### Installation

Don't believe what it says in the header, it may give errors. The following seems to be more robust:

```bash
$ python3 -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ summarizer-mv
```

To run properly it requires MMIF files from version 1.0.0 or higher.

This package comes with two command line scripts, one to create a JSON summary of a MMIF file and one to create a mini website from the summary. 


### Creating a summary

```bash
$ summarize --full -i MMIF_FILE -o JSON_FILE
```

This creates a full summary, including transcript, captions and time frames. To see all options run the command with the -h option. From the Python prompt you can do this:

```python
>>> from summarizer import Summary
>>> with open('input.mmif') as fh:
...     mmif_text = fh.read()
...     mmif_summary = Summary(mmif_text)
...     mmif_summary.report(outfile='out.json', full=True)
```

See the README file of the GitHub repository at [https://github.com/clamsproject/mmif-summarizer/](https://github.com/clamsproject/mmif-summarizer/) for an output example.

<!--
TODO: this should be pinned to a fixed file.
-->


### Creating the mini webpage

```bash
$ create-html JSON_FILE HTML_DIR
```

The directory has an index file and files for the views, transcript, captions and time frames. 

As with the summary, see the GitHub repository for example output.


### Wishlist

Things to be added soon:

- Add summary for entities recognized by spaCy.
- Add JSON schema for the output.
- The information in the view is now a summary, add an option so it prints the full content, including warnings and errors from views.
