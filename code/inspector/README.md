The inspector creates a set of webpages from a summary of a MMIF file created by the `mmif summarize` CLI command in the [mmif-python package](https://pypi.org/project/mmif-python/).

If you have installed the inspector you can use the `inspect` command utility:

```bash
inspect -i SUMMARY_FILE -o DIRECTORY
```

After this drop the index file in the output directory into a browser.

Usage within Python code:

```python
>>> import inspector
>>> inspector.create_www('path_to_summary_file', 'output_directory')
```

