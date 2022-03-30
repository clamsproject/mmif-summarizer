"""names.py

Defining some names of types.

"""

from mmif.vocabulary import DocumentTypes
from mmif.vocabulary import AnnotationTypes

TEXT_DOCUMENT = DocumentTypes.TextDocument.shortname
VIDEO_DOCUMENT = DocumentTypes.VideoDocument.shortname
TIME_FRAME = AnnotationTypes.TimeFrame.shortname
BOUNDING_BOX = AnnotationTypes.BoundingBox.shortname
ALIGNMENT = AnnotationTypes.Alignment.shortname

TOKEN = 'Token'

SEMANTIC_TAG = 'SemanticTag'
NAMED_ENTITY = 'NamedEntity'
