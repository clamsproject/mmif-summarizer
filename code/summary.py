"""MMIF Summarizer

MMIF consumer that creates a JSON summary from a MMIF file.

Makes some simplifying assumptions, including:

- There is one video in the MMIF documents list. All start and end properties
  are pointing to that video.
- The time unit is assumed to be milliseconds. 

Other assumptions are listed with the options below.


USAGE:

    $ python summary.py [OPTIONS] 

    Reads the MMIF file and creates a JSON summary file with the document list
    and any requested extra information.

Example:

    $ python summary -i input.mmif -o output.json --views --transcript

    Reads input.mmif and creates output.json with just views and transcript
    information added to the documents list.


OPTIONS:

-d DIRECTORY

Run the summarizer over all MMIF files in the directory, input files are assumed to 
have the .mmif extension and output files will be written in the same directpry with
the .json extension.

-i INFILE and -o OUTFILE

MMIF file to read and JSON summary file to write to.

--views

Shows basic information from the views: identifier, CLAMS app, timestamp, total
number of annotations and number of annotations per type.

Does NOT show parameters and application configuration.


-- timeframes

Shows basic information of all timeframes.

At the moment this does not group the timeframes accoring to apps. There used to be
a setting to just get chyrons or segments or barsandtone frames, but this has been 
retired.


--transcript

Shows the text from the transcript in pseudo sentences. Currently the sentences are
determined by splitting on end-of-sentence punctuations, which does result in bad
breaks after abbreviations. There are also stretches with barely any punctuation
which gives rise to long run-on sentence.

The transcript is taken from the last non-warning ASR view, so only the last added
transcript will be summarized. It is assumed that Tokens in the view are ordered on
text occurrence.


--captions

Shows captions from the Llava captioner app.



TODO:

- For the time unit we should really update get_start(), get_end() and other methods.
- Add parameters and appConfiguration to the views? Maybe as an options?
- Whsiper sometimes throws out very long sentences with little or no punctuation, and
  Kaldi consistently does the same in version 0.2.2 and 0. 2.3. Look intousing long
  pauzes to split the text.
- Group time frames.


"""

import sys, io, json, argparse, pathlib
from collections import defaultdict

from mmif.serialize import Mmif
from mmif.vocabulary import DocumentTypes

from utils import CharacterList
from utils import get_aligned_tokens
from utils import get_transcript_view, get_last_segmenter_view, get_captions_view
from graph import Graph
import config


VERSION = '0.1.0'


def debug(*texts):
    for text in texts:
        sys.stderr.write(f'{text}\n')


class SummaryException(Exception):
    pass


class Summary(object):

    """Implements the summary of a MMIF file.

    mmif            -  instance of mmif.serialize.Mmif
    graph           -  instance of graph.Graph
    documents       -  instance of Documents
    views           -  instance of Views
    transcript      -  instance of Transcript
    tags            -  instance of Tags
    timeframes      -  instance of TimeFrames
    entities        -  instance of Entities
    captions        -  instance of Captions

    """

    def __init__(self, mmif):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        self.warnings = []
        self.graph = Graph(self.mmif)
        self.documents = Documents(self)
        self.views = Views(self)
        self.timeframes = TimeFrames(self)
        self.transcript = Transcript(self)
        self.captions = Captions(self)

        self.tags = Tags(self)
        self.segments = Segments(self)
        self.entities = Entities(self)
        self.tags = Tags(self)
        self.validate()
        self.print_warnings()

    def validate(self):
        if len(self.video_documents()) > 1:
            raise SummaryException("More than one video document in MMIF file")

    def video_documents(self):
        return self.mmif.get_documents_by_type(DocumentTypes.VideoDocument)

    def report(self, outfile=None, full=False, views=False, timeframes=False,
               transcript=False, captions=False,
               segments=False, barsandtone=False, slate=False, chyrons=False,
               credits=False, entities=False, tags=False):
        json_obj = {
            'mmif_version': self.mmif.metadata.mmif,
            'documents': self.documents.data}
        if views or full:
            json_obj['views'] = self.views.data
        if transcript or full:
            json_obj['transcript'] = self.transcript.data
        if captions or full:
            json_obj['captions'] = self.captions.as_json()
        if timeframes or full:
            json_obj['timeframes'] = self.timeframes.as_json()
        
        if barsandtone or full:
            nodes = self.timeframes.get_nodes(frameType='bars-and-tone')
            json_obj['bars-and-tone'] = [n.summary() for n in nodes]
        if slate or full:
            nodes = self.timeframes.get_nodes(frameType='slate')
            json_obj['slate'] = [n.summary() for n in nodes]
        if segments or full:
            json_obj['segments'] = [n.summary() for n in self.segments]
        if chyrons or full:
            pass
        if credits or full:
            pass
        if tags or full:
            json_obj['tags'] = [n.summary() for n in self.tags]
        if entities or full:
            json_obj['entities'] = self.entities.as_json()
        report = json.dumps(json_obj, indent=2)
        if outfile is None:
            return report
        else:
            with open(outfile, 'w') as fh:
                fh.write(report)

    def print_warnings(self):
        for warning in self.warnings:
            print(f'WARNING: {warning}')

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

    def __init__(self, summary: Summary):
        self.data = [self.summary(doc) for doc in summary.graph.documents]

    def __len__(self):
        return len(self.data)

    @staticmethod
    def summary(doc):
        return { 'id': doc.id,
                 'type': doc.at_type.shortname,
                 'location': doc.location }

    def pp(self):
        print('\nDocuments -> ')
        for d in self.data:
            print('    %s %s' % (d['type'], d['location']))


