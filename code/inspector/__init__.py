
import argparse

from inspector.inspect import create_html


def argparser():
    parser = argparse.ArgumentParser(description='Create a mini website for a MMIF Summary')
    parser.add_argument('-i', metavar='IN_FILE', help='input JSON summary file', required=True)
    parser.add_argument('-o', metavar='HTML_DIR', help='output HTML files', required=True)
    return parser


def main():
    parser = argparser()
    args = parser.parse_args()
    create_html(args.i, args.o)
