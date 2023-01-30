import unittest
import time

from piccata import core
from piccata import message
from piccata import resource
from piccata.constants import *
from transport import tester

from ipaddress import ip_address
import sys

TEST_PAYLOAD = b"testPayload"
TEST_TOKEN = b"abcd"
TEST_MID = 1000

TEST_ADDRESS = ip_address(u"12.34.56.78")
TEST_PORT = 12345

TEST_LOCAL_ADDRESS = ip_address(u"10.10.10.10")
TEST_LOCAL_PORT = 20000

class TestResource(resource.CoapResource):

    __test__ = False

    def __init__(self):
        resource.CoapResource.__init__(self)
        self.resource_handler = None
        self.call_counter = 0

    def render_GET(self, request):
        self.call_counter += 1

        rsp = None
        if self.resource_handler != None:
            rsp = self.resource_handler(request)
        return rsp

class TestCoap(unittest.TestCase):

    def setUp(self):
        root = resource.CoapResource()
        self.test_resource = TestResource()
        root.put_child(b'test', self.test_resource)
        endpoint = resource.CoapEndpoint(root)

        self.transport = tester.TesterTransport()
        self.protocol = core.Coap(self.transport)
        self.request_handler = resource.ResourceManager(endpoint)

        self.transport.register_receiver(self.protocol)
        self.protocol.register_request_handler(self.request_handler)
        self.transport.open()

        self.resource_handler = None
        self.responseResult = None
        self.callbackCounter = 0

    def tearDown(self):
        self.transport.close()

    def assertMessageInTransport(self, message, remote, count=None):
        data = message.encode()

        self.assertTupleEqual(self.transport.tester_remote, remote)
        self.assertEqual(self.transport.tester_data, data)
        if count != None:
            self.assertEqual(self.transport.output_count, count)

    def callback(self, result, request, response):
        self.responseResult = result
        self.callbackCounter += 1

    def assertInRetransmissionList(self, message):
        self.assertIn(message.mid, self.protocol._message_layer._active_exchanges)
        self.assertEqual(self.protocol._message_layer._active_exchanges[message.mid][0], message)

    def assertNotInRetransmissionList(self, mid):
        self.assertNotIn(mid, self.protocol._message_layer._active_exchanges)

    def assertInOutgoingRequestList(self, request):
        key = (request.token, request.remote)
        self.assertIn(key, self.protocol._transaction_layer._outgoing_requests)
        self.assertEqual(self.protocol._transaction_layer._outgoing_requests[key][1], (self.callback, None, None))

    def assertNotInOutgoingRequestList(self, token, remote):
        self.assertNotIn((token, remote), self.protocol._transaction_layer._outgoing_requests)

    def assertInDeduplicationList(self, mid, remote, response=None):
        key = (mid, remote)
        self.assertIn(key, self.protocol._message_layer._recent_remote_ids)
        if response != None:
            self.assertEqual(len(self.protocol._message_layer._recent_remote_ids[key]), 3)
            self.assertEqual(self.protocol._message_layer._recent_remote_ids[key][2], response)

    def assertNotInDeduplicationList(self, mid, remote):
        self.assertIn((mid, remote), self.protocol._message_layer._recent_remote_ids)

class TestCoapSendRequestPath(TestCoap):

    def test_coap_core_shall_return_error_when_non_request_message_is_sent_as_request(self):
        req = message.Message(CON, TEST_MID, CHANGED, TEST_PAYLOAD, TEST_TOKEN)
        req.remote = (TEST_ADDRESS, TEST_PORT)
        self.assertRaises(ValueError, self.protocol.request, (req))

    def test_coap_core_shall_queue_CON_request_on_retransmission_list(self):
        req = message.Message(CON, TEST_MID, GET, TEST_PAYLOAD, TEST_TOKEN)
        req.remote = (TEST_ADDRESS, TEST_PORT)
        self.protocol.request(req)

        self.assertMessageInTransport(req, req.remote, 1)
        self.assertInRetransmissionList(req)

    def test_coap_core_shall_not_queue_NON_request_on_retransmission_list(self):
        req = message.Message(NON, TEST_MID, GET, TEST_PAYLOAD, TEST_TOKEN)
        req.remote = (TEST_ADDRESS, TEST_PORT)
        self.protocol.request(req)

        self.assertMessageInTransport(req, req.remote, 1)
        self.assertNotInRetransmissionList(TEST_MID)

    def test_coap_core_shall_queue_request_on_pending_response_list_if_callback_is_registered(self):
        req = message.Message(CON, TEST_MID, GET, TEST_PAYLOAD, TEST_TOKEN)
        req.remote = (TEST_ADDRESS, TEST_PORT)
        self.protocol.request(req, self.callback)

        self.assertInOutgoingRequestList(req)

    def test_coap_core_shall_not_queue_request_on_pending_response_list_if_callback_is_not_registered(self):
        req = message.Message(CON, TEST_MID, GET, TEST_PAYLOAD, TEST_TOKEN)
        req.remote = (TEST_ADDRESS, TEST_PORT)
        self.protocol.request(req)

        self.assertNotInOutgoingRequestList(TEST_TOKEN, req.remote)

