"""

python create_html.py SUMMARY DIRECTORY

"""

import io
import sys
import json
import pathlib

import utils


# Pages for the mini-web site
index_page = 'index.html'
views_page = 'views.html'
timeframes_page = 'timeframes.html'
transcript_page = 'transcripts.html'
captions_page = 'captions.html'


# Some XML tag attributes
a_right = 'align=right'
a_topleft = 'align=right valign=top'
a_top = 'valign=top'


# style sheet
style = '''
<style>

body {
    margin: 15px;
}

h2, h3 {
    border: 1px solid darkred;
    border-radius: 15px;
    background: lightblue;
    padding: 15px;
}

div {
    margin-top: -20px;
    margin-bottom: -20px;
}

p.view {
    border: 1px solid darkgreen;
    border-radius: 15px;
    xbackground: url(paper.gif);
    background: #fffae6;
    display: inline-block;
    padding: 15px;
}

table.noborder {
    border: 0px;
    border-collapse: collapse;
}

table {
    border: 1px solid black;
    border-collapse: collapse;
}

table.transcript {
    border: 0px;
    border-collapse: collapse;
    border-top: 1px solid #ddd;
}

.transcript tr {
    border-bottom: 1px solid #ddd;
}

.transcript tr:hover {
    background-color: #eee;
}

.transcript td {
    border: 0px;
}

td {
    border: 1px solid black;
    padding: 8px;
    spacing: 0px;
}

.noborder td {
    border: 0px;
    padding: 4px;
}

</style>
'''


def create_html(infile: str, outdir: str):
    outpath = pathlib.Path(outdir)
    outpath.mkdir(exist_ok=True)
    for f in outpath.glob("*"):
        if f.is_file() and f.name.endswith('.html'):
            f.unlink()
    summary = json.loads(pathlib.Path(infile).open().read())
    page = Html(infile, outpath / index_page)
    page.write(f'<a href="{views_page}">Views</a>\n')
    create_html_views(infile, outpath, summary)
    if 'timeframes' in summary:
        add_index_link(page, summary, 'timeframes', timeframes_page)
        create_html_timeframes(infile, outpath, summary)        
    if 'transcript' in summary:
        add_index_link(page, summary, 'transcript', transcript_page)
        create_html_transcript(infile, outpath, summary)
    if 'captions' in summary:
        add_index_link(page, summary, 'captions', captions_page)
        create_html_captions(infile, outpath, summary)
    page.write_to_file()


def add_index_link(page, summary, summary_part, part_page):
    if summary[summary_part]:
        page.write(f'<p><a href="{part_page}">{summary_part.capitalize()}</a></p>\n')


def create_html_views(infile: str, outpath: pathlib.Path, summary: dict):
    page = Html(infile, outpath / views_page, 'Views')
    for view in summary['views']:
        page.write('<div>\n<p class=view>\n<table>\n')
        page.write_tr(
            ('id', view['id']),
            ('app', view['app']),
            ('timestamp', view['timestamp']))
        page.write('<tr>\n')
        page.write(f'  <td valign=top>contains</td>\n')
        page.write(f'  <td>\n')
        page.write(f'  <table class=noborder>\n')
        #page.write(f'  <table class=noborder border=0 cellspacing=4 cellpadding=0>\n')
        for attype in sorted(view['annotation_types']):
            count = view['annotation_types'][attype]
            page.write_tr((attype, '&nbsp;', (count, a_right)), indent=2)
        page.write_tr(('TOTAL', '&nbsp;', (view["annotations"], a_right)), indent=2)
        page.write(f'  </table>\n')
        page.write(f'  </td>\n')
        page.write('</tr>\n')
        page.write('</table>\n</p>\n</div>\n\n')
    page.write_to_file()


def create_html_timeframes(infile: str, outpath: pathlib.Path, summary: dict):
    page = Html(infile, outpath / timeframes_page, 'Timeframes')
    for app in summary['timeframes']:
        page.write(f'<h4>{app}</h4>\n\n')
        page.write('<table class=transcript>\n')
        page.write_tr(('start', 'end', 'reps', 'label', 'score'))
        for tf in summary['timeframes'][app]:
            t1 = utils.timestamp(tf['start-time'])
            t2 = utils.timestamp(tf['end-time'])
            reps = [utils.timestamp(rep) for rep in tf['representatives']]
            score = '' if tf['score'] is None else f'{tf["score"]:06.4f}'
            page.write_tr(
                (t1, t2, ' '.join(reps), tf['label'], score))
        page.write('</table>\n')
        page.write_to_file()


def create_html_transcript(infile: str, outpath: pathlib.Path, summary: dict):
    page = Html(infile, outpath / transcript_page, 'Transcript')
    page.write('<table class=transcript>\n')
    for sentence in summary['transcript']:
        t1 = utils.timestamp(sentence['start-time'])
        t2 = utils.timestamp(sentence['end-time'])
        page.write_tr(((t1, a_topleft), (t2, a_topleft), sentence['text']))
    page.write('</table>\n')
    page.write_to_file()

def create_html_captions(infile: str, outpath: pathlib.Path, summary: dict):
    page = Html(infile, outpath / captions_page, 'Captions')
    page.write('<table class=transcript>\n')
    for caption in summary['captions']:
        text = caption['text'].replace('\n', '<br/>')
        tp = utils.timestamp(caption['time-point'])
        page.write_tr(((tp, a_topleft), (caption['identifier'], a_top), text))
    page.write('</table>\n')
    page.write_to_file()


class Html:

    def __init__(self, infile: str, outpath: pathlib.Path, header: str = None):
        self.path = outpath
        self.stream = io.StringIO()
        self.stream.write(f'<head>{style}</head>\n<body>\n\n')
        self.stream.write(f'<h2>{pathlib.Path(infile).stem}</h2>\n\n')
        if header is not None:
            self.stream.write(f'<h3>{header}</h3>\n\n')
        self.views = []
        self.captions = []

    def write(self, text: str):
        self.stream.write(text)

    def write_tr(self, *table_cells, indent=0):
        for cells in table_cells:
            self.stream.write(f'{" " * indent}<tr>\n')
            for cell in cells:
                if isinstance(cell, tuple):
                    self.stream.write(f'{" " * indent}  <td {cell[1]}>{cell[0]}</td>\n')
                else:
                    self.stream.write(f'{" " * indent}  <td>{cell}</td>\n')
            self.stream.write(f'{" " * indent}</tr>\n')

    def write_to_file(self):
        self.path.write_text(self.stream.getvalue())


if __name__ == '__main__':

    infile, outdir = sys.argv[1:3]
    create_html(infile, outdir)
