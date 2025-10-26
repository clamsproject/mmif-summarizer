"""

python create_html.py SUMMARY DIRECTORY

"""

import os
import io
import sys
import json
import math
from pathlib import Path

from summarizer import utils


# Pages for the mini-web site
INDEX_PAGE = 'index.html'
CSS_PAGE = 'main.css'
JS_PAGE = 'main.js'
VIEWS_PAGE = 'views.html'
TIMEFRAMES_PAGE = 'timeframes.html'
TRANSCRIPT_PAGE = 'transcripts.html'
CAPTIONS_PAGE = 'captions.html'


# Some XML tag attributes
a_right = 'align=right'
a_topleft = 'align=right valign=top'
a_top = 'valign=top'
hide = 'style="display: none"'


def main():
    infile, outdir = sys.argv[1:3]
    create_html(infile, outdir)


def create_html(infile: str, outdir: str):

    def write_origin(page):
        command = " ".join(sys.argv)
        command = command.replace(' -i', ' \\\n    -i')
        command = command.replace(' -o', ' \\\n    -o')
        command = command.replace(' --html', ' \\\n    --html')
        page.write(f'<pre class=origin>{command}</pre>\n\n')

    def write_document(page, summary):
        page.write_section('General Info')
        page.write('<table>\n')
        mv = summary["mmif_version"]
        doc = summary['document']
        page.write_tr(
            ('MMIF Version', f'<a href="{mv}">{mv}</a>\n'),
            ('Size of MMIF file', f"{doc['size']:,d}"),
            ('Size of summary', f'{os.path.getsize(infile):,d}'))
        if 'duration_ts' in doc:
            page.write_tr(('Video duration', doc['duration_ts']))
        if 'fps' in doc:
            page.write_tr(('Frames per second', doc['fps']))
        page.write('</table>\n')
        page.write_section_end()
    
    def write_documents_and_views(page, summary):
        page.write_section('Documents and views')
        page.write('<table>\n')
        for doc in summary['documents']:
            page.write_tr((doc['id'], doc['type'], doc['location']))
        page.write('</table>\n')
        page.write('<p>\n')
        page.write('<table>\n')
        for view in summary['views']:
            page.write_tr(
                (view['id'],
                f"<a href=views.html#{view['id']}>{view['app']}</a>",
                (f"{view['annotation_count']:,d}", a_right)))
        page.write('</table>\n')
        page.write_section_end()

    def write_document_annotations(page, summary):
        page.write_section('Document-level annotations')
        for v_id in summary['annotations']:
            for anno in summary['annotations'][v_id]:
                page.write('<table>\n')
                for k, v in anno.items():
                    page.write_tr((k, v))
                page.write('</table>\n')
        page.write_section_end()

    def write_content(page, summary):
        video_length = summary['document'].get('duration_ms', float('nan'))
        if 'timeframe_stats' in summary and summary['timeframe_stats']:
            page.write_section('Content')
            # TODO: this should be wrapped in a div or a table with one row
            for app in summary['timeframe_stats']:
                stats = summary['timeframe_stats'][app]
                page.write('<table>\n')
                page.write('<tr>\n')
                page.write_td('')
                page.write_td('cumulative', attrs='colspan=2')
                page.write_td('count')
                page.write_td('average')
                page.write_td('first&nbsp;at')
                page.write_td('longest&nbsp;at')
                page.write('</tr>\n')
                for label, tf_stats in sorted_pairs(stats):
                    duration_ms = tf_stats['duration']
                    duration_ts = utils.timestamp(duration_ms)
                    count = tf_stats['count']
                    average = tf_stats['average']
                    ts_first = tf_stats['first']
                    ts_longest = tf_stats['longest']
                    coverage = duration_ms * 100 / video_length
                    page.write_tr(
                        (label, 
                         (duration_ts, a_right),
                         (f'{coverage:.2f}%', a_right), 
                         (count, a_right), 
                         (utils.timestamp(average), a_right), 
                         (utils.timestamp(ts_first), a_right), 
                         (utils.timestamp(ts_longest), a_right)))
                page.write('</table>\n')
            page.write_section_end()

    outpath = Path(outdir)
    outpath.mkdir(exist_ok=True)
    for f in outpath.glob("*"):
        if f.is_file() and f.name.endswith('.html'):
            f.unlink()

    create_resources(outpath)
    summary = json.loads(Path(infile).open().read())
    page = Html(infile, outpath / INDEX_PAGE)
    write_origin(page)
    write_document(page, summary)
    write_documents_and_views(page, summary)
    #write_document_annotations(page, summary)
    write_content(page, summary)
    page.write_section('Summaries')
    page.write('[ ')
    page.write(f'<a href="{VIEWS_PAGE}">Views</a>\n')
    create_html_views(infile, outpath, summary)
    if 'timeframes' in summary:
        add_index_link(page, summary, 'timeframes', TIMEFRAMES_PAGE)
        create_html_timeframes(infile, outpath, summary)        
    if 'transcript' in summary:
        add_index_link(page, summary, 'transcript', TRANSCRIPT_PAGE)
        create_html_transcript(infile, outpath, summary)
    if 'captions' in summary:
        add_index_link(page, summary, 'captions', CAPTIONS_PAGE)
        create_html_captions(infile, outpath, summary)
    page.write(']\n')
    page.write_section_end()
    page.write_to_file()


