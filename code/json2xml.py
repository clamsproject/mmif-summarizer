"""JSON to XML converter for MMIF summaries

Usage:

$ python json2xml.py <summary_file>

"""

# TODO: This is very much out of date and may be deprecated
# TODO: add slate (with contents)
# TODO: add credits (with contents)
# TODO: add chyrons (with contents)
# TODO: add tags
# TODO: add entities


import json, io, sys
import utils


def add_version(data, s):
    s.write(f'  <mmif_version>{data["mmif_version"]}</mmif_version>\n')

def add_documents(data, s):
    s.write(utils.xml_tag('documents', 'document',
                          data['documents'], ('id', 'type', 'location')))

def add_views(data, s):
    if 'views' in data:
        s.write(utils.xml_tag('views', 'view',
                              data['views'], ('id', 'app', 'timestamp')))

def add_bars_and_tone(data, s):
    if 'bars-and-tone' in data:
        s.write(utils.xml_tag('bars_and_tone', 'timeframe',
                              data['bars-and-tone'], ('id', 'start', 'end', 'frameType')))

def add_segments(data, s):
    if 'segments' in data:
        s.write(utils.xml_tag('segments', 'timeframe',
                              data['segments'], ('id', 'start', 'end', 'frameType')))

def add_transcript(data, s):
    s.write('  <transcript>\n')
    for line in data['transcript']:
        attrs = [f'start={utils.xml_attribute(line[1])}',
                 f'end={utils.xml_attribute(line[2])}',
                 f'text={utils.xml_attribute(line[0])}']
        attrs_str = ' '.join(attrs)
        s.write(f'    <line {attrs_str}/>\n')
    s.write('  </transcript>\n')

def json2xml(fname: str):
    with open(fname) as fh:
        data = json.load(fh)
        s = io.StringIO()
        s.write('<?xml version="1.0" ?>\n')
        s.write('<summary>\n')
        add_version(data, s)
        add_documents(data, s)
        add_views(data, s)
        add_bars_and_tone(data, s)
        add_segments(data, s)
        add_transcript(data, s)
        s.write('</summary>\n')
        return s.getvalue()


if __name__ == '__main__':
    print(json2xml(sys.argv[1]))
