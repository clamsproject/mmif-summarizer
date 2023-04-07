
# The name of the Kaldi app, used to select views
KALDI = 'http://apps.clams.ai/kaldi/'

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