import aiohttp
import asyncio

from aiohttp.web import Response
from ..shared_context import SharedContext
from .common_utils import X_REQUEST_ID


def monkey_patch_asyncio_task_factory():
    """
    Monkey patch asyncio to be able to pass context from parent task to child tasks
    If its available patch this method else patch create_task() method of
    asyncio.base_events.BaseEventLoop class
    """

    def decorate_base_event_loop_create_task_routine(self, coro):
        task = self.create_task_old(coro)
        # check current task, if it's not None, set context in new task
        current_task = asyncio.Task.current_task()
        if current_task is not None and hasattr(current_task, SharedContext.SHARED_CONTEXT):
            shared_context = getattr(current_task, SharedContext.SHARED_CONTEXT)
            shared_context = shared_context or {}
            setattr(task, SharedContext.SHARED_CONTEXT, shared_context)
        return task

    asyncio.base_events.BaseEventLoop.create_task_old = asyncio.base_events.BaseEventLoop.create_task
    asyncio.base_events.BaseEventLoop.create_task = decorate_base_event_loop_create_task_routine


def monkey_patch_aiohttp_client_session_request():

    old_client_session_request = aiohttp.client.ClientSession._request

    def decorate_client_session_request(self, *args, **kwargs):
        headers = kwargs.get('headers') or dict()
        headers[X_REQUEST_ID] = SharedContext.get(X_REQUEST_ID)
        kwargs['headers'] = headers
        return (yield from old_client_session_request(self, *args, **kwargs))

    aiohttp.client.ClientSession._request = decorate_client_session_request


def monkey_patch_aiohttp_response_init():
    old_init = Response.__init__

    def new_init(self, *args, **kwargs):
        headers = kwargs.get('headers') or dict()
        headers[X_REQUEST_ID] = SharedContext.get(X_REQUEST_ID)
        kwargs['headers'] = headers
        old_init(self, *args, **kwargs)

    Response.__init__ = new_init

