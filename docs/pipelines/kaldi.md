## Kaldi pipeline

### aapb-pua-kaldi-wrapper-0.2.X

0.2.2: checked with a shortened file of unknown provenance.<br/>
0.2.3: checked with cpb-aacip-507-028pc2tq55.

The first file has one view with 1 TextDocument, 187 Tokens, 187 TimeFrames and 188 Alignments. The TextDocument is aligned to the VideoDocument and the Tokens are aligned with TimeFrames. These is all pretty much the same as with [Whisper](whisper.md) except that there are no Sentence type annotations. The second file has the same structure.

<img src="images/kaldi.png" height=140>

There is no punctuation and there are no Sentence types, so we need to either introduce punctuation or I use a semi-random way of using time signutures of tokens to create sentence-like objects. For now, everything ends up in one sentence.
