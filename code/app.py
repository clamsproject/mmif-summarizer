"""Summarizer Application

CLAMS Consumer application that wraps the summarizer in summary.py.

To start a Flask server and ping it:

$ python app.py
$ curl -X GET http://0.0.0.0:5000/
$ curl -X POST -d@examples/input-v7.mmif http://0.0.0.0:5000/
$ curl -X POST -d@examples/input-v9.mmif 'http://0.0.0.0:5000?transcript&segments'

See README.md for more details.

"""

from abc import abstractmethod
from clams.app import ClamsApp
from clams.appmetadata import AppMetadata
from clams.restify import Restifier
from mmif.serialize import Mmif

import metadata
import summary


class ClamsConsumer(ClamsApp):

    """For the summarizer, partially because like a ClamsProducer it also generates
    JSON, all the  ClamsConsumer does is add consume and _consume methods. The annotate
    and _annotate methods are inherited, but tweaked to trivially return the input Mmif."""

    # TODO: we still may want to add this to clams-python

    def _annotate(self, mmif: Mmif, **runtime_params) -> Mmif:
        """Since this is a consumer it just bounces the input back."""
        return mmif

    def consume(self, mmif, **kwargs) -> str:
        return self._consume(mmif, **kwargs)

    @abstractmethod
    def _consume(self, mmif, **kwargs) -> str:
        raise NotImplementedError()


class MmifSummarizer(ClamsConsumer):

    def _appmetadata(self) -> AppMetadata:
        return metadata.appmetadata()

    def _consume(self, mmif, **kwargs):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        mmif_summary = summary.Summary(mmif)
        return mmif_summary.report(**kwargs)


def start_service():
    summarizer = MmifSummarizer()
    service = Restifier(summarizer)
    service.run()


if __name__ == "__main__":

    start_service()
