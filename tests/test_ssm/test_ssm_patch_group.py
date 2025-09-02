import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_register_patch_baseline_for_patch_group():
    client = boto3.client("ssm", region_name="us-east-2")
    patch_group_name = "test"

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
    baseline_id = client.create_patch_baseline(
        Name=baseline_name,
        OperatingSystem="AMAZON_LINUX",
        Description=baseline_description,
        ApprovalRules=approval_rules,
    )["BaselineId"]
    resp = client.register_patch_baseline_for_patch_group(
        BaselineId=baseline_id, PatchGroup=patch_group_name
    )

    assert resp["BaselineId"] == baseline_id
    assert resp["PatchGroup"] == patch_group_name


@mock_aws
def test_get_patch_baseline_for_patch_group():
    client = boto3.client("ssm", region_name="us-east-2")
    patch_group_name = "test"

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
    baseline_id = client.create_patch_baseline(
        Name=baseline_name,
        OperatingSystem="AMAZON_LINUX",
        Description=baseline_description,
        ApprovalRules=approval_rules,
    )["BaselineId"]
    client.register_patch_baseline_for_patch_group(
        BaselineId=baseline_id, PatchGroup=patch_group_name
    )

    resp = client.get_patch_baseline_for_patch_group(
        OperatingSystem="AMAZON_LINUX", PatchGroup=patch_group_name
    )

    assert resp["BaselineId"] == baseline_id
    assert resp["PatchGroup"] == patch_group_name


@mock_aws
def test_get_patch_baseline_for_patch_group_default():
    client = boto3.client("ssm", region_name="us-east-2")
    patch_group_name = "test"

    resp = client.get_patch_baseline_for_patch_group(
        OperatingSystem="AMAZON_LINUX", PatchGroup=patch_group_name
    )

    assert (
        resp["BaselineId"]
        == "arn:aws:ssm:us-west-2:280605243866:patchbaseline/pb-0d5ff2de2fa3fa0ff"
    )
    assert resp["PatchGroup"] == patch_group_name


@mock_aws
def test_deregister_patch_baseline_for_patch_group():
    client = boto3.client("ssm", region_name="us-east-2")
    patch_group_name = "test"

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
    baseline_id = client.create_patch_baseline(
        Name=baseline_name,
        OperatingSystem="AMAZON_LINUX",
        Description=baseline_description,
        ApprovalRules=approval_rules,
    )["BaselineId"]
    client.register_patch_baseline_for_patch_group(
        BaselineId=baseline_id, PatchGroup=patch_group_name
    )

    resp = client.deregister_patch_baseline_for_patch_group(
        BaselineId=baseline_id, PatchGroup=patch_group_name
    )

    assert resp["BaselineId"] == baseline_id
    assert resp["PatchGroup"] == patch_group_name


@mock_aws
def test_deregister_patch_baseline_for_patch_group_default():
    client = boto3.client("ssm", region_name="us-east-2")
    patch_group_name = "test"
    default_baseline = (
        "arn:aws:ssm:us-west-2:280605243866:patchbaseline/pb-0d5ff2de2fa3fa0ff"
    )
    resp = client.deregister_patch_baseline_for_patch_group(
        BaselineId=default_baseline, PatchGroup=patch_group_name
    )

    assert resp["BaselineId"] == default_baseline
    assert resp["PatchGroup"] == patch_group_name
