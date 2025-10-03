"""Utility methods

"""

import io
from pathlib import Path
from xml.sax.saxutils import quoteattr, escape
from collections import UserList

from summarizer.config import KALDI, WHISPER, CAPTIONER, SEGMENTER
from summarizer.config import TOKEN, ALIGNMENT, TIME_FRAME
from summarizer.config import GRAPH_FORMATTING


def compose_id(view_id, anno_id):
    """Composes the view identifier with the annotation identifier."""
    return anno_id if ':' in anno_id else view_id + ':' + anno_id


def type_name(annotation):
    """Return the short name of the type."""
    return annotation.at_type.split('/')[-1]


def get_transcript_view(views):
    """Return the last Whisper or Kaldi view that is not a warnings view."""
    # TODO: this now has a simplified idea of how to find a view, should at least
    # move towards doing some regular expression matching on the WHISPER config
    # setting. The same holds for other functions to get views.
    for view in reversed(views):
        if view.metadata.app in KALDI + WHISPER:
            if view.metadata.warnings:
                continue
            return view
    return None


def get_captions_view(views):
    """Return the last view created by the Llava captioner."""
    for view in reversed(views):
        if view.metadata.app in CAPTIONER:
            if view.metadata.warnings:
                continue
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


def timestamp(milliseconds: int):
    seconds = milliseconds // 1000
    minutes = seconds // 60
    hours = minutes // 60
    ms = milliseconds % 1000
    s = seconds % 60
    m = minutes % 60
    return f'{m:02d}:{s:02d}'
    #return f'{hours}:{m:02d}:{s:02d}.{ms:03d}'



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
        self.size = n
        self.char = char
        self.data = n * [char]

    def __str__(self):
        return f'<CharacterList [{self.getvalue(0, len(self))}]>'

    def __len__(self):
        return self.size

    def __setitem__(self, key, value):
        try:
            self.data[key] = value
        except IndexError:
            for i in range(len(self), key + 1):
                self.data.append(self.char)
            self.data[key] = value

    def set_chars(self, text: str, start: int, end: int):
        self.data[start:end] = text

    def getvalue(self, start: int, end: int):
        return ''.join(self.data[start:end])


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


def normalize_id(doc_ids: list, view: 'View', annotation: 'Annotation'):
    """Change identifiers to include the view identifier if it wasn't included,
    do nothing otherwise. This applies to the Annotation id, target, source,
    document, targets and representatives properties. Note that timePoint is
    not included because the value is an integer and not an identifier."""
    # TODO: this seems somewhat fragile
    debug = False
    attype = annotation.at_type.shortname
    props = annotation.properties
    if ':' not in annotation.id and view is not None:
        if annotation.id not in doc_ids:
            newid = f'{view.id}:{annotation.id}'
            annotation.properties['id'] = newid
    if 'document' in props:
        doc_id = props['document']
        if ':' not in doc_id and view is not None:
            if doc_id not in doc_ids:
                props['document'] = f'{view.id}:{doc_id}'
    if 'targets' in props:
        new_targets = []
        for target in props['targets']:
            if ':' not in target and view is not None:
                if target not in doc_ids:
                    new_targets.append(f'{view.id}:{target}')
            else:
                new_targets.append(target)
        props['targets'] = new_targets
    if 'representatives' in props:
        new_representatives = []
        for rep in props['representatives']:
            if ':' not in rep and view is not None:
                new_representatives.append(f'{view.id}:{rep}')
            else:
                new_representatives.append(rep)
        props['representatives'] = new_representatives
    if attype == 'Alignment':
        if ':' not in props['source'] and view is not None:
            if props['source'] not in doc_ids:
                props['source'] = f'{view.id}:{props["source"]}'
        if ':' not in props['target'] and view is not None:
            if props['target'] not in doc_ids:
                props['target'] = f'{view.id}:{props["target"]}'
    if debug:
        print('===', annotation)


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
    props = annotation.properties
    if at_type == 'VideoDocument':
        identifier = annotation.id.replace('_', '')
        location = Path(props.location).name
        return f'{identifier} {at_type}\n{location}'
    view_id = view.id.replace('_', '')
    if at_type == 'TimeFrame':
        if 'start' in props and 'end' in props:
            start = f'{props["start"]}'
            end = f'{props["end"]}'
            label = f'{view_id} TF\n{start}-{end}'
        elif 'targets' in props:
            start = props['targets'][0]
            end = props['targets'][-1]
            label = f'{view_id} TF\n{start}-{end}'
        else:
            label = 'NONE'
        ftype = f'{props.get("frameType")}'
        return f'{label} {ftype}' if ftype != 'None' else f'{label}'
    elif at_type == 'Token':
        return f'{view_id} {props.get("start")}:{props.get("end")}\n{props.get("text")}'
    elif at_type == 'NamedEntity':
        return f'{view_id} NE\n{props.get("text")}'
    elif at_type == 'TextDocument':
        text = props.text.value
        if len(text) > 100:
            text = f'{text[:100]}...'
        return f'{view_id} {at_type}\n{text}'
    elif at_type in ('NounChunk', 'Sentence'):
        text = props.get('text')
        if len(text) > 15:
            text = f'{text[:15]}...'
        cat = 'NC' if at_type == 'NounChunk' else 'S'
        return f'{view_id} {cat}\n{text}'
    elif at_type == 'BoundingBox':
        return f'{view_id} BB\n{str(props.get("timePoint"))}'
    elif at_type == 'SemanticTag':
        return f'{view_id} Tag\n{props.get("tagName")}'
    print(annotation, props)
    return f'{view_id}\n{annotation.id.replace(":", "_")}'


def anchor(annotation: 'mmif.Annotation'):
    props = annotation.properties
    if 'start' in props and 'end' in props:
        return f'{props["start"]}-{props["end"]}'
    elif 'timePoint' in props:
        return props["timePoint"]
    else:
        return None
    

def get_shape_and_color(annotation_type: str):
    node_format = GRAPH_FORMATTING.get(annotation_type)
    if node_format is None:
        print(f'Warning: no defined shape and color for {annotation_type}, using default')
        node_format = GRAPH_FORMATTING.get(None)
    return node_format
