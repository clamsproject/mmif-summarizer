"""

Utility script to provided an entry point to some current other scripts and
utilities.

Assumes that the Python command connects to an environment with the proper
modules installed.

To run this do one of the following.


$ python run.py --load MMIF_FILE

Load a MMIF file just to check whether it loads fine.


$ python run.py --cut MMIF_FILE --start INT --end INT

Cut all annotations from a MMIF file except for those within a time range:


$ python run.py --summarize DIRECTORY

DIRECTORY is a directory with CLAMS processing results. This will ask the user to enter
an output directory. It walks trough all MMIF files in the input directory and summarizes
them and creates mini-websites for them. This actually only creates the scaffolding for
that website but also writes to standard output the commands that can be used for the
actual summarization.

This is now obsolete here and should be moved to mmif-python if we want to keep it.


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


def cut_mmif(fname: str, start: int, end: int):
    print('>>> OPENING MMIF FILE')
    mmif_obj = mmif.Mmif(open(fname).read())
    print('>>> GETTING ANNOTATIONS')
    annotations = mmif_obj.get_annotations_between_time(start, end)
    print('>>> WRITING ANNOTATIONS')
    for annotation in annotations:
        #continue
        #if annotation.at_type.shortname == 'TimeFrame':
        print(annotation.id, annotation.at_type)


def summarize(directory: str):
    outdir = prompt_for_output_directory()
    Path(outdir, 'summaries').mkdir(exist_ok=True)
    Path(outdir, 'pages').mkdir(exist_ok=True)
    create_index_file(Path(outdir, 'pages'))
    create_log_file(Path(outdir, 'log.txt'))
    links = {}
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in sorted(files):
            # Just taking the basic MMIF files, no funny business
            if name.endswith('.mmif') and name.count('.') == 1:
                mmif_file = Path(os.path.join(root, name))
                # Create a summary and save it, and add information on the summary
                # to the links dictionary 
                summarize_file(mmif_file, outdir, links)
    for fname in sorted(links):
        add_link_to_index_file(outdir, fname, links)


def summarize_file(mmif_file: Path, outdir: Path, links: dict):
    mmif_file_hash = abs(hash(mmif_file))
    json_file = Path(outdir, 'summaries', mmif_file.stem + '.json')
    html_dir = Path(outdir, 'pages', str(mmif_file_hash))
    command = create_command(mmif_file, json_file, html_dir)
    print(f'\n{command_as_pretty_string(command)}\n')
    with (outdir / 'log.txt').open('a') as fh:
        sep = "=" * 100
        fh.write(f'\n{sep}\n{command_as_pretty_string(command)}\n{sep}\n\n')
    run_command(outdir, command)
    pipeline_name, file_name, mmif_file_hash = \
        create_link_for_index_file(mmif_file, mmif_file_hash)
    links[file_name] = (pipeline_name, mmif_file_hash)
    #add_link_to_index_file(Path(outdir, 'pages'), mmif_file, mmif_file_hash)


def inspect(directory: str):
    print(9999)
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


def create_command(infile, outfile, outdir):
    return f'python run_summarizer.py --full -i {infile} -o {outfile} --html {outdir}'


def run_command(outdir: Path, command: str):
    process = Popen(command.split(), stdout=PIPE, stderr=PIPE)
    stdout_lines = process.stdout.readlines()
    stderr_lines = process.stderr.readlines()
    print('output lines:', len(stdout_lines))
    print('error lines:', len(stderr_lines))
    with (outdir / 'log.txt').open('ba') as fh:
        if stdout_lines:
            fh.write(b'STDOUT\n\n')
            for line in stdout_lines:
                fh.write(line)
            fh.write(b'\n\n')
        if stderr_lines:
            fh.write(b'STDERR\n\n')
            for line in stderr_lines:
                fh.write(line)
            fh.write(b'\n\n')


def command_as_pretty_string(command):
    """Make the command readable by spacing it out a bit."""
    command = command.replace(' -i', ' \\\n    -i')
    command = command.replace(' -o', ' \\\n    -o')
    command = command.replace(' --html', ' \\\n    --html')
    return command


def create_index_file(pages_dir: Path) -> Path:
    index_file = Path(pages_dir, 'index.html')
    style1 = 'table { border: 1px solid black; border-collapse: collapse; }'
    style2 ='td { border: 1px solid black; padding: 8px; spacing: 0px; }'
    index_file.write_text(
        '<html>\n' 
        + f'<head>\n<style>\n{style1}\n{style2}\n</style>\n</head>\n'
        + f'<body>\n\n<h3>HTML Summaries</h3>\n\n<table>\n')
    return index_file


def create_log_file(log_file):
    log_file.write_text(f'{str(datetime.datetime.now())}\n\n')


def create_link_for_index_file(mmif_file, mmif_file_hash):
    """Return a tuple with all components needed for a link."""
    print_name = str(mmif_file)
    if print_name.startswith('examples/pipelines'):
        print_name = print_name[19:]
    pipeline_name, file_name = print_name.split(os.sep)
    link = f'<a href={mmif_file_hash}/index.html>{file_name}</a>'
    return pipeline_name, file_name, mmif_file_hash


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
    help_sum = 'summarize all available MMIF files in DIR'
    help_inspect = 'create mini-websites for all summaries in DIR'
    help_cut = 'load MMIF file and keep only annotations within a timeframe'
    help_start = 'with --cut option, start of timeframe'
    help_end = 'with --cut option, end of timeframe'
    parser = argparse.ArgumentParser()
    parser.add_argument('--pretty', metavar='DIR', help=help_pretty)
    parser.add_argument('--summarize', metavar='DIR', help=help_sum)
    parser.add_argument('--inspect', metavar='DIR', help=help_inspect)
    parser.add_argument('--load', metavar='MMIF_FILE', help='load MMIF file')
    parser.add_argument('--cut', metavar='MMIF_FILE', help=help_cut)
    parser.add_argument('--start', metavar='INT', help=help_start)
    parser.add_argument('--end', metavar='INT', help=help_end)
    return parser



if __name__ == '__main__':

    args = argparser().parse_args()

    if args.pretty:
        pretty_print(args.pretty)

    if args.load:
        load_mmif(args.load)

    if args.cut:
        cut_mmif(args.cut, args.start, args.end)

    if args.summarize:
        summarize(args.summarize)

    if args.inspect:
        inspect(args.inspect)
