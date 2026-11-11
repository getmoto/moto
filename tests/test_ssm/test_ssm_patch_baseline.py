from datetime import datetime, timezone

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_get_patch_baseline():
    ssm = boto3.client("ssm", region_name="us-east-1")
    options = {
        "Name": "example-baseline",
        "OperatingSystem": "AMAZON_LINUX_2",
        "Description": "A baseline to retrieve",
        "GlobalFilters": {
            "PatchFilters": [{"Key": "PRODUCT", "Values": ["AmazonLinux2"]}]
        },
        "ApprovalRules": {
            "PatchRules": [
                {
                    "PatchFilterGroup": {
                        "PatchFilters": [
                            {"Key": "CLASSIFICATION", "Values": ["Security"]}
                        ]
                    },
                    "ApproveAfterDays": 7,
                }
            ]
        },
        "ApprovedPatches": ["approved-patch"],
        "ApprovedPatchesComplianceLevel": "HIGH",
        "ApprovedPatchesEnableNonSecurity": True,
        "RejectedPatches": ["rejected-patch"],
        "RejectedPatchesAction": "BLOCK",
        "Sources": [
            {
                "Name": "example-source",
                "Products": ["AmazonLinux2"],
                "Configuration": "[example]\nbaseurl=https://example.com",
            }
        ],
    }
    before = datetime.now(timezone.utc)
    baseline_id = ssm.create_patch_baseline(**options)["BaselineId"]
    for group in ["production", "staging"]:
        ssm.register_patch_baseline_for_patch_group(
            BaselineId=baseline_id, PatchGroup=group
        )
    other_id = ssm.create_patch_baseline(Name="other-baseline")["BaselineId"]
    ssm.register_patch_baseline_for_patch_group(BaselineId=other_id, PatchGroup="other")

    baseline = ssm.get_patch_baseline(BaselineId=baseline_id)
    assert baseline["BaselineId"] == baseline_id
    for key, value in options.items():
        assert baseline[key] == value
    assert set(baseline["PatchGroups"]) == {"production", "staging"}
    assert before <= baseline["CreatedDate"] <= datetime.now(timezone.utc)
    assert baseline["ModifiedDate"] == baseline["CreatedDate"]
    assert (
        ssm.get_patch_baseline(BaselineId=baseline_id)["CreatedDate"]
        == baseline["CreatedDate"]
    )
    assert (
        ssm.describe_patch_baselines()["BaselineIdentities"][0]["BaselineName"]
        == options["Name"]
    )


@mock_aws
def test_get_patch_baseline_defaults():
    ssm = boto3.client("ssm", region_name="us-east-1")
    baseline_id = ssm.create_patch_baseline(Name="minimal-baseline")["BaselineId"]
    baseline = ssm.get_patch_baseline(BaselineId=baseline_id)
    assert baseline["Name"] == "minimal-baseline"
    assert baseline["OperatingSystem"] == "WINDOWS"
    assert baseline["PatchGroups"] == []
    assert baseline["ApprovedPatches"] == []
    assert baseline["RejectedPatches"] == []
    assert baseline["Sources"] == []


@pytest.mark.parametrize(
    "state", ["missing", "deleted", "other-region", "other-account"]
)
@mock_aws
def test_get_patch_baseline_not_found(state, monkeypatch):
    ssm = boto3.client("ssm", region_name="us-east-1")
    baseline_id = "pb-0123456789abcdef0"
    if state != "missing":
        baseline_id = ssm.create_patch_baseline(Name="example-baseline")["BaselineId"]
        if state == "deleted":
            ssm.delete_patch_baseline(BaselineId=baseline_id)
        elif state == "other-region":
            ssm = boto3.client("ssm", region_name="us-west-2")
        else:
            monkeypatch.setenv("MOTO_ACCOUNT_ID", "111122223333")
    with pytest.raises(ClientError) as exc:
        ssm.get_patch_baseline(BaselineId=baseline_id)
    assert exc.value.response["Error"]["Code"] == "DoesNotExistException"
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_create_patch_baseLine():
    ssm = boto3.client("ssm", region_name="us-east-1")

    baseline_name = "ExamplePatchBaseline"
    baseline_description = "Example patch baseline created using Boto3"

    # Define the approval rules for the patch baseline
    approval_rules = {
        "PatchRules": [
            {
                "PatchFilterGroup": {
                    "PatchFilters": [
                        {"Key": "PRODUCT", "Values": ["AmazonLinux2012.03"]},
                        {"Key": "CLASSIFICATION", "Values": ["Security"]},
                    ]
                },
                "ApproveAfterDays": 7,
                "ComplianceLevel": "CRITICAL",
            }
        ]
    }

    # Create the patch baseline
    response = ssm.create_patch_baseline(
        Name=baseline_name,
        OperatingSystem="AMAZON_LINUX",
        Description=baseline_description,
        ApprovalRules=approval_rules,
    )

    _id = response["BaselineId"]  # mw-01d6bbfdf6af2c39a

    response = ssm.describe_patch_baselines(
        Filters=[
            {
                "Key": "NAME_PREFIX",
                "Values": [
                    baseline_name,
                ],
            },
        ],
        MaxResults=50,
    )
    assert len(response["BaselineIdentities"]) == 1
    baseline = response["BaselineIdentities"][0]
    assert baseline["BaselineId"] == _id
    assert baseline["BaselineName"] == baseline_name
    assert baseline["DefaultBaseline"] is False
    assert baseline["OperatingSystem"] == "AMAZON_LINUX"
    assert baseline["BaselineDescription"] == baseline_description


@mock_aws
def test_delete_patch_baseline():
    ssm = boto3.client("ssm", region_name="us-east-1")

    baseline_name = "ExamplePatchBaseline"

    # Create the patch baseline
    response = ssm.create_patch_baseline(
        Name="ExamplePatchBaseline",
        OperatingSystem="AMAZON_LINUX",
        Description="Example patch baseline created using Boto3",
        ApprovalRules={
            "PatchRules": [
                {
                    "PatchFilterGroup": {
                        "PatchFilters": [
                            {"Key": "PRODUCT", "Values": ["AmazonLinux2012.03"]},
                            {"Key": "CLASSIFICATION", "Values": ["Security"]},
                        ]
                    },
                    "ApproveAfterDays": 7,
                    "ComplianceLevel": "CRITICAL",
                }
            ]
        },
    )

    _id = response["BaselineId"]  # pw-0a49ee14c7f305f55
    ssm.delete_patch_baseline(BaselineId=_id)
    response = ssm.describe_patch_baselines(
        Filters=[
            {
                "Key": "NAME_PREFIX",
                "Values": [
                    baseline_name,
                ],
            },
        ],
        MaxResults=50,
    )
    assert len(response["BaselineIdentities"]) == 0
