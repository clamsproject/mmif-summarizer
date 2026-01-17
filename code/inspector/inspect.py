"""

The inspector generates a mini website in HTML_DIR with pages for views,
timeframes, transcript and captions.

It uses Jinja2 templates to create individual pages.

At the moment it only runs standalone, that is, you run it to create a static
website

Soon I will be tweaked to work in the contenxt of the MMIF Storage Server as
well. It remains to be figured out what updates here are going to be needed for
that and what kinds of changes need to be made, especially to the links and the
stylesheet and javascript files. For example for the links between the pages the
Flask site makes liberal use of get variables. Somehow those would need to be
used to determine what template to load.

More temporary developer notes:

Jinja string formatting:

https://stackoverflow.com/questions/45698629/jinja2-padding-and-aligning-strings
https://support.sendwithus.com/jinja/formatting_numbers/
https://dnmtechs.com/formatting-numbers-in-jinja2-in-python-3/

Commands:

Use the first three for index, views and timeframes
Use the first for captions
Use the third for correlations
Use the fourth for named entities

$ rm -rf x ; python run_inspector.py -i out/summaries/summaries/cpb-aacip-225-12z34w2c.json -o x
$ rm -rf x ; python run_inspector.py -i out/summaries/summaries/cpb-aacip-507-028pc2tq55.json -o x
$ rm -rf x ; python run_inspector.py -i out/summaries/summaries/cpb-aacip-526-z60bv7c69m.json -o x
$ rm -rf x ; python run_inspector.py -i examples/pipelines/spacy-v1.1/cpb-aacip-507-9882j68s35-transcript.json -o x

"""


import os
import io
import sys
import json
import math
from pathlib import Path

from jinja2 import Template

from inspector.utils import timestamp, pretty_json

from inspector.config import INDEX_PAGE, CSS_PAGE, JS_PAGE, VIEWS_PAGE
from inspector.config import TIMEFRAMES_PAGE, CORRELATIONS_PAGE, TRANSCRIPT_PAGE
from inspector.config import CAPTIONS_PAGE, ENTITIES_PAGE
from inspector.config import a_right, a_topleft, a_top, hide


entity_categories = ['PERSON', 'ORG', 'DATE', 'GPE', 'NORP', 'LANGUAGE']


class TimeFrame:

    """The time frame that is handed into the jinja template."""

    def __init__(self, timeframe_summary: dict):
        self._identifier = timeframe_summary['identifier']
        self._label = timeframe_summary['label']
        self._start = timeframe_summary['start-time']
        self._end = timeframe_summary['end-time']
        self._representatives = timeframe_summary['representatives']
        self._score = timeframe_summary['score']

    def __str__(self):
        return f'<TimeFrame {self._identifier} {self._label} {self._start}>'

    @property
    def label(self):
        return self._label

    @property
    def start(self):
        return timestamp(self._start)

    @property
    def end(self):
        return timestamp(self._end)

    @property
    def score(self):
        return '' if self._score is None else f'{self._score:06.4f}'

    @property
    def representatives(self):
        return ' '.join([timestamp(rep) for rep in self._representatives])


class Caption:

    """The caption that is handed into the jinja template."""

    def __init__(self, caption_summary: dict):
        self._identifier = caption_summary['identifier']
        self._timepoint = caption_summary['time-point']
        self._text = caption_summary['text']

    def __str__(self):
        return f'<Caption {self.identifier} {self.timepoint} {self.text[:50]}>'

    @property
    def identifier(self):
        return self._identifier

    @property
    def timepoint(self):
        return timestamp(self._timepoint)

    @property
    def text(self):
        return self._text.strip().replace('\n', '<br/>')


class TranscriptLine:

    """The transcript line that is handed into the jinja template."""

    def __init__(self, line_summary: dict):
        self._start = line_summary['start-time']
        self._end = line_summary['end-time']
        self._text = line_summary['text']

    def __str__(self):
        return f'<TranscriptLine {self.start} {self.end} "{self.text[:50]}">'

    @property
    def start(self):
        return timestamp(self._start)

    @property
    def end(self):
        return timestamp(self._end)

    @property
    def text(self):
        return self._text.strip().replace('\n', '<br/>')


class Entity:

    def __init__(self, entity_summary: dict):
        self.text = entity_summary['text']
        self.instances = []
        for inst in entity_summary['instances']:
            instance = EntityInstance(inst)
            if instance.cat in entity_categories:
                self.instances.append(instance)

    def __str__(self):
        return f'<Entity text="{self.text} instances={len(self.instances)}>'

    def has_instances(self):
        return len(self.instances) > 0


