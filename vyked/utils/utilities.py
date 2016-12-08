"""" Common utility methods for vyked apis """
import json
from functools import wraps
from .Service_exceptions import *
from vyked.exceptions import RequestException
from aiohttp.web import Response
import inspect
from vyked import Request
import datetime
from time import mktime

HTTP_STATUS_CODES = {
    'SUCCESS': 200,
    'CREATED': 201,
    'MULTI_STATUS': 207,
    'BAD_REQUEST': 400,
    'NOT_FOUND': 404,
    'FORBIDDEN': 403,
    'UNAUTHORIZED': 401,
    'INTERNAL_SERVER_ERROR': 500,
    'CONFLICT': 409
}

ERROR_MESSAGE = {
    'UNKNOWN_ERROR': 'unknown error occurred',
    'ERROR_CODE': 'error_code',
    'ERROR_MESSAGE': 'error_message'
}

ROLE_NOT_VALID_FOR_APP = 'Not valid role for app "{}"'
FORBIDDEN = 'Not permitted'


class CustomRequest(Request):
    user = None
    request = None

    def __init__(self, request: Request, user: dict):
        self.request = request
        self.user = user


def get_error_as_json(val):
    re = {'error': val}
    return json.dumps(re).encode()


def json_file_to_dict(_file: str) -> dict:
    """
    convert json file data to dict

    :param str _file: file location including name

    :rtype: dict
    :return: converted json to dict
    """
    config = None
    with open(_file) as config_file:
        config = json.load(config_file)

    return config


def is_valid_string(name, min_length=1) -> bool:
    return True


def validate_login(request: Request):
    user_name_field = 'user_name'
    password_field = 'password'
    data = yield from request.json()
    user_name = data[user_name_field]
    password = data[password_field]
    if not is_valid_string(user_name):
        raise ServiceException('{} required'.format(user_name_field))
    if not is_valid_string(password):
        raise ServiceException('{} required'.format(password_field))
    return user_name, password


def get_result_from_tcp_response(response):
    if not response:
        raise ServiceException(ERROR_MESSAGE['UNKNOWN_ERROR'])
    if ERROR_MESSAGE['ERROR_CODE'] in response:
        error_code = response[ERROR_MESSAGE['ERROR_CODE']]
        if error_code == 204:
            raise NotFoundException(response[ERROR_MESSAGE['ERROR_MESSAGE']])
        elif error_code == 201:
            raise UnAuthorizeException(response[ERROR_MESSAGE['ERROR_MESSAGE']])
        elif error_code == 205:
            raise ResourceConflictException(response[ERROR_MESSAGE['ERROR_MESSAGE']])
        elif error_code == 203:
            raise ForbiddenException(response[ERROR_MESSAGE['ERROR_MESSAGE']])
        else:
            raise ServiceException(response[ERROR_MESSAGE['ERROR_MESSAGE']])
    else:
        return response['result']


def exception_handler_http(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = yield from func(*args, **kwargs)
            return result
        except NotFoundException as ne:
            return Response(status=HTTP_STATUS_CODES['NOT_FOUND'], body=get_error_as_json(str(ne)),
                            content_type='application/*json')
        except ForbiddenException as fe:
            return Response(status=HTTP_STATUS_CODES['FORBIDDEN'], body=get_error_as_json(str(fe)),
                            content_type='application/*json')
        except UnAuthorizeException as fe:
            return Response(status=HTTP_STATUS_CODES['UNAUTHORIZED'], body=get_error_as_json(str(fe)),
                            content_type='application/*json')
        except ResourceConflictException as ae:
            return Response(status=HTTP_STATUS_CODES['CONFLICT'], body=get_error_as_json(str(ae)),
                            content_type='application/*json')
        except ServiceException as ee:
            return Response(status=HTTP_STATUS_CODES['BAD_REQUEST'], body=get_error_as_json(str(ee)),
                            content_type='application/*json')
        except Exception as e:
            return Response(status=HTTP_STATUS_CODES['INTERNAL_SERVER_ERROR'], body=get_error_as_json(str(e)),
                            content_type='application/*json')

    return wrapper


def get_response_from_tcp(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            response = yield from func(*args, **kwargs)
            result = {
                'result': response
            }
            return result
        except RequestException as e:
            error = e.error.split('_')
            error_code = error[0]
            if len(error) > 1:
                error_message = error[1]
            else:
                error_message = ERROR_MESSAGE['UNKNOWN_ERROR']
            result = {
                ERROR_MESSAGE['ERROR_CODE']: int(error_code),
                ERROR_MESSAGE['ERROR_MESSAGE']: error_message
            }
            return result

    return wrapper


def validate_authorization(user_object, roles, APP_NAME):
    if user_object is None or APP_NAME not in user_object['roles']:
        raise UnAuthorizeException(ROLE_NOT_VALID_FOR_APP.format(APP_NAME))
    _authenticated = False
    for user_role in user_object['roles'][APP_NAME]:
        if user_role in roles:
            _authenticated = True
    if not _authenticated:
        raise ForbiddenException(FORBIDDEN)


""" Need to pass app_name and list of roles to be verified against for that app """
def authenticate(app_name, roles: list):
    def decor(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            auth_token = args[0].headers.get('Authorization', None)
            if auth_token is None:
                raise UnAuthorizeException('Invalid authorization')

            """      Here identity_service_tcp_client need to
                    be passed as service parameter         """
            user_response = yield from self.identity_service_tcp_client.authenticate(auth_token)
            try:
                user_result = get_result_from_tcp_response(response=user_response)
            except NotFoundException as ne:
                raise ForbiddenException('Forbidden')
            validate_authorization(user_object=user_result, roles=roles)
            custom_request = CustomRequest(args[0], user_result, app_name)
            if inspect.isgeneratorfunction(func):
                return (yield from func(self, custom_request))
            else:
                return func(self, custom_request)
        return wrapper

    return decor


class MyEncoder(json.JSONEncoder):
    """
    json dump encoder class
    """

    def default(self, obj):
        """

        :param obj: object to convert to json
        :return: encoded json
        """
        if isinstance(obj, datetime.datetime):
            return int(mktime(obj.timetuple()))
        return json.JSONEncoder.default(self, obj)


""" Need to pass list of roles to validate against """
def login(roles: list):
    def decor(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            user_name, password = yield from validate_login(request=args[0])
            result = yield from self.clients[0].login(user_name, password, None)
            login_result = get_result_from_tcp_response(result)
            validate_authorization(user_object=login_result, roles=roles)
            return Response(status=HTTP_STATUS_CODES.SUCCESS.value, body=json.dumps(login_result, cls=MyEncoder).encode(), content_type='application/json')

        return wrapper
    return decor


def get_mandatory_parameter(req, key):
    try:
        return req[key]
    except Exception as e:
        raise ServiceException("{0} is required".format(key))
