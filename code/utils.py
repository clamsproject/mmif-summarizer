"""Utility methods

"""

import io
from pathlib import Path
from xml.sax.saxutils import quoteattr, escape
from collections import UserList

from config import KALDI, WHISPER, SEGMENTER
from config import TOKEN, ALIGNMENT, TIME_FRAME
from config import GRAPH_FORMATTING


def compose_id(view_id, anno_id):
    """Composes the view identifier with the annotation identifier."""
    return anno_id if ':' in anno_id else view_id + ':' + anno_id


def type_name(annotation):
    """Return the short name of the type."""
    return annotation.at_type.split('/')[-1]


def get_last_asr_view(views):
    for view in reversed(views):
        for app in KALDI, WHISPER:
            if view.metadata.app.startswith(app):
                return view
    return None

def get_last_segmenter_view(views):
    for view in reversed(views):
        # print(f'>>> {view.metadata.app}')
        if view.metadata.app.startswith(SEGMENTER):
            return view
    return None

def get_aligned_tokens(view):
    """Get a list of tokens from an ASR view where for each token we add a timeframe
    properties which has the start and end points of the aligned timeframe."""
    idx = AnnotationsIndex(view)
    for alignment in idx.get_annotations(ALIGNMENT).values():
        token = idx[TOKEN].get(alignment.properties['target'])
        frame = idx[TIME_FRAME].get(alignment.properties['source'])
        if token and frame:
            # add a timeframe to the token, we can do this now that we do not
            # freeze MMIF annotations anymore
            token.properties['timeframe'] = (frame.properties['start'],
                                             frame.properties['end'])
    return idx.tokens


class AnnotationsIndex:

    """Creates an index on the annotations list for a view, where each annotation type
    is indexed on its identifier. Tokens are special and get their own list."""

    def __init__(self, view):
        self.view = view
        self.idx = {}
        self.tokens = []
        for annotation in view.annotations:
            shortname = annotation.at_type.shortname
            if shortname == TOKEN:
                self.tokens.append(annotation)
            self.idx.setdefault(annotation.at_type.shortname, {})
            self.idx[shortname][annotation.properties.id] = annotation

    def __str__(self):
        return f'<AnnotationsIndex on view {self.view.id} {self.view.metadata.app}>'

    def __getitem__(self, item):
        return self.idx[item]

    def get_annotations(self, at_type):
        return self.idx.get(at_type, {})


class CharacterList(UserList):

    """Auxiliary datastructure to help print a list of tokens. It allows you to
    back-engineer a sentence from the text and character offsets of the tokens."""

    def __init__(self, n: int, char=' '):
        self.char = char
        self.data = n * [char]

    def __str__(self):
        return f'<CharacterList [{self.getvalue()}]>'

    def __setitem__(self, key, value):
        try:
            self.data[key] = value
        except IndexError:
            for i in range(len(self), key + 1):
                self.data.append(self.char)
            self.data[key] = value

    def set_chars(self, text: str, start: int, end: int):
        self.data[start:end] = text

    def getvalue(self):
        return ''.join(self.data)


def xml_tag(tag, subtag, objs, props, indent='  ') -> str:
    """Return an XML string for a list of instances of subtag, grouped under tag."""
    s = io.StringIO()
    s.write(f'{indent}<{tag}>\n')
    for obj in objs:
        s.write(xml_empty_tag(subtag, indent + '  ', obj, props))
    s.write(f'{indent}</{tag}>\n')
    return s.getvalue()


def xml_empty_tag(tag_name: str, indent: str, obj: dict, props: tuple) -> str:
    """Return an XML tag to an instance of io.StringIO(). Only properties from obj
    that are in the props tuple are printed."""
    pairs = []
    for prop in props:
        if prop in obj:
            if obj[prop] is not None:
                #pairs.append("%s=%s" % (prop, xml_attribute(obj[prop])))
                pairs.append(f'{prop}={xml_attribute(obj[prop])}')
    attrs = ' '.join(pairs)
    return f'{indent}<{tag_name} {attrs}/>\n'


def write_tag(s, tagname: str, indent: str, obj: dict, props: tuple):
    """Write an XML tag to an instance of io.StringIO(). Only properties from obj
    that are in the props tuple are printed."""
    pairs = []
    for prop in props:
        if prop in obj:
            if obj[prop] is not None:
                pairs.append("%s=%s" % (prop, xml_attribute(obj[prop])))
    s.write('%s<%s %s/>\n'
            % (indent, tagname, ' '.join(pairs)))


