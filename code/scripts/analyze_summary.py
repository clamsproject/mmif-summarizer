import json, pathlib

mmif_storage = pathlib.Path('/Users/Shared/data/clams/mmif-storage')
whisper_directory = mmif_storage / 'whisper-wrapper/v8/d3253407b97d29df1cfa2ece903c613e'

sentence_lengths = {}


def print_sentence_lengths(lengths: dict):
	for fname in sorted(lengths):
		print(f'{fname}   {lengths[fname][0]:5d}', end='')
		print(f'   {" ".join([f"{a:5d}" for a in lengths[fname][1]])}')


for f in whisper_directory.iterdir():
	if f.is_file() and f.name.endswith('.json'):
		sentence_lengths[f.name] = [None, []]
		summary = json.load(f.open())
		durations = [d['duration'] for d in summary['transcript']]
		sentence_lengths[f.name][0] = sum(durations) // len(durations)
		n = 25
		for i in range(0, len(durations), n):
			sub_durations = durations[i:i+n]
			average = sum(sub_durations) // n
			sentence_lengths[f.name][1].append(average)

print()

print_sentence_lengths(sentence_lengths)

