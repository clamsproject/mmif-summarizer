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
- entities from spacy are aligned with full document, not tokens therein
- put the entities in bins according to location
- add tags to entities

"""

import os
import sys
import json
import re
import io
import collections
from string import Template
from operator import itemgetter

from bs4 import BeautifulSoup as bs, Tag

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


VERSION = '0.0.5'
MMIF_VERSION = '0.4.0'
MMIF_PYTHON_VERSION = '0.4.5'
CLAMS_PYTHON_VERSION = '0.4.4'


# Bounding boxes have a time point, but what we are looking for below is to find
# a start and an end in the video so we manufacture an end point. Set to 1000ms
# because Tessearct samples every second
MINIMAL_TIMEFRAME_LENGTH = 1000

# When a named entity occurs 20 times we do not want to generate 20 instances of
# pbcoreSubject. If the start of the next entity occurs within the below number
# of miliseconds after the end of the previous, then it is just added to the
# previous one. Taking one minute as the default so two mentions in a minute end
# up being the same instance.
GRANULARITY = 60000
GRANULARITY = 800


class MmifSummarizer(ClamsConsumer):

    def _consumermetadata(self):
        self.metadata = \
            AppMetadata(
                identifier="https://apps.clams.ai/pbcore-converter",
                url='https://github.com/clamsproject/mmif-summarizer',
                name="MMIF Summarizer",
                description="Summarize a MMIF file.",
                mmif_version=MMIF_VERSION,
                app_version=VERSION,
                app_license='Apache 2.0',
                analyzer_version=VERSION,
                analyzer_license='Apache 2.0')
        self.metadata.add_input(DocumentTypes.TextDocument)
        self.metadata.add_input(AnnotationTypes.TimeFrame)
        self.metadata.add_input(AnnotationTypes.BoundingBox)
        self.metadata.add_input(AnnotationTypes.Alignment)
        self.metadata.add_output(Uri.TOKEN)
        return self.metadata

    def _consume(self, mmif):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        self.summarizer = Summarizer(mmif)
        self.summarizer.pp_summary()
        return self.summarizer.summary()


class Summarizer(object):

    def __init__(self, mmif: Mmif):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        self.graph = Graph(mmif)
        #self.items = {'timeframes': [], 'entities': [], 'tags': []}
        self.items = {'entities': []}
        self.graph.pp('pp-graph.txt')
        self.timeframes = SummarizedTimeFrames(self.graph)
        self.tags = SummarizedTags(self.graph)
        self.entities = SummarizedEntities(self.graph)
        self.entities.group()
        self.entities.add_tags(self.tags)
        #self._show_paths()

    def _show_paths(self):
        # some experimentation with paths from tokens
        for node in self.graph.get_nodes(names.TOKEN):
            paths = node.paths_to_docs()
            print_paths(paths)

    def summary(self):
        return json.dumps(self.items, indent=4)

    def pp_summary(self):
        print('\n<Summary>')
        print('  <Documents>')
        for document in self.graph.documents:
            print('    <Document type="%s" location="%s"/>'
                  % (document.at_type.shortname, document.location))
        print('  </Documents>')
        print('  <TimeFrames>')
        for tf in self.timeframes:
            print('   ', tf.as_xml())
        print('  </TimeFrames>')
        print('  <Entities>')
        for text in self.entities.nodes_idx:
            print('    <EntityGroup text="%s">' % text)
            for e in self.entities.nodes_idx[text]:
                print('     ', e.as_xml())
            print('    </EntityGroup>')
        print('  </Entities>')
        print('</Summary>')
        print()


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
            self.nodes_idx[text] = sorted(entities, key=(lambda e: e.anchor()['start']))
        # then create the bins, governed by the GRANULARITY setting
        self.bins = Bins()
        for text, entities in self.nodes_idx.items():
            self.bins.add_entity(text, entities[0])
            for entity in entities[1:]:
                self.bins.add(entity)
        #self.bins.print_bins()

    def add_tags(self, tags):
        for tag in tags:
            tag_doc = tag.properties['document']
            tag_p1 = tag.properties['start']
            tag_p2 = tag.properties['end']
            print('>>>', tag, tag_doc, tag_p1, tag_p2)
            entities = self.nodes_idx.get(tag.properties['text'], [])
            for entity in entities:
                props = list(entity.properties.keys())
                props = entity.properties
                doc = props['document']
                p1 = props['start']
                p2 = props['end']
                print('       ', entity, doc, p1, p2)
                # TODO: this seems to work but somehow it does not get printed in the summary
                if tag_doc == doc and tag_p1 == p1 and tag_p2 == p2:
                    print('        ==> matches!')
                    entity.properties['tag'] = tag.properties['tagName']
                    print('           ', entity.properties)

    def print_groups(self):
        for key in sorted(self.nodes_idx):
            print(key)
            for e in self.nodes_idx[key]:
                print('   ', e, e.start_in_video())
                #print('   ', e.paths_to_docs())
                #print_paths(e.paths_to_docs(), indent='    ')

    def XXX_group_instances(self, text, entities):
        """Groups all instances of the entity."""
        entities.sort(key=itemgetter(1))
        # print("%-15s" % text, [(e[1],e[2]) for e in entities])
        grouped_entities = [entities.pop(0)]
        for entity, start, end in entities:
            if grouped_entities[-1][2] + GRANULARITY >= start:
                grouped_entities[-1][2] = max(grouped_entities[-1][2], end)
            else:
                grouped_entities.append([entity, start, end])
        # print("%-15s" % text, [(e[1],e[2]) for e in grouped_entities])
        return grouped_entities

    def XXX_group_entities(self):
        # MOVED HERE FROM THE SUMMARIZER
        if not self.entities:
            return
        grouped = [self.entities[0]]
        # TODO: group on text string
        for entity in self.entities[1:]:
            text = entity.properties['text']
            start = entity.properties['start']
            end = entity.properties['end']
            last_text = grouped[-1].properties['text']
            last_start = grouped[-1].properties['start']
            last_end = grouped[-1].properties['end']
            if last_start + GRANULARITY >= start:
                # okay, this cannot be done because the bloody mmif object is immutable
                # grouped[-1].annotation.properties['end'] = max(last_end, end)
                # HA, use properties on the node instead
                grouped[-1].properties['end'] = max(last_end, end)
                g = 'GROUPING'
            else:
                grouped.append(entity)
                g = 'ADDING'
            #rint('- %-40s %2d %2d %2d %2d %s' % (entity, start, end, last_start, last_end, g))
        for x in grouped:
            continue
            print('>>>', x)
            print('   ', x.properties)
        # self.entities = grouped


class Bins(object):

    def __init__(self):
        self.bins = {}

    def add_entity(self, text, entity):
        self.current_text = text
        self.current_bin = Bin(entity)
        self.bins[text] = [self.current_bin]
            
    def add(self, entity):
        p1 = self.current_bin[-1].start_in_video()
        p2 = entity.start_in_video()
        if p2 - p1 < GRANULARITY:
            self.current_bin.add(entity)
        else:
            current_bin = Bin(entity)
            self.bins[self.current_text].append(self.current_bin)

    def print_bins(self):
        for text in self.bins:
            print(text)
            bins = self.bins[text]
            for i, bin in enumerate(bins):
                bin.print_nodes(i)
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
    result = summarizer.consume(open(fname).read())
    #print(result)


if __name__ == "__main__":

    if len(sys.argv) > 2 and sys.argv[1] == '-t':
        test_on_sample(sys.argv[2])
    else:
        start_service()
