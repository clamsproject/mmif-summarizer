import sys, json
from collections import defaultdict
from operator import itemgetter
from pathlib import Path
import argparse

from mmif import Mmif

from summarizer import config
from summarizer.utils import compose_id, flatten_paths, normalize_id
from summarizer.utils import get_shape_and_color, get_view_label, get_label


class Graph(object):

    """Graph implementation for a MMIF document. Each node contains an annotation
    or document. Alignments are stored separately. Edges between nodes are created
    from the alignments and added to the Node.targets property. The first edge added
    to Node.targets is the document that the Node points to (if there is one).

    The goal for the graph is to store all useful annotation and to have simple ways
    to trace nodes all the way up to the primary data."""

    def __init__(self, mmif):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        self.documents = []
        self.nodes = {}
        self.alignments = []
        self._init_nodes()
        self._init_edges()
        # Third pass to add links between text elements, in particular from
        # entities to tokens, adding lists of tokens to entities.
        tokens = self.get_nodes(config.TOKEN)
        entities = self.get_nodes(config.NAMED_ENTITY)
        self.token_idx = TokenIndex(tokens)
        for e in entities:
            e.tokens = self.token_idx.get_tokens_for_node(e)

    def _init_nodes(self):
        # The top-level documents are added as nodes, but they are also put in
        # the documents list.
        for doc in self.mmif.documents:
            self.add_node(None, doc)
            self.documents.append(doc)
        # First pass over all annotations and documents in all views and save
        # them in the graph.
        doc_ids = [d.id for d in self.documents]
        for view in self.mmif.views:
            for annotation in view.annotations:
                normalize_id(doc_ids, view, annotation)
                if annotation.at_type.shortname == config.ALIGNMENT:
                    # alignments are not added as nodes, but we do keep them around
                    self.alignments.append((view, annotation))
                else:
                    self.add_node(view, annotation)

    def _init_edges(self):
        # Second pass over the alignments so we create edges.
        for view, alignment in self.alignments:
            self.add_edge(view, alignment)

    def __str__(self):
        return "<Graph nodes=%d>" % len(self.nodes)

    def add_node(self, view, annotation):
        """Add an annotation as a node to the graph."""
        node = Nodes.new(self, view, annotation)
        self.nodes[node.identifier] = node

    def add_edge(self, view, alignment):
        source_id = alignment.properties['source']
        target_id = alignment.properties['target']
        #print(alignment.id, source_id, target_id)
        source = self.get_node(source_id)
        target = self.get_node(target_id)
        # make sure the direction goes from token or textdoc to annotation
        if target.annotation.at_type.shortname in (config.TOKEN, config.TEXT_DOCUMENT):
            source, target = target, source
        source.targets.append(target)
        #if target_id == "v_3:td_1":
        #    source.set_alignment_anchors(target, debug=True)
        source.set_alignment_anchors(target)
        target.set_alignment_anchors(source)

    def get_node(self, node_id):
        return self.nodes.get(node_id)

    def get_nodes(self, short_at_type: str, view_id : str = None):
        """Get all nodes for an annotation type, using the short form. If a view
        identifier is provided then only include nodes from that view."""
        return [node for node in self.nodes.values()
                if (node.at_type.shortname == short_at_type
                    and (view_id is None or node.view.id == view_id))]

    def statistics(self):
        stats = defaultdict(int)
        for node in self.nodes.values():
            stats[node.at_type.shortname] += 1
        return stats

    def trim(self, start: int, end: int):
        """Trim the graph and keep only those nodes that are included in graph
        between two timepoints (both in milliseconds). This assumes that all nodes
        are anchored on the time in the audio or video stream. At the moment it 
        keeps all nodes that are not explicitly anchored."""
        remove = set()
        for node_id, node in self.nodes.items():
            if 'time-point' in node.anchors:
                if not start <= node.anchors['time-point'] <= end:
                    remove.add(node_id)
            if 'time-offsets' in node.anchors:
                p1, p2 = node.anchors['time-offsets']
                if not (start <= p1 <= end and start <= p2 <= end):
                    remove.add(node_id)
        new_nodes = [n for n in self.nodes.values() if not n.identifier in remove]
        self.nodes = { node.identifier: node for node in new_nodes }

    def pp(self, fname=None):
        fh = sys.stdout if fname is None else open(fname, 'w')
        fh.write("%s\n" % self)
        for view in self.mmif.views:
            fh.write("  <View %s %s>\n" % (view.id, str(view.metadata['app'])))
        for node_id, node in self.nodes.items():
            fh.write("  %-40s" % node)
            targets = [str(t) for t in node.targets]
            fh.write(' -->  [%s]\n' % ' '.join(targets))