class TestCoapSendResponsePath(TestCoap):

    def setUp(self):
        super(TestCoapSendResponsePath, self).setUp()
        self.test_resource.resource_handler = self.responder

    def responder(self, request):
        return self.rsp

    def test_coap_core_shall_return_error_when_non_response_message_is_sent_as_response(self):

        self.rsp = message.Message(ACK, TEST_MID, GET, b"", TEST_TOKEN)

        # Prepare fake request to trigger response sending.
        req = message.Message(CON, TEST_MID, GET, b"", TEST_TOKEN)
        req.opt.uri_path = (b"test", )
        raw = req.encode()

        # Check that error is raised on incorrect response type
        self.assertRaises(ValueError, self.transport._receive, raw, (TEST_ADDRESS, TEST_PORT), (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

    def test_coap_core_shall_queue_CON_response_on_retransmission_list(self):

        self.rsp = message.Message(CON, TEST_MID + 1, CONTENT, b"", TEST_TOKEN)

        # Prepare fake request to trigger response sending.
        req = message.Message(NON, TEST_MID, GET, b"", TEST_TOKEN)
        req.opt.uri_path = (b"test", )
        raw = req.encode()

        # Simulate fake request reception
        self.transport._receive(raw, (TEST_ADDRESS, TEST_PORT), (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

        # Validate that response was handled properly
        self.assertInRetransmissionList(self.rsp)

    def test_coap_core_shall_not_queue_NON_response_on_retransmission_list(self):

        self.rsp = message.Message(NON, TEST_MID + 1, CONTENT, b"", TEST_TOKEN)

        # Prepare fake request to trigger response sending.
        req = message.Message(NON, TEST_MID, GET, b"", TEST_TOKEN)
        req.opt.uri_path = (b"test", )
        raw = req.encode()

        # Simulate fake request reception
        self.transport._receive(raw, (TEST_ADDRESS, TEST_PORT), (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

        # Validate that response was handled properly
        self.assertNotInRetransmissionList(TEST_MID + 1)

    def test_coap_core_shall_queue_ACK_and_RST_response_on_responded_list(self):

        self.rsp = message.Message(ACK, TEST_MID, CONTENT, b"", TEST_TOKEN)

        # Prepare fake request to trigger response sending.
        req = message.Message(NON, TEST_MID, GET, b"", TEST_TOKEN)
        req.opt.uri_path = (b"test", )
        raw = req.encode()

        remote = (TEST_ADDRESS, TEST_PORT)

        # Simulate fake request reception
        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

        # Validate that request was added to the deduplication list, and response was registered.
        self.assertInDeduplicationList(TEST_MID, remote, self.rsp)

class TestCoapReceiveRequestPath(TestCoap):

    def responder(self, request):
        return self.rsp

    def test_coap_core_shall_store_received_CON_request_on_deduplication_list(self):
        req = message.Message(CON, TEST_MID, GET, TEST_PAYLOAD, TEST_TOKEN)
        raw = req.encode()
        remote = (TEST_ADDRESS, TEST_PORT)

        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))
        self.assertInDeduplicationList(TEST_MID, remote)

    def test_coap_core_shall_store_received_NON_request_on_deduplication_list(self):
        req = message.Message(NON, TEST_MID, GET, TEST_PAYLOAD, TEST_TOKEN)
        raw = req.encode()
        remote = (TEST_ADDRESS, TEST_PORT)

        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))
        self.assertInDeduplicationList(TEST_MID, remote)

    def check_that_duplicated_request_is_automatically_responded(self):

        req = message.Message(CON, TEST_MID, GET, TEST_PAYLOAD, TEST_TOKEN)
        req.opt.uri_path = (b"test", )
        raw = req.encode()
        remote = (TEST_ADDRESS, TEST_PORT)

        # Receive first request.
        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

        # Verify that resource handler was called and response sent.
        self.assertEqual(self.test_resource.call_counter, 1)
        self.assertEqual(self.transport.output_count, 1)
        self.assertTupleEqual(self.transport.tester_remote, remote)
        self.assertEqual(self.transport.tester_data, self.rsp.encode())

        # Receive duplicated request.
        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

        # Verify that resource handler was not called but reponse was resent.
        self.assertEqual(self.test_resource.call_counter, 1)
        self.assertEqual(self.transport.output_count, 2)
        self.assertTupleEqual(self.transport.tester_remote, remote)
        self.assertEqual(self.transport.tester_data, self.rsp.encode())

    def test_coap_core_shall_resend_ACK_on_duplicated_CON_request(self):

        self.test_resource.resource_handler = self.responder
        self.rsp = message.Message(ACK, TEST_MID, CONTENT, TEST_PAYLOAD, TEST_TOKEN)

        self.check_that_duplicated_request_is_automatically_responded()

    def test_coap_core_shall_resend_RST_on_duplicated_CON_request(self):
        self.test_resource.resource_handler = self.responder
        self.rsp = message.Message(RST, TEST_MID, CONTENT, TEST_PAYLOAD, TEST_TOKEN)

        self.check_that_duplicated_request_is_automatically_responded()

    def test_coap_core_shall_ignore_duplicated_CON_if_no_response_was_sent_to_the_original_message(self):

        # No resopnse is sent.
        req = message.Message(CON, TEST_MID, GET, TEST_PAYLOAD, TEST_TOKEN)
        req.opt.uri_path = (b"test", )
        raw = req.encode()
        remote = (TEST_ADDRESS, TEST_PORT)

        # Receive first request.
        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

        # Verify that resource handler was called..
        self.assertEqual(self.test_resource.call_counter, 1)

        # Receive duplicated request.
        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

        # Verify that resource handler was not called and no response sent.
        self.assertEqual(self.test_resource.call_counter, 1)
        self.assertEqual(self.transport.output_count, 0)

    def test_coap_core_shall_ignore_duplicated_NON_request(self):

        self.test_resource.resource_handler = self.responder
        self.rsp = message.Message(NON, TEST_MID, CONTENT, TEST_PAYLOAD, TEST_TOKEN)

        req = message.Message(NON, TEST_MID, GET, TEST_PAYLOAD, TEST_TOKEN)
        req.opt.uri_path = (b"test", )
        raw = req.encode()
        remote = (TEST_ADDRESS, TEST_PORT)

        # Receive first request.
        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

        # Verify that resource handler was called and response sent.
        self.assertEqual(self.test_resource.call_counter, 1)
        self.assertEqual(self.transport.output_count, 1)
        self.assertTupleEqual(self.transport.tester_remote, remote)
        self.assertEqual(self.transport.tester_data, self.rsp.encode())

        # Receive duplicated request.
        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

        # Verify that resource handler was not called and nothing was transmitted.
        self.assertEqual(self.test_resource.call_counter, 1)
        self.assertEqual(self.transport.output_count, 1)

class TestCoapReceiveResponsePath(TestCoap):

    def send_initial_request(self, remote, timeout = None):
        self.req = message.Message(CON, TEST_MID, GET, b"", TEST_TOKEN)
        self.req.remote = remote
        if timeout != None:
            self.req.timeout = timeout
        self.protocol.request(self.req, self.callback)

    def receive_ack_response(self, remote):
        rsp = message.Message(ACK, TEST_MID, CONTENT, TEST_PAYLOAD, TEST_TOKEN)
        raw = rsp.encode()
        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

    def receive_empty_ack_response(self, remote):
        rsp = message.Message(ACK, TEST_MID, EMPTY)
        raw = rsp.encode()
        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

    def receive_rst_response(self, remote):
        rsp = message.Message(RST, TEST_MID, EMPTY)
        raw = rsp.encode()
        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

    def receive_con_response(self, remote):
        rsp = message.Message(CON, TEST_MID + 1, CONTENT, TEST_PAYLOAD, TEST_TOKEN)
        raw = rsp.encode()
        self.transport._receive(raw, remote, (TEST_LOCAL_ADDRESS, TEST_LOCAL_PORT))

    def test_coap_core_shall_remove_CON_message_from_retransmission_list_if_ACK_is_received(self):
        remote = (TEST_ADDRESS, TEST_PORT)

        # Send request so it could be queued on retransmisison list.
        self.send_initial_request(remote)
        self.assertInRetransmissionList(self.req)

        # Simulate receiveing response and verify that retransmission was removed.
        self.receive_ack_response(remote)
        self.assertNotInRetransmissionList(TEST_MID);

    def test_coap_core_shall_remove_CON_message_from_retransmission_list_if_RST_is_received(self):
        remote = (TEST_ADDRESS, TEST_PORT)

        # Send request so it could be queued on retransmisison list.
        self.send_initial_request(remote)
        self.assertInRetransmissionList(self.req)

        # Simulate receiveing response and verify that retransmission was removed.
        self.receive_rst_response(remote)
        self.assertNotInRetransmissionList(TEST_MID);

    def test_coap_core_shall_remove_request_from_pending_response_list_if_response_is_received(self):
        remote = (TEST_ADDRESS, TEST_PORT)

        # Send request so it could be queued on retransmisison list.
        self.send_initial_request(remote)
        self.assertInOutgoingRequestList(self.req)

        # Simulate receiveing response and verify that retransmission was removed.
        self.receive_ack_response(remote)
        self.assertNotInOutgoingRequestList(TEST_TOKEN, remote)

    def test_coap_core_shall_remove_request_form_pending_response_list_if_RST_is_received(self):
        remote = (TEST_ADDRESS, TEST_PORT)

        # Send request so it could be queued on retransmisison list.
        self.send_initial_request(remote)
        self.assertInOutgoingRequestList(self.req)

        # Simulate receiveing response and verify that retransmission was removed.
        self.receive_rst_response(remote)
        self.assertNotInOutgoingRequestList(TEST_TOKEN, remote)

    def test_coap_core_shall_call_application_callback_with_success_on_response_received(self):
        remote = (TEST_ADDRESS, TEST_PORT)
        self.send_initial_request(remote)
        self.receive_ack_response(remote)
        self.assertEqual(self.responseResult, RESULT_SUCCESS)

    def test_coap_core_shall_call_application_callback_with_error_on_RST_received(self):
        remote = (TEST_ADDRESS, TEST_PORT)
        self.send_initial_request(remote)
        self.receive_rst_response(remote)
        self.assertEqual(self.responseResult, RESULT_RESET)

    def test_coap_core_shall_call_application_callback_with_error_on_request_cancelled(self):
        remote = (TEST_ADDRESS, TEST_PORT)
        self.send_initial_request(remote)
        self.protocol.cancel_request(self.req)
        self.assertEqual(self.responseResult, RESULT_CANCELLED)

    def test_coap_core_shall_call_application_callback_with_timeout_on_no_response_received(self):
        remote = (TEST_ADDRESS, TEST_PORT)
        self.send_initial_request(remote, timeout = 0.5)
        time.sleep(0.6)
        self.assertEqual(self.responseResult, RESULT_TIMEOUT)

    def test_coap_core_shall_resend_ACK_on_duplicated_CON_response(self):
        # Send initial request.
        remote = (TEST_ADDRESS, TEST_PORT)
        raw_empty_ack = message.Message(ACK, TEST_MID + 1, EMPTY).encode()
        self.send_initial_request(remote)
        self.assertEqual(self.transport.output_count, 1)

        # Simulate receiving empty ACK and verify that no callback was called.
        self.receive_empty_ack_response(remote)
        self.assertIsNone(self.responseResult)

        # Receive separete CON response amd verify that callback was called and empty ACK was automatically sent.
        self.receive_con_response(remote)
        self.assertEqual(self.transport.output_count, 2)
        self.assertEqual(self.transport.tester_data, raw_empty_ack)
        self.assertEqual(self.callbackCounter, 1)
        self.assertEqual(self.responseResult, RESULT_SUCCESS)

        # Receive separate response duplicate, verify that empty ACK was forwarded and no callback was called.
        self.receive_con_response(remote)
        self.assertEqual(self.transport.output_count, 3)
        self.assertEqual(self.transport.tester_data, raw_empty_ack)
        self.assertEqual(self.callbackCounter, 1)

if __name__ == "__main__":
    unittest.main()