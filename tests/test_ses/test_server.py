"""Test the different server responses."""
from datetime import datetime
import re

import moto.server as server


def test_ses_list_identities():
    backend = server.create_backend_app("ses")
    test_client = backend.test_client()

    res = test_client.get("/?Action=ListIdentities")
    assert b"ListIdentitiesResponse" in res.data


def test_ses_get_send_statistics():
    backend = server.create_backend_app("ses")
    test_client = backend.test_client()

    res = test_client.get("/?Action=GetSendStatistics")
    assert b"GetSendStatisticsResponse" in res.data

    # Timestamps must be in ISO 8601 format
    groups = re.search("<Timestamp>(.*)</Timestamp>", res.data.decode("utf-8"))
    timestamp = groups.groups()[0]
    datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
