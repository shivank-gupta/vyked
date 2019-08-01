import asyncio
from .common_utils import SHARED_CONTEXT

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
        if current_task is not None and hasattr(current_task, SHARED_CONTEXT):
            shared_context = getattr(current_task, SHARED_CONTEXT)
            shared_context = shared_context or {}
            setattr(task, SHARED_CONTEXT, shared_context)
        return task

    asyncio.base_events.BaseEventLoop.create_task_old = asyncio.base_events.BaseEventLoop.create_task
    asyncio.base_events.BaseEventLoop.create_task = decorate_base_event_loop_create_task_routine