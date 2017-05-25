'''
Created on 16-10-2012

@author: Maciej Wasilak
'''
import unittest
from piccata import core
from piccata import message
from piccata import option
from piccata import constants

class TestMessage(unittest.TestCase):

    def test_encode(self):
        msg1 = message.Message(mtype=constants.CON, mid=0, token='')
        binary1 = chr(64)+chr(0)+chr(0)+chr(0)
        self.assertEqual(msg1.encode(), binary1, "wrong encode operation for empty CON message")

        msg2 = message.Message(mtype=constants.ACK, mid=0xBC90, code=constants.CONTENT, payload="temp = 22.5 C", token='q')
        msg2.opt.etag = "abcd"
        binary2 = chr(97)+chr(69)+chr(188)+chr(144)+chr(113)+chr(68)+"abcd"+chr(255)+"temp = 22.5 C"
        self.assertEqual(msg2.encode(), binary2, "wrong encode operation for ACK message with payload, and Etag option")

        msg3 = message.Message()
        self.assertRaises(TypeError, msg3.encode)

    def test_decode(self):
        rawdata1 = chr(64)+chr(0)+chr(0)+chr(0)
        self.assertEqual(message.Message.decode(rawdata1).mtype, constants.CON, "wrong message type for decode operation")
        self.assertEqual(message.Message.decode(rawdata1).mid, 0, "wrong message ID for decode operation")
        self.assertEqual(message.Message.decode(rawdata1).code, constants.EMPTY, "wrong message code for decode operation")
        self.assertEqual(message.Message.decode(rawdata1).token, '', "wrong message token for decode operation")
        self.assertEqual(message.Message.decode(rawdata1).payload, '', "wrong message payload for decode operation")
        rawdata2 = chr(97)+chr(69)+chr(188)+chr(144)+chr(113)+chr(68)+"abcd"+chr(255)+"temp = 22.5 C"
        self.assertEqual(message.Message.decode(rawdata2).mtype, constants.ACK, "wrong message type for decode operation")
        self.assertEqual(message.Message.decode(rawdata2).mid, 0xBC90, "wrong message ID for decode operation")
        self.assertEqual(message.Message.decode(rawdata2).code, constants.CONTENT, "wrong message code for decode operation")
        self.assertEqual(message.Message.decode(rawdata2).token, 'q', "wrong message token for decode operation")
        self.assertEqual(message.Message.decode(rawdata2).payload, 'temp = 22.5 C', "wrong message payload for decode operation")
        self.assertEqual(message.Message.decode(rawdata2).opt.etags, ["abcd"], "problem with etag option decoding for decode operation")
        self.assertEqual(len(message.Message.decode(rawdata2).opt._options), 1, "wrong number of options after decode operation")

class TestReadExtendedFieldValue(unittest.TestCase):

    def test_read_extended_field_value(self):
        arguments = ((0, "aaaa"),
                     (0, ""),
                     (1, "aaaa"),
                     (12,"aaaa"),
                     (13,"aaaa"),
                     (13,"a"),
                     (14,"aaaa"),
                     (14,"aa"))
        results = ((0, "aaaa"),
                   (0, ""),
                   (1, "aaaa"),
                   (12,"aaaa"),
                   (110,"aaa"),
                   (110,""),
                   (25198,"aa"),
                   (25198,""))

        for argument, result in zip(arguments, results):
            self.assertEqual(option.Options.read_extended_field_value(argument[0], argument[1]), result,'wrong result for value : '+ str(argument[0]) + ' , rawdata : ' + argument[1])


class TestUintOption(unittest.TestCase):

    def test_encode(self):
        arguments = (0,
                     1,
                     2,
                     40,
                     50,
                     255,
                     256,
                     1000)
        results =   ("",
                     chr(1),
                     chr(2),
                     chr(40),
                     chr(50),
                     chr(255),
                     chr(1)+chr(0),
                     chr(3)+chr(232))
        for argument, result in zip(arguments, results):
            self.assertEqual(option.UintOption(0,argument).encode(), result,'wrong encode operation for option value : '+ str(argument))

    def test_decode(self):
        arguments = ("",
                     chr(1),
                     chr(2),
                     chr(40),
                     chr(50),
                     chr(255),
                     chr(1)+chr(0),
                     chr(3)+chr(232))
        results =   (0,
                     1,
                     2,
                     40,
                     50,
                     255,
                     256,
                     1000)
        for argument, result in zip(arguments, results):
            self.assertEqual(option.UintOption(0).decode(argument).value, result,'wrong decode operation for rawdata : '+ str(argument))

    def test_length(self):
        arguments = (0,
                     1,
                     2,
                     40,
                     50,
                     255,
                     256,
                     1000)
        results =   (0,
                     1,
                     1,
                     1,
                     1,
                     1,
                     2,
                     2)
        for argument, result in zip(arguments, results):
            self.assertEqual(option.UintOption(0,argument)._length(), result,'wrong length for option value : '+ str(argument))


class TestOptions(unittest.TestCase):

    def test_setUriPath(self):
        opt1 = option.Options()
        opt1.uri_path = ["core"]
        self.assertEqual(len(opt1.get_option(constants.URI_PATH)), 1, 'wrong uri_path setter operation for single string argument')
        self.assertEqual(opt1.get_option(constants.URI_PATH)[0].value, "core", 'wrong uri_path setter operation for single string argument')
        opt2 = option.Options()
        opt2.uri_path = ("core",".well-known")
        self.assertEqual(len(opt2.get_option(constants.URI_PATH)), 2, 'wrong uri_path setter operation for 2-element tuple argument')
        self.assertEqual(opt2.get_option(constants.URI_PATH)[0].value, "core", 'wrong uri_path setter operation for 2-element tuple argument')
        self.assertEqual(opt2.get_option(constants.URI_PATH)[1].value, ".well-known", 'wrong uri_path setter operation for 2-element tuple argument')
        opt3 = option.Options()
        self.assertRaises(ValueError, setattr, opt3, "uri_path", "core")

if __name__ == "__main__":
    unittest.main()