class Views(object):

    """Contains a list of view summaries, which are dictionaries with just
    the id, app and timestamp properties."""

    def __init__(self, summary):
        self.data = [self.summary(view) for view in summary.mmif.views]

    @staticmethod
    def summary(view):
        annotation_types = defaultdict(int)
        for annotation in view.annotations:
            annotation_types[annotation.at_type.shortname] += 1
        return { 'id': view.id,
                 'app': view.metadata.app,
                 'timestamp': view.metadata.timestamp,
                 'annotations': len(view.annotations),
                 'annotation_types': dict(annotation_types) }

    def pp(self):
        print('\nViews -> ')
        for v in self.data:
            print('    %s' % v['app'])


class Transcript(object):

    """The transcript contains the string value from the first text document in the
    last ASR view. It issues a warning if there is more than one text document in
    the view."""

    # TODO: should make this a list of sentences or paragraphs, depending on
    #       what is available in the MMIF file
    # TODO: add offsets to sentences
    # TODO: should take the latest fastpunct view if we have a Kaldi view
    # TODO: use timepoints to break the transcript at long pauses

    def __init__(self, summary):
        self.data = []
        view = get_transcript_view(summary.mmif.views)
        if view is not None:
            documents = view.get_documents()
            if len(documents) > 1:
                summary.warnings.append(f'More than one TextDocument in ASR view {view.id}')
            sentence_nodes = summary.graph.get_nodes(config.SENTENCE, view_id=view.id)
            token_nodes = summary.graph.get_nodes(config.TOKEN)
            sentences = []
            current_sentence = []
            sentences.append(current_sentence)
            first = token_nodes[0]
            for token_node in token_nodes:
                props = token_node.properties
                t1, t2 = token_node.anchors['time-offsets']
                current_sentence.append(
                    [token_node.identifier, t1, t2, props['start'], props['end'], props['word']])
                if token_node.properties['word'][-1] in ('.', '?', '!'):
                    current_sentence = []
                    sentences.append(current_sentence)
            transcript_size = token_nodes[-1].properties['end']
            transcript = CharacterList(transcript_size)
            for s in sentences:
                self.add_sentence(transcript, s)

    def __str__(self):
        return str(self.data)

    def add_sentence(self, transcript: CharacterList, sentence: list):
        if not sentence:
            return
        start_time = sentence[0][1]
        end_time = sentence[-1][2]
        duration = end_time - start_time
        start_offset = sentence[0][3]
        end_offset = sentence[-1][4]
        length = end_offset - start_offset
        for tok_id, t1, t2, p1, p2, word in sentence:
            transcript.set_chars(word, p1, p2)
        sentence_text = transcript.getvalue(start_offset, end_offset)
        self.data.append(
            { 'start-time': start_time, 'end-time': end_time,
              'duration': duration, 'length': length, 'text': sentence_text })

    def pp(self):
        print('\nTranscript -> ')
        print('    %s' % self.data[:80].replace('\n', ' '))


