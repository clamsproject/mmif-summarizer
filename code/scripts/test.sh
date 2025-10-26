# Script to test the summarizer command line script straight from a 
# local distribution
#
# To run this, just enter the distribution as the single option. I tend to run
# this from the code directory:
#
#     sh test.sh ../dist/summarizer_mv-0.2.4-py3-none-any.whl 
#
# This will create a directory named out/test-summarizer

echo "Testing $1"
mkdir out/test-summarizer
cp $1 out/test-summarizer
cd out/test-summarizer
python3 -m venv .venv-test
source .venv-test/bin/activate
pip install `basename $1`
summarize -h
