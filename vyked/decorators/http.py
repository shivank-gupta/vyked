from asyncio import wait_for, TimeoutError, shield
from functools import wraps
from ..exceptions import VykedServiceException
from ..utils.stats import Stats, Aggregator
from ..utils.common_utils import json_file_to_dict, valid_timeout
import logging
import setproctitle
import socket
import time
import traceback
from ..config import CONFIG
_http_timeout = CONFIG.HTTP_TIMEOUT


def get_decorated_fun(method, path, required_params, timeout):
    def decorator(func):
        @wraps(func)
        async def f(self, *args, **kwargs):
            if True:
                Stats.http_stats['total_requests'] += 1

                t1 = time.time()
                tp1 = time.process_time()

                wrapped_func = func
                success = True
                _logger = logging.getLogger()
                api_timeout = _http_timeout

                if valid_timeout(timeout):
                    api_timeout = timeout

                service_name = '_'.join(setproctitle.getproctitle().split('_')[:-1])
                service_name = service_name.replace('vyked_', '')

                try:
                    result = await wait_for(shield(wrapped_func(self, *args, **kwargs)), api_timeout)

                except TimeoutError as e:
                    Stats.http_stats['timedout'] += 1
                    status = 'timeout'
                    success = False
                    _logger.exception("HTTP request had a timeout for method %s", func.__name__)
                    timeout_log = {
                        'time_taken': api_timeout,
                        'type': 'http',
                        'hostname': socket.gethostbyname(socket.gethostname()),
                        'service_name': service_name,
                        'endpoint': func.__name__,
                        'api_execution_threshold_exceed': True,
                        'api_timeout': True
                    }

                    logging.getLogger('stats').info(timeout_log)
                    raise e

                except VykedServiceException as e:
                    Stats.http_stats['total_responses'] += 1
                    status = 'handled_exception'
                    _logger.info('Handled exception %s for method %s ', e.__class__.__name__, func.__name__)
                    raise e

                except Exception as e:
                    Stats.http_stats['total_errors'] += 1
                    status = 'unhandled_exception'
                    success = False
                    _logger.exception('Unhandled exception %s for method %s ', e.__class__.__name__, func.__name__)
                    _stats_logger = logging.getLogger('stats')
                    d = {"exception_type": e.__class__.__name__, "method_name": func.__name__, "message": str(e),
                         "service_name": service_name, "hostname": socket.gethostbyname(socket.gethostname())}
                    _stats_logger.info(dict(d))
                    _exception_logger = logging.getLogger('exceptions')
                    d["message"] = traceback.format_exc()
                    _exception_logger.info(dict(d))
                    raise e
                    
                else:
                    t2 = time.time()
                    tp2 = time.process_time()
                    hostname = socket.gethostname()
                    service_name = '_'.join(setproctitle.getproctitle().split('_')[:-1])
                    status = result.status

                    logd = {
                        'status': result.status,
                        'time_taken': int((t2 - t1) * 1000),
                        'process_time_taken': int((tp2-tp1) * 1000),
                        'type': 'http',
                        'hostname': hostname,
                        'service_name': service_name,
                        'endpoint': func.__name__,
                        'api_execution_threshold_exceed': False
                    }

                    method_execution_time = (t2 - t1)

                    if method_execution_time > CONFIG.SLOW_API_THRESHOLD:
                        logd['api_execution_threshold_exceed'] = True
                        logging.getLogger('stats').info(logd)
                    else:
                        logging.getLogger('stats').debug(logd)

                    Stats.http_stats['total_responses'] += 1
                    return result

                finally:
                    t2 = time.time()
                    tp2 = time.process_time()
                    Aggregator.update_stats(endpoint=func.__name__, status=status, success=success,
                                            server_type='http', time_taken=int((t2 - t1) * 1000),
                                            process_time_taken=int((tp2 - tp1) * 1000))

        f.is_http_method = True
        f.method = method
        f.paths = path
        if not isinstance(path, list):
            f.paths = [path]
        return f

    return decorator


def get(path=None, required_params=None, timeout=None, is_internal=False):
    return get_decorated_fun('get', get_path(path, is_internal), required_params, timeout)


def head(path=None, required_params=None, timeout=None, is_internal=False):
    return get_decorated_fun('head', get_path(path, is_internal), required_params, timeout)


def options(path=None, required_params=None, timeout=None, is_internal=False):
    return get_decorated_fun('options', get_path(path, is_internal), required_params, timeout)


def patch(path=None, required_params=None, timeout=None, is_internal=False):
    return get_decorated_fun('patch', get_path(path, is_internal), required_params, timeout)


def post(path=None, required_params=None, timeout=None, is_internal=False):
    return get_decorated_fun('post', get_path(path, is_internal), required_params, timeout)


def put(path=None, required_params=None, timeout=None, is_internal=False):
    return get_decorated_fun('put', get_path(path, is_internal), required_params, timeout)


def trace(path=None, required_params=None, timeout=None, is_internal=False):
    return get_decorated_fun('put', get_path(path, is_internal), required_params, timeout)


def delete(path=None, required_params=None, timeout=None, is_internal=False):
    return get_decorated_fun('delete', get_path(path, is_internal), required_params, timeout)


def get_path(path, is_internal=False):
    if is_internal:
        path = CONFIG.INTERNAL_HTTP_PREFIX + path

    return path
