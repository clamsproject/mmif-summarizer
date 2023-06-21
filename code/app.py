"""Summarizer Application

CLAMS Consumer application that wraps the summarizer in summary.py.

To start a Flask server and ping it:

$ python app.py
$ curl -X GET http://0.0.0.0:5000/
$ curl -X POST -d@examples/input-v7.mmif http://0.0.0.0:5000/
$ curl -X POST -d@examples/input-v9.mmif 'http://0.0.0.0:5000?transcript&segments'

See README.md for more details.

"""

from mmif.serialize import Mmif

import metadata
import summary
from server import ClamsConsumer, Restifier


class MmifSummarizer(ClamsConsumer):

    def _consumermetadata(self):
        return metadata.appmetadata()

    def _consume(self, mmif, **kwargs):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        mmif_summary = summary.Summary(mmif)
        return mmif_summary.report(**kwargs)


def start_service():
    summarizer = MmifSummarizer()
    service = Restifier(summarizer, mimetype='application/xml')
    service.run()


if __name__ == "__main__":

    start_service()
