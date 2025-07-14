import sys

from mmif import Mmif
from mmif import Annotation

from graph import Graph, normalize_id


def cut(fname: str, start: int, end: int):

	mmif = Mmif(open(fname).read())
	graph = Graph(mmif)
	print()
	print(graph)
	graph.trim(start, end)
	print(graph)
	exit()

	print()	
	removed = set()
	for view in mmif.views:
		sys.stderr.write(f'{view.id} {view.metadata.app} {len(view.annotations)}\n')
		for annotation in view.annotations:
			normalize_id(view, annotation)
		annotations = []
		for anno in view.annotations:
			if keep(anno, start, end):
				annotations.append(anno)
			else:
				removed.add(anno.id)
		view.annotations = annotations
		sys.stderr.write(f'{view.id} {view.metadata.app} {len(view.annotations)}\n')

	print()	
	for view in mmif.views:
		sys.stderr.write(f'{view.id} {view.metadata.app} {len(view.annotations)}\n')
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
		sys.stderr.write(f'{view.id} {view.metadata.app} {len(view.annotations)}\n')

	with open('new_mmif.json', 'w') as fh:
		fh.write(mmif.serialize(pretty=True))
	graph = Graph(mmif)
	print()
	print(graph)


def keep(annotation: Annotation, start: int, end: int):
	props = annotation.properties
	if 'start' in props and 'end' in props:
		#print(props.get('start'), start, props.get('end'), end)
		return props.get('start') >= start and props.get('end') <= end
	elif 'timePoint' in props:
		return start <= props['timePoint'] <= end 
	else:
		return True


if __name__ == '__main__':

	cut(sys.argv[1], int(sys.argv[2]), int(int(sys.argv[3])))

