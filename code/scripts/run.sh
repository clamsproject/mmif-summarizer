## Command line invocation examples
## ======================================================================================

## Pretty useless if you do not have those files locally.


## Whisper output
## --------------------------------------------------------------------------------------

# v8 directory

python summary.py --full \
    -d /Users/Shared/data/clams/mmif-storage/whisper-wrapper/v8/d3253407b97d29df1cfa2ece903c613e

# v8 file

python summary.py --full \
    -i examples/pipelines/whisper-wrapper-v8/cpb-aacip-507-154dn40c26.mmif \
    -o examples/pipelines/whisper-wrapper-v8/cpb-aacip-507-154dn40c26.bis.json

python create_html.py \
    examples/pipelines/whisper-wrapper-v8/cpb-aacip-507-154dn40c26.bis.json \
    examples/pipelines/whisper-wrapper-v8/pages-bis

# v8 smaller file

python summary.py --full \
    -i examples/pipelines/whisper-wrapper-v8/cpb-aacip-507-154dn40c26.start.mmif \
    -o examples/pipelines/whisper-wrapper-v8/cpb-aacip-507-154dn40c26.start.bis.json

python create_html.py \
    examples/pipelines/whisper-wrapper-v8/cpb-aacip-507-154dn40c26.start.bis.json \
    examples/pipelines/whisper-wrapper-v8/pages-start-bis

# v8-3-g737e280 file

python summary.py --full \
    -i examples/pipelines/whisper-wrapper-v8-3-g737e280/cpb-aacip-507-154dn40c26.mmif \
    -o examples/pipelines/whisper-wrapper-v8-3-g737e280/cpb-aacip-507-154dn40c26.bis.json

python create_html.py \
    examples/pipelines/whisper-wrapper-v8-3-g737e280/cpb-aacip-507-154dn40c26.json \
    examples/pipelines/whisper-wrapper-v8-3-g737e280/pages

python summary.py --full \
    -i examples/pipelines/whisper-wrapper-v8-3-g737e280/cpb-aacip-507-154dn40c26.start.mmif \
    -o examples/pipelines/whisper-wrapper-v8-3-g737e280/cpb-aacip-507-154dn40c26.start.json

python create_html.py \
    examples/pipelines/whisper-wrapper-v8-3-g737e280/cpb-aacip-507-154dn40c26.json \
    examples/pipelines/whisper-wrapper-v8-3-g737e280/pages


## Kaldi output
## --------------------------------------------------------------------------------------

python summary.py --full \
    -i examples/pipelines/aapb-pua-kaldi-wrapper-0.2.2/example-kaldi-output-pretty.mmif \
    -o examples/pipelines/aapb-pua-kaldi-wrapper-0.2.2/example-kaldi-output-pretty.bis.json



## Llava captioner
## --------------------------------------------------------------------------------------

# swt-detection-v7.4 ⟹ llava-captioner-v1.2-6-gc824c97

python summary.py --full \
    -i examples/pipelines/swt-detection-v7.4--llava-captioner-v1.2-6-gc824c97/cpb-aacip-225-12z34w2c.mmif \
    -o examples/pipelines/swt-detection-v7.4--llava-captioner-v1.2-6-gc824c97/cpb-aacip-225-12z34w2c.json

python create_html.py \
    examples/pipelines/swt-detection-v7.4--llava-captioner-v1.2-6-gc824c97/cpb-aacip-225-12z34w2c.json \
    examples/pipelines/swt-detection-v7.4--llava-captioner-v1.2-6-gc824c97/pages

# Smaller file

python summary.py --full \
    -i examples/pipelines/swt-detection-v7.4--llava-captioner-v1.2-6-gc824c97/cpb-aacip-225-12z34w2c.start.mmif \
    -o examples/pipelines/swt-detection-v7.4--llava-captioner-v1.2-6-gc824c97/cpb-aacip-225-12z34w2c.start.json

python create_html.py \
    examples/pipelines/swt-detection-v7.4--llava-captioner-v1.2-6-gc824c97/cpb-aacip-225-12z34w2c.start.json \
    examples/pipelines/swt-detection-v7.4--llava-captioner-v1.2-6-gc824c97/pages-start


