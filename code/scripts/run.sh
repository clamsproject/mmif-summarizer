## Command line invocation examples
## ======================================================================================

## Pretty useless if you do not have those files locally.


## Whisper output
## --------------------------------------------------------------------------------------

# v8 file

python run_summarizer.py --full \
    -i examples/pipelines/whisper-v8/cpb-aacip-507-154dn40c26.mmif \
    -o examples/pipelines/whisper-v8/cpb-aacip-507-154dn40c26.json 

python run_inspector.py \
    -i examples/pipelines/whisper-v8/cpb-aacip-507-154dn40c26.json \
    -o examples/pipelines/whisper-v8/pages

# v8 smaller file

python run_summarizer.py --full \
    -i examples/pipelines/whisper-v8/cpb-aacip-507-154dn40c26.start.mmif \
    -o examples/pipelines/whisper-v8/cpb-aacip-507-154dn40c26.start.bis.json 

python run_inspector.py \
    -i examples/pipelines/whisper-v8/cpb-aacip-507-154dn40c26.start.bis.json \
    -o examples/pipelines/whisper-v8/pages-start-bis

# v8-3-g737e280 file

python run_summarizer.py --full \
    -i examples/pipelines/whisper-v8-3-g737e280/cpb-aacip-507-154dn40c26.mmif \
    -o examples/pipelines/whisper-v8-3-g737e280/cpb-aacip-507-154dn40c26.json 

python run_inspector.py \
    -i examples/pipelines/whisper-v8-3-g737e280/cpb-aacip-507-154dn40c26.json \
    -o examples/pipelines/whisper-v8-3-g737e280/pages

python run_summarizer.py --full \
    -i examples/pipelines/whisper-v8-3-g737e280/cpb-aacip-507-154dn40c26.start.mmif \
    -o examples/pipelines/whisper-v8-3-g737e280/cpb-aacip-507-154dn40c26.start.json 

python run_inspector.py \
    -i examples/pipelines/whisper-v8-3-g737e280/cpb-aacip-507-154dn40c26.start.json \
    -o examples/pipelines/whisper-v8-3-g737e280/pages


## Kaldi output
## --------------------------------------------------------------------------------------

python run_summarizer.py --full \
    -i examples/pipelines/kaldi-0.2.2/example-kaldi-output-pretty.mmif \
    -o examples/pipelines/kaldi-0.2.2/example-kaldi-output-pretty.bis.json


## TimeFrames
## --------------------------------------------------------------------------------------

# Should get some more recent SWT output.

# Testing on the output of the swt-detection/v5.1 + doctr-wrapper/v1.1 pipeline output.

# This fails when creating the Graph object, probably related to issues with the DocTR data

python run_summarizer.py --timeframes \
    -i examples/pipelines/swt-v5.1--doctr-v1.1/cpb-aacip-526-z60bv7c69m.mmif \
    -o examples/pipelines/swt-v5.1--doctr-v1.1/cpb-aacip-526-z60bv7c69m.json \

python run_inspector.py \
    -i examples/pipelines/swt-v5.1--doctr-v1.1/cpb-aacip-526-z60bv7c69m.json \
    -o examples/pipelines/swt-v5.1--doctr-v1.1/pages

# Testing on the output of swt-detection/v5.1

python run_summarizer.py --timeframes \
    -i examples/pipelines/swt-v5.1/cpb-aacip-526-z60bv7c69m.mmif \
    -o examples/pipelines/swt-v5.1/cpb-aacip-526-z60bv7c69m.json 

python run_inspector.py \
    -i examples/pipelines/swt-v5.1/cpb-aacip-526-z60bv7c69m.json \
    -o examples/pipelines/swt-v5.1/pages

python run_summarizer.py --timeframes \
    -i examples/pipelines/swt-v5.1/cpb-aacip-526-z60bv7c69m.start.mmif \
    -o examples/pipelines/swt-v5.1/cpb-aacip-526-z60bv7c69m.start.json 

python run_inspector.py \
    -i examples/pipelines/swt-v5.1/cpb-aacip-526-z60bv7c69m.start.json \
    -o examples/pipelines/swt-v5.1/pages-start



## Llava captioner
## --------------------------------------------------------------------------------------

