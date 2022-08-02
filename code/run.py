"""run.py

MMIF consumer that creates a summary XML file.

Makes some simplifying assumptions, some of them need to be revisited:

- The transcript is taken from the last Kaldi view.

- The input is the output of a pipeline where Kaldi and/or EAST/Tesseract run on
  a video file followed by spaCy NER.

- The example input file has perfect Kaldi performance which produces
  capitalization and punctuation.

- There is one video in the MMIF documents list. All start and end properties
  are pointing to that video.

- The time unit is assumed to be milliseconds. Should really update get_start()
  and get_end() and other methods.

- Makes no distinction between named entities found in the slate and those found
  in OCR elsewhere or via Kaldi.

- The identifier is assumed to be the local file path to the video document.

USAGE:

To run just the summarizer on one of the simple sample input documents:

$ python run.py -t examples/input-v7.mmif
$ python run.py -t examples/input-v9.mmif

The second one is like the first one but also includes spaCy annotations.

To start a Flask server and ping it:

$ python run.py
$ curl -X GET http://0.0.0.0:5000/
$ curl -X POST -d@examples/input-v7.mmif http://0.0.0.0:5000/
$ curl -X POST -d@examples/input-v9.mmif http://0.0.0.0:5000/

See README.md for more details.

TODO:
- entities from spacy are aligned with full document, not tokens therein
- define summary() to create a summary and then separate the export into XML
  versus JSON
- run this on a real file with Kaldi and other real annotations:
    Bars-and-tone --> Slate Recognition --> Slate parser mockup -->
    Segmenter --> Kaldi --> EAST --> Tesseract --> SpacyNER

"""

import sys
import json
import io

from server import ClamsConsumer, Restifier
from clams.appmetadata import AppMetadata
from mmif.serialize import Mmif
from mmif.vocabulary import DocumentTypes
from mmif.vocabulary import AnnotationTypes
from lapps.discriminators import Uri

from utils import type_name, as_xml, write_tag, xml_attribute, xml_data
from utils import flatten_paths, print_paths
from utils import get_annotations_from_view, find_matching_tokens
from graph import Graph
import names


VERSION = '0.1.1'
MMIF_VERSION = '0.4.0'
MMIF_PYTHON_VERSION = '0.4.6'
CLAMS_PYTHON_VERSION = '0.5.1'


# The name of the Kaldi app, used to select views
KALDI = 'http://apps.clams.ai/kaldi/'

# Bounding boxes have a time point, but what we are looking for below is to find
# a start and an end in the video so we manufacture an end point. Set to 1000ms
# because Tesseract samples every second
# TODO: this is not used anymore, probably needs to be re-introduced
MINIMAL_TIMEFRAME_LENGTH = 1000

# When a named entity occurs 20 times we do not want to generate 20 instances of
# it. If the start of the next entity occurs within the below number of
# miliseconds after the end of the previous, then it is just added to the
# previous one. Taking one minute as the default so two mentions in a minute end
# up being the same instance. This setting can be changed with the 'granularity'
# parameter.
# TODO: this seems broken
GRANULARITY = 1000
GRANULARITY_HELP = 'maximum interval between two entities in the same cluster'

# The transcript is probably the largest part of the summary, but in some cases
# it is not needed for the user, in which case we can suppress it from being in
# the output This setting can be changed with the 'transcript' parameter.
TRANSCRIPT = True
TRANSCRIPT_HELP = ''

# Properties used for the summary for various tags
DOC_PROPS = ('id', 'type', 'location')
VIEW_PROPS = ('id', 'timestamp', 'app')
TF_PROPS = ('id', 'start', 'end', 'frameType')
E_PROPS = ('id', 'group', 'cat', 'tag', 'video-start', 'video-end', 'coordinates')