def add_index_link(page, summary, summary_part, part_page):
    if summary[summary_part]:
        page.write(f'| <a href="{part_page}">{summary_part.capitalize()}</a>\n')


def create_resources(outpath):
    """Copy the stylesheet and javascript file into the website."""
    css_source = Path(Path(__file__).parent, CSS_PAGE)
    css_target = Path(outpath, CSS_PAGE)
    css_target.write_text(css_source.read_text())
    js_source = Path(Path(__file__).parent, JS_PAGE)
    js_target = Path(outpath, JS_PAGE)
    js_target.write_text(js_source.read_text())


def create_html_views(infile: str, outpath: Path, summary: dict):
    """Create the page with the view information."""

    def write_view_list(page, summary):
        page.write('<div class=section>\n')
        page.write('<table class=noborder>\n')
        for view in summary['views']:
            page.write_tr(
                (f'<a href="#{view["id"]}">{view["id"]} &mdash; {view["app"]}</a>',))
        page.write('</table>\n')
        page.write('</div>\n\n')

    def write_contains(page, view):
        page.write('<tr>\n')
        page.write(f'  <td {a_top}>contains</td>\n')
        page.write(f'  <td>\n')
        for atype in view['contains']:
            page.write(f'    <a href={atype}>{atype}</a><br/>\n')
        page.write(f'  </td>\n')
        page.write('</tr>\n')

    def write_annotations(page, view, summary):
        page.write('<tr>\n')
        page.write(f'  <td {a_top}>annotation summary</td>\n')
        page.write(f'  <td>\n')
        page.write(f'  <table class=noborder>\n')
        for attype in sorted(view['annotation_types']):
            count = view['annotation_types'][attype]
            page.write_tr((attype, '&nbsp;', (count, a_right)), indent=2)
        page.write_tr(('TOTAL', '&nbsp;', (view["annotation_count"], a_right)), indent=2)
        page.write(f'  </table>\n')
        page.write(f'  </td>\n')
        page.write('</tr>\n')

    def write_warnings(page, view):
        if 'warnings' in view:
            page.write('<tr>\n')
            page.write(f'  <td {a_top}>warnings</td>\n')
            page.write('  <td>\n')
            page.write('    <pre>\n')
            for w in view['warnings']:
                try:
                    s = json.dumps(json.loads(w), indent=2)
                except Exception:
                    s = w
                page.write(f'{s}\n')
            page.write('    </pre>\n')
            page.write('  </td>\n')
            page.write('\n')
            page.write('\n')
            page.write('\n')
            page.write('</tr>\n')

    page = Html(infile, outpath / VIEWS_PAGE, 'Views')
    write_view_list(page, summary)
    for view in summary['views']:
        identifier = view['id']
        app = view['app'] 
        page.write_section(f'{identifier}', identifier=identifier)
        page.write('<table>\n')
        page.write_tr(
            ('app', f"<a href={app}>{app}</a>"),
            ('timestamp', view['timestamp']))
        if 'warnings' not in view:
            write_contains(page, view)
            write_annotations(page, view, summary)
        attrs = f'{a_top} id={view["id"]}-config style="display: none"'
        button = f'<button onclick="toggle(\'conf-{view["id"]}\')">Show/Hide</button>'
        page.write_tr((('parameters', a_top), pretty_json(view['parameters'])))
        page.write('<tr>\n')
        page.write_td('appConfiguration', a_top)
        page.write('  <td>\n')
        page.write(f'    {button}\n')
        page.write(f'    <pre id=conf-{view["id"]} style="display: none">')
        page.write(pretty_json(view['appConfiguration']))
        page.write('</pre>\n')
        page.write('  </td>\n')
        page.write('</tr>\n')
        if 'warnings' in view:
            write_warnings(page, view)
        page.write('</table>\n')
        page.write_section_end()
    page.write_to_file()


