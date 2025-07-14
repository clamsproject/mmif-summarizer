"""

"""

import io
import sys
import json
import pathlib

import utils


index_page = 'index.html'
views_page = 'views.html'
timeframes_page = 'timeframes.html'
transcript_page = 'transcripts.html'
captions_page = 'captions.html'
swt_page = 'swt.html'


def create_html(infile: str, outdir: str):
	print(infile, outdir)
	outpath = pathlib.Path(outdir)
	outpath.mkdir(exist_ok=True)
	for f in outpath.glob("*"):
		if f.is_file():
			f.unlink() 
	summary = json.loads(pathlib.Path(infile).open().read())
	page = Html(infile)
	index_html = outpath / index_page
	page.write(f'<p><a href="{views_page}">Views</a></p>\n')
	create_html_views(infile, outpath, summary)
	if 'timeframes' in summary:
		if summary['timeframes']:
			page.write(f'<p><a href="{timeframes_page}">Timeframes</a></p>\n')
		create_html_timeframes(infile, outpath, summary)		
	if 'transcript' in summary:
		if summary['transcript']:
			page.write(f'<p><a href="{transcript_page}">Transcript</a></p>\n')
		create_html_transcript(infile, outpath, summary)
	if 'captions' in summary:
		if summary['captions']:
			page.write(f'<p><a href="{captions_page}">Captions</a></p>\n')
		create_html_captions(infile, outpath, summary)
	index_html.write_text(page.getvalue())


def create_html_views(infile: str, outpath: pathlib.Path, summary: dict):
	views_html = outpath / views_page
	page = Html(infile, 'Views')
	for view in summary['views']:
		page.write('<table border=1 cellspacing=0 cellpadding=8>\n')
		page.write_tr(
			('id', view['id']),
			('app', view['app']),
			('timestamp', view['timestamp']))
		page.write('<tr>\n')
		page.write(f'  <td valign=top>contains</td>\n')
		page.write(f'  <td>\n')
		page.write(f'  <table border=0 cellspacing=4 cellpadding=0>\n')
		for attype in sorted(view['annotation_types']):
			count = view['annotation_types'][attype]
			page.write_tr(
				(attype, '&nbsp;', (count, 'align=right')), indent='  ')
		page.write_tr(
			('TOTAL', '&nbsp;', (view["annotations"], 'align=right')), indent='  ')
		page.write(f'  </table>\n')
		page.write(f'  </td>\n')
		page.write('</tr>\n')
		page.write('</table>\n\n')
		page.write('<p/>\n\n')
	views_html.write_text(page.getvalue())


def create_html_timeframes(infile: str, outpath: pathlib.Path, summary: dict):
	timeframes_html = outpath / timeframes_page
	page = Html(infile, 'Timeframes')
	page.write('<table border=1 cellspacing=0 cellpadding=8>\n')
	page.write_tr(('t1', 't2', 'reps', 'label', 'score'))
	for tf in summary['timeframes']:
		t1 = utils.timestamp(tf['start-time'])
		t2 = utils.timestamp(tf['end-time'])
		reps = [utils.timestamp(rep) for rep in tf['representatives']]
		score = '' if tf['score'] is None else f'{tf["score"]:06.4f}'
		page.write_tr(
			(t1, t2, ' '.join(reps), tf['label'], score))
	page.write('</table>\n')
	timeframes_html.write_text(page.getvalue())


def create_html_transcript(infile: str, outpath: pathlib.Path, summary: dict):
	transcript_html = outpath / transcript_page
	page = Html(infile, 'Transcript')
	page.write('<table border=1 cellspacing=0 cellpadding=8>\n')
	for sentence in summary['transcript']:
		t1 = utils.timestamp(sentence['start-time'])
		t2 = utils.timestamp(sentence['end-time'])
		td1 = f'  <td valign=top align=right>{t1}</td>\n'
		td2 = f'  <td valign=top align=right>{t2}</td>\n'
		td3 = f'  <td>{sentence["text"]}</td>\n'
		page.write('<tr>\n')
		page.write(td1 + td2 + td3)
		page.write('</tr>\n')
	page.write('</table>\n')
	transcript_html.write_text(page.getvalue())


def create_html_captions(infile: str, outpath: pathlib.Path, summary: dict):
	transcript_html = outpath / captions_page
	page = Html(infile, 'Captions')
	page.write('<table border=1 cellspacing=0 cellpadding=8>\n')
	for caption in summary['captions']:
		text = caption['text'].replace('\n', '<br/>')
		tp = utils.timestamp(caption['time-point'])
		td1 = f'  <td valign=top align=right>{tp}</td>\n'
		td2 = f'  <td valign=top>{caption["identifier"]}</td>\n'
		td3 = f'  <td><pre>{text}</pre></td>\n'
		page.write('<tr>\n')
		page.write(td1 + td2 + td3)
		page.write('</tr>\n')
	page.write('</table>\n')
	transcript_html.write_text(page.getvalue())
	


class Html:

	def __init__(self, infile: str, header: str = None):
		self.stream = io.StringIO()
		self.stream.write(f'<h2>{pathlib.Path(infile).stem}</h2>\n\n')
		if header is not None:
			self.stream.write(f'<h3>{header}</h3>\n\n')
		self.views = []
		self.captions = []

	def write(self, text: str):
		self.stream.write(text)

	def write_tr(self, *table_cells, indent=''):
		for cells in table_cells:
			self.stream.write(f'{indent}<tr>\n')
			for cell in cells:
				if isinstance(cell, tuple):
					val, attrs = cell
					self.stream.write(f'{indent}  <td {attrs}>{val}</td>\n')
				else:
					self.stream.write(f'{indent}  <td>{cell}</td>\n')
			self.stream.write(f'{indent}</tr>\n')

	def getvalue(self):
		return self.stream.getvalue()


if __name__ == '__main__':

	infile, outdir = sys.argv[1:3]
	create_html(infile, outdir)