class MmifSummarizer(ClamsConsumer):

    def _consumermetadata(self):
        self.metadata = \
            AppMetadata(
                identifier="https://apps.clams.ai/mmif-summarizer",
                url='https://github.com/clamsproject/mmif-summarizer',
                name="MMIF Summarizer",
                description="Summarize a MMIF file.",
                mmif_version=MMIF_VERSION,
                app_version=VERSION,
                app_license='Apache 2.0',
                analyzer_version=VERSION,
                analyzer_license='Apache 2.0')
        self.metadata.add_input(DocumentTypes.TextDocument, required=False)
        self.metadata.add_input(AnnotationTypes.TimeFrame, required=False)
        self.metadata.add_input(AnnotationTypes.BoundingBox, required=False)
        self.metadata.add_input(AnnotationTypes.Alignment, required=False)
        self.metadata.add_input(Uri.TOKEN, required=False)
        self.metadata.add_input(Uri.NE, required=False)
        self.metadata.add_parameter('granularity', GRANULARITY_HELP, 'integer')
        self.metadata.add_parameter('transcript', TRANSCRIPT_HELP, 'boolean')
        return self.metadata

    def _consume(self, mmif, **kwargs):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        summary = Summary(mmif, **kwargs)
        return summary.as_xml()
        #print('!!! returning None for now')


class Summary(object):

    """Implements the summary of a MMIF file.

    granularity     -  boolean used for combining entities
    add_transcript  -  boolean to determine whether a transcript is added
    mmif            -  instance of mmif.serialize.Mmif
    graph           -  instance of graph.Graph
    documents       -  instance of Documents
    views           -  instance of Views
    transcript      -  instance of Transcript
    tags            -  instance of SummarizedTags
    timeframes      -  instance of SummarizedTimeFrames
    entities        -  instance of SummarizedEntities

    """

    def __init__(self, mmif, **args):
        self.granularity = args.get('granularity', GRANULARITY)
        self.add_transcript = args.get('transcript', TRANSCRIPT)
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        self.graph = Graph(self.mmif)
        self.documents = Documents(self)
        self.views = Views(self)
        self.transcript = Transcript(self)
        self.tags = SummarizedTags(self)
        self.timeframes = SummarizedTimeFrames(self)
        self.entities = SummarizedEntities(self)

    def as_xml(self):
        s = io.StringIO()
        s.write('<Summary>\n')
        s.write(self.documents.as_xml())
        s.write(self.views.as_xml())
        if self.add_transcript:
            s.write(self.transcript.as_xml())
        s.write(self.timeframes.as_xml())
        s.write(self.entities.as_xml())
        s.write('</Summary>\n')
        return s.getvalue()

    def pp(self):
        self.documents.pp()
        self.views.pp()
        self.transcript.pp()
        self.timeframes.pp()
        self.entities.pp()
        print()


class Documents(object):

    """Contains a list of document summaries, which are dictionaries with just
    the id, type and location properties."""

    def __init__(self, summary):
        self.data = [self.doc_summary(doc) for doc in summary.graph.documents]

    @staticmethod
    def doc_summary(doc):
        return { 'id': doc.id,
                 'type': doc.at_type.shortname,
                 'location': doc.location }

    def as_xml(self):
        return as_xml('Document', self.data, DOC_PROPS)

    def pp(self):
        print('\nDocuments -> ')
        for d in self.data:
            print('    %s %s' % (d['type'], d['location']))


class Views(object):

    """Contains a list of view summaries, which are dictionaries with just
    the id, app and timestamp properties."""

    def __init__(self, summary):
        self.data = [self.view_summary(view) for view in summary.mmif.views]

    @staticmethod
    def view_summary(view):
        return { 'id': view.id,
                 'app': view.metadata.app,
                 'timestamp': view.metadata.timestamp }

    def as_xml(self):
        return as_xml('View', self.data, VIEW_PROPS)

    def pp(self):
        print('\nViews -> ')
        for v in self.data:
            print('    %s' % v['app'])


class Transcript(object):

    """The transcript contains the string value from the first text document in
    the Kaldi view (there should be only one text document in that view)."""

    # TODO: should make this a list of sentences or paragraphs, depending on
    #       what is available in the MMIF file
    # TODO: should take the latest fastpunct view if available

    def __init__(self, summary):
        """Returns the document text from the most recent kaldi view."""
        self.data = []
        views = [view for view in summary.mmif.views
                 if view.metadata.app.startswith(KALDI)]
        if views:
            for anno in views[-1].annotations:
                # find the first text document in the Kaldi view
                if anno.at_type.shortname == names.TEXT_DOCUMENT:
                    text = anno.properties['text'].value
                    #text = f"{text} {text} {text}"
                    lines = text.split('. ')
                    for line in lines[:-1]:
                        self.data.append(line + '.')
                    self.data.append(lines[-1])
                    break

    def __str__(self):
        return str(self.data)

    def as_xml(self):
        s = io.StringIO()
        s.write('  <Transcript>\n')
        for line in self.data:
            s.write('    <line>%s</line>\n' % xml_data(line))
        s.write('  </Transcript>\n')
        return s.getvalue()

    def pp(self):
        print('\nTranscript -> ')
        print('    %s' % self.data[:80].replace('\n', ' '))


