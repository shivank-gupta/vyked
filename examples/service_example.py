from vyked import BaseRequestHandler, get, Request, Response, Host
import asyncio
import aiotask_context as context

class OrderHandler(BaseRequestHandler):
    @get(path='/order/test')
    async def order_test(self, _request: Request):
        await asyncio.sleep(2)
        print(context.get("X-Request-ID"))
        return Response(status=200, body="hello order test")


class CartHandler(BaseRequestHandler):
    @get(path='/cart/test')
    async def cart_test(self, _request: Request):
        print(context.get("X-Request-ID"))
        return Response(status=200, body="hello cart test")


if __name__ == '__main__':
    order_handler = OrderHandler()
    cart_handler = CartHandler()
    handlers = [order_handler, cart_handler]

    Host.host = '0.0.0.0'
    Host.port = '3200'
    Host.name = 'test_service'
    Host.attach_handlers(handlers)
    Host.run()