class TokenIndex(object):

    """
    The tokens are indexed on the identifier on the TextDocument that they occur
    in and for each text document we have a list of <offsets, Node> pairs

    {'v_4:td1': [
        ((0, 5), <__main__.Node object at 0x1039996d0>),
        ((5, 6), <__main__.Node object at 0x103999850>),
        ...
    }
    """

    def __init__(self, tokens):
        self.tokens = {}
        self.token_count = len(tokens)
        for t in tokens:
            tup = ((t.properties['start'], t.properties['end']), t)
            self.tokens.setdefault(t.document.identifier, []).append(tup)
        # Make sure the tokens for each document are ordered.
        for document, token_list in self.tokens.items():
            self.tokens[document] = sorted(token_list, key=itemgetter(0))
        # In some cases there are two tokens with identical offset (for example
        # with tokenization from both Kaldi and spaCy, not sure what to do with
        # these, but should probably be more careful on what views to access

    def __len__(self):
        return self.token_count

    def __str__(self):
        return f'<TokenIndex on with {len(self)} tokens>'

    # TODO: benchmark this method. I may want to use something like this to 
    # determine encloced nodes and enclosing nodes and that may blow up since
    # that would be O(n^2). If it does matter, probably start using binary
    # search or add an index from character offset to nodes.
    def get_tokens_for_node(self, node):
        """Return all tokens included in the span of a node."""
        doc = node.document.identifier
        start = node.properties['start']
        end = node.properties['end']
        tokens = []
        for (t_start, t_end), token in self.tokens.get(doc, []):
            if t_start >= start and t_end <= end:
                tokens.append(token)
        return tokens

    def pp(self, fname=None):
        fh = sys.stdout if fname is None else open(fname, 'w')
        for document in self.tokens:
            fh.write("\n[%s] -->\n" % document)
            for t in self.tokens[document]:
                fh.write('    %s %s\n' % (t[0], t[1]))


