# Summarizer Notes

Notes on the Graph implementation and the summarizer.


## Scope

The older version really only worked on a small mocked up file with some hand-created annotations including some timeframes, transcripts, entities and tags.

We are pivoting here to using real data from the MMIF Server. Currently (June 2025), that server contains output from the following pipelines:

```
<aapb-pua-kaldi-wrapper v3>
<chyron-detection v1.0>
<clipsearch v1-6-g8e7a0ff>
<dbpedia-spotlight-wrapper 5dad157>
<dbpedia-spotlight-wrapper v1.1>
<distil-whisper-wrapper v1.1>
<east-textdetection v1.1>
<east-textdetection v1.1> ==> <parseqocr-wrapper v1.0>
<east-textdetection v1.1> ==> <tesseractocr-wrapper v1.0>
<gentle-forced-aligner-wrapper v1.0>
<slatedetection v2.0>
<spacy-wrapper v1.1>
<swt-detection v5.0>
<swt-detection v5.1>
<swt-detection v5.1> ==> <doctr-wrapper v1.1>
<swt-detection v5.1> ==> <paddleocr-wrapper becfa66>
<swt-detection v6.0-1-g627f8dd>
<swt-detection v6.0-2-gdea09ae>
<swt-detection v6.1>
<swt-detection v6.1> ==> <doctr-wrapper v1.1>
<swt-detection v6.1> ==> <simple-timepoints-stitcher v3.0>
<swt-detection v6.1> ==> <simple-timepoints-stitcher v3.1>
<whisper-wrapper v3>
<whisper-wrapper v6-3-ge33e60f>
<whisper-wrapper v7>
<whisper-wrapper v8>
<whisper-wrapper v8-3-g737e280>
```

Of those I am now prioritizing the following

```
<chyron-detection v1.0>
<slatedetection v2.0>
<spacy-wrapper v1.1>
<swt-detection v6.1>
<swt-detection v6.1> ==> <doctr-wrapper v1.1>
<swt-detection v6.1> ==> <simple-timepoints-stitcher v3.0>
<swt-detection v6.1> ==> <simple-timepoints-stitcher v3.1>
<whisper-wrapper v8>
<whisper-wrapper v8-3-g737e280>
```

In addition, I am working with an example output file from the Llava captioner, which is using he following pipeline:

```
<swt-detection v7.4> ==> <llava-captioner v1.2-6-gc824c97>
```

The example files are all stored in the `code/examples/pipelines` folder in subdirectories that encode the pipeline name. Various output files are also stored in those subdirectories with suffixes or perhaps in further subdirectories.


## Data Description

Looking at Whisper, Kaldi, SWT, DocTR, Llava-captioner, Chyron detection, Slate detection and spaCy.


### whisper-wrapper-v8

Checked on cpb-aacip-507-154dn40c26.

Contains one VideoDocument d1 in the documents list and two views. One view (v\_1) has user warnings and the other (v\_0) has instances of TextDocument, Token, Sentence, TimeFrame and Alignment.

- TextDocument (1). The identifier is v\_0:td\_1. Aligned with the VideoDocument d1.
- Token (9,375). All aligned with TimeFrames. They all have start and end properties and the local document property always refers to v\_0:td\_1
- Sentence (549). Not aligned. Have a text property and a list of targets, but no start and end.
- TimeFrame (9,375). With frameType (always "speech"), start and end properties.
- Alignment (9,376).

For the **summary** we get all the Sentences with their start and end timepoints and some other goodies.

```json
{
  "start-time": 110860,
  "end-time": 113560,
  "duration": 2700,
  "length": 48,
  "text": "South Africa's currency, The Rant, fell sharply."
}
```

Problem: the Sentences are not Sentences, instead, they are semi-random Spans that cut through sentence boundaries with abandon. Here are the first 10 sentences from the example file (well, skipping the fist which was a long sequence of beeps):

```
 667  702  beep, beep, beep, beep, beep, beep.
 703  708  Sound
 709  754  Good evening. Here are the top news headlines
 755  854  today. Moscow threatened to deploy anti-satellite weapons in space. The farm credit administration,
 855  949  the biggest farm lender, said it needs financial help. South Africa's currency, The Rant, fell
 950 1037  sharply. Delta Airlines is suing the FAA for negligence in the Dallas crash that killed
1038 1128  to 135 people. More details of these stories in a moment. Jim Lehrer is away tonight. Judy
1129 1161  Woodruff is in Washington. Judy?
1162 1248  We focus most of the news hour tonight on AIDS, the disease that is fast becoming this
```

Note that there is no real sentence structure, there are still punctuation characters to work with.

Other Whisper versions that we have data for and that need to be tested:

- whisper-wrapper-v3
- whisper-wrapper-v6-3-ge33e60f
- whisper-wrapper-v7
- whisper-wrapper-v8
- whisper-wrapper-v8-3-g737e280


### aapb-pua-kaldi-wrapper-0.2.X

0.2.2: checked with a shortened file of unknown provenance.<br/>
0.2.3: checked with cpb-aacip-507-028pc2tq55.

The first file has one view with 1 TextDocument, 187 Tokens, 187 TimeFrames and 188 Alignments. The TextDocument is aligned to the VideoDocument and the Tokens are aligned with TimeFrames. These are all pretty much the same as with the Whisper output. The other file has the same structure.

There is no punctuation and there are no Sentence types, so we need to either introcude punctuation or I use a semi-random way of using time signutures of tokens to create sentence-like objects. For now, everythin ends up in one sentence.


### swt-detection-v5.1--doctr-wrapper-v1.1

Checked with: cpb-aacip-526-z60bv7c69m and cpb-aacip-526-z892806c9c.

Using this both for SWT testing and DocTR testing. Note that for SWT I would also like to test on the version that splits off the stitcher in a separate app.


### swt-detection-v7.4--llava-captioner-v1.2-6-gc824c97

Checked with cpb-aacip-225-12z34w2c.

Using this both for SWT/TimeFrames testing and Llava testing

The example file has four views. Three SWT views: one with 30,614 TimePoints, one with 24 TimeFrames and 1 Annotation (with framecount etcetera), and one with a warning. And one Llava captioner view with 24 TextDocuments and 24 Alignments (to TimeFrames). The alignments is really understood to be to the TimePoint that is mentioned in the representative for the TimeFrame.

For the timeframes **summary** we get the basics (at the moment not including the identifier of the representative time points):

```json
{
  "identifier": "v_1:tf_1",
  "label": "chyron",
  "score": 0.40812081484390156,
  "start-time": 34134,
  "end-time": 39273,
  "representatives": [ 38405 ]
}
```
     
For the captions **summary** we grab the time point of the representative and the text:

```json
{
  "identifier": "v_3:td_1",
  "time-point": 38405,
  "text": "\nCHARLES STUBBLEFIELD HAWAII PUNL!"
}
```

The identifier of the TextDocument is also listed here (which we did not do for the transcript), this is an illustration that we can easily do this if it is useful to have a backtrace to the MMIF file.


### spacy-wrapper-v1.1





## Graph



## Summary



## Visualization

