# Summarizing MMIF

Code to create a summary of an MMIF file, only keeping those annotations that are useful metadata (and reducing the size of the file by one or two orders of magnitude), and making some implicit relations between annotations and anchors in the source explicit.

See `code/summary.py` for some of the limitations of the code.

This code requries Python 3.8 or higher and the clams-python module:

```bash
$ pip install clams-python==0.5.3
```

## Usage

Run the summarizer in stand-alone mode on one of the sample input documents and print an XML summary:

```bash
$ cd code
$ python summary.py examples/input-v7.mmif
```

The output for this should be something like

```json
{
  "mmif_version": "http://mmif.clams.ai/0.4.0",
  "documents": [
    {
      "id": "m1",
      "type": "VideoDocument",
      "location": "file:///var/archive/video-002.mp4"
    }
  ]
}
```

The default is to just print the MMIF version and the list of documents, and ignore all information in the views. You can however print all kinds of other information for which the following options are available:

| option        | description                                                        |
| ------------- | ------------------------------------------------------------------ |
| --views       | print the metadata for all views                                   |
| --transcript  | print the transcript, with alignments if available                 |
| --barsandtone | print the timeframe that was recognized as the bars-and-tone frame |
| --segments    | print the timeframes recognized by the segmenter                   |
| --slate       | print information from the slate timeframe                         |
| --chyrons     | print information from chyrons (lower-thirds)                      |
| --credits     | print information from the credits                                 |
| --entities    | print the entities from the transcript                             |
| --full        | print all data                                                     |

For example:

```bash
$ python summary.py examples/input-v7.mmif --barsandtone
```

```json
{
  "mmif_version": "http://mmif.clams.ai/0.4.0",
  "documents": [
    {
      "id": "m1",
      "type": "VideoDocument",
      "location": "file:///var/archive/video-002.mp4"
    }
  ],
  "bars-and-tone": [
    {
      "id": "v_1:s1",
      "start": 0,
      "end": 2600,
      "frameType": "bars-and-tone"
    }
  ]
}
```

> Not all options are fully implemented yet. In particular: (1) for slates the tool currently only prints the timeframe, not the information contained in it, (2) chyrons and credits are not implmented, and (3) entities are implmented, but need to be revamped. Also missing are some sanity checks that alert the user to overly complicated MMIF input, for example with many layers of the same kind.

If you want XML output (which tends to be a little bit more compact) you can run `json2xml.py` over the output.


### Running a Flask server

To start a Flask server:

```bash
$ python app.py
```

To use the server from curl (do this from a different terminal than the run.py script, but from the directory with this readme file):

```bash
$ curl -X GET http://0.0.0.0:5000/
$ curl --request POST -d@examples/input-v7.mmif http://0.0.0.0:5000/
```

The first gets you the metadata for the summarizer, the second sends off the file `examples/input-v7.mmif` to get summarized. To add options simply add them to the url. For example to print the transcript and the segments you can do

```bash
$ curl --request POST -d@examples/input-v7.mmif 'http://0.0.0.0:5000?segments&transcript'
```

Note that with more than one parameter you need to add quotes around the URL.


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