class Node(object):

    def __init__(self, graph, view, annotation):
        self.graph = graph
        self.view = view
        self.annotation = annotation
        # copy some information from the Annotation
        self.at_type = annotation.at_type
        self.identifier = annotation.id
        self.properties = json.loads(str(annotation.properties))
        # get the document from the view or the properties
        self.document = self._get_document()
        # The targets property contains a list of annotations or documents that
        # the node content points to. This includes the document the annotation
        # points to as well as the alignment from a token or text document to a
        # bounding box or time frame (which is added later).
        # TODO: the above does not seem to be true since there is no evidence of
        # data from alignments being added.
        self.targets = [] if self.document is None else [self.document]
        self.set_local_anchors()

    def set_local_anchors(self):
        """Set the anchors that you can get from the annotation itself, which 
        includes the start and end offsets, the coordinates and the timePoint of
        a BoundingBox."""
        # TODO: start/end in time frames now does the wrong thing
        # TODO: should probably be overridden on subtypes
        props = self.properties
        attype = self.annotation.at_type.shortname
        self.anchors = {}
        if 'start' in props and 'end' in props:
            self.anchors['text-offsets'] = (props['start'], props['end'])
        if 'coordinates' in props:
            self.anchors['coordinates'] = props['coordinates']
        if 'timePoint' in props:
            self.anchors['time-point'] = props['timePoint']
        if 'targets' in props:
            # TODO: this is a placeholder, should get the targets and
            # find start/end properties
            self.anchors['targets'] = props['targets']
        if attype == 'TimeFrame' and "targets" in props:
            tp1 = self.graph.nodes[props['targets'][0]]
            tp2 = self.graph.nodes[props['targets'][-1]]
            self.anchors['time-offsets'] = (
                tp1.properties['timePoint'], tp2.properties['timePoint'])
        if not self.anchors and not attype.endswith('Document'):
            if attype != 'Annotation':
                print('set_local_anchors', attype, self, self.properties.keys())

    def set_alignment_anchors(self, target: None, debug=False):
        source_attype = self.at_type.shortname
        target_attype = target.at_type.shortname
        if debug:
            print('DEBUG', source_attype, target_attype)
            print('DEBUG', self.annotation)
            print('DEBUG', target.annotation)
            print('DEBUG', target.anchors)
        # If a TextDocument is aligned to a BoundingBox then we grab the coordinates
        # TODO: how are we getting the time point?
        if source_attype == 'TextDocument' and target_attype == 'BoundingBox':
            if 'coordinates' in target.properties:
                self.anchors['coordinates'] = target.properties['coordinates']
            #print(source_attype, self.anchors)
        elif source_attype == 'BoundingBox' and target_attype == 'TextDocument':
            pass
        # If a TextDocument is aligned to a TimeFrame then we copy time anchors
        # but also targets and representatives, the latter because some alignments
        # are not precise
        elif source_attype == 'TextDocument' and target_attype == 'TimeFrame':
            if 'start' in target.properties and 'end' in target.properties:
                self.anchors['time-offsets'] = (target.properties['start'],
                                                target.properties['end'])
            if 'time-offsets' in target.anchors:
                # TODO: is this ever used?
                self.anchors['time-offsets'] = target.anchors['time-offsets']
            if 'targets' in target.properties:
                self.anchors['targets'] = target.properties['targets']
            if 'representatives' in target.properties:
                self.anchors['representatives'] = target.properties['representatives']
            #print('-', source_attype, self.anchors, self, target)
        elif source_attype == 'TimeFrame' and target_attype == 'TextDocument':
            pass
        # For Token-TimeFrame alignments all we need are the start and end time points
        elif source_attype == 'Token' and target_attype == 'TimeFrame':
            if 'start' in target.properties and 'end' in target.properties:
                self.anchors['time-offsets'] = (target.properties['start'],
                                                target.properties['end'])
            #print(source_attype, self.anchors)
        elif source_attype == 'TimeFrame' and target_attype == 'Token':
            pass
        # TODO: check whether some action is needed for the next options
        elif source_attype == 'TextDocument' and target_attype == 'VideoDocument':
            pass
        elif source_attype == 'VideoDocument' and target_attype == 'TextDocument':
            pass
        elif source_attype == 'BoundingBox' and target_attype == 'TimePoint':
            pass
        elif source_attype =='TimePoint' and target_attype == 'BoundingBox':
            pass
        elif source_attype == 'BoundingBox' and target_attype in ('Token', 'Sentence', 'Paragraph'):
            pass
        elif source_attype in ('Token', 'Sentence', 'Paragraph') and target_attype == 'BoundingBox':
            pass
        elif source_attype == 'TextDocument' and target_attype == 'TimePoint':
            pass
        elif source_attype == 'TimePoint' and target_attype == 'TextDocument':
            pass
        else:
            print('-', source_attype, target_attype)
        if debug:
            print('>>>', self.anchors)

    def __str__(self):
        anchor = ''
        if self.at_type.shortname == config.TOKEN:
            anchor = " %s:%s '%s'" % (self.properties['start'],
                                      self.properties['end'],
                                      self.properties.get('text'))
        return "<%s %s%s>" % (self.at_type.shortname, self.identifier, anchor)

    def _get_document(self):
        """Return the document or annotation node that the annotation/document in
        the node refers to via the document property. This could be a local property
        or a metadata property if there is no such local property. Return None
        if neither of those exist."""
        # try the local property
        docid = self.properties.get('document')
        if docid is not None:
            # print('>>>', docid, self.graph.get_node(docid))
            return self.graph.get_node(docid)
        # try the metadata property
        if self.view is not None:
            try:
                metadata = self.view.metadata.contains[self.at_type]
                docid = metadata['document']
                return self.graph.get_node(docid)
            except KeyError:
                return None
        return None

    def _get_document_plus_span(self):
        props = self.properties
        return "%s:%s:%s" % (self.document.identifier,
                             props['start'], props['end'])

    def paths_to_docs(self):
        """Return all the paths from the node to documents."""
        paths = self._paths_to_docs()
        return flatten_paths(paths)

    def _paths_to_docs(self):
        paths = []
        if not self.targets:
            return [[self]]
        for t in self.targets:
            paths.append([self])
        for i, target in enumerate(self.targets):
            paths[i].extend(target._paths_to_docs())
        return paths

    def summary(self):
        """The default summary is just the identfier, this should typically be
        overriden by sub classes."""
        return { 'id': self.identifier }

    def pp(self):
        print('-' * 80)
        print(self)
        for prop in self.properties:
            print(f'  {prop} = {self.properties[prop]}')
        print('  targets = ')
        for target in self.targets:
            print('   ', target)
        print('-' * 80)


