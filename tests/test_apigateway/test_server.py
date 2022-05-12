import sure  # noqa # pylint: disable=unused-import
import json

import moto.server as server

"""
Test the different server responses
"""


def test_list_apis():
    backend = server.create_backend_app("apigateway")
    test_client = backend.test_client()

    res = test_client.get("/restapis")
    json.loads(res.data).should.contain("item")


def test_usage_plans_apis():
    backend = server.create_backend_app("apigateway")
    test_client = backend.test_client()

    # List usage plans (expect empty)
    res = test_client.get("/usageplans")
    json.loads(res.data)["item"].should.have.length_of(0)

    # Create usage plan
    res = test_client.post("/usageplans", data=json.dumps({"name": "test"}))
    created_plan = json.loads(res.data)
    created_plan["name"].should.equal("test")

    # List usage plans (expect 1 plan)
    res = test_client.get("/usageplans")
    json.loads(res.data)["item"].should.have.length_of(1)

    # Get single usage plan
    res = test_client.get("/usageplans/{0}".format(created_plan["id"]))
    fetched_plan = json.loads(res.data)
    fetched_plan.should.equal(created_plan)

    # Not existing usage plan
    res = test_client.get("/usageplans/{0}".format("not_existing"))
    res.status_code.should.equal(404)

    # Delete usage plan
    res = test_client.delete("/usageplans/{0}".format(created_plan["id"]))
    res.data.should.equal(b"{}")

    # List usage plans (expect empty again)
    res = test_client.get("/usageplans")
    json.loads(res.data)["item"].should.have.length_of(0)


def test_usage_plans_keys():
    backend = server.create_backend_app("apigateway")
    test_client = backend.test_client()
    usage_plan_id = "test_plan_id"

    # Create API key to be used in tests
    res = test_client.post("/apikeys", data=json.dumps({"name": "test"}))
    created_api_key = json.loads(res.data)

    # List usage plans keys (expect empty)
    res = test_client.get("/usageplans/{0}/keys".format(usage_plan_id))
    json.loads(res.data)["item"].should.have.length_of(0)

    # Invalid api key (does not exists at all)
    res = test_client.get(
        "/usageplans/{0}/keys/{1}".format(usage_plan_id, "not_existing")
    )
    res.status_code.should.equal(404)

    # not existing usage plan with existing api key
    res = test_client.get(
        "/usageplans/{0}/keys/{1}".format("not_existing", created_api_key["id"])
    )
    res.status_code.should.equal(404)

    # not jet added api key
    res = test_client.get(
        "/usageplans/{0}/keys/{1}".format(usage_plan_id, created_api_key["id"])
    )
    res.status_code.should.equal(404)

    # Create usage plan key
    res = test_client.post(
        "/usageplans/{0}/keys".format(usage_plan_id),
        data=json.dumps({"keyId": created_api_key["id"], "keyType": "API_KEY"}),
    )
    created_usage_plan_key = json.loads(res.data)

    # List usage plans keys (expect 1 key)
    res = test_client.get("/usageplans/{0}/keys".format(usage_plan_id))
    json.loads(res.data)["item"].should.have.length_of(1)

    # Get single usage plan key
    res = test_client.get(
        "/usageplans/{0}/keys/{1}".format(usage_plan_id, created_api_key["id"])
    )
    fetched_plan_key = json.loads(res.data)
    fetched_plan_key.should.equal(created_usage_plan_key)

    # Delete usage plan key
    res = test_client.delete(
        "/usageplans/{0}/keys/{1}".format(usage_plan_id, created_api_key["id"])
    )
    res.data.should.equal(b"{}")

    # List usage plans keys (expect to be empty again)
    res = test_client.get("/usageplans/{0}/keys".format(usage_plan_id))
    json.loads(res.data)["item"].should.have.length_of(0)


def test_create_usage_plans_key_non_existent_api_key():
    backend = server.create_backend_app("apigateway")
    test_client = backend.test_client()
    usage_plan_id = "test_plan_id"

    # Create usage plan key with non-existent api key
    res = test_client.post(
        "/usageplans/{0}/keys".format(usage_plan_id),
        data=json.dumps({"keyId": "non-existent", "keyType": "API_KEY"}),
    )
    res.status_code.should.equal(404)


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
    # ex.value.response["Error"]["Code"].should.equal("BadRequestException")
    # ex.value.response["Error"]["Message"].should.equal("Invalid request input")
    #
    # As a workaround, we can create a PUT-request without body, which will force the error
    # Related: # https://github.com/aws/aws-sdk-js/issues/2588
    #
    backend = server.create_backend_app("apigateway")
    test_client = backend.test_client()

    res = test_client.put(
        "/restapis/f_id/resources/r_id/methods/m_id/integration/responses/200/"
    )
    res.status_code.should.equal(400)
    json.loads(res.data).should.equal(
        {"__type": "BadRequestException", "message": "Invalid request input"}
    )
