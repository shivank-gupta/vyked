from .utils.ordered_class_member import OrderedClassMembers
import logging
import json
from .utils.stats import Aggregator
from .wrappers import Response, Request

class BaseRequestHandler(metaclass=OrderedClassMembers):

    """
        Wraps the base handler request object to handle multiple handlers
    """
    pass


class ApplicationRequestHandler(BaseRequestHandler):

    @staticmethod
    def stats(_):
        res_d = Aggregator.dump_stats()
        return Response(status=200, content_type='application/json', body=json.dumps(res_d).encode())

    @staticmethod
    def ping(_):
        return Response(status=200, content_type='application/json', body=json.dumps({}).encode())

    @staticmethod
    def handle_log_change(request: Request):
        try:
            level = getattr(logging, request.match_info.get('level').upper())
        except AttributeError as e:
            logging.getLogger().error(e)
            response = 'Allowed logging levels: DEBUG, INFO, WARNING, ERROR, CRITICAL'
            return Response(status=400, content_type='application/json', body=json.dumps({'message': response}).encode())
        logging.getLogger().setLevel(level)
        for handler in logging.getLogger().handlers:
            handler.setLevel(level)
        response = 'Logging level updated'
        return Response(status=200, content_type='application/json', body=json.dumps({'message': response}).encode())
