# Script to test the inspect command line script straight from a 
# local distribution
#
# To run this, enter the distribution and the directory where to test it.
#
#     sh test.sh ../dist/inspector_mv-0.0.5-py3-none-any.whl tmp-test
#
# The first argument is the distribution to test and the second is the playpen
# in which the test is run.

echo "Testing $1 in $2"
mkdir $2
cp $1 $2
cd $2
python3 -m venv .venv
source .venv/bin/activate
pip install `basename $1`
.venv/bin/inspect -h
