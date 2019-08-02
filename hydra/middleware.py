import aiotask_context as context
from aiohttp.web import middleware
import uuid

@middleware
async def request_id_middleware(request, handler):
    context.set("X-Request-ID", request.headers.get("X-Request-ID", str(uuid.uuid4())))
    response = await handler(request)
    response.headers["X-Request-ID"] = context.get("X-Request-ID")
    return response