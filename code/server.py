"""server.py

The classes in this module are all adapted from the clams-python app and
restify modules, but the following changes were made:

- Parameterized the mimetype (since it is probably not standardized).
- POST maps to consume() instead of annotate().
- Renamed appmetadata() into consumermetadata() (since this is not an app).
- Replaced App in classnames with Consumer.
- Made some changes to follow the new app signatures of using appmetadata()
  versus _appmetadata() and annotate() versus _annotate(), the latter two
  renamed for consumers.

If consumers have significant overlap in how they run as REST services then the
code in here could be added to clams-python in some form.

"""


from abc import ABC, abstractmethod
from flask import Flask, request, Response
from flask_restful import Resource, Api

from mmif import Mmif


class ClamsConsumer(ABC):

    def __init__(self):
        self.metadata = self._consumermetadata()
        super().__init__()

    def consumermetadata(self):
        return self.metadata.json(indent=2)

    def consume(self, mmif, **kwargs) -> str:
        return self._consume(mmif, **kwargs)

    @abstractmethod
    def _consumermetadata(self) -> dict:
        raise NotImplementedError()

    @abstractmethod
    def _consume(self, mmif, **kwargs) -> str:
        raise NotImplementedError()


class Restifier(object):

    def __init__(self, app_instance,
                 loopback=False, port=5000, debug=True,
                 mimetype='application/json'):
        super().__init__()
        self.cla = app_instance
        self.import_name = app_instance.__class__.__name__
        self.flask_app = Flask(self.import_name)
        self.host = 'localhost' if loopback else '0.0.0.0'
        self.port = port
        self.debug = debug
        api = Api(self.flask_app)
        api.add_resource(ClamsConsumerRestfulApi, '/',
                         resource_class_args=[self.cla, mimetype])

    def run(self):
        self.flask_app.run(host=self.host, port=self.port, debug=self.debug)

    def test_client(self):
        return self.flask_app.test_client()


class ClamsConsumerRestfulApi(Resource):

    def __init__(self, cla_instance, mimetype):
        super().__init__()
        self.cla = cla_instance
        self.mimetype = mimetype

    @staticmethod
    def response(response_str: str, status=200, mimetype='application/xml'):
        if not isinstance(response_str, str):
            response_str = str(response_str)
        return Response(response=response_str,
                        status=status,
                        mimetype=mimetype)

    def get(self):
        return self.response(self.cla.consumermetadata())

    def post(self):
        params = cast(request.args)
        return self.response(self.cla.consume(Mmif(request.get_data()), **params),
                             mimetype=self.mimetype)


def cast(params):
    """A temporary stub to deal with parameters for this consumer. This is awaiting
    the code that hooks up this consumer to the parameter casting code."""
    true_values = ('True', 'true', '1', 'yes')
    casted = {}
    if 'granularity' in params:
        casted['granularity'] = int(params['granularity'])
    if 'transcript' in params:
        val = params['transcript']
        casted['transcript'] = True if val in true_values else False
    return casted
