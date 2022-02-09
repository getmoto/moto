import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_apigatewayv2


@mock_apigatewayv2
def test_get_routes_empty():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.get_routes(ApiId=api_id)
    resp.should.have.key("Items").equals([])


@mock_apigatewayv2
def test_create_route_minimal():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    resp = client.create_route(ApiId=api_id, RouteKey="GET /")

    resp.should.have.key("ApiKeyRequired").equals(False)
    resp.should.have.key("AuthorizationType").equals("NONE")
    resp.should.have.key("RouteId")
    resp.should.have.key("RouteKey").equals("GET /")

    resp.shouldnt.have.key("AuthorizationScopes")
    resp.shouldnt.have.key("AuthorizerId")
    resp.shouldnt.have.key("ModelSelectionExpression")
    resp.shouldnt.have.key("OperationName")
    resp.shouldnt.have.key("RequestModels")
    resp.shouldnt.have.key("RouteResponseSelectionExpression")
    resp.shouldnt.have.key("Target")


@mock_apigatewayv2
def test_create_route_full():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(
        Name="test-api",
        ProtocolType="WEBSOCKET",
        RouteSelectionExpression="${request.method}",
    )["ApiId"]
    resp = client.create_route(
        ApiId=api_id,
        ApiKeyRequired=True,
        AuthorizerId="auth_id",
        AuthorizationScopes=["scope1", "scope2"],
        AuthorizationType="CUSTOM",
        ModelSelectionExpression="mse",
        OperationName="OP",
        RequestModels={"req": "uest"},
        RequestParameters={"action": {"Required": True}},
        RouteKey="GET /",
        RouteResponseSelectionExpression="$default",
        Target="t",
    )

    resp.should.have.key("ApiKeyRequired").equals(True)
    resp.should.have.key("AuthorizationType").equals("CUSTOM")
    resp.should.have.key("AuthorizationScopes").equals(["scope1", "scope2"])
    resp.should.have.key("AuthorizerId").equals("auth_id")
    resp.should.have.key("RouteId")
    resp.should.have.key("RouteKey").equals("GET /")

    resp.should.have.key("ModelSelectionExpression").equals("mse")
    resp.should.have.key("OperationName").equals("OP")
    resp.should.have.key("RequestModels").equals({"req": "uest"})
    resp.should.have.key("RequestParameters").equals({"action": {"Required": True}})
    resp.should.have.key("RouteResponseSelectionExpression").equals("$default")
    resp.should.have.key("Target").equals("t")


@mock_apigatewayv2
def test_delete_route():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]

    client.delete_route(ApiId=api_id, RouteId=route_id)

    resp = client.get_routes(ApiId=api_id)
    resp.should.have.key("Items").length_of(0)


@mock_apigatewayv2
def test_get_route():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]

    resp = client.get_route(ApiId=api_id, RouteId=route_id)

    resp.should.have.key("ApiKeyRequired").equals(False)
    resp.should.have.key("AuthorizationType").equals("NONE")
    resp.should.have.key("RouteId")
    resp.should.have.key("RouteKey").equals("GET /")

    resp.shouldnt.have.key("AuthorizationScopes")
    resp.shouldnt.have.key("AuthorizerId")
    resp.shouldnt.have.key("ModelSelectionExpression")
    resp.shouldnt.have.key("OperationName")
    resp.shouldnt.have.key("RouteResponseSelectionExpression")
    resp.shouldnt.have.key("Target")


@mock_apigatewayv2
def test_get_route_unknown():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    with pytest.raises(ClientError) as exc:
        client.get_route(ApiId=api_id, RouteId="unknown")

    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("Invalid Route identifier specified unknown")


@mock_apigatewayv2
def test_get_routes():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    client.create_route(ApiId=api_id, RouteKey="GET /")

    resp = client.get_routes(ApiId=api_id)
    resp.should.have.key("Items").length_of(1)


@mock_apigatewayv2
def test_update_route_single_attribute():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]

    resp = client.update_route(ApiId=api_id, RouteId=route_id, RouteKey="POST /")

    resp.should.have.key("ApiKeyRequired").equals(False)
    resp.should.have.key("AuthorizationType").equals("NONE")
    resp.should.have.key("RouteId").equals(route_id)
    resp.should.have.key("RouteKey").equals("POST /")


