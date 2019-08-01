import asyncio
from .utils.common_utils import SHARED_CONTEXT


def set(key, value):
    current_task = asyncio.Task.current_task()
    if hasattr(current_task, SHARED_CONTEXT):
        shared_context = getattr(current_task, SHARED_CONTEXT)
        shared_context[key] = value
    else:
        setattr(current_task, SHARED_CONTEXT, {key: value})
        shared_context = getattr(current_task, SHARED_CONTEXT)
        print(shared_context)

    return


def get(key) -> str:
    current_task = asyncio.Task.current_task()

    if hasattr(current_task, SHARED_CONTEXT):
        print('asa')
        shared_context = getattr(current_task, SHARED_CONTEXT)
        print(shared_context)
        return shared_context[key]

    return None