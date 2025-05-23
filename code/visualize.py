"""

Visualize the JSON file that was created by the summarizer or visualize a MMIF
file, both the raw MMIF and the Graph created from it.

This visualization is not so much meant for end users, but more for debugging
the graph and summarization code.

Visualize MMIF:

    $ python visualize.py --mmif -i examples/input-v9.mmif -o examples/dot-v9

    Creates files 

        examples/dot-v9.graph
        examples/dot-v9.graph.pdf
        examples/dot-v9.graph.png
        examples/dot-v9.mmif
        examples/dot-v9.mmif.pdf
        examples/dot-v9.mmif.png

Visualize summary:

    $ python visualize.py --summary -i examples/output-v9.json -o examples/dot-v9

    Creates files 

        examples/dot-v9.summary.ents
        examples/dot-v9.summary.ents.pdf
        examples/dot-v9.summary.ents.png
        examples/dot-v9.summary.tags
        examples/dot-v9.summary.tags.pdf
        examples/dot-v9.summary.tags.png
        examples/dot-v9.summary.tfs
        examples/dot-v9.summary.tfs.pdf
        examples/dot-v9.summary.tfs.png
        examples/dot-v9.summary.trans
        examples/dot-v9.summary.trans.pdf
        examples/dot-v9.summary.trans.png
        examples/dot-v9.summary.views
        examples/dot-v9.summary.views.pdf
        examples/dot-v9.summary.views.png

If you use the commands as above you can load the file "examples/dot-v9.html" in
your browser to view the PNG images.

"""

import sys
import json
import pathlib
import collections
import argparse

import graphviz

from mmif import Mmif
from graph import Graph
from utils import get_shape_and_color, get_view_label, get_label


FRAME_TYPES = ['bars-and-tone', 'slate', 'segments']


# Visualizing the MMIF file and the Graph created from it

def visualize_mmif(mmif: Mmif, out: str):
    """Visualize the explicit links in the MMIF file."""
    # TODO: this is not working as it should probably due to lack of
    # standardization in the identifiers, will fix this after taking
    # a good look at the graph and summarizer code.
    dot = graphviz.Digraph(comment=out)
    alignments = []
    for view in mmif.views:
        for anno in view.annotations:
            identifier = f'{view.id} {anno.id}'
            if anno.at_type.shortname == 'Alignment':
                alignments.append((view.id, anno))
            else:
                shape, color = get_shape_and_color(anno.at_type.shortname)
                label = get_label(view, anno)
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
    dot.render(out, format='pdf')
    dot.render(out, format='png')


def visualize_graph(graph: Graph, out: str):
    dot = graphviz.Digraph(comment=out)
    nodes = list(graph.nodes.values())
    for node in nodes:
        node_name = node.identifier.replace(':', '_')
        label = get_label(node.view, node.annotation)
        shape, color = get_shape_and_color(node.at_type.shortname)
        dot.node(node_name, label=label, shape=shape, color=color)
    for node in nodes:
        node_name = node.identifier.replace(':', '_')
        for t in node.targets:
            target_name = t.identifier.replace(':', '_')
            # TODO: this should not depend on a specific identifier
            if (target_name != 'm1'):
                dot.edge(node_name, target_name)
    dot.render(out, format='pdf')
    dot.render(out, format='png')


# Visualizing the summary

def visualize_summary(fname: str, out: str):
    """Visualize the summary in file 'fname' by creating a set of graphs all
    starting with 'out'."""
    summary = json.load(open(fname))
    print(summary.keys())
    _visualize_views(summary.get('views', []), out + '.summary.views')
    _visualize_transcript(summary.get('transcript', []), out + '.summary.trans')
    _visualize_timeframes(summary, out + '.summary.tfs')
    _visualize_tags(summary.get('tags', []), out + '.summary.tags')
    _visualize_entities(summary.get('entities', []), out + '.summary.ents')


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
    dot.render(fname, format='pdf')
    dot.render(fname, format='png')


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
    dot.render(fname, format='pdf')
    dot.render(fname, format='png')


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
    dot.render(fname, format='pdf')
    dot.render(fname, format='png')


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
    dot.render(fname, format='pdf')
    dot.render(fname, format='png')


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
    dot.render(fname, format='pdf')
    dot.render(fname, format='png')


# Utilities

def group_instances(instances: list):
    d = collections.defaultdict(list)
    for instance in instances:
        d[instance['group']].append(instance)
    return d


def create_argument_parser():
    h_mmif = "visualize a MMIF file, both the raw file and the underlying graph"
    h_summary = "visualize the summary of a MMIF file"
    h_input = "input file, either a MMIF file or a summary"
    h_output = "output directory for graphviz files (default='.')"
    parser = argparse.ArgumentParser()
    parser.add_argument('--mmif', action="store_true", help=h_mmif)
    parser.add_argument('--summary', action="store_true", help=h_summary)
    parser.add_argument('-i', metavar='FILE', help=h_input)
    parser.add_argument('-o', metavar='PATH', help=h_output, default='.')
    return parser


def doctr_example(mmif_file: str):
    mmif = Mmif(open(mmif_file).read())
    dot = graphviz.Digraph(comment=mmif_file)
    graph = Graph(mmif)
    print(graph)
    visualize_graph(graph)



if __name__ == '__main__':

    parser = create_argument_parser()
    args = parser.parse_args()
    if not args.mmif and not args.summary:
        print('\nWARNING: you must either use the --mmif or the --summary option\n')
        parser.print_help()
        exit()

    if args.mmif:
        mmif = Mmif(open(args.i).read())
        graph = Graph(mmif)
        print(graph)
        visualize_mmif(mmif, f'{args.o}.mmif')
        visualize_graph(graph, f'{args.o}.graph')

    if args.summary:
        visualize_summary(args.i, args.o)

    #doctr_example(sys.argv[1])


'''

uv run visualize.py --mmif -i examples/input-v9.mmif -o examples/dot-v9
uv run visualize.py --summary -i examples/output-v9.json -o examples/dot-v9

'''
