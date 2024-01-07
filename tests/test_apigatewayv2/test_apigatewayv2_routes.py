import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_get_routes_empty():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.get_routes(ApiId=api_id)
    assert resp["Items"] == []


@mock_aws
def test_create_route_minimal():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    resp = client.create_route(ApiId=api_id, RouteKey="GET /")

    assert resp["ApiKeyRequired"] is False
    assert resp["AuthorizationType"] == "NONE"
    assert "RouteId" in resp
    assert resp["RouteKey"] == "GET /"

    assert "AuthorizationScopes" not in resp
    assert "AuthorizerId" not in resp
    assert "ModelSelectionExpression" not in resp
    assert "OperationName" not in resp
    assert "RequestModels" not in resp
    assert "RouteResponseSelectionExpression" not in resp
    assert "Target" not in resp


@mock_aws
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

    assert resp["ApiKeyRequired"] is True
    assert resp["AuthorizationType"] == "CUSTOM"
    assert resp["AuthorizationScopes"] == ["scope1", "scope2"]
    assert resp["AuthorizerId"] == "auth_id"
    assert "RouteId" in resp
    assert resp["RouteKey"] == "GET /"

    assert resp["ModelSelectionExpression"] == "mse"
    assert resp["OperationName"] == "OP"
    assert resp["RequestModels"] == {"req": "uest"}
    assert resp["RequestParameters"] == {"action": {"Required": True}}
    assert resp["RouteResponseSelectionExpression"] == "$default"
    assert resp["Target"] == "t"


@mock_aws
def test_delete_route():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]

    client.delete_route(ApiId=api_id, RouteId=route_id)

    resp = client.get_routes(ApiId=api_id)
    assert len(resp["Items"]) == 0


@mock_aws
def test_get_route():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]

    resp = client.get_route(ApiId=api_id, RouteId=route_id)

    assert resp["ApiKeyRequired"] is False
    assert resp["AuthorizationType"] == "NONE"
    assert "RouteId" in resp
    assert resp["RouteKey"] == "GET /"

    assert "AuthorizationScopes" not in resp
    assert "AuthorizerId" not in resp
    assert "ModelSelectionExpression" not in resp
    assert "OperationName" not in resp
    assert "RouteResponseSelectionExpression" not in resp
    assert "Target" not in resp


@mock_aws
def test_get_route_unknown():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    with pytest.raises(ClientError) as exc:
        client.get_route(ApiId=api_id, RouteId="unknown")

    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid Route identifier specified unknown"


@mock_aws
def test_get_routes():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    client.create_route(ApiId=api_id, RouteKey="GET /")

    resp = client.get_routes(ApiId=api_id)
    assert len(resp["Items"]) == 1


@mock_aws
def test_update_route_single_attribute():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]

    resp = client.update_route(ApiId=api_id, RouteId=route_id, RouteKey="POST /")

    assert resp["ApiKeyRequired"] is False
    assert resp["AuthorizationType"] == "NONE"
    assert resp["RouteId"] == route_id
    assert resp["RouteKey"] == "POST /"


@mock_aws
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

    assert resp["ApiKeyRequired"] is False
    assert resp["AuthorizationType"] == "JWT"
    assert resp["AuthorizationScopes"] == ["scope"]
    assert resp["AuthorizerId"] == "auth_id"
    assert "RouteId" in resp
    assert resp["RouteKey"] == "GET /"
    assert resp["ModelSelectionExpression"] == "mse"
    assert resp["OperationName"] == "OP"
    assert resp["RequestModels"] == {"req": "uest"}
    assert resp["RequestParameters"] == {"action": {"Required": True}}
    assert resp["RouteResponseSelectionExpression"] == "$default"
    assert resp["Target"] == "t"


@mock_aws
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
    assert len(request_params.keys()) == 3

    client.delete_route_request_parameter(
        ApiId=api_id,
        RouteId=route_id,
        RequestParameterKey="route.request.header.authorization",
    )

    request_params = client.get_route(ApiId=api_id, RouteId=route_id)[
        "RequestParameters"
    ]
    assert len(request_params.keys()) == 2
    assert "action" in request_params
    assert "zparam" in request_params


@mock_aws
def test_create_route_response_minimal():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]

    resp = client.create_route_response(
        ApiId=api_id, RouteId=route_id, RouteResponseKey="$default"
    )

    assert "RouteResponseId" in resp
    assert resp["RouteResponseKey"] == "$default"


@mock_aws
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

    assert "RouteResponseId" in resp
    assert resp["RouteResponseKey"] == "$default"
    assert resp["ModelSelectionExpression"] == "mse"
    assert resp["ResponseModels"] == {"test": "tfacctest5832545056931060873"}


@mock_aws
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

    assert "RouteResponseId" in resp
    assert resp["RouteResponseKey"] == "$default"


@mock_aws
def test_get_route_response_unknown():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]
    route_id = client.create_route(ApiId=api_id, RouteKey="GET /")["RouteId"]

    with pytest.raises(ClientError) as exc:
        client.get_route_response(
            ApiId=api_id, RouteId=route_id, RouteResponseId="unknown"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"


@mock_aws
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
    assert err["Code"] == "NotFoundException"
