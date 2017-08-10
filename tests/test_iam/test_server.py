from __future__ import unicode_literals

import json

import re
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_iam_server_get():
    backend = server.create_backend_app("iam")
    test_client = backend.test_client()

    group_data = test_client.action_data(
        "CreateGroup", GroupName="test group", Path="/")
    group_id = re.search("<GroupId>(.*)</GroupId>", group_data).groups()[0]

    groups_data = test_client.action_data("ListGroups")
    groups_ids = re.findall("<GroupId>(.*)</GroupId>", groups_data)

    assert group_id in groups_ids