class SummarizedNodes(object):

    """Abstract class to store instances of subclasses of graph.Node. The
    initialization methods of subclasses of SummarizedNodes can guard what nodes
    will be allowed in, for example, as of July 2022 the SummarizedTimeFrames
    class only allowed time frames that had a frame type (thereby blocking the
    many timeframes from Kaldi).

    Instance variables:

    summary    -  an instance of Summary
    graph      -  an instance of graph.Graph, taken from the summary
    nodes      -  list of instances of subclasses of graph.Node

    """

    def __init__(self, summary):
        self.summary = summary
        self.graph = summary.graph
        self.nodes = []

    def __getitem__(self, i):
        return self.nodes[i]

    def __len__(self):
        return len(self.nodes)

    def add(self, node):
        self.nodes.append(node)


class SummarizedTimeFrames(SummarizedNodes):

    """For now we take only the TimeFrames that have a frame type, which rules out
    all the frames we got from Kaldi."""

    def __init__(self, summary):
        super().__init__(summary)
        for timeframe in self.graph.get_nodes(names.TIME_FRAME):
            if timeframe.has_frame_type():
                self.add(timeframe)

    def as_xml(self):
        s = io.StringIO()
        s.write('  <TimeFrames>\n')
        for tf in self.nodes:
            write_tag(s, 'TimeFrame', '    ', tf.summary(), TF_PROPS)
        s.write('  </TimeFrames>\n')
        return s.getvalue()

    def pp(self):
        print('\nTimeframes -> ')
        for tf in self.nodes:
            summary = tf.summary()
            print('    %s:%s %s' % (summary['start'], summary['end'],
                                    summary['frameType']))


class SummarizedTags(SummarizedNodes):

    """For now we take all semantic tags."""

    def __init__(self, summary):
        super().__init__(summary)
        for tag in self.graph.get_nodes(names.SEMANTIC_TAG):
            self.add(tag)


class SummarizedEntities(SummarizedNodes):

    """Collecting instances of graph.EntityNode.

    nodes_idx  -  lists of instances of graph.EntityNode, indexed on entity text
                  { entity-string ==> list of graph.EntityNode }
    bins       -  an instance of Bins

    """

    def __init__(self, summary):
        super().__init__(summary)
        self.nodes_idx = {}
        self.bins = None
        for ent in self.graph.get_nodes(names.NAMED_ENTITY):
            self.add(ent)
        self._create_node_index()
        self._group()
        self._add_tags(summary.tags)

    def _create_node_index(self):
        """Put all the entities from self.nodes in self.node_idx. This first puts
        the nodes into the dictionary indexed on text string and then sorts the
        list of nodes for each string on video position."""
        for e in self:
            self.nodes_idx.setdefault(e.properties['text'], []).append(e)
        for text, entities in self.nodes_idx.items():
            self.nodes_idx[text] = sorted(entities,
                                          key=(lambda e: e.start_in_video()))

    def _group(self):
        """Groups all the nodes on the text and sorts them on position in the video,
        for the latter it will also created bins of entities that occur close to each
        other in the text."""
        #print('>>> grouping entities, granularity=%s' % self.summary.granularity)
        # create the bins, governed by the summary's granularity
        self.bins = Bins(self.summary)
        for text, entities in self.nodes_idx.items():
            #print('>>> adding %d instances of "%s"' % (len(entities), text))
            self.bins.current_bin = None
            for entity in entities:
                self.bins.add_entity(text, entity)
        self.bins.mark_entities()
        #self.bins.print_bins()

    def _add_tags(self, tags):
        for tag in tags:
            tag_doc = tag.properties['document']
            tag_p1 = tag.properties['start']
            tag_p2 = tag.properties['end']
            #print('>>>', tag, tag_doc, tag_p1, tag_p2)
            entities = self.nodes_idx.get(tag.properties['text'], [])
            for entity in entities:
                props = list(entity.properties.keys())
                props = entity.properties
                doc = props['document']
                p1 = props['start']
                p2 = props['end']
                #print('       ', entity, doc, p1, p2)
                if tag_doc == doc and tag_p1 == p1 and tag_p2 == p2:
                    #print('        ==> matches!')
                    entity.properties['tag'] = tag.properties['tagName']
                    #print('           ', entity.properties)

    def as_xml(self):
        s = io.StringIO()
        s.write('  <Entities>\n')
        for text in self.nodes_idx:
            s.write('    <Entity text=%s>\n' % xml_attribute(text))
            for e in self.nodes_idx[text]:
                write_tag(s, 'Instance', '      ', e.summary(), E_PROPS)
            s.write('    </Entity>\n')
        s.write('  </Entities>\n')
        return s.getvalue()

    def pp(self):
        print('\nEntities -> ')
        for e in self.nodes_idx:
            print('    %s' % e)
            for d in self.nodes_idx[e]:
                props = ["%s=%s" % (p, v) for p, v in d.summary().items()]
                print('        %s' % ' '.join(props))

    def print_groups(self):
        for key in sorted(self.nodes_idx):
            print(key)
            for e in self.nodes_idx[key]:
                print('   ', e, e.start_in_video())
                #print('   ', e.paths_to_docs())
                #print_paths(e.paths_to_docs(), indent='    ')


