import boto3
import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time

from moto import mock_aws


@freeze_time("2015-01-01")
@mock_aws
def test_create_layer_response():
    client = boto3.client("opsworks", region_name="us-east-1")
    stack_id = client.create_stack(
        Name="test_stack_1",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn",
    )["StackId"]

    response = client.create_layer(
        StackId=stack_id,
        Type="custom",
        Name="TestLayer",
        Shortname="TestLayerShortName",
    )

    assert "LayerId" in response

    second_stack_id = client.create_stack(
        Name="test_stack_2",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn",
    )["StackId"]

    response = client.create_layer(
        StackId=second_stack_id,
        Type="custom",
        Name="TestLayer",
        Shortname="TestLayerShortName",
    )

    assert "LayerId" in response

    # ClientError
    with pytest.raises(ClientError) as exc:
        client.create_layer(
            StackId=stack_id, Type="custom", Name="TestLayer", Shortname="_"
        )
    assert (
        r'already a layer named "TestLayer"' in exc.value.response["Error"]["Message"]
    )

    # ClientError
    with pytest.raises(ClientError) as exc:
        client.create_layer(
            StackId=stack_id, Type="custom", Name="_", Shortname="TestLayerShortName"
        )
    assert (
        r'already a layer with shortname "TestLayerShortName"'
    ) in exc.value.response["Error"]["Message"]

    # ClientError
    with pytest.raises(ClientError) as exc:
        client.create_layer(
            StackId="nothere", Type="custom", Name="TestLayer", Shortname="_"
        )
    assert exc.value.response["Error"]["Message"] == "nothere"


@freeze_time("2015-01-01")
@mock_aws
def test_describe_layers():
    client = boto3.client("opsworks", region_name="us-east-1")
    stack_id = client.create_stack(
        Name="test_stack_1",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn",
    )["StackId"]
    layer_id = client.create_layer(
        StackId=stack_id,
        Type="custom",
        Name="TestLayer",
        Shortname="TestLayerShortName",
    )["LayerId"]

    rv1 = client.describe_layers(StackId=stack_id)
    rv2 = client.describe_layers(LayerIds=[layer_id])
    assert rv1["Layers"] == rv2["Layers"]

    assert rv1["Layers"][0]["Name"] == "TestLayer"

    # ClientError
    with pytest.raises(ClientError) as exc:
        client.describe_layers(StackId=stack_id, LayerIds=[layer_id])
    assert exc.value.response["Error"]["Message"] == (
        "Please provide one or more layer IDs or a stack ID"
    )

    # ClientError
    with pytest.raises(ClientError) as exc:
        client.describe_layers(StackId="nothere")
    assert exc.value.response["Error"]["Message"] == (
        "Unable to find stack with ID nothere"
    )

    # ClientError
    with pytest.raises(ClientError) as exc:
        client.describe_layers(LayerIds=["nothere"])
    assert exc.value.response["Error"]["Message"] == "nothere"
