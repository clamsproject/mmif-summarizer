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

TODO: the file "examples/dot-v9.html" should be created from a template

"""

import sys
import json
import pathlib
import collections
import argparse
from pathlib import Path

import graphviz

from mmif import Mmif
from summarizer.graph import Graph
#from summarizer.utils import get_shape_and_color, get_view_label, get_label


PRINT_WARNINGS = False

FRAME_TYPES = ['bars-and-tone', 'slate', 'segments']

# Shape and color settings for the nodes
GRAPH_FORMATTING = {
    'VideoDocument': ('component', 'black'),
    'TextDocument': ('component', 'darkblue'),
    'Annotation': ('component', 'darkgreen'),
    'BoundingBox': ('box', 'darkgreen'),
    'Token': ('note', 'darkblue'),
    'Sentence': ('note', 'darkblue'),
    'NounChunk': ('note', 'darkblue'),
    'TimeFrame': ('oval', 'darkred'),
    'TimePoint': ('box', 'darkred'),
    'SemanticTag': ('note', 'darkorange'),
    'NamedEntity': ('note', 'darkorange'),
    None: ('Msquare', 'black')
}


class MmifVisualizer:

    def __init__(self, mmif: Mmif, out: str):
        self.mmif = mmif
        self.out = out
        self.dot = graphviz.Digraph(comment=out)
        self.alignments = []
        self.target_links = []
        self._add_nodes()
        self._add_target_edges()
        self._add_alignments()

    def _add_nodes(self):
        """Add nodes to the graph, but skip alignment nodes for now."""
        for view in self.mmif.views:
            for anno in view.annotations:
                at_type = anno.at_type.shortname
                identifier = anno.id if ':' in anno.id else f'{view.id}:{anno.id}'
                # colons in dot identifiers indicate ports
                dot_identifier = identifier.replace(':', ' ')
                if at_type == 'Alignment':
                    self.alignments.append((view.id, anno))
                else:
                    shape, color = get_shape_and_color(anno.at_type.shortname)
                    label = get_label(view, anno)
                    label_tmp = label.replace("\n", " ")
                    #print(f'>>> {identifier} [{label_tmp}]')
                    self.dot.node(dot_identifier, shape=shape, color=color, label=label)
                    if 'targets' in anno.properties:
                        for target in anno.properties['targets']:
                            self.target_links.append((dot_identifier, target.replace(':', ' ')))

    def _add_target_edges(self):
        for source, target in self.target_links:
            self.dot.edge(source, target)

    def _add_alignments(self):
        for view_id, alignment in self.alignments:
            identifier = alignment.id
            dot_identifier = alignment.id.replace(':', ' ')
            source = alignment.properties['source'].replace(':', ' ')
            target = alignment.properties['target'].replace(':', ' ')
            self.dot.node(dot_identifier, shape='diamond', label=identifier)
            self.dot.edge(dot_identifier, source, label='s')
            self.dot.edge(dot_identifier, target, label='t')

    def write(self):
        self.dot.render(self.out, format='pdf')
        self.dot.render(self.out, format='png')



def visualize_graph(graph: Graph, out: str):
    dot = graphviz.Digraph(comment=out)
    nodes = list(graph.nodes.values())
    for node in nodes:
        node_name = node.identifier.replace(':', '_')
        label = get_label(node.view, node.annotation)
        shape, color = get_shape_and_color(node.at_type.shortname)
        style = 'bold' if node.view is None else None
        dot.node(node_name, label=label, shape=shape, color=color, style=style)
    for node in nodes:
        node_name = node.identifier.replace(':', '_')
        for t in node.targets:
            target_name = t.identifier.replace(':', '_')
            # TODO: this should not depend on a specific identifier
            if (target_name != 'm1'):
                dot.edge(node_name, target_name)
    dot.render(out, format='pdf')
    dot.render(out, format='png')


def visualize_summary(fname: str, out: str):
    """Visualize the summary in file 'fname' by creating a set of graphs all
    starting with 'out'."""
    summary = json.load(open(fname))
    #print(summary.keys())
    _visualize_views(summary.get('views', []), out + '.summary.views')
    #_visualize_transcript(summary.get('transcript', []), out + '.summary.trans')
    _visualize_timeframes(summary, out + '.summary.tfs')
    _visualize_tags(summary.get('tags', []), out + '.summary.tags')
    _visualize_entities(summary.get('entities', []), out + '.summary.ents')
    _visualize_caption(summary.get('captions', []), out + '.summary.caps')


def _visualize_views(views: list, fname: str):
    dot = graphviz.Digraph(comment=fname)
    dot.node('views', shape='cylinder')
    for view in views:
        view_id = view['id'].replace('_', '')
        print(view)
        app = pathlib.Path(view['app']).parts[-2]
        #app = pathlib.Path(view['metadata']['app']).parts[-2]
        view_label = f'{view_id} {app}\n{view["annotations"]} annotations'
        print('>>>', app, view_label)
        dot.node(view_label, shape='box')
        dot.edge('views', view_label)
    print(f'Writing {fname}')
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
    print(f'Writing {fname}')
    dot.render(fname, format='pdf')
    dot.render(fname, format='png')


def _visualize_timeframes(summary: dict, fname: str):
    dot = graphviz.Digraph(comment=fname)
    for frame_type in FRAME_TYPES:
        dot.node(frame_type, shape='cylinder')
        #print(summary)
        for tf in summary[frame_type]:
            identifier = tf['id'].replace(':', '|')
            label = f'{tf["frameType"]}\n{tf["start"]}-{tf["end"]} '
            dot.node(identifier, label=f'{label}', color="darkred")
            dot.edge(frame_type, identifier)
    print(f'Writing {fname}')
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
    print(f'Writing {fname}')
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
    print(f'Writing {fname}')
    dot.render(fname, format='pdf')
    dot.render(fname, format='png')



t = '''<<table cellspacing="0" cellpadding="5" border="0">
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

def _visualize_caption(captions: list, fname: str):
    dot = graphviz.Digraph(comment=fname)
    dot.node('Captions', shape='cylinder')
    tab = '''<<table cellspacing="0" cellpadding="5" border="0">\n'''
    for _, p1, p2, text in captions:
        h, m, s, ms = convert_milliseconds(p1)
        timestamp = f'{m:02d}:{s:02d}.{ms:04d}'
        timestamp = f'{m:02d}:{s:02d}'
        s = f'<tr>\n  <td align="right">{timestamp}</td>\n  <td align="right">chyron</td>\n  <td align="left">{text}</td>\n</tr>\n'
        s = s.strip().strip("`")
        tab = tab + s
        dot.node(f'text-{p1}-{p2}', label=f'{text.strip()}', shape='box', color='darkblue')
        dot.node(f'tf-{p1}-{p2}', label=f'chyron\n{timestamp}', shape='oval', color='darkred')
        #dot.node(f'tf-{p1}-{p2}', label=f'chyron\n{p1}-{p2}', shape='oval', color='darkred')
        dot.edge('Captions', f'text-{p1}-{p2}')
        dot.edge(f'text-{p1}-{p2}', f'tf-{p1}-{p2}')
    tab = tab + '\n</table>>'
    print(f'Writing {fname}')
    dot.render(fname, format='pdf')
    dot.render(fname, format='png')



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
    # Documents
    if at_type == 'VideoDocument':
        location = Path(props.location).name
        return f'{annotation.id} {at_type}\n{location}'
    elif at_type == 'TextDocument':
        text = props.text.value
        if len(text) > 100:
            text = f'{text[:100]}...'
        return f'{annotation.id}\n{text}'
    # Time points and time frames
    elif at_type == 'TimePoint':
        return f'{annotation.id}\n{props["timePoint"]}'
    elif at_type == 'TimeFrame':
        if 'start' in props and 'end' in props:
            label = f'{annotation.id}\n{props["start"]}-{props["end"]}'
        elif 'targets' in props:
            label = f'{annotation.id}' #TF\n{props["targets"][0]}-{props["targets"][-1]}'
        else:
            label = 'NONE'
        ftype = f'{props.get("frameType")}'
        return f'{label} {ftype}' if ftype != 'None' else f'{label}'
    # Image elements
    elif at_type == 'BoundingBox':
        return f'{view.id} BB\n{str(props.get("timePoint"))}'
    # Linguistic entities
    elif at_type == 'Token':
        return f'{view.id} {props.get("start")}:{props.get("end")}\n{props.get("text")}'
    elif at_type == 'NamedEntity':
        return f'{view.id} NE\n{props.get("text")}'
    elif at_type in ('NounChunk', 'Sentence'):
        text = props.get('text')
        if len(text) > 15:
            text = f'{text[:15]}...'
        cat = 'NC' if at_type == 'NounChunk' else 'S'
        return f'{view.id} {cat}\n{text}'
    # Other
    elif at_type == 'Annotation':
        props_string = '\n'.join([f'{k} = {v}' for k, v in props.items()])
        return f'{annotation.id}\n\n{props_string}'
    #print(annotation, props)
    return f'{view.id}\n{annotation.id}'


def XXXanchor(annotation: 'mmif.Annotation'):
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
        if PRINT_WARNINGS:
            print(f'Warning: no defined shape and color for {annotation_type}, using default')
        node_format = GRAPH_FORMATTING.get(None)
    return node_format


# Other Utilities


def convert_milliseconds(t: int):
    milliseconds = int(t) % 1000
    seconds = int(t/1000) % 60
    minutes = int(t/(1000 * 60)) % 60
    hours = int(t/(1000 * 60 * 60)) %24
    return hours, minutes, seconds, milliseconds


def group_instances(instances: list):
    d = collections.defaultdict(list)
    for instance in instances:
        d[instance['group']].append(instance)
    return d


def create_argument_parser():
    h_mmif = "visualize a MMIF file"
    h_graph = "visualize the underlying graph of a MMIF file"
    h_summary = "visualize the JSON summary previously created from a MMIF file"
    h_input = "input file, either a MMIF file or a summary"
    h_output = "output directory for graphviz files (default='.')"
    parser = argparse.ArgumentParser()
    parser.add_argument('--mmif', action="store_true", help=h_mmif)
    parser.add_argument('--graph', action="store_true", help=h_graph)
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
    if not args.mmif and not args.graph and not args.summary:
        print('\nWARNING: you must use one of the --mmif, --graph or --summary options\n')
        parser.print_help()
        exit()

    if args.graph or args.mmif:
        print(f'>>> Opening MMIF file "{args.i}"')
        mmif = Mmif(open(args.i).read())
        if args.mmif:
            print(f'>>> Creating mmif visualization in "{args.o}.mmif.*"')
            MmifVisualizer(mmif, f'{args.o}.mmif').write()
        if args.graph:
            print(f'>>> Creating graph visualization in "{args.o}.graph.*"')
            graph = Graph(mmif)
            visualize_graph(graph, f'{args.o}.graph')

    if args.summary:
        visualize_summary(args.i, args.o)

    #doctr_example(sys.argv[1])


'''

uv run visualize.py --mmif -i examples/input-v9.mmif -o examples/dot-v9
uv run visualize.py --summary -i examples/output-v9.json -o examples/dot-v9

'''