class TimeFrameNode(Node):

    def __str__(self):
        frame_type = ' ' + self.frame_type() if self.has_label() else ''
        return ('<TimeFrameNode %s %s:%s%s>'
                % (self.identifier, self.start(), self.end(), frame_type))

    def start(self):
        return self.properties.get('start', -1)

    def end(self):
        return self.properties.get('end', -1)

    def frame_type(self):
        # TODO: rename this, uses old property since replaced by "label""
        # NOTE: this is still aloowing for the old property though
        return self.properties.get('label') or self.properties.get('frameType')

    def has_label(self):
        return self.frame_type() is not None

    def representatives(self) -> list:
        """Return a list of the representative TimePoints."""
        # TODO: why could I not get this from the anchors?
        rep_ids = self.properties.get('representatives', [])
        reps = [self.graph.get_node(rep_id) for rep_id in rep_ids]
        return reps

    def summary(self):
        """The summary of a time frame just contains the identifier, start, end
        and frame type."""
        return { 'id': self.identifier,
                 'start': self.properties['start'],
                 'end': self.properties['end'],
                 'frameType': self.properties.get('frameType') }


class EntityNode(Node):

    def __init__(self, graph, view, annotation):
        super().__init__(graph, view, annotation)
        self.tokens = []
        self._paths = None
        self._anchor = None

    def __str__(self):
        return ("<NamedEntityNode %s %s:%s %s>"
                % (self.identifier,
                   self.properties['start'],
                   self.properties['end'],
                   self.properties['text']))

    def start_in_video(self):
        return self.anchor()['video-start']

    def end_in_video(self):
        return self.anchor().get('video-end')

    def pp(self):
        print(self)
        print('  %s' % ' '.join([str(t) for t in self.tokens]))
        for i, p in enumerate(self.paths_to_docs()):
            print('  %s' % ' '.join([str(n) for n in p[1:]]))

    def summary(self):
        """The summary for entities needs to include where in the video or image
        the entity occurs, it is not enough to just give the text document."""
        anchor = self.anchor()
        return {
            'id': self.identifier,
            'group': self.properties['group'],
            'cat': self.properties['category'],
            'tag': self.properties.get('tag'),
            'document': self._get_document_plus_span(),
            'video-start': anchor.get('video-start'),
            'video-end': anchor.get('video-end'),
            'coordinates': self._coordinates_as_string(anchor)}

    def anchor(self):
        """The anchor is the position in the video that the entity is linked to.
        This anchor cannot be found in the document property because that points
        to a text document that was somehow derived from the video document. Some
        graph traversal is needed to get the anchor, but we know that the anchor
        is always a time frame or a bounding box.
        """
        # TODO: deal with the case where the primary document is not a video
        self.paths = self.paths_to_docs()
        bbtf = self.find_boundingbox_or_timeframe()
        # for path in paths:
        #     print('... [')
        #     for n in path: print('     ', n)
        # print('===', bbtf)
        if bbtf.at_type.shortname == config.BOUNDING_BOX:
            return {'video-start': bbtf.properties['timePoint'],
                    'coordinates': bbtf.properties['coordinates']}
        elif bbtf.at_type.shortname == config.TIME_FRAME:
            return {'video-start': bbtf.properties['start'],
                    'video-end': bbtf.properties['end']}

    def anchor2(self):
        """The anchor is the position in the video that the entity is linked to.
        This anchor cannot be found in the document property because that points
        to a text document that was somehow derived from the video document. Some
        graph traversal is needed to get the anchor, but we know that the anchor
        is always a time frame or a bounding box.
        """
        # TODO: with this version you get an error that the paths variable does
        #       not exist yet, must get a clearer picture on how to build a graph
        #       where nodes have paths to anchors
        # TODO: deal with the case where the primary document is not a video
        if self._anchor is None:
            self._paths = self.paths_to_docs()
            bbtf = self.find_boundingbox_or_timeframe()
            # for path in self._paths:
            #    print('... [')
            #    for n in path: print('     ', n)
            # print('===', bbtf)
            if bbtf.at_type.shortname == config.BOUNDING_BOX:
                self._anchor = {'video-start': bbtf.properties['timePoint'],
                                'coordinates': bbtf.properties['coordinates']}
            elif bbtf.at_type.shortname == config.TIME_FRAME:
                self._anchor = {'video-start': bbtf.properties['start'],
                                'video-end': bbtf.properties['end']}
        return self._anchor

    def find_boundingbox_or_timeframe(self):
        return self.paths[-1][-2]

    @staticmethod
    def _coordinates_as_string(anchor):
        if 'coordinates' not in anchor:
            return None
        return ','.join(["%s:%s" % (pair[0], pair[1])
                         for pair in anchor['coordinates']])


class Nodes(object):

    """Factory class for Node creation. Use Node for creation unless a special
    class was registered for the kind of annotation we have."""

    node_classes = { config.NAMED_ENTITY: EntityNode,
                     config.TIME_FRAME: TimeFrameNode }

    @classmethod
    def new(cls, graph, view, annotation):
        node_class = cls.node_classes.get(annotation.at_type.shortname, Node)
        return node_class(graph, view, annotation)



if __name__ == '__main__':

    graph = Graph(open(sys.argv[1]).read())
    print(graph)
    #graph.pp()
    #graph.nodes['v_7:st12'].pp()
    #graph.nodes['v_2:s1'].pp()
    #graph.nodes['v_4:tf1'].pp()
    exit()
    for node in graph.nodes.values():
        print(node.at_type.shortname, node.identifier, node.anchors)


'''

Printing some graphs:

uv run graph.py -i examples/input-v9.mmif -e dot -f png -o examples/dot-v9-1-full -p -a -v
uv run graph.py -i examples/input-v9.mmif -e dot -f png -o examples/dot-v9-2-no-view-links -p -a
uv run graph.py -i examples/input-v9.mmif -e dot -f png -o examples/dot-v9-3-no-anchor-to-doc -p

'''
