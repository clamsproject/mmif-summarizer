"""util.py

Module with utility methods.

"""


def matches(at_type, type_name):
    """Return True if the @type matches the short name."""
    return at_type == type_name or at_type.endswith('/' + type_name)


def compose_id(view_id, anno_id):
    """Composes the view identifier with the annotation identifier."""
    return anno_id if ':' in anno_id else view_id + ':' + anno_id


def type_name(annotation):
    """Return the short name of the type."""
    return annotation.at_type.split('/')[-1]    


def get_annotations_from_view(view, annotation_type):
    """Return all annotation from a view that match the annotation type."""
    # TODO: there is probably a method on View for this
    return [a for a in view.annotations if matches(a.at_type, annotation_type)]


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
