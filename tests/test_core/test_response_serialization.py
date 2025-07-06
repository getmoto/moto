from botocore.model import ServiceModel

from moto.core.responses import ActionContext, ActionResult, BaseResponse, EmptyResult
from moto.core.serialize import QuerySerializer, never_return

TEST_MODEL = {
    "metadata": {"protocol": "query", "apiVersion": "2014-01-01"},
    "documentation": "",
    "operations": {
        "TestOperation": {
            "name": "TestOperation",
            "http": {
                "method": "POST",
                "requestUri": "/",
            },
            "output": {"shape": "OutputShape"},
        }
    },
    "shapes": {
        "OutputShape": {
            "type": "structure",
            "members": {
                "string": {"shape": "StringType"},
                "TransformerTest": {"shape": "StringType"},
            },
        },
        "StringType": {
            "type": "string",
        },
    },
}


def test_response_result_execution() -> None:
    """Exercise various response result execution paths."""

    class TestResponseClass(BaseResponse):
        RESPONSE_KEY_PATH_TO_TRANSFORMER = {"OutputShape.TransformerTest": never_return}

    class TestResponseObject:
        string = "test-string"
        TransformerTest = "some data"

    service_model = ServiceModel(TEST_MODEL)
    operation_model = service_model.operation_model("TestOperation")
    serializer_class = QuerySerializer
    response_class = TestResponseClass

    context = ActionContext(
        service_model, operation_model, serializer_class, response_class
    )

    result = ActionResult(TestResponseObject())
    _, __, body = result.execute_result(context)
    assert "test-string" in body
    assert "TransformerTest" not in body

    result = EmptyResult()
    _, __, body = result.execute_result(context)
    assert "<OutputShapeResult/>" in body