def xml_attribute(attr):
    """Return attr as an XML attribute."""
    return quoteattr(str(attr))


def xml_data(text):
    """Return text as XML data."""
    return escape(str(text))


def flatten_paths(paths):
    """Take paths implemented as singly linked lists and return regular lists."""
    return [flatten_path(path) for path in paths]


def flatten_path(path):
    """Take a path implemented as singly linked lists and return a regular list."""
    while path:
        if len(path) == 1:
            return path
        else:
            first, rest = path
            return [first] + flatten_path(rest)


def print_paths(paths, indent=''):
    """Print paths, which may be flattened."""
    for path in paths:
        print(indent, end='')
        print_path(path)
        print()


def print_path(p):
    if isinstance(p, list):
        print('[', end=' ')
        for e in p:
            print_path(e)
        print(']', end=' ')
    else:
        print(p, end=' ')


def normalize_id(view: 'View', annotation: 'Annotation'):
    """Change the identifier to include the view identifier if it wasn't included,
    do nothing otherwise."""
    # TODO: should set the identifier, this is still being debugged
    newid = ''
    if ':' not in annotation.id and view is not None:
        newid = f'{view.id}:{annotation.id}'
    print(annotation.id, newid, annotation.at_type)


def get_annotations_from_view(view, annotation_type):
    """Return all annotations from a view that match the short name of the
    annotation type."""
    # Note: there is method mmif.View.get_annotations() where you can give
    # at_type as a parameter, but it requires a full match.
    return [a for a in view.annotations
            if a.at_type.shortname == annotation_type]


def find_matching_tokens(tokens, ne):
    matching_tokens = []
    ne_start = ne.properties["start"]
    ne_end = ne.properties["end"]
    start_token = None
    end_token = None
    for token in tokens:
        if token.properties['start'] == ne_start:
            start_token = token
        if token.properties['end'] == ne_end:
            end_token = token
    return start_token, end_token


# Visualization utilities


def get_view_label(view):
    #print(view)
    view_id = view.id.replace('_', '')
    app = Path(view.metadata.app).parts[-2]
    note = f'{len(view.annotations)} annotations'
    return f'{view_id} {app}\n{note}'


def get_label(view: 'mmif.View', annotation: 'mmif.Annotation'):
    at_type = annotation.at_type.shortname
    if at_type == 'VideoDocument':
        identifier = annotation.id.replace('_', '')
        location = Path(annotation.properties.location).name
        return f'{identifier} {at_type}\n{location}'
    view_id = view.id.replace('_', '')
    if at_type == 'TimeFrame':
        if 'start' in annotation.properties and 'end' in annotation.properties:
            start = f'{annotation.properties["start"]}'
            end = f'{annotation.properties["end"]}'
            label = f'{view_id} TF\n{start}-{end}'
        elif 'targets' in annotation.properties:
            start = annotation.properties['targets'][0]
            end = annotation.properties['targets'][-1]
            label = f'{view_id} TF\n{start}-{end}'
        else:
            label = 'NONE'
        ftype = f'{annotation.properties.get("frameType")}'
        return f'{label} {ftype}' if ftype != 'None' else f'{label}'
    elif at_type == 'Token':
        return f'{view_id}\n{annotation.properties.get("text")}'
    elif at_type == 'NamedEntity':
        return f'{view_id} NE\n{annotation.properties.get("text")}'
    elif at_type == 'TextDocument':
        text = annotation.properties.text.value
        if len(text) > 100:
            text = f'{text[:100]}...'
        return f'{view_id} {at_type}\n{text}'
    elif at_type in ('NounChunk', 'Sentence'):
        text = annotation.properties.get('text')
        if len(text) > 15:
            text = f'{text[:15]}...'
        cat = 'NC' if at_type == 'NounChunk' else 'S'
        return f'{view_id} {cat}\n{text}'
    elif at_type == 'BoundingBox':
        return f'{view_id} BB\n{str(annotation.properties.get("timePoint"))}'
    elif at_type == 'SemanticTag':
        return f'{view_id} Tag\n{annotation.properties.get("tagName")}'
    print(annotation, annotation.properties)
    return f'{view_id}\n{annotation.id.replace(":", "_")}'


def get_shape_and_color(annotation_type: str):
    node_format = GRAPH_FORMATTING.get(annotation_type)
    if node_format is None:
        print(f'Warning: no defined shape and color for {annotation_type}, using default')
        node_format = GRAPH_FORMATTING.get(None)
    return node_format
