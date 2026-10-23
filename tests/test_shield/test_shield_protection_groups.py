import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_protection_group():
    client = boto3.client("shield", region_name="us-east-1")

    client.create_protection_group(
        ProtectionGroupId="all-resources",
        Aggregation="SUM",
        Pattern="ALL",
    )

    group = client.describe_protection_group(ProtectionGroupId="all-resources")[
        "ProtectionGroup"
    ]
    assert group["ProtectionGroupId"] == "all-resources"
    assert group["Aggregation"] == "SUM"
    assert group["Pattern"] == "ALL"
    assert group["Members"] == []
    assert "ResourceType" not in group
    assert group["ProtectionGroupArn"].endswith("protection-group/all-resources")


@mock_aws
def test_create_protection_group__arbitrary():
    client = boto3.client("shield", region_name="us-east-1")
    member = "arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE"

    client.create_protection_group(
        ProtectionGroupId="arbitrary-group",
        Aggregation="MEAN",
        Pattern="ARBITRARY",
        Members=[member],
    )

    group = client.describe_protection_group(ProtectionGroupId="arbitrary-group")[
        "ProtectionGroup"
    ]
    assert group["Pattern"] == "ARBITRARY"
    assert group["Members"] == [member]


@mock_aws
def test_create_protection_group__by_resource_type():
    client = boto3.client("shield", region_name="us-east-1")

    client.create_protection_group(
        ProtectionGroupId="by-type",
        Aggregation="MAX",
        Pattern="BY_RESOURCE_TYPE",
        ResourceType="CLOUDFRONT_DISTRIBUTION",
    )

    group = client.describe_protection_group(ProtectionGroupId="by-type")[
        "ProtectionGroup"
    ]
    assert group["ResourceType"] == "CLOUDFRONT_DISTRIBUTION"
    assert group["Members"] == []


