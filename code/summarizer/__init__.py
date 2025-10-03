
import argparse
import pathlib
from summarizer.summary import Summary
from summarizer.summary2html import main as create_html


def argparser():
    parser = argparse.ArgumentParser(description='Create a JSON Summary for a MMIF file')
    parser.add_argument('-d', metavar='DIRECTORY', help='directory with input files')
    parser.add_argument('-i', metavar='MMIF_FILE', help='input MMIF file')
    parser.add_argument('-o', metavar='JSON_FILE', help='output summary file')
    parser.add_argument('--full', action='store_true', help='print full report')
    parser.add_argument('--transcript', action='store_true', help='print transcript')
    parser.add_argument('--captions', action='store_true', help='print Llava captions')
    parser.add_argument('--timeframes', action='store_true', help='print all time frames')
    #parser.add_argument('--entities', action='store_true', help='print entities from transcript')
    return parser


def create_summary():
    parser = argparser()
    args = parser.parse_args()
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
    else:
        parser.print_help()
