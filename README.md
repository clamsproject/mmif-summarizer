# Summarizing MMIF

Code to create a summary of an MMIF file, only keeping those annotations that are useful metadata (and reducing the size of the file by one or two orders of magnitude), and making some implicit relations between annotations and anchors in the source explicit.

See `code/summary.py` for some of the limitations of the code.

This code requries Python 3.8 or higher and two modules:

```bash
$ pip install clams-python==0.5.3
$ pip install beautifulsoup4
```

## Usage

Run the summary code in stand-alone mode on one of the sample input documents: `examples/input-v7.mmif` and `examples/input-v9.mmif`. The first has seven manually created views iews from the following applications: bars-and-tone, slates, audio-segmenter, kaldi, east, tesseract and slate-parser. The second has two views added by the app-spacy-nlp application.

```bash
$ cd code
$ python summary.py examples/input-v7.mmif
```

The output for this should be something like

```xml
<?xml version="1.0" encoding="utf-8"?>
<Summary>
  <Documents>
    <Document type="VideoDocument" location="file:///var/archive/video-002.mp4"/>
  </Documents>
  <Transcript>
    <line>Hello, this is Jim Lehrer with the NewsHour on PBS.</line>
    <line>We have exciting news about the tomato &amp; Florida.</line>
  </Transcript>
  <TimeFrames>
    <TimeFrame start="0" end="2600" frameType="bars-and-tone"/>
    <TimeFrame start="2700" end="5300" frameType="slate"/>
    <TimeFrame start="0" end="5500" frameType="non-speech"/>
    <TimeFrame start="5500" end="22000" frameType="speech"/>
  </Documents>
  <Entities>
  </Entities>
</Summary>
```

The example outputs for both input examples are in the `examples` folder.

To start a Flask server:

```bash
$ python app.py
```

To use the server from curl (do this from a different terminal than the run.py script, but from the directory with this readme file):

```bash
$ curl -X GET http://0.0.0.0:5000/
$ curl --request POST -d@examples/input-v7.mmif http://0.0.0.0:5000/
```

The first gets you the metadata, the second sends off the file `examples/input-v7.mmif` to get summarized.


## Docker

Building the image (use any name of your liking for the tag):

```bash
$ cd code
$ docker build --tag mmif-summarizer .
```

Entering the container and testing the converter:

```bash
$ docker run --rm -it mmif-summarizer bash
$ python summary.py examples/input-v7.mmif
```

In real life, the second prompt will be the container prompt, something like `root@f9deb9a6115f:/app#`.

To run the Flask server in a Docker container:

```bash
$ docker run --rm -d -p 5000:5000 mmif-summarizer
$ curl --request POST -d@examples/input-v7.mmif http://0.0.0.0:5000/
```

