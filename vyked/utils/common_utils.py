import asyncio
import inspect

import json


ONEMG_REQUEST_ID = 'X-REQUEST-ID'


def json_file_to_dict(_file: str) -> dict:
    """
    convert json file data to dict

    :param str _file: file location including name

    :rtype: dict
    :return: converted json to dict
    """
    config = None
    try:
        with open(_file) as config_file:
            config = json.load(config_file)
    except:
        pass

    return config


def valid_timeout(timeout):
    return True if isinstance(timeout, (int, float)) and timeout > 0 and timeout <= 600 else False


@asyncio.coroutine
def call_anonymous_function(function_to_call, *args, **kwargs):
    if inspect.isgeneratorfunction(function_to_call):
        return (yield from function_to_call(*args, **kwargs))
    else:
        return function_to_call(*args, **kwargs)


def monkey_patch_asyncio_task_factory():
    """
    Monkey patch asyncio to be able to pass context from parent task to child tasks
    """
    def decorate_base_event_loop_create_task_routine(self, coro):
        task = self.create_task_old(coro)
        # check current task, if it's not None, set context in new task
        current_task = asyncio.Task.current_task()
        if current_task is not None and hasattr(current_task, ONEMG_REQUEST_ID):
            request_id = getattr(current_task, ONEMG_REQUEST_ID)
            setattr(task, ONEMG_REQUEST_ID, request_id)
        return task

    asyncio.base_events.BaseEventLoop.create_task_old = asyncio.base_events.BaseEventLoop.create_task
    asyncio.base_events.BaseEventLoop.create_task = decorate_base_event_loop_create_task_routine


def set_request_id_in_coro_task(request_id):
    coro_task = asyncio.Task.current_task()
    return setattr(coro_task, ONEMG_REQUEST_ID, request_id)


def get_coro_task_request_id() -> str:
    coro_task = asyncio.Task.current_task()
    if not hasattr(coro_task, ONEMG_REQUEST_ID):
        return getattr(coro_task, ONEMG_REQUEST_ID)
    return None
