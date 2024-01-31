import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.route53resolver.models import ResolverEndpoint

from .test_route53resolver_endpoint import TEST_REGION, create_test_endpoint


@mock_aws
def test_route53resolver_tag_resource():
    """Test the addition of tags to a resource."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    resolver_endpoint = create_test_endpoint(client, ec2_client)

    # Unknown resolver endpoint id.
    bad_arn = "foobar"
    with pytest.raises(ClientError) as exc:
        client.tag_resource(ResourceArn=bad_arn, Tags=[{"Key": "foo", "Value": "bar"}])
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert f"Resolver endpoint with ID '{bad_arn}' does not exist" in err["Message"]

    # Too many tags.
    tags = [
        {"Key": f"{x}", "Value": f"{x}"}
        for x in range(ResolverEndpoint.MAX_TAGS_PER_RESOLVER_ENDPOINT + 1)
    ]
    with pytest.raises(ClientError) as exc:
        client.tag_resource(ResourceArn=resolver_endpoint["Arn"], Tags=tags)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        f"'tags' failed to satisfy constraint: Member must have length less "
        f"than or equal to {ResolverEndpoint.MAX_TAGS_PER_RESOLVER_ENDPOINT}"
    ) in err["Message"]

    # Bad tags.
    with pytest.raises(ClientError) as exc:
        client.tag_resource(
            ResourceArn=resolver_endpoint["Arn"], Tags=[{"Key": "foo!", "Value": "bar"}]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        "1 validation error detected: Value 'foo!' at 'tags.1.member.key' "
        "failed to satisfy constraint: Member must satisfy regular "
        "expression pattern"
    ) in err["Message"]

    # Successful addition of tags.
    added_tags = [{"Key": f"{x}", "Value": f"{x}"} for x in range(10)]
    client.tag_resource(ResourceArn=resolver_endpoint["Arn"], Tags=added_tags)
    result = client.list_tags_for_resource(ResourceArn=resolver_endpoint["Arn"])
    assert len(result["Tags"]) == 10
    assert result["Tags"] == added_tags


@mock_aws
def test_route53resolver_untag_resource():
    """Test the removal of tags to a resource."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Create a resolver endpoint for testing purposes.
    tag_list = [
        {"Key": "one", "Value": "1"},
        {"Key": "two", "Value": "2"},
        {"Key": "three", "Value": "3"},
    ]
    resolver_endpoint = create_test_endpoint(client, ec2_client, tags=tag_list)

    # Untag all of the tags.  Verify there are no more tags.
    client.untag_resource(
        ResourceArn=resolver_endpoint["Arn"], TagKeys=[x["Key"] for x in tag_list]
    )
    result = client.list_tags_for_resource(ResourceArn=resolver_endpoint["Arn"])
    assert not result["Tags"]
    assert "NextToken" not in result


@mock_aws
def test_route53resolver_list_tags_for_resource():
    """Test ability to list all tags for a resource."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Create a resolver endpoint to work with.
    tags = [
        {"Key": f"{x}_k", "Value": f"{x}_v"}
        for x in range(1, ResolverEndpoint.MAX_TAGS_PER_RESOLVER_ENDPOINT)
    ]
    resolver_endpoint = create_test_endpoint(client, ec2_client, tags=tags)

    # Verify limit and next token works.
    result = client.list_tags_for_resource(
        ResourceArn=resolver_endpoint["Arn"], MaxResults=1
    )
    assert len(result["Tags"]) == 1
    assert result["Tags"] == [{"Key": "1_k", "Value": "1_v"}]
    assert result["NextToken"]

    result = client.list_tags_for_resource(
        ResourceArn=resolver_endpoint["Arn"],
        MaxResults=10,
        NextToken=result["NextToken"],
    )
    assert len(result["Tags"]) == 10
    assert result["Tags"] == [
        {"Key": f"{x}_k", "Value": f"{x}_v"} for x in range(2, 12)
    ]
    assert result["NextToken"]


@mock_aws
def test_route53resolver_bad_list_tags_for_resource():
    """Test ability to list all tags for a resource."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Create a resolver endpoint to work with.
    tags = [{"Key": "foo", "Value": "foobar"}]
    resolver_endpoint = create_test_endpoint(client, ec2_client, tags=tags)

    # Bad resolver endpoint ARN.
    bad_arn = "xyz"
    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(ResourceArn=bad_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert f"Resolver endpoint with ID '{bad_arn}' does not exist" in err["Message"]

    # Bad next token.
    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(
            ResourceArn=resolver_endpoint["Arn"], NextToken="foo"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidNextTokenException"
    assert "Invalid value passed for the NextToken parameter" in err["Message"]