class Nodes(object):

    """Abstract class to store instances of subclasses of graph.Node. The
    initialization methods of subclasses of Nodes can guard what nodes will
    be allowed in, for example, as of July 2022 the TimeFrames class only
    allowed time frames that had a frame type (thereby blocking the many
    timeframes from Kaldi).

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

    def get_nodes(self, **props):
        """Return all the nodes that match the given properties."""
        def prop_check(p, v, props_given):
            return v == props_given.get(p) if p in props_given else False
        return [n for n in self
                if all([prop_check(p, v, n.annotation.properties)
                        for p, v in props.items()])]


class TimeFrames(Nodes):

    """For now, we take only the TimeFrames that have a frame type, which rules out
    all the frames we got from Kaldi."""

    # TODO: problem here is that this is totally unstructured and gets frames
    #       from all over the graph

    def __init__(self, summary):
        super().__init__(summary)
        for timeframe in self.graph.get_nodes(config.TIME_FRAME):
            if timeframe.has_label():
                self.add(timeframe)

    def as_json(self):
        timeframes = []
        for tf in self.nodes:
            #print('>>>', tf)
            #print('---', tf.properties)
            #print('---', tf.anchors.keys())
            label = tf.frame_type()
            try:
                start, end = tf.anchors['time-offsets']
            except KeyError:
                # TODO: this defies the notion of using the anchors for this,
                # but maybe in this case we should go straight to the start/end
                start = tf.properties['start']
                end = tf.properties['end']
            representatives = tf.representatives()
            rep_tps = [rep.properties['timePoint'] for rep in representatives]
            score = tf.properties.get('classification', {}).get(label)
            timeframes.append(
                { 'identifier': tf.identifier, 'label': label, 'score': score,
                  'start-time': start, 'end-time': end, 'representatives': rep_tps })
        return timeframes

    def pp(self):
        print('\nTimeframes -> ')
        for tf in self.nodes:
            summary = tf.summary()
            print('    %s:%s %s' % (summary['start'], summary['end'],
                                    summary['frameType']))


class Segments(Nodes):

    def __init__(self, summary):
        super().__init__(summary)
        self.summary = summary
        self.mmif = summary.mmif
        self.view = get_last_segmenter_view(self.mmif.views)
        for timeframe in self.summary.timeframes:
            # TODO: not good at all this code
            if timeframe.frame_type() in ('speech', 'non-speech'):
                self.add(timeframe)


class Tags(Nodes):

    """For now, we take all semantic tags."""

    def __init__(self, summary):
        super().__init__(summary)
        tags = {}
        for tag in self.graph.get_nodes(config.SEMANTIC_TAG):
            #sys.stderr.write(f'{type(tag)} {tag} {tag.annotation}\n')
            tags[tag.properties['text']] = tag
        #for t in tags:
        #    sys.stderr.write(f'{t}\n')
        for tag in tags.values():
            self.add(tag)


class Entities(Nodes):

    """Collecting instances of graph.EntityNode.

    nodes_idx  -  lists of instances of graph.EntityNode, indexed on entity text
                  { entity-string ==> list of graph.EntityNode }
    bins       -  an instance of Bins

    """

    def __init__(self, summary):
        super().__init__(summary)
        self.nodes_idx = {}
        self.bins = None
        for ent in self.graph.get_nodes(config.NAMED_ENTITY):
            self.add(ent)
        self._create_node_index()
        self._group()
        self._add_tags(summary.tags)

    def __str__(self):
        return f'<Entities with {len(self.nodes_idx)} nodes and {len(self.bins)} bins>'

    def _create_node_index(self):
        """Put all the entities from self.nodes in self.node_idx. This first puts
        the nodes into the dictionary indexed on text string and then sorts the
        list of nodes for each string on video position."""
        for ent in self:
            self.nodes_idx.setdefault(ent.properties['text'], []).append(ent)
        for text, entities in self.nodes_idx.items():
            self.nodes_idx[text] = sorted(entities,
                                          key=(lambda e: e.start_in_video()))

    def _group(self):
        """Groups all the nodes on the text and sorts them on position in the video,
        for the latter it will also create bins of entities that occur close to each
        other in the text."""
        # create the bins, governed by the summary's granularity
        self.bins = Bins(self.summary)
        for text, entities in self.nodes_idx.items():
            self.bins.current_bin = None
            for entity in entities:
                self.bins.add_entity(text, entity)
        self.bins.mark_entities()

    def _add_tags(self, tags):
        for tag in tags:
            tag_doc = tag.properties['document']
            tag_p1 = tag.properties['start']
            tag_p2 = tag.properties['end']
            entities = self.nodes_idx.get(tag.properties['text'], [])
            for entity in entities:
                props = entity.properties
                doc = props['document']
                p1 = props['start']
                p2 = props['end']
                if tag_doc == doc and tag_p1 == p1 and tag_p2 == p2:
                    entity.properties['tag'] = tag.properties['tagName']

    def as_json(self):
        json_obj = []
        for text in self.nodes_idx:
            entity = {"text": text, "instances": []}
            json_obj.append(entity)
            for e in self.nodes_idx[text]:
                entity["instances"].append(e.summary()) # e.summary(), E_PROPS)
        return json_obj

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


class Captions(Nodes):

    def __init__(self, summary):
        super().__init__(summary)
        self.captions = []
        view = get_captions_view(summary.mmif.views)
        if view is not None:
            for doc in self.graph.get_nodes(config.TEXT_DOCUMENT, view_id=view.id):
                text = doc.properties['text']['@value'].split('[/INST]')[-1]
                p1, p2 = doc.anchors['time-offsets']
                if 'representatives' in doc.anchors:
                    tp_id = doc.anchors["representatives"][0]
                    tp = summary.graph.get_node(tp_id)
                self.captions.append(
                    { 'identifier': doc.identifier,
                      'time-point': tp.properties['timePoint'],
                      'text': text })

    def as_json(self):
        return self.captions
        #return [(ident, p1, p2, text) for ident, p1, p2, text in self.captions]


class Bins(object):

    def __init__(self, summary):
        self.summary = summary
        self.bins = {}
        self.current_bin = None
        self.current_text = None

    def __str__(self):
        return f'<Bins {len(self.bins)}>'

    def __len__(self):
        return len(self.bins)

    def add_entity(self, text, entity):
        """Add an entity instance to the appropriate bin."""
        if self.current_bin is None:
            # Add the first instance of a new entity (as defined by the text),
            # since it is the first a new bin will be created.
            self.current_text = text
            self.current_bin = Bin(entity)
            self.bins[text] = [self.current_bin]
        else:
            # For following entities with the same text, a new bin may be
            # created depending on the positions and the granularity.
            p1 = self.current_bin[-1].start_in_video()
            p2 = entity.start_in_video()
            # p3 = entity.end_in_video()
            if p2 - p1 < config.GRANULARITY:
                # TODO: should add p3 here
                self.current_bin.add(entity)
            else:
                self.current_bin = Bin(entity)
                self.bins[self.current_text].append(self.current_bin)

    def mark_entities(self):
        """Marks all entities with the bin that they occur in. This is done to export
        the grouping done with the bins to the entities and this way the bins never need
        to be touched again."""
        # TODO: maybe use the bins when we create the output
        for entity_bins in self.bins.values():
            for i, e_bin in enumerate(entity_bins):
                for entity in e_bin:
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


def parse_arguments():
    parser = argparse.ArgumentParser(description='Create a JSON Summary for a MMIF file')
    parser.add_argument('-d', metavar='DIRECTORY', help='directory with input files')
    parser.add_argument('-i', metavar='MMIF_FILE', help='input MMIF file')
    parser.add_argument('-o', metavar='JSON_FILE', help='output summary file')
    parser.add_argument('--full', action='store_true', help='print full report, overrule other options')
    parser.add_argument('--views', action='store_true', help='include view metadata')
    parser.add_argument('--transcript', action='store_true', help='include transcript')
    parser.add_argument('--captions', action='store_true', help='include Llava captions')
    parser.add_argument('--timeframes', action='store_true', help='include all time frames')

    parser.add_argument('--barsandtone', action='store_true', help='include bars-and-tone')
    parser.add_argument('--segments', action='store_true', help='include segments')
    parser.add_argument('--slate', action='store_true', help='include slate')
    parser.add_argument('--credits', action='store_true', help='include credits')
    parser.add_argument('--chyrons', action='store_true', help='include chyrons')
    parser.add_argument('--tags', action='store_true', help='include semantic tags')
    parser.add_argument('--entities', action='store_true', help='include entities from transcript')
    return parser.parse_args()


if __name__ == '__main__':

    args = parse_arguments()
    if args.d:
        for mmif_file in pathlib.Path(args.d).iterdir():
            if mmif_file.is_file() and mmif_file.name.endswith('.mmif'):
                print(mmif_file)
                json_file = str(mmif_file)[:-4] + 'json'
                mmif_summary = Summary(mmif_file.read_text())
                mmif_summary.report(
                    outfile=json_file, full=args.full, views=args.views,
                    timeframes=args.timeframes, transcript=args.transcript,
                    captions=args.captions,
                    segments=args.segments, barsandtone=args.barsandtone, slate=args.slate,
                    credits=args.credits, chyrons=args.chyrons, entities=args.entities,
                    tags=args.tags)
    elif args.i and args.o:
        with open(args.i) as fh:
            mmif_text = fh.read()
            mmif_summary = Summary(mmif_text)
            mmif_summary.report(
                outfile=args.o, full=args.full,
                views=args.views, timeframes=args.timeframes,
                transcript=args.transcript, captions=args.captions,

                segments=args.segments, barsandtone=args.barsandtone, slate=args.slate,
                credits=args.credits, chyrons=args.chyrons, entities=args.entities,
                tags=args.tags)
