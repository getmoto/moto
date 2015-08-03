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
    res = test_client.get(
        '/?{0}'.format(
            urlencode({
                "Action": "CreateStack",
                "StackName": stack_name,
                "TemplateBody": json.dumps(template_body)
            })
        ),
        headers={"Host": "cloudformation.us-east-1.amazonaws.com"}
    )
    stack_id = json.loads(res.data.decode("utf-8"))["CreateStackResponse"]["CreateStackResult"]["StackId"]

    res = test_client.get(
        '/?Action=ListStacks',
        headers={"Host": "cloudformation.us-east-1.amazonaws.com"}
    )
    stacks = re.search("<StackId>(.*)</StackId>", res.data.decode('utf-8'))

    list_stack_id = stacks.groups()[0]
    assert stack_id == list_stack_id
