import asyncio

class SharedContext:
    SHARED_CONTEXT = 'X-Shared-Context'

    @classmethod
    def set(cls, key, value):
        key = cls.transform_key(key)
        current_task = asyncio.Task.current_task()

        if hasattr(current_task, cls.SHARED_CONTEXT):
            shared_context = getattr(current_task, cls.SHARED_CONTEXT)
            shared_context[key] = value
        else:
            setattr(current_task, cls.SHARED_CONTEXT, {key: value})

        return

    @classmethod
    def get(cls, key) -> str:
        key = cls.transform_key(key)
        current_task = asyncio.Task.current_task()

        if hasattr(current_task, cls.SHARED_CONTEXT):
            shared_context = getattr(current_task, cls.SHARED_CONTEXT)
            return shared_context.get(key)

        return None

    @classmethod
    def transform_key(cls, key):
        return key.lower()