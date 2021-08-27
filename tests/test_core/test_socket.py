import unittest
from moto import mock_dynamodb2_deprecated, mock_dynamodb2
import socket


class TestSocketPair(unittest.TestCase):
    @mock_dynamodb2_deprecated
    def test_asyncio_deprecated(self):
        self.assertIn(
            "httpretty.core.fakesock.socket",
            str(socket.socket),
            "Our mock should be present",
        )
        import asyncio

        self.assertIsNotNone(asyncio.get_event_loop())

    @mock_dynamodb2_deprecated
    def test_socket_pair_deprecated(self):

        self.assertIn(
            "httpretty.core.fakesock.socket",
            str(socket.socket),
            "Our mock should be present",
        )
        a, b = socket.socketpair()
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        if a:
            a.close()
        if b:
            b.close()

    @mock_dynamodb2
    def test_socket_pair(self):
        a, b = socket.socketpair()
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        if a:
            a.close()
        if b:
            b.close()
