import json
from operator import itemgetter

from mmif import Mmif

import names
from utils import compose_id
from utils import flatten_paths, print_paths


class Graph(object):

    """Graph implementation for a MMIF document. Each node contains an annotation
    or document. Alignments are stored separately. Edges between nodes are created
    from the alignments and added to the Node.targets property. The goal for the
    graph is to store all useful annotation and to have simple ways to trace nodes
    all the way up to the primary data."""

    def __init__(self, mmif):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        self.documents = []
        self.nodes = {}
        self.alignments = []
        # The top-level documents are added as nodes, but they are also put in
        # the documents list.
        for doc in self.mmif.documents:
            self.add_node(None, doc)
            self.documents.append(doc)
        # First pass over all annotations and documents in all views and save
        # them in the graph.
        for view in self.mmif.views:
            for annotation in view.annotations:
                self.add_node(view, annotation)
        # Second pass over the alignments so we create edges.
        for view, alignment in self.alignments:
            self.add_edge(view, alignment)
        # Third pass to add links between text elements, in particular from
        # entities to tokens, adding lists of tokens to entities.
        tokens = self.get_nodes(names.TOKEN)
        entities = self.get_nodes(names.NAMED_ENTITY)
        self.token_idx = TokenIndex(tokens)
        for e in entities:
            e.tokens = self.token_idx.get_tokens_for_node(e)

    def __str__(self):
        return "<Graph nodes=%d>" % len(self.nodes)

    def add_node(self, view, annotation):
        """Add annotations and documents to the graph."""
        if annotation.at_type.shortname == names.ALIGNMENT:
            # alignments are not added as nodes, but we do keep them around
            self.alignments.append((view, annotation))
        else:
            node = Nodes.new(self, view, annotation)
            self.nodes[node.identifier] = node

    def add_edge(self, view, alignment):
        source_id = compose_id(view.id, alignment.properties['source'])
        target_id = compose_id(view.id, alignment.properties['target'])
        source = self.get_node(source_id)
        target = self.get_node(target_id)
        # make sure the direction goes from token or textdoc to annotation
        if target.annotation.at_type.shortname in (names.TOKEN, names.TEXT_DOCUMENT):
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

    def __init__(self, tokens):
        self.tokens = {}
        for t in tokens:
            tup = ((t.properties['start'], t.properties['end']), t)
            self.tokens.setdefault(t.document.identifier, []).append(tup)
        # Make sure the tokens for each document are ordered.
        for document, token_list in self.tokens.items():
            self.tokens[document] = sorted(token_list, key=itemgetter(0))
        # In some cases there will be two tokens with identical offset (for
        # example with tokenization from both Kaldi and spaCy, not sure what to
        # do with these, but started some code to filter them, it doesn't do
        # anything at the moment.
        for document_id in self.tokens:
            view_id = document_id.split(':')[0]
            #print(view_id)
            for (start, end), token in self.tokens[document_id]:
                token_view = token.identifier.split(':')[0]
                #print(' ', token.identifier, token_view)

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
        self.identifier = self._create_identifier()
        # copy the properties to the top-level, where we can edit them
        self.properties = json.loads(str(annotation.properties))
        # The targets property contains a list of annotations or documents that
        # the node content points to. This includes the document the annotation
        # points to (which is calculated right here) as well as the alignment
        # from a token or text document to a bounding box or time frame (which
        # is added later). The document is also stored separately.
        target = self._get_document()
        self.targets = [] if target is None else [target]
        self.document = target

    def __str__(self):
        anchor = ''
        if self.at_type.shortname == names.TOKEN:
            anchor =  " %s:%s '%s'" % (self.properties['start'],
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


class TimeFrameNode(Node):

    def __str__(self):
        return ('<TimeFrameNode %s %s:%s %s>'
                % (self.identifier,
                   self.properties['start'],
                   self.properties['end'],
                   self.frame_type()))

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
        #for path in paths:
        #    print('... [')
        #    for n in path: print('     ', n)
        #print('===', bbtf)
        if bbtf.at_type.shortname == names.BOUNDING_BOX:
            return {'video-start': bbtf.properties['timePoint'],
                    'coordinates': bbtf.properties['coordinates']}
        elif bbtf.at_type.shortname == names.TIME_FRAME:
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
            #for path in self._paths:
            #    print('... [')
            #    for n in path: print('     ', n)
            #print('===', bbtf)
            if bbtf.at_type.shortname == names.BOUNDING_BOX:
                self._anchor = {'video-start': bbtf.properties['timePoint'],
                               'coordinates': bbtf.properties['coordinates']}
            elif bbtf.at_type.shortname == names.TIME_FRAME:
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

    def __str__(self):
        return "<%s %s %s:%s %s '%s'>" \
            % (self.at_type.shortname,
               self.identifier,
               self.properties['start'],
               self.properties['end'],
               self.properties['tagName'],
               self.properties['text'])


class Nodes(object):

    """Factory class for Node creation. Use Node for creation unless a special
    class was registered for the kind of annotation we have."""

    node_classes = { names.NAMED_ENTITY: EntityNode,
                     names.SEMANTIC_TAG: TagNode,
                     names.TIME_FRAME: TimeFrameNode }

    @classmethod
    def new(cls, graph, view, annotation):
        node_class = cls.node_classes.get(annotation.at_type.shortname, Node)
        return node_class(graph, view, annotation)
