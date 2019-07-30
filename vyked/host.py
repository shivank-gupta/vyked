import asyncio
import logging
from aiohttp import web
from .utils.log import setup_logging, LogFormatHelper
from vyked.utils.stats import Stats, Aggregator
from .utils.client_stats import ClientStats
from .utils.common_utils import ServiceAttribute
from .handler import ApplicationRequestHandler
import socket
import aiotask_context as context
from .middleware import request_id_middleware

class Host:
    name = None
    host = "0.0.0.0"
    port = None
    _middlewares = [request_id_middleware]
    _host_id = None
    _handlers = None

    _logger = logging.getLogger(__name__)

    @classmethod
    def _set_process_name(cls):
        from setproctitle import setproctitle

        setproctitle('{}_{}_{}'.format('vyked', cls.name, cls._host_id))

    @classmethod
    def _stop(cls, signame: str):
        cls._logger.info('\ngot signal {} - exiting'.format(signame))
        asyncio.get_event_loop().stop()

    @classmethod
    def attach_handlers(cls, handlers):
        if handlers:
            cls._handlers =  handlers
        else:
            cls._logger.error('Invalid argument attached as handlers')

    @classmethod
    def attach_web_middlewares(cls, middlewares):
        if middlewares:
            for each in middlewares:
                cls._middlewares.append(each)
        else:
            cls._logger.error('Invalid argument attached as middlewares')

    @classmethod
    def run(cls):
        if cls._handlers:
            cls._set_host_id()
            cls._set_process_name()
            cls._setup_service_attribute()
            cls._setup_logging()

            cls._start_server()
        else:
            cls._logger.error('No handlers to start host')

    @classmethod
    def _start_server(cls):
        if cls._handlers:
            app = web.Application(loop=asyncio.get_event_loop(), middlewares=cls._middlewares)
            loop = asyncio.get_event_loop()
            loop.set_task_factory(context.task_factory)

            app.router.add_route('GET', '/ping', getattr(ApplicationRequestHandler, 'ping'))
            app.router.add_route('GET', '/_stats', getattr(ApplicationRequestHandler, 'stats'))
            app.router.add_route('GET', '/_change_log_level/{level}', getattr(ApplicationRequestHandler, 'handle_log_change'))

            for handler in cls._handlers:
                for each in handler.__ordered__:
                    fn = getattr(handler, each)
                    if callable(fn) and getattr(fn, 'is_http_method', False):
                        for path in fn.paths:
                            app.router.add_route(fn.method, path, fn)
                            cls._logger.debug(path)

            web.run_app(app=app,
                        host=cls.host,
                        port=cls.port,
                        access_log=cls._logger,
                        access_log_format=LogFormatHelper.LogFormat)

    @classmethod
    def _set_host_id(cls):
        from uuid import uuid4

        cls._host_id = uuid4()

    @classmethod
    def _setup_service_attribute(cls):
        ServiceAttribute.name = cls.name
        ServiceAttribute.hostname = socket.gethostbyname(socket.gethostname())

    @classmethod
    def _setup_logging(cls):
        identifier = '{}_{}'.format(cls.name, cls.port)
        setup_logging(identifier)
        Stats.periodic_stats_logger()
        Aggregator.periodic_aggregated_stats_logger()
        ClientStats.periodic_aggregator()
