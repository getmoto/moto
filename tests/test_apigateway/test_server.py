from __future__ import unicode_literals
import sure  # noqa
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
