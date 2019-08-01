import asyncio
from .shared_context import SharedContext
from .utils.common_utils import X_REQUEST_ID, get_uuid

@asyncio.coroutine
def request_id_middleware_factory(app, handler):

    @asyncio.coroutine
    def middleware(request):
        tracking_id = request.headers.get(X_REQUEST_ID, get_uuid())
        SharedContext.set(X_REQUEST_ID, tracking_id)
        response = yield from handler(request)
        return response

    return middleware
