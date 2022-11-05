import unittest
from moto import mock_dynamodb
import socket


class TestSocketPair(unittest.TestCase):
    @mock_dynamodb
    def test_socket_pair(self):
        a, b = socket.socketpair()
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        if a:
            a.close()
        if b:
            b.close()
