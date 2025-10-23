import mmif
import cut

fname = 'examples/pipelines/swt-detection-v5.1/cpb-aacip-526-z60bv7c69m.start.mmif'
fname = 'examples/pipelines/swt-detection-v5.1/cpb-aacip-526-z60bv7c69m.start.minimal.mmif'
start = 0
end = 40000
end = 12000


## Using the mmif utility

print('>>> OPENING MMIF FILE')
mmif_obj = mmif.Mmif(open(fname).read())

print('>>> GETTING ANNOTATIONS')
annotations = mmif_obj.get_annotations_between_time(start, end)

print('>>> WRITING ANNOTATIONS')
for annotation in annotations:
	#continue
	#if annotation.at_type.shortname == 'TimeFrame':
	print(annotation.id, annotation.at_type)


# Using cut
#cut.main(fname, start, end)

