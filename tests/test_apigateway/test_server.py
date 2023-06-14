import json

import moto.server as server

"""
Test the different server responses
"""


def test_list_apis():
    backend = server.create_backend_app("apigateway")
    test_client = backend.test_client()

    res = test_client.get("/restapis")
    assert "item" in json.loads(res.data)


def test_usage_plans_apis():
    backend = server.create_backend_app("apigateway")
    test_client = backend.test_client()

    # List usage plans (expect empty)
    res = test_client.get("/usageplans")
    assert len(json.loads(res.data)["item"]) == 0

    # Create usage plan
    res = test_client.post("/usageplans", data=json.dumps({"name": "test"}))
    created_plan = json.loads(res.data)
    assert created_plan["name"] == "test"

    # List usage plans (expect 1 plan)
    res = test_client.get("/usageplans")
    assert len(json.loads(res.data)["item"]) == 1

    # Get single usage plan
    res = test_client.get(f"/usageplans/{created_plan['id']}")
    fetched_plan = json.loads(res.data)
    assert fetched_plan == created_plan

    # Not existing usage plan
    res = test_client.get("/usageplans/not_existing")
    assert res.status_code == 404

    # Delete usage plan
    res = test_client.delete(f"/usageplans/{created_plan['id']}")
    assert res.data == b"{}"

    # List usage plans (expect empty again)
    res = test_client.get("/usageplans")
    assert len(json.loads(res.data)["item"]) == 0


def test_usage_plans_keys():
    backend = server.create_backend_app("apigateway")
    test_client = backend.test_client()
    usage_plan_id = "test_plan_id"

    # Create API key to be used in tests
    res = test_client.post("/apikeys", data=json.dumps({"name": "test"}))
    created_api_key = json.loads(res.data)

    # List usage plans keys (expect empty)
    res = test_client.get(f"/usageplans/{usage_plan_id}/keys")
    assert len(json.loads(res.data)["item"]) == 0

    # Invalid api key (does not exists at all)
    res = test_client.get(f"/usageplans/{usage_plan_id}/keys/not_existing")
    assert res.status_code == 404

    # not existing usage plan with existing api key
    res = test_client.get(f"/usageplans/not_existing/keys/{created_api_key['id']}")
    assert res.status_code == 404

    # not jet added api key
    res = test_client.get(f"/usageplans/{usage_plan_id}/keys/{created_api_key['id']}")
    assert res.status_code == 404

    # Create usage plan key
    res = test_client.post(
        f"/usageplans/{usage_plan_id}/keys",
        data=json.dumps({"keyId": created_api_key["id"], "keyType": "API_KEY"}),
    )
    created_usage_plan_key = json.loads(res.data)

    # List usage plans keys (expect 1 key)
    res = test_client.get(f"/usageplans/{usage_plan_id}/keys")
    assert len(json.loads(res.data)["item"]) == 1

    # Get single usage plan key
    res = test_client.get(f"/usageplans/{usage_plan_id}/keys/{created_api_key['id']}")
    fetched_plan_key = json.loads(res.data)
    assert fetched_plan_key == created_usage_plan_key

    # Delete usage plan key
    res = test_client.delete(
        f"/usageplans/{usage_plan_id}/keys/{created_api_key['id']}"
    )
    assert res.data == b"{}"

    # List usage plans keys (expect to be empty again)
    res = test_client.get(f"/usageplans/{usage_plan_id}/keys")
    assert len(json.loads(res.data)["item"]) == 0


def test_create_usage_plans_key_non_existent_api_key():
    backend = server.create_backend_app("apigateway")
    test_client = backend.test_client()
    usage_plan_id = "test_plan_id"

    # Create usage plan key with non-existent api key
    res = test_client.post(
        f"/usageplans/{usage_plan_id}/keys",
        data=json.dumps({"keyId": "non-existent", "keyType": "API_KEY"}),
    )
    assert res.status_code == 404


def test_put_integration_response_without_body():
    # Method under test: put_integration_response
    #
    # Moto/Boto3 requires the responseTemplates-parameter to have a value - even if it's an empty dict
    # Botocore <= 1.21.65 does not automatically pass this parameter, so Moto will successfully throw an error if it's not supplied
    # However: As of botocore >= 1.22.0, the responseTemplates is automatically supplied - which means we can no longer test this using boto3
    #
    # This was the equivalent boto3-test:
    # with pytest.raises(ClientError) as ex:
    #     client.put_integration_response(
    #         restApiId=api_id, resourceId=root_id, httpMethod="GET", statusCode="200"
    #     )
    # assert ex.value.response["Error"]["Code"] == "BadRequestException"
    # assert ex.value.response["Error"]["Message"] == "Invalid request input"
    #
    # As a workaround, we can create a PUT-request without body, which will force the error
    # Related: # https://github.com/aws/aws-sdk-js/issues/2588
    #
    backend = server.create_backend_app("apigateway")
    test_client = backend.test_client()

    res = test_client.put(
        "/restapis/f_id/resources/r_id/methods/m_id/integration/responses/200/"
    )
    assert res.status_code == 400
    assert json.loads(res.data) == {
        "__type": "BadRequestException",
        "message": "Invalid request input",
    }
