"""

Main script to run the summarizer. Collects the arguments and uses the summary
package to do the real work.

"""


import argparse
import pathlib
from summarizer import Summary


def parse_arguments():
    parser = argparse.ArgumentParser(description='Create a JSON Summary for a MMIF file')
    parser.add_argument('-d', metavar='DIRECTORY', help='directory with input files')
    parser.add_argument('-i', metavar='MMIF_FILE', help='input MMIF file')
    parser.add_argument('-o', metavar='JSON_FILE', help='output summary file')
    parser.add_argument('--full', action='store_true', help='print full report, overrule other options')
    parser.add_argument('--views', action='store_true', help='include view metadata')
    parser.add_argument('--transcript', action='store_true', help='include transcript')
    parser.add_argument('--captions', action='store_true', help='include Llava captions')
    parser.add_argument('--timeframes', action='store_true', help='include all time frames')
    parser.add_argument('--entities', action='store_true', help='include entities from transcript')
    return parser.parse_args()


if __name__ == '__main__':

    args = parse_arguments()
    if args.d:
        for mmif_file in pathlib.Path(args.d).iterdir():
            if mmif_file.is_file() and mmif_file.name.endswith('.mmif'):
                print(mmif_file)
                json_file = str(mmif_file)[:-4] + 'json'
                mmif_summary = Summary(mmif_file.read_text())
                mmif_summary.report(
                    outfile=json_file, full=args.full,
                    timeframes=args.timeframes, transcript=args.transcript,
                    captions=args.captions, entities=args.entities)
    elif args.i and args.o:
        with open(args.i) as fh:
            mmif_text = fh.read()
            mmif_summary = Summary(mmif_text)
            mmif_summary.report(
                outfile=args.o, full=args.full,
                timeframes=args.timeframes, transcript=args.transcript,
                captions=args.captions, entities=args.entities)
