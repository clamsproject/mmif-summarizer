"""Summarizer Application

CLAMS Consumer application that wraps the summarizer in summary.py.

To start a Flask server and ping it:

$ python app.py
$ curl -X GET http://0.0.0.0:5000/
$ curl -X POST -d@examples/input-v7.mmif http://0.0.0.0:5000/
$ curl -X POST -d@examples/input-v9.mmif 'http://0.0.0.0:5000?transcript&segments'

See README.md for more details.

"""

from clams.appmetadata import AppMetadata
from mmif.serialize import Mmif
from mmif.vocabulary import DocumentTypes, AnnotationTypes
from lapps.discriminators import Uri

import summary
from server import ClamsConsumer, Restifier


VERSION = '0.2.0'
LICENSE = 'Apache 2.0'
MMIF_VERSION = '0.4.2'
MMIF_PYTHON_VERSION = '0.4.8'
CLAMS_PYTHON_VERSION = '0.5.3'


class MmifSummarizer(ClamsConsumer):

    def _consumermetadata(self):
        self.metadata = \
            AppMetadata(
                identifier="https://apps.clams.ai/mmif-summarizer",
                url='https://github.com/clamsproject/mmif-summarizer',
                name="MMIF Summarizer",
                description="Summarize a MMIF file.",
                mmif_version=MMIF_VERSION,
                app_version=VERSION,
                app_license=LICENSE,
                analyzer_version=VERSION,
                analyzer_license=LICENSE)
        self.metadata.add_input(DocumentTypes.TextDocument, required=False)
        self.metadata.add_input(AnnotationTypes.TimeFrame, required=False)
        self.metadata.add_input(AnnotationTypes.BoundingBox, required=False)
        self.metadata.add_input(AnnotationTypes.Alignment, required=False)
        self.metadata.add_input(Uri.TOKEN, required=False)
        self.metadata.add_input(Uri.NE, required=False)
        return self.metadata

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
