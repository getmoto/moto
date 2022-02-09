from datetime import datetime
import re

import sure  # noqa # pylint: disable=unused-import

import moto.server as server

"""
Test the different server responses
"""


def test_ses_list_identities():
    backend = server.create_backend_app("ses")
    test_client = backend.test_client()

    res = test_client.get("/?Action=ListIdentities")
    res.data.should.contain(b"ListIdentitiesResponse")


def test_ses_get_send_statistics():
    backend = server.create_backend_app("ses")
    test_client = backend.test_client()

    res = test_client.get("/?Action=GetSendStatistics")
    res.data.should.contain(b"GetSendStatisticsResponse")

    # Timestamps must be in ISO 8601 format
    groups = re.search("<Timestamp>(.*)</Timestamp>", res.data.decode("utf-8"))
    timestamp = groups.groups()[0]
    datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
