"""

Utility script to take a file and pretty print the JSON object in that file.

$ python pretty.py JSON_FILE

Writes to the standard output.

"""


import sys
import json


obj = json.load(open(sys.argv[1]))

print(json.dumps(obj, indent=2))
