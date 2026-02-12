"""

Utility script to provided an entry point to some current other scripts and
utilities.

Assumes that the Python command connects to an environment with the proper
modules installed.

To run this do one of the following.


$ python run.py --load MMIF_FILE

Load a MMIF file just to check whether it loads fine.


$ python run.py --inspect DIRECTORY

DIRECTORY is a directory with MMIF Summaries. This will ask the user to enter an output
directory. It walks trough all summaries in the input directory  and creates mini-websites
for them.


"""


import os
import sys
import json
import datetime
import argparse
import subprocess
from pathlib import Path
from subprocess import Popen, PIPE

sys.path.extend('..', '../../../mmif-python/')
from mmif.serialize import Mmif
from inspector import create_www



def load_mmif(fname: str):
    loaded_mmif = Mmif(open(fname).read())
    print(len(str(loaded_mmif)))


def inspect(directory: str):
    outdir = prompt_for_output_directory()
    index_file = create_index_file(Path(outdir))
    links = {}
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in sorted(files):
            #print('>>>', name)
            # Just taking the basic MMIF files, no funny business
            if name.endswith('.json') and name.count('.') == 1:
                summary_file = Path(os.path.join(root, name))
                # Create a summary and save it, and add information on the summary
                # to the links dictionary
                inspect_file(summary_file, outdir, links)
    #index_file = Path(outdir, 'index.html')
    with index_file.open("a") as fh:
        for fname in sorted(links):
            # this is a bit like add_link_to_index_file(), refactor?
            summary_file_hash = links[fname]
            link = f'<a href={summary_file_hash}/index.html>{fname}</a>'
            fh.write(f'<tr><td>{summary_file_hash}<td>{link}</tr>\n')


def inspect_file(summary_file: Path, outdir: Path, links: dict):
    summary_file_hash = abs(hash(summary_file))
    html_dir = Path(outdir, str(summary_file_hash))
    create_www(summary_file, html_dir)
    links[summary_file] = summary_file_hash


def prompt_for_output_directory():
    outdir = input('Enter the name of an output directory: ')
    outdir = Path(outdir)
    if outdir.exists():
        exit(f'WARNING: "{outdir}" already exists, exiting...')
    outdir.mkdir(exist_ok=True)
    return outdir


def create_index_file(pages_dir: Path) -> Path:
    index_file = Path(pages_dir, 'index.html')
    style1 = 'table { border: 1px solid black; border-collapse: collapse; }'
    style2 ='td { border: 1px solid black; padding: 8px; spacing: 0px; }'
    index_file.write_text(
        '<html>\n' 
        + f'<head>\n<style>\n{style1}\n{style2}\n</style>\n</head>\n'
        + f'<body>\n\n<h3>HTML Summaries</h3>\n\n<table>\n')
    return index_file


def add_link_to_index_file(outdir: str, fname: str, links: dict):
    pipeline_name, mmif_file_hash = links[fname]
    link = f'<a href={mmif_file_hash}/index.html>{fname}</a>'
    index_file = Path(outdir, 'pages', 'index.html')
    with index_file.open("a") as fh:
        fh.write(f'<tr><td>{pipeline_name}<td>{link}</tr>\n')


def pretty_print(fname: str):
    obj = json.load(open(fname))
    print(json.dumps(obj, indent=2))


def argparser():
    help_pretty = 'pretty print a json file'
    help_inspect = 'create mini-websites for all summaries in DIR'
    parser = argparse.ArgumentParser()
    parser.add_argument('--pretty', metavar='DIR', help=help_pretty)
    parser.add_argument('--inspect', metavar='DIR', help=help_inspect)
    parser.add_argument('--load', metavar='MMIF_FILE', help='load MMIF file')
    return parser



if __name__ == '__main__':

    args = argparser().parse_args()

    if args.pretty:
        pretty_print(args.pretty)

    if args.load:
        load_mmif(args.load)

    if args.inspect:
        inspect(args.inspect)