class EntityInstance:

    def __init__(self, instance_summary: dict):
        self.identifier = instance_summary['id']
        self.document = instance_summary['document']
        self.timepoint = instance_summary.get('time-point', -1)
        self.start = instance_summary['text-offsets'][0]
        self.end = instance_summary['text-offsets'][1]
        self.group = instance_summary['group']
        self.cat = instance_summary['cat']

    @property
    def location(self) -> tuple:
        # This was how the old code was getting the locations, but it wasn't
        # used really (because then and now as well we have only looked at
        # entities from transcripts). This needs to be updated once we have
        # entities with timepoints.
        time_point = ''
        start = ''
        end = ''
        if self.timepoint != -1:
            time_point = timestamp(self.timepoint)
        if 'text-offsets' in self:
            start = str(self.start)
            end = str(self.end)
        return (time_point, start, end)


def create_html(infile: str, outdir: str):

    inpath = Path(infile)
    outpath = create_directory(outdir)

    summary = json.loads(inpath.open().read())
    docinfo = document_info(infile, summary)
    tf_stats = timeframe_statistics(summary)
    summaries = available_summaries(summary)
    warnings = all_warnings(summary)
    timeframes = all_timeframes(summary)
    captions = [Caption(c) for c in summary['captions']]
    transcript = [TranscriptLine(line) for line in summary['transcript']]
    entities = [Entity(e) for e in summary['entities']]
    entities = [e for e in entities if e.has_instances()]

    template = Template(Path('inspector/templates/index.html').read_text())
    rendered_template = template.render(
        title=inpath.stem, summary=summary, origin=None, docinfo=docinfo,
        tfstats=tf_stats, summaries=summaries)
    (outpath / INDEX_PAGE).write_text(rendered_template)

    template = Template(Path('inspector/templates/views.html').read_text())
    rendered_template = template.render(
        title=inpath.stem, summary=summary, warnings=warnings, display=pretty_json)
    (outpath / VIEWS_PAGE).write_text(rendered_template)

    template = Template(Path('inspector/templates/timeframes.html').read_text())
    rendered_template = template.render(
        title=inpath.stem, timeframes=timeframes)
    (outpath / TIMEFRAMES_PAGE).write_text(rendered_template)

    template = Template(Path('inspector/templates/captions.html').read_text())
    rendered_template = template.render(
        title=inpath.stem, captions=captions)
    (outpath / CAPTIONS_PAGE).write_text(rendered_template)

    template = Template(Path(f'inspector/templates/{TRANSCRIPT_PAGE}').read_text())
    rendered_template = template.render(
        title=inpath.stem, transcript=transcript)
    (outpath / TRANSCRIPT_PAGE).write_text(rendered_template)

    template = Template(Path(f'inspector/templates/{ENTITIES_PAGE}').read_text())
    rendered_template = template.render(
        title=inpath.stem, categories=entity_categories, entities=entities)
    (outpath / ENTITIES_PAGE).write_text(rendered_template)


def create_directory(directory: str) -> Path:
    """Create a new directory with the resources in place. If it already exists then
    html files in that directory will be deleted."""
    path = Path(directory)
    path.mkdir(exist_ok=True)
    for f in path.glob("*"):
        if f.is_file() and f.name.endswith('.html'):
            f.unlink()
    create_resources(path)
    return path


def create_resources(outpath: Path):
    """Copy the stylesheet and javascript file into the website."""
    # TODO: this would not deal with running this in a Flask site. For that we
    # probably need some whay to copy the file from here or have the server ask
    # this module to run the server. May want to use the static/{css,js} locations.
    css_source = Path(Path(__file__).parent, CSS_PAGE)
    css_target = Path(outpath, CSS_PAGE)
    css_target.write_text(css_source.read_text())
    js_source = Path(Path(__file__).parent, JS_PAGE)
    js_target = Path(outpath, JS_PAGE)
    js_target.write_text(js_source.read_text())


def origin_command() -> str:
    """Create pretty print version for command as it was entered on the CLI."""
    command = " ".join(sys.argv)
    command = command.replace(' -i', ' \\\n    -i')
    command = command.replace(' -o', ' \\\n    -o')
    command = command.replace(' --html', ' \\\n    --html')
    return command


def document_info(infile: str, summary: dict) -> dict:
    """Collect document-level information from the summary."""
    mv = summary["mmif_version"]
    doc = summary['document']
    return {
        'MMIF Version': f'<a href="{mv}">{mv}</a>',
        'Size of MMIF file': f"{doc['size']:,d}    ",
        'Size of summary': f'{os.path.getsize(infile):,d}',
        'Video duration': doc.get('duration_ts', 'Not available'),
        'Frames per second': doc.get('fps', 'Not available') }


