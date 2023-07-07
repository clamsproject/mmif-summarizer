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

    """For the summarizer, partially because like a ClamsProducer it now also generates
    JSON, all the  ClamsConsumer does is add consume and _consume methods and tweak the
    annotate and _annotate methods."""

    # TODO: we still may want to add this to clams-python

    def annotate(self, mmif: Mmif, **runtime_params) -> Mmif:
        """Since this is a consumer we just redirect the annotate method to the consume
        method. This way we do not need to change the post method on the ClamsHTTPApi
        instance used by the Restifier."""
        return self._consume(mmif, **runtime_params)

    def _annotate(self, mmif: Mmif, **runtime_params) -> Mmif:
        """Will never be used but is needed due to superclass requirements."""
        pass

    def consume(self, mmif: Mmif, **runtime_params) -> str:
        return self._consume(mmif, **runtime_params)

    @abstractmethod
    def _consume(self, mmif, **kwargs) -> str:
        raise NotImplementedError()


class MmifSummarizer(ClamsConsumer):

    def _appmetadata(self) -> AppMetadata:
        return metadata.appmetadata()

    def _consume(self, mmif, **runtime_params):
        self.mmif = mmif if type(mmif) is Mmif else Mmif(mmif)
        mmif_summary = summary.Summary(mmif)
        return mmif_summary.report(**runtime_params)


def start_service():
    summarizer = MmifSummarizer()
    service = Restifier(summarizer)
    service.run()


if __name__ == "__main__":

    start_service()
