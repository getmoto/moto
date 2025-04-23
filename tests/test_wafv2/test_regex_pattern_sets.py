import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_regex_pattern_set_crud():
    client = boto3.client("wafv2", region_name="us-east-1")

    # Create regex pattern set
    create_response = client.create_regex_pattern_set(
        Name="test-regex-pattern-set",
        Scope="REGIONAL",
        Description="Test regex pattern set",
        RegularExpressionList=[{"RegexString": "test.*pattern"}],
        Tags=[{"Key": "test-key", "Value": "test-value"}],
    )

    assert "Summary" in create_response
    summary = create_response["Summary"]
    assert summary["Id"]
    assert summary["LockToken"]
    assert summary["ARN"]
    assert summary["Name"] == "test-regex-pattern-set"
    assert summary["Description"] == "Test regex pattern set"

    # Get regex pattern set
    get_response = client.get_regex_pattern_set(
        Name=summary["Name"],
        Scope="REGIONAL",
        Id=summary["Id"],
    )

    assert "RegexPatternSet" in get_response
    assert "LockToken" in get_response
    pattern_set = get_response["RegexPatternSet"]
    assert pattern_set["RegularExpressionList"] == [{"RegexString": "test.*pattern"}]

    # Test update with invalid lock token
    with pytest.raises(ClientError) as e:
        client.update_regex_pattern_set(
            Name=summary["Name"],
            Scope="REGIONAL",
            Id=summary["Id"],
            Description="Updated description",
            RegularExpressionList=[{"RegexString": "updated.*pattern"}],
            LockToken="invalid-lock-token",
        )
    assert e.value.response["Error"]["Code"] == "WAFOptimisticLockException"

    # Update regex pattern set
    update_response = client.update_regex_pattern_set(
        Name=summary["Name"],
        Scope="REGIONAL",
        Id=summary["Id"],
        Description="Updated description",
        RegularExpressionList=[{"RegexString": "updated.*pattern"}],
        LockToken=get_response["LockToken"],
    )

    assert "NextLockToken" in update_response

    # Verify update
    updated_get_response = client.get_regex_pattern_set(
        Name=summary["Name"],
        Scope="REGIONAL",
        Id=summary["Id"],
    )
    updated_pattern_set = updated_get_response["RegexPatternSet"]
    assert updated_pattern_set["Description"] == "Updated description"
    assert updated_pattern_set["RegularExpressionList"] == [
        {"RegexString": "updated.*pattern"}
    ]
    assert updated_get_response["LockToken"] == update_response["NextLockToken"]

    # List regex pattern sets
    list_response = client.list_regex_pattern_sets(Scope="REGIONAL")
    assert len(list_response["RegexPatternSets"]) == 1
    assert all(
        key in list_response["RegexPatternSets"][0]
        for key in ["ARN", "Description", "Id", "LockToken", "Name"]
    )

    # Delete regex pattern set
    client.delete_regex_pattern_set(
        Name=summary["Name"],
        Scope="REGIONAL",
        Id=summary["Id"],
        LockToken=updated_get_response["LockToken"],
    )

    # Verify deletion
    with pytest.raises(ClientError) as e:
        client.get_regex_pattern_set(
            Name=summary["Name"],
            Scope="REGIONAL",
            Id=summary["Id"],
        )
    assert e.value.response["Error"]["Code"] == "WAFNonexistentItemException"


@mock_aws
def test_duplicate_regex_pattern_set():
    client = boto3.client("wafv2", region_name="us-east-1")

    # Create first regex pattern set
    client.create_regex_pattern_set(
        Name="test-regex-pattern-set",
        Scope="REGIONAL",
        Description="Test regex pattern set",
        RegularExpressionList=[{"RegexString": "test.*pattern"}],
    )

    # Attempt to create duplicate
    with pytest.raises(ClientError) as e:
        client.create_regex_pattern_set(
            Name="test-regex-pattern-set",
            Scope="REGIONAL",
            Description="Duplicate regex pattern set",
            RegularExpressionList=[{"RegexString": "duplicate.*pattern"}],
        )
    assert e.value.response["Error"]["Code"] == "WafV2DuplicateItem"


@mock_aws
def test_cloudfront_scope():
    client = boto3.client("wafv2", region_name="us-east-1")

    # Create regex pattern set with CLOUDFRONT scope
    create_response = client.create_regex_pattern_set(
        Name="test-cloudfront-regex-set",
        Scope="CLOUDFRONT",
        Description="Test CloudFront regex pattern set",
        RegularExpressionList=[{"RegexString": "test.*pattern"}],
    )

    assert "Summary" in create_response
    summary = create_response["Summary"]
    assert ":us-east-1:" in summary["ARN"]

    # List only CLOUDFRONT regex pattern sets
    list_response = client.list_regex_pattern_sets(Scope="CLOUDFRONT")
    assert len(list_response["RegexPatternSets"]) == 1
    assert all(
        ":us-east-1:" in pattern_set["ARN"]
        for pattern_set in list_response["RegexPatternSets"]
    )
