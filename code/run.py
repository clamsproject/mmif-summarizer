"""run.py

MMIF consumer that creates a PBCore XML file.

Makes some simplifying assumptions, some of them need to be revisited:

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

To run just the converter on one of the simple sample input documents:

$ python run.py -t input-v7.mmif
$ python run.py -t input-v9.mmif

The second one is like the first one but also includes spaCy annotations.

To start a Flask server and ping it:

$ python run.py
$ curl -X GET http://0.0.0.0:5000/
$ curl -H "Accept: application/json" -X POST -d@input-v7.mmif http://0.0.0.0:5000/
$ curl -H "Accept: application/json" -X POST -d@input-v9.mmif http://0.0.0.0:5000/

See README.md for more details.

TODO:
- DONE need to add granularity and others as parameters
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
from xml.sax.saxutils import escape, quoteattr

from server import ClamsConsumer, Restifier
from clams.appmetadata import AppMetadata
from mmif.serialize import Mmif
from mmif.vocabulary import DocumentTypes
from mmif.vocabulary import AnnotationTypes
from lapps.discriminators import Uri

from utils import type_name
from utils import flatten_paths, print_paths
from utils import get_annotations_from_view, find_matching_tokens
from graph import Graph
import names


VERSION = '0.1.0'
MMIF_VERSION = '0.4.0'
MMIF_PYTHON_VERSION = '0.4.5'
CLAMS_PYTHON_VERSION = '0.5.0'


# Bounding boxes have a time point, but what we are looking for below is to find
# a start and an end in the video so we manufacture an end point. Set to 1000ms
# because Tessearct samples every second
# TODO: this is not used anymore, probably needs to be re-introduced
MINIMAL_TIMEFRAME_LENGTH = 1000

# When a named entity occurs 20 times we do not want to generate 20 instances of
# pbcoreSubject. If the start of the next entity occurs within the below number
# of miliseconds after the end of the previous, then it is just added to the
# previous one. Taking one minute as the default so two mentions in a minute end
# up being the same instance. This setting can be changed with the 'granularity'
# parameter.
GRANULARITY = 60000
GRANULARITY_HELP = 'maximum interval between two entities in the same cluster'

# The transcript is probably the largest part of the summary, but in some cases
# it is not needed for the user, in which case we can suppress it from being in
# the output This setting can be changed with the 'transcript' parameter.
TRANSCRIPT = True
TRANSCRIPT_HELP = ''

# Properties used for the summary for various tags
DOC_PROPS = ('type', 'location')
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
        #print('>>>', kwargs)
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        self.summarizer = Summarizer(mmif, **kwargs)
        return self.summarizer.as_xml()


class Summarizer(object):

    def __init__(self, mmif: Mmif, **kwargs: dict):
        global GRANULARITY, TRANSCRIPT
        GRANULARITY = kwargs.get('granularity', GRANULARITY)
        TRANSCRIPT = kwargs.get('transcript', TRANSCRIPT)
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        self.graph = Graph(mmif)
        #self.graph.pp('pp-graph.txt')
        #self.graph.token_idx.pp('pp-tokens.txt')
        #self._show_paths()
        self.summarize()

    def summarize(self):
        self.timeframes = SummarizedTimeFrames(self.graph)
        self.tags = SummarizedTags(self.graph)
        self.entities = SummarizedEntities(self.graph)
        self.entities.group()
        self.entities.add_tags(self.tags)
        self.transcript = self.get_transcript()
        self.summary = {
            'Documents': [],
            'Transcript': self.transcript,
            'TimeFrames': [],
            'Entities': {} }
        for document in self.graph.documents:
            self.summary['Documents'].append(
                { 'type': document.at_type.shortname,
                  'location': document.location })
        for tf in self.timeframes:
            self.summary['TimeFrames'].append(tf.node_summary())
        for text in self.entities.nodes_idx:
            self.summary['Entities'][text] = []
            for ent in self.entities.nodes_idx[text]:
                self.summary['Entities'][text].append(ent.node_summary())

    def _show_paths(self):
        # some experimentation with paths from tokens
        for node in self.graph.get_nodes(names.TOKEN):
            paths = node.paths_to_docs()
            print_paths(paths)

    def get_transcript(self):
        """Returns the document text from the most recent kaldi view."""
        kaldi_view = None
        for view in self.mmif.views:
            # TODO: a bit fragile perhaps
            if 'kaldi' in view.metadata.app:
                kaldi_view = view
        transcript = None
        for anno in kaldi_view.annotations:
            if anno.at_type.shortname == names.TEXT_DOCUMENT:
                return anno.properties['text'].value
 
    def print_summary(self):
        print(json.dumps(self.summary, indent=4))

    def as_xml(self):
        s = io.StringIO()
        s.write('<Summary>\n')
        s.write('  <Documents>\n')
        for doc in self.summary['Documents']:
            self.write_tag(s, 'Document', '    ', doc, DOC_PROPS)
        s.write('  </Documents>\n')
        if TRANSCRIPT:
            s.write('  <Transcript text=%s/>\n' % quoteattr(self.transcript))
        s.write('  <TimeFrames>\n')
        for tf in self.summary['TimeFrames']:
            self.write_tag(s,'TimeFrame', '    ', tf, TF_PROPS)
        s.write('  </TimeFrames>\n')
        s.write('  <Entities>\n')
        for text in self.summary['Entities']:
            s.write('    <Entity text=%s>\n' % quoteattr(text))
            for e in self.summary['Entities'][text]:
                self.write_tag(s,'Instance', '      ', e, E_PROPS)
            s.write('    </Entity>\n')
        s.write('  </Entities>\n')
        s.write('</Summary>\n')
        return s.getvalue()

    def write_tag(self, s, tagname, indent, obj, props):
        pairs = []
        for prop in props:
            if prop in obj:
                pairs.append("%s=%s" % (prop, quoteattr(str(obj[prop]))))
        s.write('%s<%s %s/>\n'
                % (indent, tagname, ' '.join(pairs)))


class SummarizedNodes(object):

    def __init__(self, graph):
        self.graph = graph
        self.nodes = []
        self.nodes_idx = {}

    def __getitem__(self, i):
        return self.nodes[i]

    def __len__(self):
        return len(self.nodes)

    def add(self, node):
        self.nodes.append(node)


class SummarizedTimeFrames(SummarizedNodes):

    """For now we take only the TimeFrames that have a frame type, which rules out
    all the frames we got from Kaldi."""

    def __init__(self, graph):
        super().__init__(graph)
        for timeframe in self.graph.get_nodes(names.TIME_FRAME):
            if timeframe.has_frame_type():
                self.add(timeframe)


class SummarizedTags(SummarizedNodes):

    """For now we take all semantic tags."""

    def __init__(self, graph):
        super().__init__(graph)
        for tag in self.graph.get_nodes(names.SEMANTIC_TAG):
            self.add(tag)


class SummarizedEntities(SummarizedNodes):

    def __init__(self, graph):
        super().__init__(graph)
        for ent in self.graph.get_nodes(names.NAMED_ENTITY):
            self.add(ent)

    def group(self):
        """Groups all the nodes on the text and sorts them on position in the video,
        for the latter it will also created bins of entities that occur close to each
        other in the text."""
        # first put the nodes in a dictionary indexed on text string
        for e in self:
            self.nodes_idx.setdefault(e.properties['text'], []).append(e)
        for text, entities in self.nodes_idx.items():
            self.nodes_idx[text] = sorted(entities,
                                          key=(lambda e: e.start_in_video()))
        # then create the bins, governed by the GRANULARITY setting
        self.bins = Bins()
        for text, entities in self.nodes_idx.items():
            self.bins.add_entity(text, entities[0])
            for entity in entities[1:]:
                self.bins.add_instance(entity)
        self.bins.mark_entities()
        #self.bins.print_bins()

    def add_tags(self, tags):
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

    def print_groups(self):
        for key in sorted(self.nodes_idx):
            print(key)
            for e in self.nodes_idx[key]:
                print('   ', e, e.start_in_video())
                #print('   ', e.paths_to_docs())
                #print_paths(e.paths_to_docs(), indent='    ')


class Bins(object):

    def __init__(self):
        self.bins = {}

    def add_entity(self, text, entity):
        #print('>>> add_entity', text, entity)
        self.current_text = text
        self.current_bin = Bin(entity)
        self.bins[text] = [self.current_bin]

    def add_instance(self, entity):
        p1 = self.current_bin[-1].start_in_video()
        p2 = entity.start_in_video()
        #print('--- add_instance', entity, p1, p2)
        if p2 - p1 < GRANULARITY:
            self.current_bin.add(entity)
        else:
            self.current_bin = Bin(entity)
            self.bins[self.current_text].append(self.current_bin)

    def mark_entities(self):
        """Marks all entities with the bin that they occur in."""
        for entity_bins in self.bins.values():
            for i, ebin in enumerate(entity_bins):
                for entity in ebin:
                    entity.properties['group'] = i

    def print_bins(self):
        for text in self.bins:
            print(text)
            bins = self.bins[text]
            for i, ebin in enumerate(bins):
                ebin.print_nodes(i)
            print()


class Bin(object):

    def __init__(self, node):
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
                                granularity=800,
                                transcript=True,
                                transcript_mode='sentence')
    print(result)


if __name__ == "__main__":

    if len(sys.argv) > 2 and sys.argv[1] == '-t':
        test_on_sample(sys.argv[2])
    else:
        start_service()
