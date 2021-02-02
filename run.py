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

- When an entity is found in a TextDocument it is aligned with the TimeFrame of
  the entire document, which is useless if the document is for the entire video.

- The identifier is assumed to be the local file path to the video document.

USAGE:

To run just the converter on the sample input document:

$> python run.py -t

To start a Flask server and ping it:

$> python run.py
$> curl -i -H -X GET http://0.0.0.0:5000/
$> curl -i -H "Accept: application/json" -X POST -d@input.mmif http://0.0.0.0:5000/

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


METADATA_FILE = 'metadata.json'
PBCORE_TEMPLATE = 'pbcore.template'
SAMPLE_INPUT = 'input.mmif'

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
# previous one. Taking one minute as the default so two mentions in a minute and
# up being the same pbcoreSubject.
GRANULARITY = 60000

# Options to create pretty-printed XML or pretty printed and compact XML.
# Do not use compact XML in production settings.
PRETTY_XML = True
COMPACT_XML = False


class MmifIndex(object):

    """An index on the MMIF file that makes it easy to find the source of a
    document. The reason we need this is that TextDocument instances do not
    refer to the sources they come from, that information is handled in
    Alignment instances."""

    def __init__(self, mmif: Mmif):
        self.mmif = mmif
        # alignments from text documents to bounding boxes
        self.alignments = {}
        for view in self.mmif.views:
            for annotation in view.annotations:
                if annotation.at_type.endswith(AnnotationTypes.Alignment.name):
                    self._add_alignment(view, annotation)

    def _add_alignment(self, view, annotation):
        source = annotation.properties['source']
        document = "%s:%s" % (view.id, annotation.properties['target'])
        self.alignments[document] = source

    def get_document_source(self, docid):
        """Returns the source of the document, which sometimes is a bounding box
        (when found by OCR) and sometimes a time frame (when found via speech
        recognition). If the document is not in a view then this should return
        None."""
        full_id = self.alignments.get(docid)
        try:
            view_id, source_id = full_id.split(':')
            view = self.mmif.views.get(view_id)
            return None if view is None else view.annotations.get(source_id)
        except AttributeError:
            return None


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
        soup = None
        with open(PBCORE_TEMPLATE) as fh:
            s = Template(fh.read())
            soup = bs(s.substitute(DATE='', ID=self.asset_id), 'xml')
        return soup

    def _add_timeframe_as_description(self, time_frame):
        """This is to add timeframes that describe a segment of the video, like
        bars-and-tone and slate."""
        frame_type = time_frame.properties['frameType']
        if frame_type in ('bars-and-tone', 'slate'):
            tag = Tag(name='pbcoreDescription', parser='xml')
            tag.attrs['descriptionType'] = frame_type
            tag.attrs['start'] = time_frame.properties['start']
            tag.attrs['end'] = time_frame.properties['end']
            self.soup.pbcoreDescriptionDocument.append(tag)

    def _collect_entity(self, ne, view):
        """Collect lists of entity specification, grouped on the string of the
        entity. This is now just whatever we found in the text, but in the
        future this should be a normalized form from an authority file."""
        docid = ne.properties['document']
        text = ne.properties['text']
        source = self.mmif_index.get_document_source(docid)
        if ne.properties['category'] != 'Date':
            # An entity specification is a list with the view the entity occurs
            # in, the entity and the source of the entity (a time frame or a
            # bounding box).
            start = get_start(source)
            end = get_end(source)
            self._entities.setdefault(text, []).append([ne, start, end])

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


def matches(at_type, type_name):
    """Return True if the @type matches the short name."""
    return at_type == type_name or at_type.endswith('/' + type_name)


def get_start(source):
    """Return the start of the TimeFrame or the timePoint of the BoundingBox."""
    if matches(source.at_type, TIME_FRAME):
        return source.properties['start']
    elif matches(source.at_type, BOUNDING_BOX):
        return source.properties['timePoint']
    else:
        return None


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
