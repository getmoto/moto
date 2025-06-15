"""
Route53 has some idiosyncrasies related to HostedZone ids
Some operations return `/hosted_zone/{id}`
Other operations return `{id}`
Some operations expect `/hosted_zone/{id}`
Other operations expect `{id}`
Some operations allow both (probably..)

The tests in this file are purely to test the different scenarios.

Note that all tests are verified against AWS.
If you want to run the tests against AWS yourself, make sure `TEST_DOMAIN_NAME` is changed to a domain name that's known to AWS.
"""

from functools import wraps
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from tests import allow_aws_request

TEST_DOMAIN_NAME = "mototests.click"
TEST_HOSTED_ZONE_NAME = f"test.{TEST_DOMAIN_NAME}"


def route53_aws_verified(func):
    @wraps(func)
    def pagination_wrapper(**kwargs):
        def create_hosted_zone():
            client = boto3.client("route53", "us-east-1")

            hosted_zone = client.create_hosted_zone(
                Name=TEST_HOSTED_ZONE_NAME, CallerReference=str(uuid4())
            )["HostedZone"]

            kwargs["hosted_zone"] = hosted_zone

            try:
                return func(**kwargs)
            finally:
                client.delete_hosted_zone(Id=hosted_zone["Id"])

        if allow_aws_request():
            return create_hosted_zone()
        else:
            with mock_aws():
                return create_hosted_zone()

    return pagination_wrapper


@pytest.mark.aws_verified
@route53_aws_verified
def test_hosted_zone_id_in_change_tags(hosted_zone=None):
    client = boto3.client("route53", "us-east-1")

    full_zone_id = hosted_zone["Id"]
    assert full_zone_id.startswith("/hostedzone/")

    # Can't use full ID here
    with pytest.raises(ClientError) as exc:
        client.change_tags_for_resource(
            ResourceType="hostedzone",
            ResourceId=full_zone_id,
            AddTags=[{"Key": "foo", "Value": "bar"}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"
    assert (
        err["Message"]
        == f"1 validation error detected: Value '{full_zone_id}' at 'resourceId' failed to satisfy constraint: Member must have length less than or equal to 32"
    )

    # if we naively limit the id-length to 32, we get a NoSuchHostedZone-exception (as expected)
    with pytest.raises(ClientError) as exc:
        client.change_tags_for_resource(
            ResourceType="hostedzone",
            ResourceId=full_zone_id[0:32],
            AddTags=[{"Key": "foo", "Value": "bar"}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchHostedZone"

    # Need to strip the '/hosted_zone/'-prefix
    id_without_prefix = full_zone_id.replace("/hostedzone/", "")
    client.change_tags_for_resource(
        ResourceType="hostedzone",
        ResourceId=id_without_prefix,
        AddTags=[{"Key": "foo", "Value": "bar"}],
    )

    # Test retrieval of tags with full ID
    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(
            ResourceType="hostedzone", ResourceId=full_zone_id
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"
    assert (
        err["Message"]
        == f"1 validation error detected: Value '{full_zone_id}' at 'resourceId' failed to satisfy constraint: Member must have length less than or equal to 32"
    )

    # Test retrieval of tags with stripped ID
    tags = client.list_tags_for_resource(
        ResourceType="hostedzone", ResourceId=id_without_prefix
    )["ResourceTagSet"]
    assert tags == {
        "ResourceId": id_without_prefix,
        "ResourceType": "hostedzone",
        "Tags": [{"Key": "foo", "Value": "bar"}],
    }
