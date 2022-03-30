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
            node = NodeFactory.new_node(self, view, annotation)
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
        # Will be filled in the first time the summary() method is used
        self.summary = None

    def __str__(self):
        anchor = ''
        if self.at_type.shortname == names.TOKEN:
            anchor =  " %s:%s '%s'" % (self.properties['start'],
                                       self.properties['end'],
                                       self.properties['text'])
        return "<%s %s%s>" % (self.at_type.shortname, self.identifier, anchor)

    def _get_view_id(self):
        """Return the view identifier of the annoation, this will be None when
        the Node was created from an element of the MMIF document list."""
        return None if self.view is None else self.view.id

    def _create_identifier(self):
        """Create a composite identifier view_id:annotation_id. If the Node was
        created for an element of the document list just retun the document
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


class TimeFrameNode(Node):

    def __str__(self):
        return '<Timeframe %s:%s %s:%s %s>' % (
            self.view.id,
            self.properties['id'],
            self.properties['start'],
            self.properties['end'],
            self.frame_type())

    def frame_type(self):
        return self.properties.get('frameType')

    def has_frame_type(self):
        return self.frame_type() is not None

    def node_summary(self, full=False):
        if self.summary is None:
            props = self.properties
            self.summary = { 'start': props['start'],
                             'end': props['end'],
                             'frameType': props['frameType'] }
            if full:
                self.summary['id'] = "%s:%s" % (self.view.id, props['id'])
        return self.summary


class EntityNode(Node):

    def __init__(self, graph, view, annotation):
        super().__init__(graph, view, annotation)
        self.tokens = []

    def __str__(self):
        return "<%s %s %s:%s %s>" \
            % (self.at_type.shortname,
               self.identifier,
               self.properties['start'],
               self.properties['end'],
               self.properties['text'])

    def start_in_video(self):
        return self.anchor()['video-start']

    def pp(self):
        print(self)
        print('  %s' % ' '.join([str(t) for t in self.tokens]))
        for i, p in enumerate(self.paths_to_docs()):
            print('  %s' % ' '.join([str(n) for n in p[1:]]))

    def node_summary(self, full=False):
        if self.summary is None:
            props = self.properties
            anchor = self.anchor()
            if 'coordinates' in anchor:
                anchor['coordinates'] = \
                    ','.join(["%s:%s" % (pair[0], pair[1])
                              for pair in anchor['coordinates']])
            self.summary = {
                'group': props['group'],
                'cat': props['category'],
                'tag': props.get('tag', 'nil'),
                'document': self._get_document_plus_span() }
            if full:
                self.summary['id'] = "%s:%s" % (self.view.id, props['id'])
            for prop in ('video-start', 'video-end', 'coordinates'):
                if prop in anchor:
                    self.summary[prop] = anchor[prop] 
        return self.summary
        
    def as_xml(self, verbose=False):
        props = self.properties
        anchor = self.anchor()
        anchor_str = ''
        if 'coordinates' in anchor:
            anchor_str = 'video-start="%s" coor="%s"' \
                % (anchor['start'],
                   ','.join(["%s:%s" % (pair[0], pair[1])
                             for pair in anchor['coordinates']]))
        elif 'end' in anchor:
             anchor_str = 'video-start="%s" video-end="%s"' \
                 % (anchor['start'], anchor['end'])
        tag = props.get('tag', 'nil')
        if verbose:
            return ('<Entity group="%s" id="%s:%s" doc="%s:%s"%s" cat="%s" %s />'
                    % (props['group'], self.view.id, props['id'],
                       self.document.identifier, props['start'], props['end'],
                       props['category'], anchor_str))
        else:
            return ('<Instance group="%s" cat="%s" tag="%s" %s />'
                    % (props['group'], props['category'], tag, anchor_str))

    def anchor(self):
        # TODO: deal with when the primary document is not a video
        self.paths = self.paths_to_docs()
        bbtf = self.find_boundingbox_or_timeframe()
        if bbtf.at_type.shortname == names.BOUNDING_BOX:
            return {'video-start': bbtf.properties['timePoint'],
                    'coordinates': bbtf.properties['coordinates']}
        elif bbtf.at_type.shortname == names.TIME_FRAME:
            return {'video-start': bbtf.properties['start'],
                    'video-end': bbtf.properties['end']}

    def find_boundingbox_or_timeframe(self):
        return self.paths[-1][-2]


class TagNode(Node):

    def __str__(self):
        return "<%s %s %s:%s %s '%s'>" \
            % (self.at_type.shortname,
               self.identifier,
               self.properties['start'],
               self.properties['end'],
               self.properties['tagName'],
               self.properties['text'])


class NodeFactory(object):

    """Factory class for Node creation. Use Node for creation unless a special
    class was registered for the kind of annotation we have."""

    node_classes = { names.NAMED_ENTITY: EntityNode,
                     names.SEMANTIC_TAG: TagNode,
                     names.TIME_FRAME: TimeFrameNode }

    @classmethod
    def new_node(cls, graph, view, annotation):
        node_class = cls.node_classes.get(annotation.at_type.shortname, Node)
        return node_class(graph, view, annotation)
