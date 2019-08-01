import asyncio
from .shared_context import set
import uuid
from .utils.common_utils import X_REQUEST_ID

@asyncio.coroutine
def request_id_middleware_factory(app, handler):

    @asyncio.coroutine
    def middleware(request):
        tracking_id = request.headers.get(X_REQUEST_ID, str(uuid.uuid4()))
        set(X_REQUEST_ID, tracking_id)
        print(tracking_id)
        response = yield from handler(request)
        return response

    return middleware
