"""Unit tests for shield-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_protection():
    client = boto3.client("shield")
    resp = client.create_protection(
        Name="foobar",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
        Tags=[
            {"Key": "key1", "Value": "value1"},
        ],
    )
    assert "ProtectionId" in resp


@mock_aws
def test_create_protection_resource_already_exists():
    client = boto3.client("shield")
    client.create_protection(
        Name="foobar",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
    )
    with pytest.raises(ClientError) as exc:
        client.create_protection(
            Name="foobar",
            ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceAlreadyExistsException"


@mock_aws
def test_create_protection_invalid_resource():
    client = boto3.client("shield")
    with pytest.raises(ClientError) as exc:
        client.create_protection(
            Name="foobar",
            ResourceArn="arn:aws:dynamodb:us-east-1:123456789012:table/foobar",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidResourceException"
    assert err["Message"] == "Unrecognized resource 'table' of service 'dynamodb'."

    with pytest.raises(ClientError) as exc:
        client.create_protection(
            Name="foobar",
            ResourceArn="arn:aws:sns:us-east-2:123456789012:MyTopic",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidResourceException"
    assert err["Message"] == "Relative ID must be in the form '<resource>/<id>'."


@mock_aws
def test_describe_protection_with_resource_arn():
    client = boto3.client("shield")
    client.create_protection(
        Name="foobar",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
    )
    resp = client.describe_protection(
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar"
    )
    protection = resp["Protection"]
    assert "Id" in protection
    assert "Name" in protection
    assert "ResourceArn" in protection
    assert "ProtectionArn" in protection


@mock_aws
def test_describe_protection_with_protection_id():
    client = boto3.client("shield")
    protection = client.create_protection(
        Name="foobar",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
    )
    protection_id = protection["ProtectionId"]
    resp = client.describe_protection(ProtectionId=protection_id)
    protection = resp["Protection"]
    assert "Id" in protection
    assert "Name" in protection
    assert "ResourceArn" in protection
    assert "ProtectionArn" in protection


@mock_aws
def test_describe_protection_with_both_resource_and_protection_id():
    client = boto3.client("shield")
    with pytest.raises(ClientError) as exc:
        client.describe_protection(
            ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
            ProtectionId="aaaaaaaa-bbbb-cccc-dddd-aaa221177777",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"


@mock_aws
def test_describe_protection_resource_doesnot_exist():
    client = boto3.client("shield")
    with pytest.raises(ClientError) as exc:
        client.describe_protection(
            ResourceArn="arn:aws:cloudfront::123456789012:distribution/donotexist"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_describe_protection_doesnot_exist():
    client = boto3.client("shield")
    with pytest.raises(ClientError) as exc:
        client.describe_protection(ProtectionId="aaaaaaaa-bbbb-cccc-dddd-aaa221177777")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_protections():
    client = boto3.client("shield")
    client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
    )
    client.create_protection(
        Name="shield2",
        ResourceArn="arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/foobar",
    )
    resp = client.list_protections()
    assert "Protections" in resp
    assert len(resp["Protections"]) == 2


@mock_aws
def test_list_protections_with_only_resource_arn():
    client = boto3.client("shield")
    client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
    )
    client.create_protection(
        Name="shield2",
        ResourceArn="arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/foobar",
    )
    resp = client.list_protections(
        InclusionFilters={
            "ResourceArns": ["arn:aws:cloudfront::123456789012:distribution/foobar"],
        }
    )
    assert "Protections" in resp
    assert len(resp["Protections"]) == 1


@mock_aws
def test_list_protections_with_only_protection_name():
    client = boto3.client("shield")
    client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
    )
    client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/foobar",
    )
    resp = client.list_protections(
        InclusionFilters={
            "ProtectionNames": ["shield1"],
        }
    )
    assert "Protections" in resp
    assert len(resp["Protections"]) == 2


@mock_aws
def test_list_protections_with_only_resource_type():
    client = boto3.client("shield")
    client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
    )
    client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/foobar",
    )
    client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-load-balancer/1234567890123456",
    )
    resp_elb = client.list_protections(
        InclusionFilters={
            "ResourceTypes": ["CLASSIC_LOAD_BALANCER"],
        }
    )
    assert "Protections" in resp_elb
    assert len(resp_elb["Protections"]) == 1
    resp_alb = client.list_protections(
        InclusionFilters={
            "ResourceTypes": ["APPLICATION_LOAD_BALANCER"],
        }
    )
    assert len(resp_alb["Protections"]) == 1


@mock_aws
def test_list_protections_with_resource_arn_and_protection_name():
    client = boto3.client("shield")
    client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
    )
    client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/foobar",
    )
    resp = client.list_protections(
        InclusionFilters={
            "ResourceArns": ["arn:aws:cloudfront::123456789012:distribution/foobar"],
            "ProtectionNames": ["shield1"],
        }
    )
    assert "Protections" in resp
    assert len(resp["Protections"]) == 1


@mock_aws
def test_list_protections_invalid_resource_arn():
    client = boto3.client("shield")
    with pytest.raises(ClientError) as exc:
        client.list_protections(
            InclusionFilters={
                "ResourceArns": [
                    "arn:aws:cloudfront::123456789012:distribution/foobar",
                    "arn:aws:cloudfront::123456789012:distribution/foobar2",
                ],
            }
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"


@mock_aws
def test_list_protections_invalid_protection_names():
    client = boto3.client("shield")
    with pytest.raises(ClientError) as exc:
        client.list_protections(
            InclusionFilters={
                "ProtectionNames": ["shield1", "shield2"],
            }
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"


@mock_aws
def test_list_protections_invalid_resource_types():
    client = boto3.client("shield")
    with pytest.raises(ClientError) as exc:
        client.list_protections(
            InclusionFilters={
                "ResourceTypes": ["CLOUDFRONT_DISTRIBUTION", "ROUTE_53_HOSTED_ZONE"],
            }
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"


@mock_aws
def test_delete_protection():
    client = boto3.client("shield")
    protection = client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/foobar",
    )
    client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
    )
    client.delete_protection(ProtectionId=protection["ProtectionId"])
    with pytest.raises(ClientError) as exc:
        client.describe_protection(ProtectionId=protection["ProtectionId"])
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    resp = client.list_protections()
    assert len(resp["Protections"]) == 1


@mock_aws
def test_delete_protection_invalid_protection_id():
    client = boto3.client("shield")
    with pytest.raises(ClientError) as exc:
        client.delete_protection(ProtectionId="aaaaaaaa-bbbb-cccc-dddd-aaa221177777")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("shield")
    protection = client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
        Tags=[
            {"Key": "key1", "Value": "value1"},
            {"Key": "key2", "Value": "value2"},
        ],
    )
    desc_protection = client.describe_protection(
        ProtectionId=protection["ProtectionId"]
    )
    resp = client.list_tags_for_resource(
        ResourceARN=desc_protection["Protection"]["ProtectionArn"]
    )
    assert len(resp["Tags"]) == 2


@mock_aws
def test_tag_resource():
    client = boto3.client("shield")
    protection = client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
        Tags=[{"Key": "key1", "Value": "value1"}],
    )
    desc_protection = client.describe_protection(
        ProtectionId=protection["ProtectionId"]
    )
    protection_arn = desc_protection["Protection"]["ProtectionArn"]
    client.tag_resource(
        ResourceARN=protection_arn,
        Tags=[
            {"Key": "key2", "Value": "value2"},
        ],
    )
    resp = client.list_tags_for_resource(ResourceARN=protection_arn)
    assert len(resp["Tags"]) == 2


@mock_aws
def test_untag_resource():
    client = boto3.client("shield")
    protection = client.create_protection(
        Name="shield1",
        ResourceArn="arn:aws:cloudfront::123456789012:distribution/foobar",
        Tags=[
            {"Key": "key1", "Value": "value1"},
            {"Key": "key2", "Value": "value2"},
        ],
    )
    desc_protection = client.describe_protection(
        ProtectionId=protection["ProtectionId"]
    )
    protection_arn = desc_protection["Protection"]["ProtectionArn"]
    client.untag_resource(
        ResourceARN=protection_arn,
        TagKeys=[
            "key1",
        ],
    )
    resp = client.list_tags_for_resource(ResourceARN=protection_arn)
    assert len(resp["Tags"]) == 1
    assert "key2" == resp["Tags"][0]["Key"]


@mock_aws
def test_create_and_describe_subscription():
    client = boto3.client("shield", region_name="eu-west-1")
    client.create_subscription()
    connection = client.describe_subscription()
    subscription = connection["Subscription"]
    assert subscription["AutoRenew"] == "ENABLED"
    assert subscription["Limits"][0]["Type"] == "MitigationCapacityUnits"
    assert subscription["Limits"][0]["Max"] == 10000
    assert subscription["ProactiveEngagementStatus"] == "ENABLED"
    assert (
        subscription["SubscriptionLimits"]["ProtectionLimits"][
            "ProtectedResourceTypeLimits"
        ][0]["Type"]
        == "ELASTIC_IP_ADDRESS"
    )
    assert (
        subscription["SubscriptionLimits"]["ProtectionLimits"][
            "ProtectedResourceTypeLimits"
        ][0]["Max"]
        == 100
    )
    assert (
        subscription["SubscriptionLimits"]["ProtectionLimits"][
            "ProtectedResourceTypeLimits"
        ][1]["Type"]
        == "APPLICATION_LOAD_BALANCER"
    )
    assert (
        subscription["SubscriptionLimits"]["ProtectionLimits"][
            "ProtectedResourceTypeLimits"
        ][1]["Max"]
        == 50
    )
    assert (
        subscription["SubscriptionLimits"]["ProtectionGroupLimits"][
            "MaxProtectionGroups"
        ]
        == 20
    )
    assert (
        subscription["SubscriptionLimits"]["ProtectionGroupLimits"][
            "PatternTypeLimits"
        ]["ArbitraryPatternLimits"]["MaxMembers"]
        == 100
    )
    assert subscription["TimeCommitmentInSeconds"] == 31536000
