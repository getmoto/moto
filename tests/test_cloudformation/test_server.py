from __future__ import unicode_literals

import json
from six.moves.urllib.parse import urlencode
import re
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_cloudformation_server_get():
    backend = server.create_backend_app("cloudformation")
    stack_name = 'test stack'
    test_client = backend.test_client()
    template_body = {
        "Resources": {},
    }
    res = test_client.action_json("CreateStack", StackName=stack_name,
        TemplateBody=json.dumps(template_body))
    stack_id = res["CreateStackResponse"]["CreateStackResult"]["StackId"]

    data = test_client.action_data("ListStacks")

    stacks = re.search("<StackId>(.*)</StackId>", data)

    list_stack_id = stacks.groups()[0]
    assert stack_id == list_stack_id