def create_html_timeframes(infile: str, outpath: Path, summary: dict):
    page = Html(infile, outpath / TIMEFRAMES_PAGE, 'Timeframes')
    for app in summary['timeframes']:
        page.write_section(app)
        #page.write(f'<h4>{app}</h4>\n\n')
        #page.write('<blockquote>\n')
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
        page.write_section_end()
        #page.write('</blockquote>\n\n')
        page.write_to_file()


def create_html_transcript(infile: str, outpath: Path, summary: dict):
    page = Html(infile, outpath / TRANSCRIPT_PAGE, 'Transcript')
    page.write('<table class=transcript>\n')
    for sentence in summary['transcript']:
        t1 = utils.timestamp(sentence['start-time'])
        t2 = utils.timestamp(sentence['end-time'])
        page.write_tr(((t1, a_topleft), (t2, a_topleft), sentence['text']))
    page.write('</table>\n')
    page.write_to_file()


def create_html_captions(infile: str, outpath: Path, summary: dict):
    page = Html(infile, outpath / CAPTIONS_PAGE, 'Captions')
    page.write('<div class=section>\n')
    page.write('<table class=transcript>\n')
    for caption in summary['captions']:
        text = caption['text'].replace('\n', '<br/>')
        tp = utils.timestamp(caption['time-point'])
        page.write_tr(((tp, a_topleft), (caption['identifier'], a_top), text))
    page.write('</table>\n')
    page.write('</div>\n')
    page.write_to_file()


class Html:

    stylesheet_link = f'<link rel="stylesheet" href="{CSS_PAGE}">'
    javascript_link = f'<script src="{JS_PAGE}"></script>'

    def __init__(self, infile: str, outpath: Path, header: str = None):
        self.path = outpath
        self.stream = io.StringIO()
        self.stream.write(f'<html>\n\n')
        self.stream.write(f'<head>\n')
        self.stream.write(f'{self.__class__.stylesheet_link}\n')
        self.stream.write(f'{self.__class__.javascript_link}\n')
        self.stream.write(f'</head>\n\n')
        self.stream.write(f'<body>\n\n')
        self.stream.write(f'<h2>{Path(infile).stem}</h2>\n\n')
        if header is not None:
            self.stream.write(f'<h3>{header}</h3>\n\n')
        self.views = []
        self.captions = []

    def write(self, text: str):
        self.stream.write(text)

    def write_section(self, title: str = None, identifier: str = None):
        id_attr = '' if identifier is None else f' id={identifier}' 
        self.stream.write(f'<div class=section{id_attr}>\n')
        if title is not None:
            self.stream.write(f'<strong>{title}</strong>\n')
        self.stream.write(f'<blockquote>\n')

    def write_section_end(self):
        self.stream.write('</blockquote>\n')
        self.stream.write('</div>\n\n')

    def write_tr(self, *table_cells, indent=0, attrs=''):
        if attrs:
            attrs = ' ' + ' '.join([f'{k}={v}' for k, v in attrs.items()])
        for cells in table_cells:
            self.stream.write(f'{" " * indent}<tr{attrs}>\n')
            for cell in cells:
                if isinstance(cell, tuple):
                    self.stream.write(f'{" " * indent}  <td {cell[1]}>{cell[0]}</td>\n')
                else:
                    self.stream.write(f'{" " * indent}  <td>{cell}</td>\n')
            self.stream.write(f'{" " * indent}</tr>\n')

    def write_td(self, content: str, attrs=None, indent=0):
        if attrs is None:
            opening_tag = '<td>'
        elif isinstance(attrs, str):
            opening_tag = f'<td {attrs}>'
        else:
            opening_tag = '<td ' + " ".join(f"{k}={v}" for k, v in attrs.items()) + '>'
        self.stream.write(f'  {opening_tag}\n')
        self.stream.write(f'{content}\n')
        self.stream.write('  </td>\n')

    def write_to_file(self):
        self.path.write_text(self.stream.getvalue())


def pretty_json(json_obj: dict):
    return '<pre>'+json.dumps(json_obj, indent=2)+'</pre>'


def sorted_pairs(d: dict):
    """Return the dictionary as a list of sorted <key, value> where the sorting
    is done on the 'duration' property of the values in the dictionary."""
    sort_function = lambda item: item[1]['duration']
    return [(k, v) for k, v in 
            sorted(d.items(), key=sort_function, reverse=True)]

