
from mmif.vocabulary import DocumentTypes
from mmif.vocabulary import AnnotationTypes


# The name of CLAMS applications, used to select views and to determine whether
# the summarizer is appropriate for the app version.

KALDI = [
    # The first two use MMIF 0.4 and should probably be retired
    'http://apps.clams.ai/aapb-pua-kaldi-wrapper/0.2.2',
    'http://apps.clams.ai/aapb-pua-kaldi-wrapper/0.2.3',
    'http://apps.clams.ai/aapb-pua-kaldi-wrapper/v3']

WHISPER = [
    'http://apps.clams.ai/whisper-wrapper/v7',
    'http://apps.clams.ai/whisper-wrapper/v8',
    'http://apps.clams.ai/whisper-wrapper/v8-3-g737e280']

CAPTIONER = [
    'http://apps.clams.ai/llava-captioner/v1.2-6-gc824c97']

SEGMENTER = 'http://apps.clams.ai/audio-segmenter'


# Bounding boxes have a time point, but what we are looking for below is to find
# a start and an end in the video so we manufacture an end point. Set to 1000ms
# because Tesseract samples every second
# TODO: this is not used anymore, probably needs to be re-introduced

MINIMAL_TIMEFRAME_LENGTH = 1000


# When a named entity occurs 20 times we do not want to generate 20 instances of
# it. If the start of the next entity occurs within the below number of
# milliseconds after the end of the previous, then it is just added to the
# previous one. Taking one minute as the default so two mentions in a minute end
# up being the same instance. This setting can be changed with the 'granularity'
# parameter.
# TODO: this seems broken

GRANULARITY = 1000


# Properties used for the summary for various tags

DOC_PROPS = ('id', 'type', 'location')
VIEW_PROPS = ('id', 'timestamp', 'app')
TF_PROPS = ('id', 'start', 'end', 'frameType')
E_PROPS = ('id', 'group', 'cat', 'tag', 'video-start', 'video-end', 'coordinates')


# Names of types

TEXT_DOCUMENT = DocumentTypes.TextDocument.shortname
VIDEO_DOCUMENT = DocumentTypes.VideoDocument.shortname
TIME_FRAME = AnnotationTypes.TimeFrame.shortname
BOUNDING_BOX = AnnotationTypes.BoundingBox.shortname
ALIGNMENT = AnnotationTypes.Alignment.shortname

TOKEN = 'Token'
SENTENCE = 'Sentence'
SEMANTIC_TAG = 'SemanticTag'
NAMED_ENTITY = 'NamedEntity'


# Shape and color settings for the nodes in the graph visualization

GRAPH_FORMATTING = {
	'VideoDocument': ('component', 'black'),
	'TextDocument': ('component', 'darkblue'),
	'BoundingBox': ('box', 'darkgreen'),
    'Token': ('note', 'darkblue'),
    'Sentence': ('note', 'darkblue'),
    'NounChunk': ('note', 'darkblue'),
    'TimeFrame': ('oval', 'darkred'),
    'TimePoint': ('circle', 'darkred'),
    'SemanticTag': ('note', 'darkorange'),
    'NamedEntity': ('note', 'darkorange'),
    None: ('Msquare', 'black')
}
