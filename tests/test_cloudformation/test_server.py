import json
import re

import moto.server as server

"""
Test the different server responses
"""


def test_cloudformation_server_get():
    backend = server.create_backend_app("cloudformation")
    stack_name = "test stack"
    test_client = backend.test_client()
    template_body = {"Resources": {}}
    create_stack_resp = test_client.action_data(
        "CreateStack", StackName=stack_name, TemplateBody=json.dumps(template_body)
    )
    assert "<CreateStackResponse>" in create_stack_resp
    assert "<StackId>" in create_stack_resp
    stack_id_from_create = re.search(
        "<StackId>(.*)</StackId>", create_stack_resp
    ).groups()[0]

    list_stacks_resp = test_client.action_data("ListStacks")
    stack_id_from_list = re.search(
        "<StackId>(.*)</StackId>", list_stacks_resp
    ).groups()[0]

    assert stack_id_from_create == stack_id_from_list
