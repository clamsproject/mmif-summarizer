"""

Create a smaller version of the MMIF storage archive.

$ python select.py ARCHIVE_DIR OUTPUT_DIR COUNT

Creates OUTPUT_DIR from ARCHIVE_DIR, but for each directory the number of MMIF
files is restricted to COUNT. Selection of files is ransom.

Example:

$ python scripts/select.py \
	/Users/Shared/data/clams/mmif/mmif-storage \
	/Users/Shared/data/clams/mmif/mmif-storage-shrunk \
	5

"""


import os
import sys
import random
import pathlib


def	select(indir: str, outdir: str, count: int):
	inpath = pathlib.Path(indir)
	outpath = pathlib.Path(outdir)
	print(inpath, inpath.parent)
	print(outpath, outpath.parent)
	for root, dirs, files in os.walk(inpath):
		# NOTE: doing the length test because I found a file named ".mmif" in
		# whisper-wrapper/v6-3-ge33e60f/d41d8cd98f00b204e9800998ecf8427e/
		files = [f for f in files if f.endswith('.mmif') and len(f) > 5]
		random.shuffle(files)
		files = files[:count]
		print(root)
		for f in files:
			source = pathlib.Path(root) / f
			common_path = os.path.commonpath([inpath, source])
			rel_path = os.path.relpath(source, start=common_path)
			target = outpath / rel_path
			print('   ', rel_path)
			target.parent.mkdir(exist_ok=True, parents=True)
			target.write_text(source.read_text())

		continue
		random.shuffle(files)
		files = [f for f in files if f.endswith('.mmif')]
		files = files[:count]
		target_root = os.sep.join(root.parts[1:])
		for d in dirs:
			dp = outpath / target_root / d
			dp.mkdir(exist_ok=True, parents=True)
		for f in files:
			fp_in = pathlib.Path(root) / f
			fp_out = outpath / os.sep.join(root.parts[1:]) / f
			fp_out.write_text(fp_in.read_text())
			print(fp_out)


if __name__ == '__main__':

	indir, outdir, count = sys.argv[1:4]
	select(indir, outdir, int(count))