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

To run just the converter on the simple sample input document (the one without
spacy views):

$ python run.py -t input-v7.mmif

To start a Flask server and ping it:

$ python run.py
$ curl -X GET http://0.0.0.0:5000/
$ curl -H "Accept: application/json" -X POST -d@input-v7.mmif http://0.0.0.0:5000/

See README.md for more details.

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
from mmif.serialize import Mmif
from mmif.vocabulary import DocumentTypes
from mmif.vocabulary import AnnotationTypes
from lapps.discriminators import Uri

import metadata
from utils import compose_id, type_name
from utils import get_annotations_from_view, find_matching_tokens


VERSION = '0.0.5'
MMIF_VERSION = '0.4.0'
MMIF_PYTHON_VERSION = '0.4.5'
CLAMS_PYTHON_VERSION = '0.4.4'


PBCORE_TEMPLATE = 'pbcore.template'

TEXT_DOCUMENT = DocumentTypes.TextDocument.shortname
VIDEO_DOCUMENT = DocumentTypes.VideoDocument.shortname
TIME_FRAME = AnnotationTypes.TimeFrame.shortname
BOUNDING_BOX = AnnotationTypes.BoundingBox.shortname
ALIGNMENT = AnnotationTypes.Alignment.shortname
TOKEN = 'Token'

# Bounding boxes have a time point, but what we are looking for below is to find
# a start and an end in the video so we manufacture and end point. Set to 1000ms
# because Tessearct samples every second
MINIMAL_TIMEFRAME_LENGTH = 1000

# When a named entity occurs 20 times we do not want to generate 20 instances of
# pbcoreSubject. If the start of the next entity occurs within the below number
# of miliseconds after the end of the previous, then it is just added to the
# previous one. Taking one minute as the default so two mentions in a minute end
# up being the same pbcoreSubject.
GRANULARITY = 60000

# Options to create pretty-printed XML or pretty printed and compact XML.
# Do not use compact XML in production settings.
PRETTY_XML = True
COMPACT_XML = False


class MmifIndex(object):

    """An index on a MMIF file that makes it easy to find the source of a document
    or token (which is a time frame or bounding box). The reason we need this is
    that TextDocument and Token instances do not refer to the sources they come
    from, that information is handled in Alignment instances."""

    def __init__(self, mmif: Mmif):
        """Initialize an index of all documents and annotations and an index of
        all alignments going from tokens or text documents to time frames and
        bounding boxes. For the latter we assume that a document or token is
        aligned with only one bounding box or time frame, and vice versa."""
        self.mmif = mmif
        self.idx = {}                            # { id => element }
        self.alignments = {}                     # { id1 => id2 }
        for document in self.mmif.documents:
            self._add_element(None, document)
        for view in self.mmif.views:
            for annotation in view.annotations:
                self._add_element(view, annotation)
        for view in self.mmif.views:
            for annotation in view.annotations:
                #print(annotation.at_type.shortname, annotation.properties)
                if annotation.at_type.shortname == ALIGNMENT:
                    self._add_alignment(view, annotation)
                    source_id = compose_id(view.id, annotation.properties['source'])
                    target_id = compose_id(view.id, annotation.properties['target'])

    def _add_element(self, view, element):
        """Add an element to the index, using its identifier, but prefixing the
        view identifier if there is one. Assumes that annotation identifiers do
        not include the view indentifier."""
        element_id = element.properties["id"]
        if view is not None:
            element_id = "%s:%s" % (view.id, element_id)
        self.idx[element_id] = element

    def _add_alignment(self, view, alignment):
        """Add an alignment from the identifier of a text document or token to the
        identifier of a time frame or bounding box. This assumes that the target is
        the token or text."""
        source_id = compose_id(view.id, alignment.properties['source'])
        target_id = compose_id(view.id, alignment.properties['target'])
        self.alignments[target_id] = source_id

    def __str__(self):
        return "<MmifIndex idx=%s alignments=%s>" \
            % (len(self.idx), len(self.alignments))

    def get(self, identifier):
        """Get the element associated with the identifier, which should be a composed
        identifier if the element is an annotation from a view."""
        return self.idx.get(identifier)

    def get_aligned_annotation(self, identifier):
        """Get the annotation that is aligned with the annotation with the given
        identifier."""
        aligned_id = self.alignments.get(identifier)
        return self.get(aligned_id)

    def pp(self):
        print(self)
        print("idx:")
        for identifier in sorted(self.idx):
            print("  %s --> %s" % (identifier, self.idx[identifier].at_type.shortname))
        print("alignments:")
        for k, v in self.alignments.items():
            print("  %s --> %s" % (k, v))