def document_annotations(summary: dict) -> dict:
    """Collect document annotations from the summary. Not used at the
    moment because there is a lot of overlap with the document info."""
    # TODO: if used this should be changed because now it produces on big flat
    # list per view, mingling all annotations.
    document_annotations = {}
    for v_id in summary['annotations']:
        document_annotations[v_id] = []
        for anno in summary['annotations'][v_id]:
            for k, v in anno.items():
                document_annotations[v_id].append((k, v))
    return document_annotations


def timeframe_statistics(summary: dict) -> dict:
    """Create a dictioray with statistics on timeframe labels like average length,
    coverage (% of the vido that falls under the labels timeframe spans) and number
    of frames."""
    video_length = summary['document'].get('duration_ms', float('nan'))
    all_stats = {}
    for app in summary['timeframe_stats']:
        all_stats[app] = {}
        stats = summary['timeframe_stats'][app]
        for label, tf_stats in sorted_pairs(stats):
            duration_ms = tf_stats['duration']
            duration_ts = timestamp(duration_ms)
            label_stats = {
                'duration': duration_ts,
                'coverage': duration_ms * 100 / video_length,
                'count': tf_stats['count'],
                'average': timestamp(tf_stats['average']),
                'first': timestamp(tf_stats['first']),
                'longest': timestamp(tf_stats['longest']) }    
            all_stats[app][label] = label_stats
    return all_stats


def available_summaries(summary: dict) -> list:
    """Returns a list of specifications for what summaries are available, the
    specifications include the name of the link and the name of the page with
    that summary.""" 
    links = [('Views', VIEWS_PAGE)]
    if summary.get('timeframes'):
        links.append(('TimeFrames', TIMEFRAMES_PAGE, None))
        #links.append(('Correlations', CORRELATIONS_PAGE, 'correlations'))
    if summary.get('transcript'):
        links.append(('Transcript', TRANSCRIPT_PAGE, None))
    if summary.get('captions'):
        links.append(('Captions', CAPTIONS_PAGE, None))
    if summary.get('entities'):
        links.append(('Entities', ENTITIES_PAGE, None))
    return links


def all_warnings(summary:dict) -> dict:
    """Return a dictionary with list of warnings for those views that have warnings."""
    warnings = {}
    for view in summary['views']:
        if 'warnings' in view:
            warning_messages = []
            for w in view['warnings']:
                try:
                    s = json.dumps(json.loads(w), indent=2)
                except Exception:
                    s = w
            warning_messages.append(s)
            warnings[view['id']] = warning_messages
    return warnings


def all_timeframes(summary: dict) -> dict:
    timeframes = {}
    for app in summary['timeframes']:
        timeframes[app] = []
        for tf in summary['timeframes'][app]:
            timeframes[app].append(TimeFrame(tf))
    return timeframes


# The following is some legacy code from when we did not use jinja templates. It
# is kept here for now because we may want to reintroduce the correlations (they
# were removed because they weren't doing a lot on the data we were working with
# and besides it was somewhat unclear what we wanted it do do exactly).

def create_html_correlations(infile: str, outpath: Path, summary: dict):
    page = Html(infile, outpath / CORRELATIONS_PAGE, 'Correlations')
    for app1 in summary['timeframes']:
        print(app1)
        for app2 in summary['timeframes']:
            print(app2)
            if app1 == app2:
                continue
            app1_name = '/'.join(Path(app1).parts[-2:])
            app2_name = '/'.join(Path(app2).parts[-2:])
            page.write_section(f'{app1_name} &#8596; {app2_name}')
            count1 = collect_observations(app1, summary)
            count2 = collect_observations(app2, summary)
            pairs = set()
            observations = {}
            page.write('<table class=transcript>\n')
            for key1 in sorted(count1):
                for key2 in sorted(count2):
                    if (key1, key2) in pairs:
                        continue
                    pairs.add((key1, key2))
                    pairs.add((key2, key1))
                    jacc = jaccard(count1[key1], count2[key2])
                    if jacc > 0.001:
                        class_ = 'bold' if jacc > 0.2 else 'normal'
                        page.write_tr((key1, key2, f'{jacc:.5f}'), attrs={'class': class_})
            page.write('</table>\n')
            page.write_section_end()
    page.write_to_file()


def collect_observations(app: str, summary: dict):
    from collections import defaultdict
    result = defaultdict(set)
    for tf in summary['timeframes'][app]:
        #for tp in range(tf['start-time'], tf['end-time'], 1000):
        for tp in range(round(tf['start-time'] / 1000), round(tf['end-time'] / 1000)):
            result[tf['label']].add(tp)
    return result


def jaccard(s1, s2):
    intersection = s1.intersection(s2)
    union = s1.union(s2)
    #print (len(intersection), len(union))
    return (len(intersection) / len(union))
