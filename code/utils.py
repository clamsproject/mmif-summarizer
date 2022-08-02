"""util.py

Module with utility methods.

"""

import io
from xml.sax.saxutils import quoteattr, escape


def compose_id(view_id, anno_id):
    """Composes the view identifier with the annotation identifier."""
    return anno_id if ':' in anno_id else view_id + ':' + anno_id


def type_name(annotation):
    """Return the short name of the type."""
    return annotation.at_type.split('/')[-1]


def as_xml(tag, objs, props):
    """Return an XML string for a list of instances of tag."""
    s = io.StringIO()
    s.write('  <%ss>\n' % tag)
    for obj in objs:
        write_tag(s, tag, '    ', obj, props)
    s.write('  </%ss>\n' % tag)
    return s.getvalue()


def write_tag(s, tagname: str, indent: str, obj: dict, props: tuple):
    """Write an XML tag to stringbuffer s. Only properties from obj that are in
    the props tuple are printed."""
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


def get_annotations_from_view(view, annotation_type):
    """Return all annotation from a view that match the annotation type."""
    # TODO: there is probably a method on View for this
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
