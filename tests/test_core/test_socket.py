import unittest
from moto import mock_dynamodb2_deprecated, mock_dynamodb2
import socket

from six import PY3


class TestSocketPair(unittest.TestCase):

    @mock_dynamodb2_deprecated
    def test_asyncio_deprecated(self):
        if PY3:
            self.assertIn(
                'moto.packages.httpretty.core.fakesock.socket',
                str(socket.socket),
                'Our mock should be present'
            )
            import asyncio
            self.assertIsNotNone(asyncio.get_event_loop())

    @mock_dynamodb2_deprecated
    def test_socket_pair_deprecated(self):

        # In Python2, the fakesocket is not set, for some reason.
        if PY3:
            self.assertIn(
                'moto.packages.httpretty.core.fakesock.socket',
                str(socket.socket),
                'Our mock should be present'
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
