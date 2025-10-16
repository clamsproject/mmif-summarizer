"""

Experiments to get to code that trims a MMIF file by removing all annotations that
ultimately occur outside a given time range.

$ uv run cut.py smolvlm2_fresh_output.mmif 1883016 2658025
$ uv run cut.py smolvlm2_fresh_output.trimmed.mmif 1883016 1900000

It reads the MMIF file and creates an instance of summarizer.graph.Graph  from it,
which is then trimmed. Finally, a new MMIF file is created using just the nodes in
the graph that were not trimmed. Note that this new MMIF file will include a new
disclaimer in th etop-level metadata that the contents do not reflect anymore the 
results of the processing pipeline from the view metadata.

"""

import sys

from mmif import Mmif
from mmif import Annotation

from summarizer.graph import Graph, normalize_id


def cut(fname: str, start: int, end: int):

    mmif = Mmif(open(fname).read())
    graph = Graph(mmif)
    
    print_nodes(graph.nodes.values(), skip_timepoints=True)
    
    #print(); graph.pp(skip_timepoints=True)
    print(); graph.pp_statistics()
    
    


    exit()

    removed = set()
    for view in mmif.views:
        app = view.metadata.app
        annos_t0 = len(view.annotations)
        for annotation in view.annotations:
            normalize_id([], view, annotation)
        annotations = []
        for anno in view.annotations:
            if keep(anno, start, end):
                annotations.append(anno)
            else:
                removed.add(anno.id)
        view.annotations = annotations
        annos_t1 = len(view.annotations)
        sys.stderr.write(f'{view.id} {app} ::  {annos_t0:>4} -> {annos_t1:>4}\n')

    for view in mmif.views:
        app = view.metadata.app
        annos_t0 = len(view.annotations)
        annotations = []
        for anno in view.annotations:
            remove = False
            if 'targets' in anno.properties:
                for target in anno.properties['targets']:
                    if target in removed:
                        remove = True
            if 'source' in anno.properties:
                if anno.properties['source'] in removed:
                    remove = True
            if 'target' in anno.properties:
                if anno.properties['target'] in removed:
                    remove = True
            if remove:
                removed.add(anno.id)
            else:
                annotations.append(anno)
            view.annotations = annotations
        annos_t1 = len(view.annotations)
        sys.stderr.write(f'{view.id} {app} ::  {annos_t0:>4} -> {annos_t1:>4}\n')

    with open('out-trimmed.json', 'w') as fh:
        fh.write(mmif.serialize(pretty=True))
    #graph = Graph(mmif)
    #print()
    #print(graph)


def keep(annotation: Annotation, start: int, end: int):
    props = annotation.properties
    if 'start' in props and 'end' in props:
        #print(props.get('start'), start, props.get('end'), end)
        return props.get('start') >= start and props.get('end') <= end
    elif 'timePoint' in props:
        return start <= props['timePoint'] <= end 
    else:
        return True


def print_nodes(nodes: list, skip_timepoints=False):
    for node in nodes:
        if node.at_type.shortname == 'TimePoint':
            continue
        print(f'\n{node.at_type.shortname} {node.identifier}')
        for t in node.targets:
            print('    T', t)
        for key in node.anchors:
            val = node.anchors[key]
            if isinstance(val, list):
                val = ' '.join([str(x) for x in val])
            else:
                val = str(val)
            print(f'    A {key:12}  ==>  {val[:100]}')
    

if __name__ == '__main__':

    cut(sys.argv[1], int(sys.argv[2]), int(int(sys.argv[3])))

