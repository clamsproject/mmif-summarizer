import sys, json
from operator import itemgetter
from pathlib import Path
import argparse

import graphviz

from mmif import Mmif

import config
from utils import compose_id, flatten_paths, normalize_id
from utils import get_shape_and_color, get_view_label, get_label


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
        for view in self.mmif.views:
            for annotation in view.annotations:
                # TODO: this causes trouble, probably id-lookup-related
                #normalize_id(view, annotation)
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
        source_id = compose_id(view.id, alignment.properties['source'])
        target_id = compose_id(view.id, alignment.properties['target'])
        source = self.get_node(source_id)
        target = self.get_node(target_id)
        # make sure the direction goes from token or textdoc to annotation
        if target.annotation.at_type.shortname in (config.TOKEN, config.TEXT_DOCUMENT):
            source, target = target, source
        source.targets.append(target)

    def get_node(self, node_id):
        return self.nodes.get(node_id)

    def get_nodes(self, short_at_type):
        return [node for node in self.nodes.values()
                if node.at_type.shortname == short_at_type]

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
        self.at_type = annotation.at_type
        #id1 = self._create_identifier()
        #id2 = annotation.id
        #print(id1, id2, self)
        #self.identifier = annotation.id
        self.identifier = self._create_identifier()
        # copy the properties to the top-level
        self.properties = json.loads(str(annotation.properties))
        self.document = self._get_document()
        # The targets property contains a list of annotations or documents that
        # the node content points to. This includes the document the annotation
        # points to as well as the alignment from a token or text document to a
        # bounding box or time frame (which is added later).
        # TODO: the above does not seem to be true since there is no evidence of
        # data from alignments being added.
        self.targets = [] if self.document is None else [self.document]

    def __str__(self):
        anchor = ''
        if self.at_type.shortname == config.TOKEN:
            anchor = " %s:%s '%s'" % (self.properties['start'],
                                      self.properties['end'],
                                      self.properties['text'])
        return "<%s %s%s>" % (self.at_type.shortname, self.identifier, anchor)

    def _get_view_id(self):
        """Return the view identifier of the annotation, this will be None when
        the Node was created from an element of the MMIF document list."""
        return None if self.view is None else self.view.id

    def _create_identifier(self):
        """Create a composite identifier view_id:annotation_id. If the Node was
        created for an element of the document list just return the document
        identifier."""
        # TODO: what if the annotation_id already had the view_id prepended?
        view_id = self._get_view_id()
        anno_id = self.annotation.properties['id']
        return anno_id if view_id is None else "%s:%s" % (view_id, anno_id)

    def _get_document(self):
        """Return the document or annotation node that the annotation/document in
        the node refers to via the document property. This could be a local property
        or a metadata property if there is no such local property. Return None
        if neither of those exist."""
        # try the local property
        docid = self.properties.get('document')
        if docid is not None:
            docid = self._adjust_identifier(docid)
            # print('>>>', docid, self.graph.get_node(docid))
            return self.graph.get_node(docid)
        # try the metadata property
        if self.view is not None:
            try:
                metadata = self.view.metadata.contains[self.at_type]
                docid = metadata['document']
                docid = self._adjust_identifier(docid)
                return self.graph.get_node(docid)
            except KeyError:
                return None
        return None

    def _get_document_plus_span(self):
        props = self.properties
        return "%s:%s:%s" % (self.document.identifier,
                             props['start'], props['end'])

    def _adjust_identifier(self, docid):
        """Compose the identifier if needed."""
        if docid is None:
            return None
        elif ':' not in docid and docid not in self.graph.nodes:
            return compose_id(self.view.id, docid)
        else:
            return docid

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
        print(self)
        for target in self.targets:
            print('   ', target)


class TimeFrameNode(Node):

    def __str__(self):
        frame_type = ' ' + self.frame_type() if self.has_frame_type() else ''
        return ('<TimeFrameNode %s %s:%s%s>'
                % (self.identifier, self.start(), self.end(), frame_type))

    def start(self):
        return self.properties.get('start', -1)

    def end(self):
        return self.properties.get('end', -1)

    def frame_type(self):
        return self.properties.get('frameType')

    def has_frame_type(self):
        return self.frame_type() is not None

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


class TagNode(Node):

    # TODO: this is very preliminay, and not much beyond a hack

    def __str__(self):
        return "<%s %s %s:%s %s '%s'>" \
            % (self.at_type.shortname,
               self.identifier,
               self.properties['start'],
               self.properties['end'],
               self.properties['tagName'],
               self.properties['text'])

    def summary(self):
        #sys.stderr.write(f'>>> {self.annotation}\n')
        return {
            'id': self.identifier,
            'tag': self.properties['tagName'],
            'start': self.properties['start'],
            'end': self.properties['end'],
            'text': self.properties['text'],
            'document': self.annotation.properties['document']
        }


class Nodes(object):

    """Factory class for Node creation. Use Node for creation unless a special
    class was registered for the kind of annotation we have."""

    node_classes = { config.NAMED_ENTITY: EntityNode,
                     config.SEMANTIC_TAG: TagNode,
                     config.TIME_FRAME: TimeFrameNode }

    @classmethod
    def new(cls, graph, view, annotation):
        node_class = cls.node_classes.get(annotation.at_type.shortname, Node)
        return node_class(graph, view, annotation)



if __name__ == '__main__':

    graph = Graph(open(sys.argv[1]).read())
    graph.pp()
    #graph.nodes['v_7:st12'].pp()
    #graph.nodes['v_2:s1'].pp()
    #graph.nodes['v_4:tf1'].pp()


'''

Printing some graphs:

uv run graph.py -i examples/input-v9.mmif -e dot -f png -o examples/dot-v9-1-full -p -a -v
uv run graph.py -i examples/input-v9.mmif -e dot -f png -o examples/dot-v9-2-no-view-links -p -a
uv run graph.py -i examples/input-v9.mmif -e dot -f png -o examples/dot-v9-3-no-anchor-to-doc -p

'''
