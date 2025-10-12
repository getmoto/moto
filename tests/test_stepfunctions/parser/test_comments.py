import json
from unittest import SkipTest

from moto import mock_aws, settings

from . import verify_execution_result


@mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
def test_comments_in_parameters():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Don't need to test this in ServerMode")
    tmpl_name = "comments/comments_in_parameters"
    exec_input = {"type": "Public"}

    def _verify_result(client, execution, execution_arn):
        output = json.loads(execution["output"])
        assert output == {
            "Comment": "Comment text",
            "comment": "comment text",
            "constant": "constant text",
        }

    verify_execution_result(
        _verify_result, "SUCCEEDED", tmpl_name, exec_input=json.dumps(exec_input)
    )