class MmifSummarizer(ClamsConsumer):

    def _consumermetadata(self):
        return metadata.METADATA

    def _consume(self, mmif):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        #self.mmif_index = MmifIndex(self.mmif)
        self.mmif_index.pp()
        self.mmif_summary = Summarizer(mmif)
        self.mmif.summary.write_json()


class Summarizer(object):

    def __init__(self, mmif : Mmif):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        self.graph = Graph()
        self.summary = {}
        self.populate_graph()
        print(self.graph)
        #self.graph.pp()
        self.summarize()

    def populate_graph(self):
        # top-level documents are added as nodes
        for doc in self.mmif.documents:
            self.graph.add_node(None, doc)
        # first pass over all annotations (including documents) except for the
        # alignments, save those for later so you have access to the annotations
        # that are aligned
        alignments = []
        for view in self.mmif.views:
            for annotation in view.annotations:
                if annotation.at_type.shortname == ALIGNMENT:
                    alignments.append((view, annotation))
                else:
                    self.graph.add_node(view, annotation)
        # second pass over the alignments
        for view, alignment in alignments:
            self.graph.add_edge(view, alignment)

    def summarize(self):
        print('summarizing...')
        self.summary['timeframes'] = []
        self.summary['entities'] = []

    def write_json(self):
        print(self.summary)


def get_attributes(annotation_properties):
    # Is this the best way to get all the attributes? Should probably be added
    # to mmif.serialize.annotation.AnnotationProperties. Note that with the code
    # below the text property on TextDocuments is returned, even if it is not in
    # there. So maybe what I really want is a way to iterate over all the
    # properties. And a get() method on the properties. Note that the canonical
    # way of accessing a property is annotation_properties[prop] which gives a
    # KeyError if there is no such property.
    attributes = []
    if hasattr(annotation_properties, '_unnamed_attributes') \
       and annotation_properties._unnamed_attributes is not None:
        attributes.extend(annotation_properties._unnamed_attributes)
    for name in annotation_properties._named_attributes():
        attributes.append(name)
    return attributes


class Graph(object):

    """Graph implementation for a MMIF document. Each node contains an annotation or
    document. Edges between nodes are implemented with the Node.targets property."""

    def __init__(self):
        self.nodes = {}

    def __str__(self):
        return "<Graph nodes=%d>" % len(self.nodes)

    def add_node(self, view, annotation):
        node = Node(self, view, annotation)
        self.nodes[node.identifier] = node

    def add_edge(self, view, alignment):
        source_id = compose_id(view.id, alignment.properties['source'])
        target_id = compose_id(view.id, alignment.properties['target'])
        source = self.get_node(source_id)
        target = self.get_node(target_id)
        # make sure the direction goes from token or textdoc to annotation
        if target.annotation.at_type.shortname in (TOKEN, TEXT_DOCUMENT):
            source, target = target, source
        source.targets.append(target)

    def get_node(self, node_id):
        return self.nodes.get(node_id)

    def get_nodes_of_type(self, short_at_type):
        return [node for node in self.nodes.values()
                if node.at_type.shortname == short_at_type]

    def get_sorted_nodes(self):
        pass

    def pp(self):
        print(self)
        for node_id, node in self.nodes.items():
            print("  %-30s" % node, end='')
            targets = [str(t) for t in node.targets]
            print(' -->  [%s]' % ' '.join(targets), end='')
            print()


class Node(object):

    def __init__(self, graph, view, annotation):
        self.graph = graph
        self.view = view
        self.annotation = annotation
        self.at_type = annotation.at_type
        self.properties = json.loads(str(annotation.properties))
        view_id = self.get_view_id()
        self.identifier = self.create_identifier()
        # The targets property contains a list of annotations or documents that
        # the node content points to. This includes the document the annotation
        # points and the alignment from a token or text document to a bounding
        # box or time frame.
        self.targets = []
        target = self.get_annotation_target()
        if target is not None:
            self.targets.append(target)

    def __str__(self):
        return "<Node %s %s>" % (self.at_type.shortname, self.identifier)

    def get_view_id(self):
        """Return the view identifier of the annoation, this will be None when
        the Node was create from an element of the MMIF document list."""
        return None if self.view is None else self.view.id

    def create_identifier(self):
        """Create a composite identifier view_id:annotation_id. If the Node was
        created for an element of the document list just retun the document
        identifier."""
        # TODO: what if the annotation_id already had the view_id prepended?
        view_id = self.get_view_id()
        anno_id = self.annotation.properties['id']
        return anno_id if view_id is None else "%s:%s" % (view_id, anno_id)

    def get_annotation_target(self):
        """Return the document or annotation node that the annotation/document in
        the node refers to via the document property. This could be a local property
        or a metadata property if there is no such local property. Return None
        if neither of those exist."""
        # try the local property
        docid = self.properties.get('document')
        if docid is not None:
            if ':' not in docid and docid not in self.graph.nodes:
                docid = compose_id(self.view.id, docid)
            return self.graph.get_node(docid)
        # try the metadata property
        if self.view is not None:
            metadata = self.view.metadata.contains[self.at_type]
            try:
                docid = metadata['document']
                if ':' not in docid and docid not in self.graph.nodes:
                    docid = compose_id(self.view.id, docid)
                return self.graph.get_node(docid)
            except KeyError:
                return None
        return None


