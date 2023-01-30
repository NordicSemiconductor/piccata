import unittest
import time

import transport.tester
import transport.tsocket

class TestUtils:

    @staticmethod
    def create_test_receivers(name_list=[]):
        receiver_dict = {}
        for name in name_list:
            receiver_dict[name] = TestReceiver(name)
        return receiver_dict

    @staticmethod
    def register_test_receivers(transport=None, receiver_dict={}):
        for name, rec in receiver_dict.items():
            transport.register_receiver(rec)

class TestReceiver:

    __test__ = False

    def __init__(self, name):
        self.counter = 0
        self.name = name
        self.data = None
        self.remote = None
        self.local = None

    def receive(self, payload, remote, local):
        self.counter += 1
        self.data = payload
        self.remote = remote
        self.local = local

class TestTransport(unittest.TestCase):

    receiver_names = ["receiver_1", "receiver_2", "receiver_3"]

    def setUp(self):
        self.transport = transport.tester.TesterTransport()
        self.receivers = TestUtils.create_test_receivers(self.receiver_names)

    def test_transport_shall_register_receivers(self):
        '''Check if all receivers are successfully registered'''
        TestUtils.register_test_receivers(self.transport, self.receivers)

        self.assertEqual(len(self.transport._receivers), len(self.receiver_names))
        for index, rec in enumerate(self.receiver_names):
            self.assertEqual(self.transport._receivers[index].name, rec)

    def test_transport_shall_remove_receivers(self):
        '''Check if receiver is correctly removed'''
        TestUtils.register_test_receivers(self.transport, self.receivers)

        self.transport.remove_receiver(self.receivers["receiver_2"])

        self.assertEqual(len(self.transport._receivers), len(self.receivers) - 1)
        for rec in self.transport._receivers:
            self.assertNotEqual(rec, self.receivers["receiver_2"])
            self.assertNotEqual(rec.name, "receiver_2")

    def test_tranport_shall_call_receive_callbacks_when_receive_is_called(self):
        '''Check if receiver callback is called when transport receives data'''
        for name in self.receiver_names:
            self.transport.register_receiver(self.receivers[name])
            self.transport._receive(None, None, None)

        count = len(self.receivers)
        for name in self.receiver_names:
            self.assertEqual(self.receivers[name].counter, count)
            count -= 1

class TestSocketTransport(unittest.TestCase):

    TEST_PORT = 30000

    receiver_names = ["server", "client"]

    def setUp(self):
        self.server = transport.tsocket.SocketTransport(self.TEST_PORT)
        self.client = transport.tsocket.SocketTransport()
        self.receivers = TestUtils.create_test_receivers(self.receiver_names)

        self.server.open()
        self.client.open()

        self.server.register_receiver(self.receivers["server"])
        self.client.register_receiver(self.receivers["client"])

    def tearDown(self):
        self.server.close()
        self.client.close()

    def test_socket_transport_shall_close_socket_and_terminate_thread_on_close(self):
        self.assertNotEqual(self.server._sock, None)
        self.assertNotEqual(self.server._listener_thread, None)

        self.server.close()
        self.assertEqual(self.server._sock, None)
        self.assertEqual(self.server._listener_thread, None)

    def test_socket_transport_data_from_client_shall_reach_server(self):
        test_request = b"test request"
        test_response = b"test response"

        self.client.send(test_request, ("127.0.0.1", self.TEST_PORT))

        time.sleep(0.1)

        self.assertEqual(self.receivers["server"].counter, 1)
        self.assertEqual(self.receivers["server"].data, test_request)

        self.server.send(test_response, self.receivers["server"].remote)
        time.sleep(0.1)

        self.assertEqual(self.receivers["client"].counter, 1)
        self.assertEqual(self.receivers["client"].data, test_response)

if __name__ == "__main__":
    unittest.main()