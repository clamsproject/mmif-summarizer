"""

Visualize the JSON file that was created by the summarizer or visualize a raw
MMIF file, only printing explicit links between annotations.

Visualize summary:

    $ python visualize.py -s examples/output-v9.json examples/dot-v9

    This creates a couple of files, all starting with examples/dot-v9

Visualize MMIF:

    $ python visualize.py -m examples/input-v9.mmif examples/dot-v9-0-mmif

"""

import sys
import json
import pathlib
import collections

import graphviz
from mmif import Mmif
from utils import get_shape_and_color


FORMAT = 'png'

FRAME_TYPES = ['bars-and-tone', 'slate', 'segments']


def visualize_summary(fname: str, basename: str):
    """Visualize the summary in file 'fname' by creating a set of graphs all
    starting with 'basename'."""
    summary = json.load(open(fname))
    print(summary.keys())
    _visualize_views(summary.get('views', []), basename + '.summary.views')
    _visualize_transcript(summary.get('transcript', []), basename + '.summary.trans')
    _visualize_timeframes(summary, basename + '.summary.tfs')
    _visualize_tags(summary.get('tags', []), basename + '.summary.tags')
    _visualize_entities(summary.get('entities', []), basename + '.summary.ents')


def _visualize_views(views: list, fname: str):
    dot = graphviz.Digraph(comment=fname)
    dot.node('views', shape='cylinder')
    for view in views:
        view_id = view['id'].replace('_', '')
        app = pathlib.Path(view['app']).parts[-2]
        view_label = f'{view_id} {app}\n{view["annotations"]} annotations'
        dot.node(view_label, shape='box')
        dot.edge('views', view_label)
    print(f'Wrinting {fname}')
    dot.render(fname, format=FORMAT)


def _visualize_transcript(transcript: list, fname):
    dot = graphviz.Digraph(comment=fname)
    dot.node('transcript', shape='cylinder')
    # TODO: this is a total hack just for the demo, delete afterwards
    dot.node(f'transcript-text', label=table, shape="box", color='darkblue')
    dot.edge('transcript', 'transcript-text')
    if False:
        # TODO: this should replace the above, but only once we have set up the input
        # mmif properly
        for n, (line, p1, p2) in enumerate(transcript):
            dot.node(f'line-s{n}', label=f'S{n}\n{line}', shape='box', color='darkblue')
            dot.node(f'pos-s{n}', label=f'{p1}-{p2}', color='darkred')
            dot.edge('transcript', f'line-s{n}')
            dot.edge(f'line-s{n}', f'pos-s{n}')
    print(f'Wrinting {fname}')
    dot.render(fname, format=FORMAT)


table = '''<<table cellspacing="0" cellpadding="5" border="0">
<tr>
  <td>s1</td>
  <td align="right">5500</td>
  <td align="right">11467</td>
  <td align="left">
    Hello, this is Jim Lehrer with the NewsHour on PBS.
  </td>
</tr>
<tr>
  <td>s2</td>
  <td align="right">12380</td>
  <td align="right">22098</td>
  <td align="left">
    Today, we are talking about the increasing problem with barking dogs in New York.
  </td>
</tr>
</table>>
'''


def _visualize_timeframes(summary: dict, fname: str):
    dot = graphviz.Digraph(comment=fname)
    for frame_type in FRAME_TYPES:
        dot.node(frame_type, shape='cylinder')
        for tf in summary[frame_type]:
            identifier = tf['id'].replace(':', '|')
            label = f'{tf["frameType"]}\n{tf["start"]}-{tf["end"]} '
            dot.node(identifier, label=f'{label}', color="darkred")
            dot.edge(frame_type, identifier)
    print(f'Wrinting {fname}')
    dot.render(fname, format=FORMAT)


def _visualize_tags(tags: list, fname: str):
    # TODO: totally in progress, it is now a bit of a hack that may only work for
    # the example bundled with the code (input-v9.mmif)
    dot = graphviz.Digraph(comment=fname)
    dot.node('Tags', shape='cylinder')
    for tag in tags:
        tag_name = tag['tag']
        tag_text = tag['text']
        dot.node(tag_name, color='darkorange')
        dot.edge('Tags', tag_name)
        dot.node(tag_text)
        dot.edge(tag_name, tag_text)
        dot.node(tag_name + 'bb', label='3500', color='darkgreen', shape='box')
        dot.edge(tag_text, tag_name + 'bb')
    print(f'Wrinting {fname}')
    dot.render(fname, format=FORMAT)