class PBCoreConverter(ClamsConsumer):

    def _consumermetadata(self):
        return metadata.METADATA

    def _consume(self, mmif):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        #self.mmif_index = MmifIndex(self.mmif)
        #print(self.mmif_index)
        #self.mmif_index.pp()
        self.mmif_summary = Summarizer(mmif)
        self.mmif_summary.write_json()
        self.asset_id = self._get_asset_id()
        self.soup = self._get_pbcore_template()
        self._entities = {}
        for view in list(self.mmif.views):
            for annotation in view.annotations:
                if annotation.at_type.shortname == TIME_FRAME:
                    if 'frameType' in annotation.properties:
                        self._add_timeframe_as_description(annotation)
                elif annotation.at_type == Uri.NE:
                    self._collect_entity(annotation, view)
        self._add_entities()
        return self._emit_pbcore()

    def _get_asset_id(self):
        """Returns the asset identifier, which for now is assumed to be the location of
        the video document."""
        video_docs = [d for d in self.mmif.documents
                      if d.at_type.shortname == VIDEO_DOCUMENT]
        try:
            return video_docs[0].properties.location
        except IndexError:
            return None

    def _get_pbcore_template(self):
        """Load the PBCore template from disk, enter the identfier and date, and return
        it as a BeautifulSoup instance."""
        soup = None
        with open(PBCORE_TEMPLATE) as fh:
            s = Template(fh.read())
            soup = bs(s.substitute(DATE='', ID=self.asset_id), 'xml')
        return soup

    def _add_timeframe_as_description(self, time_frame):
        """Add timeframes that describe a segment of the video, like
        bars-and-tone and slate."""
        frame_type = time_frame.properties['frameType']
        if frame_type in ('bars-and-tone', 'slate'):
            tag = Tag(name='pbcoreDescription', parser='xml')
            tag.attrs['descriptionType'] = frame_type
            tag.attrs['start'] = time_frame.properties['start']
            tag.attrs['end'] = time_frame.properties['end']
            self.soup.pbcoreDescriptionDocument.append(tag)

    def _collect_entity(self, ne, view):
        """Collect entities, grouped on the string of the entity. This is now
        just whatever we found in the text, but in the future this should be a
        normalized form from an authority file. What we collect is the entity
        annotation and the start and end times in the video, which we reached
        via the aligned bounding box or time frame."""
        if ne.properties['category'] != 'Date':
            ent = Entity(self.mmif, self.mmif_index, ne)
            self._entities.setdefault(ent.text, []).append([ne, ent.start, ent.end])

    def _add_entities(self):
        """Go through all collected entities, group them, and add them to the
        PBCore document."""
        for text, entity_instances in self._entities.items():
            grouped_instances = self._group_instances(text, entity_instances)
            for (ne, start, end) in grouped_instances:
                tag = Tag(name='pbcoreSubject', parser='xml')
                tag.attrs['subjectType'] = ne.properties['category']
                tag.string = ne.properties['text']
                tag.attrs['start'] = start
                tag.attrs['end'] = end
                self.soup.pbcoreDescriptionDocument.append(tag)

    def _group_instances(self, text, entities):
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

    def _read_text(self, textdoc):
        """Read the text content from the document or the text value."""
        if textdoc.location:
            with open(textdoc.location) as fh:
                text = fh.read()
        else:
            text = textdoc.properties.text.value
        return text

    def _emit_pbcore(self):
        if PRETTY_XML:
            xml = self.soup.prettify() + '\n'
            return compact_xml(xml) if COMPACT_XML else xml
        else:
            return str(self.soup)


