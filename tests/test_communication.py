from piccata.constants import *
from piccata import core
from piccata import message
from piccata import resource
from transport import tsocket

from ipaddress import ip_address
import sys

import unittest
import time

SERVER_PORT = 5683

PAYLOAD = b"123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 "

class TextResource(resource.CoapResource):

    def __init__(self):
        resource.CoapResource.__init__(self)
        self.text = PAYLOAD

    def render_GET(self, request):
        response = message.Message(code=CONTENT, payload=self.text)
        return response

class TestClientServerCommunication(unittest.TestCase):

    def setUp(self):
        self.stopWaiting = False
        self.responseReceived = False
        self.responsePayload = ""

        server_root = resource.CoapResource()
        text = TextResource()
        server_root.put_child(b'text', text)
        server_endpoint = resource.CoapEndpoint(server_root)

        self.server_transport = tsocket.SocketTransport(SERVER_PORT)
        self.server_protocol = core.Coap(self.server_transport)
        self.server_request_handler = resource.ResourceManager(server_endpoint)
        self.server_transport.register_receiver(self.server_protocol)
        self.server_protocol.register_request_handler(self.server_request_handler)

        self.client_transport = tsocket.SocketTransport()
        self.client_protocol = core.Coap(self.client_transport)
        self.client_transport.register_receiver(self.client_protocol)

        self.server_transport.open()
        self.client_transport.open()

    def tearDown(self):
        self.server_transport.close()
        self.client_transport.close()

    def _handle_text_response(self, result, request, response):
        if result == RESULT_SUCCESS:
            self.responsePayload = response.payload
            self.responseReceived = True
            self.stopWaiting = True
        else:
            self.stopWaiting = True
            self.assertFalse(True, "No response received.")

    def test_client_server_communication(self):
        request = message.Message(mtype = CON, code=GET)
        request.opt.uri_path = (b"text", )
        request.remote = (ip_address(u"127.0.0.1"), SERVER_PORT)
        request.timeout = ACK_TIMEOUT
        request.payload = b""
        req = self.client_protocol.request(request, self._handle_text_response)

        counter = 0
        while not self.stopWaiting:
            counter += 1
            time.sleep(0.01)
            self.assertLess(counter, 500, "Timeout while waiting for callback from Coap")

        self.assertTrue(self.responseReceived)
        self.assertEqual(self.responsePayload, PAYLOAD)

if __name__ == "__main__":
    unittest.main()