@mock_apigatewayv2
def test_update_route_all_attributes():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, ApiKeyRequired=True, RouteKey="GET /")[
        "RouteId"
    ]

    resp = client.update_route(
        ApiId=api_id,
        RouteId=route_id,
        ApiKeyRequired=False,
        AuthorizationScopes=["scope"],
        AuthorizerId="auth_id",
        AuthorizationType="JWT",
        ModelSelectionExpression="mse",
        OperationName="OP",
        RequestModels={"req": "uest"},
        RequestParameters={"action": {"Required": True}},
        RouteResponseSelectionExpression="$default",
        Target="t",
    )

    resp.should.have.key("ApiKeyRequired").equals(False)
    resp.should.have.key("AuthorizationType").equals("JWT")
    resp.should.have.key("AuthorizationScopes").equals(["scope"])
    resp.should.have.key("AuthorizerId").equals("auth_id")
    resp.should.have.key("RouteId")
    resp.should.have.key("RouteKey").equals("GET /")
    resp.should.have.key("ModelSelectionExpression").equals("mse")
    resp.should.have.key("OperationName").equals("OP")
    resp.should.have.key("RequestModels").equals({"req": "uest"})
    resp.should.have.key("RequestParameters").equals({"action": {"Required": True}})
    resp.should.have.key("RouteResponseSelectionExpression").equals("$default")
    resp.should.have.key("Target").equals("t")


@mock_apigatewayv2
def test_delete_route_request_parameter():
    client = boto3.client("apigatewayv2", region_name="us-east-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(
        ApiId=api_id,
        RequestParameters={
            "action": {"Required": True},
            "route.request.header.authorization": {"Required": False},
            "zparam": {"Required": False},
        },
        RouteKey="GET /",
    )["RouteId"]

    request_params = client.get_route(ApiId=api_id, RouteId=route_id)[
        "RequestParameters"
    ]
    request_params.keys().should.have.length_of(3)

    client.delete_route_request_parameter(
        ApiId=api_id,
        RouteId=route_id,
        RequestParameterKey="route.request.header.authorization",
    )

    request_params = client.get_route(ApiId=api_id, RouteId=route_id)[
        "RequestParameters"
    ]
    request_params.keys().should.have.length_of(2)
    request_params.should.have.key("action")
    request_params.should.have.key("zparam")


@mock_apigatewayv2
def test_create_route_response_minimal():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]

    resp = client.create_route_response(
        ApiId=api_id, RouteId=route_id, RouteResponseKey="$default"
    )

    resp.should.have.key("RouteResponseId")
    resp.should.have.key("RouteResponseKey").equals("$default")


@mock_apigatewayv2
def test_create_route_response():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]

    resp = client.create_route_response(
        ApiId=api_id,
        ModelSelectionExpression="mse",
        ResponseModels={"test": "tfacctest5832545056931060873"},
        RouteId=route_id,
        RouteResponseKey="$default",
    )

    resp.should.have.key("RouteResponseId")
    resp.should.have.key("RouteResponseKey").equals("$default")
    resp.should.have.key("ModelSelectionExpression").equals("mse")
    resp.should.have.key("ResponseModels").equals(
        {"test": "tfacctest5832545056931060873"}
    )


@mock_apigatewayv2
def test_get_route_response():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]

    route_response_id = client.create_route_response(
        ApiId=api_id, RouteId=route_id, RouteResponseKey="$default"
    )["RouteResponseId"]

    resp = client.get_route_response(
        ApiId=api_id, RouteId=route_id, RouteResponseId=route_response_id
    )

    resp.should.have.key("RouteResponseId")
    resp.should.have.key("RouteResponseKey").equals("$default")


@mock_apigatewayv2
def test_get_route_response_unknown():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]

    with pytest.raises(ClientError) as exc:
        client.get_route_response(
            ApiId=api_id, RouteId=route_id, RouteResponseId="unknown"
        )

    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")


@mock_apigatewayv2
def test_delete_route_response_unknown():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    r_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]
    rr_id = client.create_route_response(
        ApiId=api_id, RouteId=r_id, RouteResponseKey="$default"
    )["RouteResponseId"]

    client.delete_route_response(ApiId=api_id, RouteId=r_id, RouteResponseId=rr_id)

    with pytest.raises(ClientError) as exc:
        client.get_route_response(ApiId=api_id, RouteId=r_id, RouteResponseId=rr_id)

    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
