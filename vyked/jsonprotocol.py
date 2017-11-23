import asyncio
import json
import logging
import time
from jsonstreamer import ObjectStreamer
from .sendqueue import SendQueue
from .utils.jsonencoder import VykedEncoder
from .utils.common_utils import json_file_to_dict

config = json_file_to_dict('config.json')
_VALID_MAXIMUM_PACKET_SIZE_IN_BYTES = 1000000
_VALID_MAXIMUM_JSON_LOADS_TIME_IN_MS = 500

if isinstance(config, dict):
    if 'VALID_MAXIMUM_PACKET_SIZE_IN_BYTES' in config and isinstance(config['VALID_MAXIMUM_PACKET_SIZE_IN_BYTES'], int):
        _VALID_MAXIMUM_PACKET_SIZE_IN_BYTES = config['VALID_MAXIMUM_PACKET_SIZE_IN_BYTES']
    
    if 'VALID_MAXIMUM_JSON_LOADS_TIME_IN_MS' in config and isinstance(config['VALID_MAXIMUM_JSON_LOADS_TIME_IN_MS'], int):
        _VALID_MAXIMUM_JSON_LOADS_TIME_IN_MS = config['VALID_MAXIMUM_JSON_LOADS_TIME_IN_MS']

class JSONProtocol(asyncio.Protocol):
    logger = logging.getLogger(__name__)

    def __init__(self):
        self._send_q = None
        self._connected = False
        self._transport = None
        self._obj_streamer = None
        self._pending_data = []
        self._partial_data = ""
        self._json_loads_time = 0.0

    @staticmethod
    def _make_frame(packet):
        string = json.dumps(packet, cls=VykedEncoder) + '!<^>!'
        string = string.encode()
        
        if packet['type'] in ['request', 'response']:
            packet_length = len(string)
            if packet_length >= _VALID_MAXIMUM_PACKET_SIZE_IN_BYTES:
                logging.error('{} Packet Size in Bytes: {} Endpoint Method: {}'.format(packet['type'].capitalize(), packet_length, packet['endpoint']))
        
        return string

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

        self.set_streamer()
        self._send_q.send()

    def set_streamer(self):
        self._obj_streamer = ObjectStreamer()
        self._obj_streamer.auto_listen(self, prefix='on_')
        self._obj_streamer.consume('[')

    def connection_lost(self, exc):
        self._connected = False
        self.logger.info('Peer closed %s', self._transport.get_extra_info('peername'))

    def send(self, packet: dict):
        frame = self._make_frame(packet)
        self._send_q.send(frame)
        self.logger.debug('Data sent: %s', frame.decode())

    def close(self):
        self._transport.write(']'.encode())  # end the json array
        self._transport.close()

    def data_received(self, byte_data):
        string_data = byte_data.decode()
        self.logger.debug('Data received: %s', string_data)
        json_parse = False

        try:
            pass
            try:
                string_data = self._partial_data + string_data
                partial_data = ''
                json_loads_time = self._json_loads_time

                for e in string_data.split('!<^>!'):
                    if e:
                        try:
                            start_time = time.time()
                            element = json.loads(partial_data + e)
                            partial_data = ''
                            json_parse = True
                            self.on_element(element)
                        except Exception as exc:
                            partial_data += e
                            self.logger.debug('Packet splitting: %s', self._partial_data)

                    json_loads_time += ((time.time() - start_time) * 1000)

                self._partial_data = partial_data
                if json_parse:
                    self._json_loads_time = 0.0
                else:
                    self._json_loads_time = json_loads_time

            except Exception as e:
                self.logger.error('Could not parse data: %s', string_data)
            # self._obj_streamer.consume(string_data)
        except:
            # recover from invalid data
            self.logger.exception('Invalid data received')
            self.set_streamer()
        
        if json_parse and json_loads_time >= _VALID_MAXIMUM_JSON_LOADS_TIME_IN_MS and element['type'] in ['request', 'response']:
            self.logger.error("{} Packet Endpoint: {}  Json Loads Time: {} ms".format(element['type'], element['endpoint'], json_loads_time))

    def on_object_stream_start(self):
        raise RuntimeError('Incorrect JSON Streaming Format: expect a JSON Array to start at root, got object')

    def on_object_stream_end(self):
        del self._obj_streamer
        raise RuntimeError('Incorrect JSON Streaming Format: expect a JSON Array to end at root, got object')

    def on_array_stream_start(self):
        self.logger.debug('Array Stream started')

    def on_array_stream_end(self):
        del self._obj_streamer
        self.logger.debug('Array Stream ended')

    def on_pair(self, pair):
        self.logger.debug('Pair {}'.format(pair))
        raise RuntimeError('Received a key-value pair object - expected elements only')


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