@mock_aws
def test_create_protection_group__already_exists():
    client = boto3.client("shield", region_name="us-east-1")

    client.create_protection_group(
        ProtectionGroupId="duplicated", Aggregation="SUM", Pattern="ALL"
    )

    with pytest.raises(ClientError) as exc:
        client.create_protection_group(
            ProtectionGroupId="duplicated", Aggregation="SUM", Pattern="ALL"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceAlreadyExistsException"
    assert err["Message"] == "The referenced protection group already exists."


@mock_aws
def test_create_protection_group__arbitrary_without_members():
    client = boto3.client("shield", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_protection_group(
            ProtectionGroupId="arbitrary-group",
            Aggregation="SUM",
            Pattern="ARBITRARY",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "Invalid parameter. You must specify Members when Pattern is ARBITRARY."
    )


@mock_aws
def test_create_protection_group__by_resource_type_without_resource_type():
    client = boto3.client("shield", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_protection_group(
            ProtectionGroupId="by-type",
            Aggregation="SUM",
            Pattern="BY_RESOURCE_TYPE",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "Invalid parameter. You must specify ResourceType when Pattern is BY_RESOURCE_TYPE."
    )


@mock_aws
def test_create_protection_group__by_resource_type_with_members():
    client = boto3.client("shield", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_protection_group(
            ProtectionGroupId="by-type",
            Aggregation="SUM",
            Pattern="BY_RESOURCE_TYPE",
            ResourceType="CLOUDFRONT_DISTRIBUTION",
            Members=["arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "Invalid parameter. You cannot specify Members when Pattern is BY_RESOURCE_TYPE."
    )


@mock_aws
def test_create_protection_group__arbitrary_with_resource_type():
    client = boto3.client("shield", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_protection_group(
            ProtectionGroupId="arbitrary-group",
            Aggregation="SUM",
            Pattern="ARBITRARY",
            ResourceType="CLOUDFRONT_DISTRIBUTION",
            Members=["arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "Invalid parameter. You cannot specify ResourceType when Pattern is ARBITRARY."
    )


@mock_aws
def test_create_protection_group__all_with_members():
    client = boto3.client("shield", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_protection_group(
            ProtectionGroupId="all-resources",
            Aggregation="SUM",
            Pattern="ALL",
            Members=["arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "Invalid parameter. You cannot specify Members or ResourceType when Pattern is ALL."
    )


@mock_aws
def test_describe_protection_group__unknown_id():
    client = boto3.client("shield", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.describe_protection_group(ProtectionGroupId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "The referenced protection group does not exist."


@mock_aws
def test_update_protection_group():
    client = boto3.client("shield", region_name="us-east-1")
    member = "arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE"

    client.create_protection_group(
        ProtectionGroupId="group", Aggregation="SUM", Pattern="ALL"
    )

    client.update_protection_group(
        ProtectionGroupId="group",
        Aggregation="MAX",
        Pattern="ARBITRARY",
        Members=[member],
    )

    group = client.describe_protection_group(ProtectionGroupId="group")[
        "ProtectionGroup"
    ]
    assert group["Aggregation"] == "MAX"
    assert group["Pattern"] == "ARBITRARY"
    assert group["Members"] == [member]


@mock_aws
def test_update_protection_group__drops_resource_type():
    client = boto3.client("shield", region_name="us-east-1")

    client.create_protection_group(
        ProtectionGroupId="group",
        Aggregation="SUM",
        Pattern="BY_RESOURCE_TYPE",
        ResourceType="CLOUDFRONT_DISTRIBUTION",
    )

    client.update_protection_group(
        ProtectionGroupId="group", Aggregation="SUM", Pattern="ALL"
    )

    group = client.describe_protection_group(ProtectionGroupId="group")[
        "ProtectionGroup"
    ]
    assert group["Pattern"] == "ALL"
    assert "ResourceType" not in group


@mock_aws
def test_update_protection_group__unknown_id():
    client = boto3.client("shield", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.update_protection_group(
            ProtectionGroupId="unknown", Aggregation="SUM", Pattern="ALL"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_update_protection_group__invalid_pattern():
    client = boto3.client("shield", region_name="us-east-1")

    client.create_protection_group(
        ProtectionGroupId="group", Aggregation="SUM", Pattern="ALL"
    )

    with pytest.raises(ClientError) as exc:
        client.update_protection_group(
            ProtectionGroupId="group", Aggregation="SUM", Pattern="ARBITRARY"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"

    group = client.describe_protection_group(ProtectionGroupId="group")[
        "ProtectionGroup"
    ]
    assert group["Pattern"] == "ALL"


@mock_aws
def test_delete_protection_group():
    client = boto3.client("shield", region_name="us-east-1")

    client.create_protection_group(
        ProtectionGroupId="group", Aggregation="SUM", Pattern="ALL"
    )
    client.delete_protection_group(ProtectionGroupId="group")

    assert client.list_protection_groups()["ProtectionGroups"] == []

    with pytest.raises(ClientError) as exc:
        client.describe_protection_group(ProtectionGroupId="group")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_delete_protection_group__unknown_id():
    client = boto3.client("shield", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.delete_protection_group(ProtectionGroupId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_protection_groups():
    client = boto3.client("shield", region_name="us-east-1")

    assert client.list_protection_groups()["ProtectionGroups"] == []

    client.create_protection_group(
        ProtectionGroupId="first", Aggregation="SUM", Pattern="ALL"
    )
    client.create_protection_group(
        ProtectionGroupId="second",
        Aggregation="MAX",
        Pattern="BY_RESOURCE_TYPE",
        ResourceType="CLOUDFRONT_DISTRIBUTION",
    )

    groups = client.list_protection_groups()["ProtectionGroups"]
    assert sorted(group["ProtectionGroupId"] for group in groups) == ["first", "second"]


@mock_aws
def test_list_protection_groups__inclusion_filters():
    client = boto3.client("shield", region_name="us-east-1")

    client.create_protection_group(
        ProtectionGroupId="first", Aggregation="SUM", Pattern="ALL"
    )
    client.create_protection_group(
        ProtectionGroupId="second",
        Aggregation="MAX",
        Pattern="BY_RESOURCE_TYPE",
        ResourceType="CLOUDFRONT_DISTRIBUTION",
    )

    groups = client.list_protection_groups(
        InclusionFilters={"ProtectionGroupIds": ["second"]}
    )["ProtectionGroups"]
    assert [group["ProtectionGroupId"] for group in groups] == ["second"]

    groups = client.list_protection_groups(InclusionFilters={"Patterns": ["ALL"]})[
        "ProtectionGroups"
    ]
    assert [group["ProtectionGroupId"] for group in groups] == ["first"]

    groups = client.list_protection_groups(
        InclusionFilters={"ResourceTypes": ["CLOUDFRONT_DISTRIBUTION"]}
    )["ProtectionGroups"]
    assert [group["ProtectionGroupId"] for group in groups] == ["second"]

    groups = client.list_protection_groups(InclusionFilters={"Aggregations": ["MAX"]})[
        "ProtectionGroups"
    ]
    assert [group["ProtectionGroupId"] for group in groups] == ["second"]

    groups = client.list_protection_groups(
        InclusionFilters={"Patterns": ["ALL"], "Aggregations": ["MAX"]}
    )["ProtectionGroups"]
    assert groups == []


@mock_aws
def test_list_protection_groups__too_many_filter_values():
    client = boto3.client("shield", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.list_protection_groups(
            InclusionFilters={"Patterns": ["ALL", "ARBITRARY"]}
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"


@mock_aws
def test_protection_group_tags():
    client = boto3.client("shield", region_name="us-east-1")

    client.create_protection_group(
        ProtectionGroupId="group",
        Aggregation="SUM",
        Pattern="ALL",
        Tags=[{"Key": "team", "Value": "security"}],
    )

    arn = client.describe_protection_group(ProtectionGroupId="group")[
        "ProtectionGroup"
    ]["ProtectionGroupArn"]
    assert client.list_tags_for_resource(ResourceARN=arn)["Tags"] == [
        {"Key": "team", "Value": "security"}
    ]
