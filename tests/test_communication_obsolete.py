'''
Created on 04-10-2015

@author: Maciej Wasilak
'''
from coap.constants import *
from coap import core
from coap import message
from coap import resource

import unittest
from threading import Timer
import sys
import ipaddress

SERVER_ADDRESS = ipaddress.ip_address(u"192.168.37.137")
SERVER_PORT = 5683

CLIENT_ADDRESS = ipaddress.ip_address(u"192.168.37.2")
CLIENT_PORT = 61616

PAYLOAD = "123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 "

class FakeTwoWayDatagramTransport:

    def __init__(self, recipient, address, port):
        self.recipient = recipient
        self.address = address
        self.port = port

    def write(self, packet, addr):
        timer = Timer(0.1, self.recipient.datagramReceived, (packet, (self.address, self.port)))
        timer.daemon = True
        timer.start()


class TextResource (resource.CoapResource):

    def __init__(self):
        resource.CoapResource.__init__(self)
        self.text = PAYLOAD

    def render_GET(self, request):
        response = message.Message(code=CONTENT, payload='%s' % (self.text,))
        return defer.succeed(response)

class TestGetRemoteResource(unittest.TestCase):
    """This is a very high-level test case which tests blockwise exchange between
       client and server."""

    def setUp(self):
        root = resource.CoapResource()
        text = TextResource()
        root.putChild('text', text)
        server_endpoint = resource.CoapEndpoint(root)
        self.server_protocol = core.Coap(server_endpoint)

        client_endpoint = resource.CoapEndpoint(None)
        self.client_protocol = core.Coap(client_endpoint)

        self.server_transport = FakeTwoWayDatagramTransport(recipient=self.client_protocol, address=SERVER_ADDRESS, port=SERVER_PORT)
        self.client_transport = FakeTwoWayDatagramTransport(recipient=self.server_protocol, address=CLIENT_ADDRESS, port=CLIENT_PORT)

        self.client_protocol.transport = self.client_transport
        self.server_protocol.transport = self.server_transport

    # def test_exchange(self):
    #     request = message.Message(code=GET)
    #     request.opt.uri_path = ('text',)
    #     request.remote = (SERVER_ADDRESS, SERVER_PORT)
    #     d = self.client_protocol.request(request)
    #     d.addCallback(self.evaluateResponse)
    #     return d

    # def test_get_same_block_twice(self):
    #     request = message.Message(code=GET)
    #     request.opt.uri_path = ('text',)
    #     request.opt.block2 = (0, 0, 0) # block = 0, more = 0, size_exp = 0
    #     request.remote = (SERVER_ADDRESS, SERVER_PORT)
    #     d = self.client_protocol.request(request)
    #     d.addCallback(self.evaluateResponse)
    #     return d

    def evaluateResponse(self, response):
        for value in self.client_protocol.recent_local_ids.itervalues():
            value[1].cancel()
        for value in self.server_protocol.recent_remote_ids.itervalues():
            value[1].cancel()
        self.assertEqual(response.payload, PAYLOAD)


# log.startLogging(sys.stdout)
# if __name__ == "__main__":
#     unittest.main()