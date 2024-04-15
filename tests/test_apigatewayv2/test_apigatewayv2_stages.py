import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_stage__defaults():
    client = boto3.client("apigatewayv2", "us-east-2")

    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    stages = client.get_stages(ApiId=api_id)
    assert stages["Items"] == []

    stage = client.create_stage(ApiId=api_id, StageName="my_stage")
    assert stage["StageName"] == "my_stage"

    resp = client.get_stage(ApiId=api_id, StageName="my_stage")
    assert resp["StageName"] == "my_stage"

    stages = client.get_stages(ApiId=api_id)
    assert len(stages["Items"]) == 1

    assert stages["Items"][0]["StageName"] == "my_stage"
    assert stages["Items"][0]["DefaultRouteSettings"] == {
        "DetailedMetricsEnabled": False
    }
    assert stages["Items"][0]["CreatedDate"]
    assert stages["Items"][0]["LastUpdatedDate"]
    assert stages["Items"][0]["RouteSettings"] == {}
    assert stages["Items"][0]["StageVariables"] == {}
    assert stages["Items"][0]["Tags"] == {}

    client.delete_stage(ApiId=api_id, StageName="my_stage")

    with pytest.raises(ClientError) as exc:
        client.get_stage(ApiId=api_id, StageName="my_stage")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Invalid stage identifier specified"


@mock_aws
def test_create_stage__defaults_for_websocket_api():
    client = boto3.client("apigatewayv2", "us-east-2")

    api_id = client.create_api(Name="test-api", ProtocolType="WEBSOCKET")["ApiId"]

    client.create_stage(ApiId=api_id, StageName="my_stage")

    stage = client.get_stage(ApiId=api_id, StageName="my_stage")
    assert stage["StageName"] == "my_stage"
    assert stage["DefaultRouteSettings"] == {
        "DataTraceEnabled": False,
        "DetailedMetricsEnabled": False,
        "LoggingLevel": "OFF",
    }


@mock_aws
def test_create_stage():
    client = boto3.client("apigatewayv2", "us-east-2")

    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    stage = client.create_stage(
        ApiId=api_id,
        StageName="my_stage",
        AccessLogSettings={"Format": "JSON"},
        AutoDeploy=True,
        ClientCertificateId="ccid",
        DefaultRouteSettings={"LoggingLevel": "INFO", "ThrottlingBurstLimit": 9000},
        Description="my shiny stage",
        RouteSettings={
            "route1": {"DataTraceEnabled": True},
        },
        StageVariables={"sv1": "val1"},
        Tags={"k1": "v1"},
    )

    assert stage["StageName"] == "my_stage"
    assert stage["AccessLogSettings"] == {"Format": "JSON"}
    assert stage["AutoDeploy"] is True
    assert stage["ClientCertificateId"] == "ccid"
    assert stage["DefaultRouteSettings"] == {
        "LoggingLevel": "INFO",
        "ThrottlingBurstLimit": 9000,
    }
    assert stage["Description"] == "my shiny stage"
    assert stage["CreatedDate"]
    assert stage["LastUpdatedDate"]
    assert stage["RouteSettings"] == {"route1": {"DataTraceEnabled": True}}
    assert stage["StageVariables"] == {"sv1": "val1"}
    assert stage["Tags"] == {"k1": "v1"}
