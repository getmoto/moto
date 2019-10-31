# #!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import mock

from moto.packages.httpretty.core import (
    HTTPrettyRequest,
    fake_gethostname,
    fake_gethostbyname,
)


def test_parse_querystring():

    core = HTTPrettyRequest(headers="test test HTTP/1.1")

    qs = "test test"
    response = core.parse_querystring(qs)

    assert response == {}


def test_parse_request_body():
    core = HTTPrettyRequest(headers="test test HTTP/1.1")

    qs = "test"
    response = core.parse_request_body(qs)

    assert response == "test"


def test_fake_gethostname():

    response = fake_gethostname()

    assert response == "localhost"


def test_fake_gethostbyname():

    host = "test"
    response = fake_gethostbyname(host=host)

    assert response == "127.0.0.1"
