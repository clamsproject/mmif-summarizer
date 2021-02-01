"""run.py

MMIF consumer that creates a PBCore XML file.

"""

import os
import json
import collections
from string import Template

from bs4 import BeautifulSoup as bs, Tag

from server import ClamsConsumer, Restifier
from mmif.serialize import *
from mmif.vocabulary import DocumentTypes
from mmif.vocabulary import AnnotationTypes
from lapps.discriminators import Uri


METADATA_FILE = 'metadata.json'
PBCORE_TEMPLATE = 'pbcore.template'


class MmifIndex(object):

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


class PBCoreApp(ClamsConsumer):

    def setupmetadata(self):
        with open(METADATA_FILE) as fh:
            return json.load(fh)

    def get_pbcore_template(self):
        soup = None
        with open(PBCORE_TEMPLATE) as fh:
            s = Template(fh.read())
            soup = bs(s.substitute(DATE='today', ID=17), 'xml')
        return soup

    def consume(self, mmif):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        self.mmif_index = MmifIndex(self.mmif)
        self.soup = self.get_pbcore_template()
        self._subjects = []
        for view in list(self.mmif.views):
            for annotation in view.annotations:
                if matches(annotation.at_type, AnnotationTypes.TimeFrame.name):
                    if 'frameType' in annotation.properties:
                        self._add_timeframe_as_description(annotation)
                elif annotation.at_type == Uri.NE:
                    self._collect_entity(annotation, view)
        self._add_subjects()
        return self.soup.prettify() + '\n\n'

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
        docid = ne.properties['document']
        # trace the document that the entity occurs in to the source
        source = self.mmif_index.get_document_source(docid)
        if ne.properties['category'] != 'Date':
            self._subjects.append([view, ne, source])

    def _add_subjects(self):
        for (view, ne, source) in self._subjects:
            tag = Tag(name='pbcoreSubject', parser='xml')
            tag.attrs['subjectType'] = ne.properties['category']
            tag.attrs['doc'] = ne.properties['document']
            tag.attrs['src'] = source.properties['id']
            tag.string = ne.properties['text']
            self.soup.pbcoreDescriptionDocument.append(tag)

    def _read_text(self, textdoc):
        """Read the text content from the document or the text value."""
        if textdoc.location:
            with open(textdoc.location) as fh:
                text = fh.read()
        else:
            text = textdoc.properties.text.value
        return text


def matches(at_type, type_name):
    return at_type == type_name or at_type.endswith('/' + type_name)


if __name__ == "__main__":

    app = PBCoreApp()
    service = Restifier(app, mimetype='application/xml')
    service.run()