# swt-detection-v7.4 ⟹ llava-captioner-v1.2-6-gc824c97

python run_summarizer.py --full \
    -i examples/pipelines/swt-v7.4--llava/cpb-aacip-225-12z34w2c.mmif \
    -o examples/pipelines/swt-v7.4--llava/cpb-aacip-225-12z34w2c.json \

python run_inspector.py \
    -i examples/pipelines/swt-v7.4--llava/cpb-aacip-225-12z34w2c.json \
    -o examples/pipelines/swt-v7.4--llava/pages

# Smaller files

python run_summarizer.py --full \
    -i examples/pipelines/swt-v7.4--llava/cpb-aacip-225-12z34w2c.start.mmif \
    -o examples/pipelines/swt-v7.4--llava/cpb-aacip-225-12z34w2c.start.json 

python run_inspector.py \
    -i examples/pipelines/swt-v7.4--llava/cpb-aacip-225-12z34w2c.start.json \
    -o examples/pipelines/swt-v7.4--llava/pages-start

python run_summarizer.py --full \
    -i examples/pipelines/swt-v7.4--llava/cpb-aacip-225-12z34w2c.start.minimal.mmif \
    -o examples/pipelines/swt-v7.4--llava/cpb-aacip-225-12z34w2c.start.minimal.json 

python run_inspector.py \
    -i examples/pipelines/swt-v7.4--llava/cpb-aacip-225-12z34w2c.start.minimal.json \
    -o examples/pipelines/swt-v7.4--llava/pages-start-minimal

python run_summarizer.py --full \
    -i examples/pipelines/swt-v7.4--llava/cpb-aacip-225-12z34w2c.trimmed.mmif \
    -o examples/pipelines/swt-v7.4--llava/cpb-aacip-225-12z34w2c.trimmed.json 

python run_inspector.py \
    -i examples/pipelines/swt-v7.4--llava/cpb-aacip-225-12z34w2c.trimmed.json \
    -o examples/pipelines/swt-v7.4--llava/pages-trimmed



## smolvlm2 captioner
## --------------------------------------------------------------------------------------

# swt-detection-v7.7 ⟹ smolvlm2-captioner

python run_summarizer.py --full \
    -i examples/pipelines/swt-v7.7--smolvlm2/smolvlm2_fresh_output.mmif \
    -o examples/pipelines/swt-v7.7--smolvlm2/smolvlm2_fresh_output.json 

python run_inspector.py \
    -i examples/pipelines/swt-v7.7--smolvlm2/smolvlm2_fresh_output.json \
    -o examples/pipelines/swt-v7.7--smolvlm2/pages

# Smaller file

python run_summarizer.py --full \
    -i examples/pipelines/swt-v7.7--smolvlm2/smolvlm2_fresh_output.trimmed.mmif \
    -o examples/pipelines/swt-v7.7--smolvlm2/smolvlm2_fresh_output.trimmed.json

python run_inspector.py \
    -i examples/pipelines/swt-v7.7--smolvlm2/smolvlm2_fresh_output.trimmed.json \
    -o examples/pipelines/swt-v7.7--smolvlm2/pages-trimmed



## spacy output
## --------------------------------------------------------------------------------------

# just spacy on a transcript

python run_summarizer.py --full \
    -i examples/pipelines/spacy-v1.1/cpb-aacip-507-9882j68s35-transcript.mmif \
    -o examples/pipelines/spacy-v1.1/cpb-aacip-507-9882j68s35-transcript.json 

python run_inspector.py \
    -i examples/pipelines/spacy-v1.1/cpb-aacip-507-9882j68s35-transcript.json \
    -o examples/pipelines/spacy-v1.1/pages

# spacy on captions

python run_summarizer.py --full \
    -i examples/pipelines/swt-v7.7--smolvlm2--spacy-v2.1/smolvlm.trimmed.mmif \
    -o examples/pipelines/swt-v7.7--smolvlm2--spacy-v2.1/smolvlm.trimmed.json 

python run_inspector.py \
    -i examples/pipelines/swt-v7.7--smolvlm2--spacy-v2.1/smolvlm.trimmed.json \
    -o examples/pipelines/swt-v7.7--smolvlm2--spacy-v2.1/pages


