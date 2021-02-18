"""run.py

MMIF consumer that creates a PBCore XML file.

Makes some simplifying assumptions, some of them need to be revisited:

- The input is the output of a pipeline where Kaldi and/or EAST/Tesseract run on
  a video file followed by spaCy NER.

- There is one video in the MMIF documents list. All start and end properties
  are pointing to that video.

- The time unit is assumed to be milliseconds. Should really update get_start()
  and get_end() and other methods.

- Makes no distinction between named entities found in the slate and those found
  in OCR elsewhere or via Kaldi.

- The identifier is assumed to be the local file path to the video document.

USAGE:

To run just the converter on the sample input document:

$> python run.py -t

To start a Flask server and ping it:

$> python run.py
$> curl -X GET http://0.0.0.0:5000/
$> curl -H "Accept: application/json" -X POST -d@input.mmif http://0.0.0.0:5000/

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
from mmif.serialize import *
from mmif.vocabulary import DocumentTypes
from mmif.vocabulary import AnnotationTypes
from lapps.discriminators import Uri

import metadata
from utils import matches, compose_id, type_name
from utils import get_annotations_from_view, find_matching_tokens


METADATA_FILE = 'metadata.json'
PBCORE_TEMPLATE = 'pbcore.template'
SAMPLE_INPUT = 'input.mmif'

TEXT_DOCUMENT = DocumentTypes.TextDocument.name
VIDEO_DOCUMENT = DocumentTypes.VideoDocument.name
TIME_FRAME = AnnotationTypes.TimeFrame.name
BOUNDING_BOX = AnnotationTypes.BoundingBox.name

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
        """Initialize an index of all documents and annotations: { id => element }
        and an index of all alignments going from tokens or text documents to time
        frames and bounding boxes: { id1 => id2 }. For the latter we assume that
        a document or token is aligned with only one bounding box or time frame,
        and vice versa."""
        self.mmif = mmif
        self.idx = {}
        self.alignments = {}
        for document in self.mmif.documents:
            self._add_element(None, document)
        for view in self.mmif.views:
            for annotation in view.annotations:
                self._add_element(view, annotation)
                if annotation.at_type.endswith(AnnotationTypes.Alignment.name):
                    self._add_alignment(view, annotation)

    def _add_element(self, view, element):
        """Add an element to the index, using its identifier, but prefixing the view
        identifier if there is one."""
        element_id = element.properties["id"]
        if view is not None:
            element_id = "%s:%s" % (view.id, element_id)
        self.idx[element_id] = element
        
    def _add_alignment(self, view, alignment): #source_id, target_id):
        """Add an alignment from the identifier of a text document or token to the
        identifier of a time frame or bounding box. This assume that the target is
        the token or text."""
        source_id = compose_id(view.id, alignment.properties['source'])
        target_id = compose_id(view.id, alignment.properties['target'])
        self.alignments[target_id] = source_id

    def get(self, identifier):
        """Get the element associated with the identifier, which should be a composed id
        if the element is an annotaiton from a view."""
        return self.idx.get(identifier)

    def get_aligned_annotation(self, identifier):
        """Get the annotation that is aligned with the annotation with the given
        identifier."""
        aligned_id = self.alignments.get(identifier)
        return self.get(aligned_id)


class PBCoreConverter(ClamsConsumer):

    def _consumermetadata(self):
        return metadata.METADATA

    def _consume(self, mmif):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        self.mmif_index = MmifIndex(self.mmif)
        self.asset_id = self._get_asset_id()
        self.soup = self._get_pbcore_template()
        self._entities = {}
        for view in list(self.mmif.views):
            for annotation in view.annotations:
                if matches(annotation.at_type, TIME_FRAME):
                    if 'frameType' in annotation.properties:
                        self._add_timeframe_as_description(annotation)
                elif annotation.at_type == Uri.NE:
                    self._collect_entity(annotation, view)
        self._add_entities()
        return self._emit_pbcore()

    def _get_asset_id(self):
        """Returns the asset identifier, which for now is assumed to be the location of
        the video document."""
        video_docs = [d for d in self.mmif.documents if matches(d.at_type, VIDEO_DOCUMENT)]
        return video_docs[0].properties['location']

    def _get_pbcore_template(self):
        """Load the PBCore template from disk, enter the identfier and date, and return
        it as a BeautifulSoup instance."""
        soup = None
        with open(PBCORE_TEMPLATE) as fh:
            s = Template(fh.read())
            soup = bs(s.substitute(DATE='', ID=self.asset_id), 'xml')
        print(type(soup))
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
        print(self)

    def __str__(self):
        return("%-12s %-8s %-5s  %-12s → %-12s %5s %5s" %
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
        if matches(self.aligned_type.at_type, TIME_FRAME):
            # get the tokens for the entity
            view_id = self.doc_id.split(':')[0]
            token_view = self.mmif.views[view_id]
            tokens = get_annotations_from_view(token_view, Uri.TOKEN)
            start_token, end_token = find_matching_tokens(tokens, self.ne)
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
        if matches(source.at_type, TIME_FRAME):
            return source.properties['start']
        elif matches(source.at_type, BOUNDING_BOX):
            return source.properties['timePoint']
        else:
            return None

    @staticmethod
    def get_end(source):
        """Return the end of the TimeFrame or the timePoint of the BoundingBox plus some
        number of milliseconds."""
        if matches(source.at_type, TIME_FRAME):
            return source.properties['end']
        elif matches(source.at_type, BOUNDING_BOX):
            return source.properties['timePoint'] + MINIMAL_TIMEFRAME_LENGTH
        else:
            return None

                    
def start_service():
    converter = PBCoreConverter()
    service = Restifier(converter, mimetype='application/xml')
    service.run()


def test_on_sample():
    global COMPACT_XML
    COMPACT_XML = True
    converter = PBCoreConverter()
    mmif = converter.consume(open(SAMPLE_INPUT).read())
    print(mmif)
    

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

    if len(sys.argv) > 1 and sys.argv[1] == '-t':
        test_on_sample()
    else:
        start_service()