def _visualize_entities(entities: list, fname: str):
    # TODO: totally in progress, it is now a total hack that only works for one of 
    # the examples bundled with the code (input-v7.mmif)
    dot = graphviz.Digraph(comment=fname)
    dot.node('Entities', shape='cylinder')
    for entity in entities:
        etext = entity['text']
        #print(etext)
        dot.node(etext, color='darkorange', shape='note')
        dot.edge('Entities', etext)
        groups = group_instances(entity['instances'])
        for group in groups:
            group_id = f'{etext}{group}'
            group_name = str(group)
            group_name = ''
            tps = [str(instance['video-start']) for instance in groups[group]]
            if len(tps) == 1:
                label = str(tps[0])
            else:
                label = f'{tps[0]}-{tps[-1]}'
            dot.node(group_id, label=label, color='darkred')
            dot.edge(etext, group_id)
    print(f'Wrinting {fname}')
    dot.render(fname, format=FORMAT)


def group_instances(instances: list):
    d = collections.defaultdict(list)
    for instance in instances:
        d[instance['group']].append(instance)
    return d


def visualize_mmif(mmif_file: str, image_file: str):
    """Visualize the explicit links in the MMIF file."""
    # TODO: this is not working as it should probably due to lack of
    # standardization in the identifiers, will fix this after taking
    # a good look at the graph and summarizer code.
    mmif = Mmif(open(mmif_file).read())
    dot = graphviz.Digraph(comment=mmif_file)
    alignments = []
    for view in mmif.views:
        for anno in view.annotations:
            identifier = f'{view.id} {anno.id}'
            if anno.at_type.shortname == 'Alignment':
                alignments.append((view.id, anno))
            else:
                shape, color = get_shape_and_color(anno.at_type.shortname)
                label = f'{view.id.replace("_","")} {get_label(anno)}'
                dot.node(identifier, shape=shape, color=color, label=label)
    for view_id, alignment in alignments:
        identifier = f'{view_id} {alignment.id}'
        source = alignment.properties['source'].replace(':', ' ')
        target = alignment.properties['target']
        if ' ' not in source:
            source = f'{view_id} {source}'
        if ' ' not in target:
            target = f'{view_id} {target}'
        dot.node(identifier, shape='diamond')
        dot.edge(identifier, source)
        dot.edge(identifier, target)
    dot.render(image_file, format=FORMAT)


def get_label(anno):
    # This is slightly different from the one in utils since that one works
    # on a Node instead of on an Annotation.
    identifier = anno.id.replace(':', ' ')
    at_type = anno.at_type.shortname
    if at_type == 'VideoDocument':
        identifier = anno.identifier.replace('_', '')
        location = Path(anno.properties['location']).name
        return f'{identifier} {at_type}\n{location}'
    if at_type == 'TimeFrame':
        start = f'{anno.properties["start"]}'
        ftype = f'{anno.properties.get("frameType")}'
        return f'{identifier}\n{start} {ftype}' if ftype != 'None' else f'{identifier}\n{start}'
    elif at_type == 'Token':
        return f'{identifier}\n{anno.properties.get("text")}'
    elif at_type == 'NamedEntity':
        return f'{identifier}\n[{anno.properties.get("text")}]'
    elif at_type == 'TextDocument':
        text = anno.properties.get('text').value
        if len(text) > 10:
            text = f'{text[:10]}...'
        return f'{identifier} {at_type}\n{text}'
    elif at_type in ('NounChunk', 'Sentence'):
        text = anno.properties.get('text')
        if len(text) > 15:
            text = f'{text[:15]}...'
        cat = 'NC' if at_type == 'NounChunk' else 'S'
        return f'{identifier} {cat}\n{text}'
    elif at_type == 'BoundingBox':
        return f'{identifier}\n{str(anno.properties.get("timePoint"))}'
    elif at_type == 'SemanticTag':
        return f'{identifier} Tag\n{anno.properties.get("tagName")}'
    return f'{identifier}\n{anno.identifier.replace(":", "_")}'


if __name__ == '__main__':

    if sys.argv[1] == '-s':
        visualize_summary(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == '-m':
        visualize_mmif(sys.argv[2], sys.argv[3])


'''
uv run visualize.py -s examples/output-v7.json
uv run visualize.py -m examples/input-v7.mmif
'''