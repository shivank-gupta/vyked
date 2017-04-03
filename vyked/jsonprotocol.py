import asyncio
import json
import logging

from jsonstreamer import ObjectStreamer
from .sendqueue import SendQueue
from .utils.jsonencoder import VykedEncoder


class JSONProtocol(asyncio.Protocol):
    logger = logging.getLogger(__name__)

    def __init__(self):
        self._send_q = None
        self._connected = False
        self._transport = None
        self._pending_data = []
        self._partial_data = ""

    @staticmethod
    def _make_frame(packet):
        string = json.dumps(packet, cls=VykedEncoder) + '!<^>!'
        return string.encode()

    def is_connected(self):
        return self._connected

    def _write_pending_data(self):
        for packet in self._pending_data:
            frame = self._make_frame(packet)
            self._transport.write(frame.encode())
        self._pending_data.clear()

    def connection_made(self, transport):
        self._connected = True
        self._transport = transport

        self._transport.send = self._transport.write
        self._send_q = SendQueue(transport, self.is_connected)

        self._send_q.send()

    def connection_lost(self, exc):
        self._connected = False
        self.logger.info('Peer closed %s', self._transport.get_extra_info('peername'))

    def send(self, packet: dict):
        frame = self._make_frame(packet)
        self._send_q.send(frame)
        self.logger.debug('Data sent: %s', frame.decode())

    def data_received(self, byte_data):
        string_data = byte_data.decode()
        self.logger.debug('Data received: %s', string_data)
        try:
            string_data = self._partial_data + string_data
            self._partial_data = ''
            for e in string_data.split('!<^>!'):
                if e:
                    try:
                        element = json.loads(e)
                        self.on_element(element)
                    except Exception as exc:
                        self._partial_data = e
                        self.logger.debug('Packet splitting: %s', self._partial_data)
        except Exception as e:
            self.logger.error('Could not parse data: %s', string_data)


class VykedProtocol(JSONProtocol):

    def __init__(self, handler):
        super().__init__()
        self._handler = handler

    def connection_made(self, transport):
        peer_name = transport.get_extra_info('peername')
        self.logger.info('Connection from %s', peer_name)
        super(VykedProtocol, self).connection_made(transport)

    def connection_lost(self, exc):
        super(VykedProtocol, self).connection_lost(exc)

    def on_element(self, element):
        try:
            self._handler.receive(packet=element, protocol=self, transport=self._transport)
        except:
            # ignore any unhandled errors raised by handler
            self.logger.exception('api request exception')
            pass