class Entity(object):

    """Object to collect exportable entity information from the annotation."""

    def __init__(self, mmif, mmif_index, entity_annotation):
        #print('ENTITY',
        #      entity_annotation.at_type.shortname,
        #      entity_annotation.properties)
        self.mmif = mmif
        self.mmif_index = mmif_index
        self.ne = entity_annotation
        self.doc_id = self.ne.properties['document']
        self.text = self.ne.properties['text']
        self.doc = None
        self.aligned_type = None
        self.start = None
        self.end = None
        self._set_start_and_end()

    def __str__(self):
        return(
            "%-12s %-8s %-5s  %-12s → %-12s %5s %5s" %
            (self.text, self.ne.properties["document"],
             "%s:%s" % (self.ne.properties["start"], self.ne.properties["end"]),
             type_name(self.textdoc), type_name(self.aligned_type),
             self.start, self.end))

    def _set_start_and_end(self):
        # The NE is in a document that aligns with a bounding box or time frame
        # and we get the start and end from the aligned type
        self.textdoc = self.mmif_index.get(self.doc_id)
        self.aligned_type = self.mmif_index.get_aligned_annotation(self.doc_id)
        self.start = self.get_start(self.aligned_type)
        self.end = self.get_end(self.aligned_type)
        # But in the time frame case we get the frame for the entire document
        # and we need to go via the tokens.
        if self.aligned_type.at_type.shortname == TIME_FRAME:
            # get the tokens for the entity
            view_id = self.doc_id.split(':')[0]
            token_view = self.mmif.views[view_id]
            tokens = get_annotations_from_view(token_view, Uri.TOKEN)
            start_token, end_token = find_matching_tokens(tokens, self.ne)
            #print('stet', tokens, start_token, end_token)
            tok1_id = compose_id(token_view.id, start_token.properties['id'])
            tok2_id = compose_id(token_view.id, end_token.properties['id'])
            # get the time frames aligned with the token
            tf1 = self.mmif_index.get_aligned_annotation(tok1_id)
            tf2 = self.mmif_index.get_aligned_annotation(tok2_id)
            # get the start and end
            self.start = tf1.properties['start']
            self.end = tf2.properties['end']

    @staticmethod
    def get_start(source):
        """Return the start of the TimeFrame or the timePoint of the BoundingBox."""
        if source.at_type.shortname == TIME_FRAME:
            return source.properties['start']
        elif source.at_type.shortname == BOUNDING_BOX:
            return source.properties['timePoint']
        else:
            return None

    @staticmethod
    def get_end(source):
        """Return the end of the TimeFrame or the timePoint of the BoundingBox plus
        some number of milliseconds."""
        if source.at_type.shortname == TIME_FRAME:
            return source.properties['end']
        elif source.at_type.shortname == BOUNDING_BOX:
            return source.properties['timePoint'] + MINIMAL_TIMEFRAME_LENGTH
        else:
            return None


def start_service():
    converter = PBCoreConverter()
    service = Restifier(converter, mimetype='application/xml')
    service.run()


def test_on_sample(fname):
    global COMPACT_XML
    COMPACT_XML = True
    converter = PBCoreConverter()
    xml = converter.consume(open(fname).read())
    print(xml)


def NEWtest_on_sample(fname):
    global COMPACT_XML
    COMPACT_XML = True
    summarizer = MmifSummarizer()
    result = summarizer.consume(open(fname).read())
    print(result)


def compact_xml(xml):
    """Making the prettified XML a bit compacter, useful for debugging."""
    s = io.StringIO()
    one_liners = '|'.join(['Identifier', 'AssetDate', 'Subject', 'Description'])
    for line in xml.split("\n"):
        stripped = line.strip()
        # xml version line, the main opening and closing tag and empty tags are
        # always on their own line, keep any leading spaces
        if (re.match("<\?xml", stripped)
            or re.match("<pbcoreDescriptionDocument[^>]*>", stripped)
            or re.match("</pbcoreDescriptionDocument>", stripped)
            or re.match("<[^>/]+/>", stripped)):
            s.write(line.rstrip() + "\n")
        # closing tag always followed by a newline
        elif re.match("</[^>]+>", stripped):
            s.write(line.strip() + "\n")
        # opening tags in a set of one liners are not followed by EOL
        elif re.match("<pbcore(%s)" % one_liners, stripped):
            s.write(line.rstrip())
        # skip empty lines
        elif stripped == '':
            pass
        # anything else, no newline, no leading spaces
        else:
            s.write(stripped)
    return s.getvalue()


if __name__ == "__main__":

    if len(sys.argv) > 2 and sys.argv[1] == '-t':
        test_on_sample(sys.argv[2])
    else:
        start_service()
