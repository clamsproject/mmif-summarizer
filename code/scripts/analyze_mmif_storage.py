import pathlib

mmif_storage_list = 'mmif-storage.find.txt'

pipelines = set()

with open(mmif_storage_list) as fh:
	for line in fh:
		path = pathlib.Path(line.strip())
		filtered_path = []
		for part in path.parts[6:]:
			if part[-5:] == '.mmif':
				continue
			if part[-5:] == '.json':
				part = part[:-5]
			filtered_path.append(part)
		if filtered_path and len(filtered_path) % 3 == 0:
			pipelines.add(tuple(filtered_path))


filtered_pipelines = set()
for pipeline in pipelines:
	#print(pipeline)
	pairs = tuple(zip(pipeline[::3], pipeline[1::3]))
	filtered_pipelines.add(pairs)


for filtered_pipeline in sorted(filtered_pipelines):
	print(' ==> '.join([f'<{x} {y}>' for x, y in filtered_pipeline]))