class Bins(object):

    def __init__(self, summary):
        self.summary = summary
        self.bins = {}
        self.current_bin = None

    def add_entity(self, text, entity):
        """Add an entity instance to the appropriate bin."""
        if self.current_bin is None:
            # Add the first instance of a new entity (as defined by the text),
            # since it is the first a new bin will be created.
            self.current_text = text
            self.current_bin = Bin(entity)
            self.bins[text] = [self.current_bin]
            #print('   ', entity, end='')
            #print('  -- added new bin')
        else:
            # For following entities with the same text, a new bin may be
            # created depending on the positions and the granularity.
            p1 = self.current_bin[-1].start_in_video()
            p2 = entity.start_in_video()
            p3 = entity.end_in_video()
            #print('   ', entity, p1, p2, end='')
            if p2 - p1 < self.summary.granularity:
                #print('  -- added to current bin')
                # TODO: should add p3 here
                self.current_bin.add(entity)
            else:
                #print('  -- added new bin')
                self.current_bin = Bin(entity)
                self.bins[self.current_text].append(self.current_bin)

    def mark_entities(self):
        """Marks all entities with the bin that they occur in. This is done to export
        the grouping done with the bins to the entities and this way the bins never need
        to be touched again."""
        # TODO: maybe use the bins when we create the output
        for entity_bins in self.bins.values():
            for i, ebin in enumerate(entity_bins):
                for entity in ebin:
                    entity.properties['group'] = i

    def print_bins(self):
        for text in self.bins:
            print(text)
            text_bins = self.bins[text]
            for i, text_bin in enumerate(text_bins):
                text_bin.print_nodes(i)
            print()


class Bin(object):

    def __init__(self, node):
        # TODO: we are not using these yet, but a bin should have a begin and
        # end in the video which should be derived from the start and end of
        # entities in the video. The way we put things in bins now is a bit
        # fragile since it depends on the start or end of the last element.
        self.start = 0
        self.end = 0
        self.nodes = [node]

    def __getitem__(self, i):
        return self.nodes[i]

    def add(self, node):
        self.nodes.append(node)

    def print_nodes(self, i):
        for node in self.nodes:
            print(' ', i, node)


def start_service():
    summarizer = MmifSummarizer()
    service = Restifier(summarizer, mimetype='application/xml')
    service.run()


def test_on_sample(fname):
    summarizer = MmifSummarizer()
    result = summarizer.consume(open(fname).read(),
                                granularity=GRANULARITY,
                                transcript=True,
                                transcript_mode='sentence')
    print(result)


if __name__ == "__main__":

    if len(sys.argv) > 2 and sys.argv[1] == '-t':
        test_on_sample(sys.argv[2])
    else:
        start_service()
