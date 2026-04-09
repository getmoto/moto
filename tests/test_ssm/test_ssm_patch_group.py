import boto3
import botocore
import pytest

from moto import mock_aws
from moto.utilities.utils import load_resource

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
def test_register_patch_baseline_for_patch_group_invalid_id():
    client = boto3.client("ssm", region_name="us-east-2")
    patch_group_name = "test"
    bad_baseline_id = "pb-00000000000000000"
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        client.register_patch_baseline_for_patch_group(
            BaselineId=bad_baseline_id, PatchGroup=patch_group_name
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "DoesNotExistException"
    assert err["Message"] == f"Maintenance window {bad_baseline_id} does not exist"


@mock_aws
def test_register_patch_baseline_for_patch_group_already_exists():
    client = boto3.client("ssm", region_name="us-east-2")
    patch_group_name = "test"
    operating_system = "AMAZON_LINUX"
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
    baseline_id_a = client.create_patch_baseline(
        Name=baseline_name,
        OperatingSystem=operating_system,
        Description=baseline_description,
        ApprovalRules=approval_rules,
    )["BaselineId"]
    baseline_id_b = client.create_patch_baseline(
        Name=baseline_name,
        OperatingSystem=operating_system,
        Description=baseline_description,
        ApprovalRules=approval_rules,
    )["BaselineId"]
    client.register_patch_baseline_for_patch_group(
        BaselineId=baseline_id_a, PatchGroup=patch_group_name
    )
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        client.register_patch_baseline_for_patch_group(
            BaselineId=baseline_id_b, PatchGroup=patch_group_name
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "AlreadyExistsException"
    assert (
        err["Message"]
        == f"Patch Group baseline already has a baseline registered for OperatingSystem {operating_system}."
    )


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
    region = "us-east-2"
    client = boto3.client("ssm", region_name=region)
    patch_group_name = "test"
    default_baseline = load_resource(
        __name__, "../../moto/ssm/resources/default_baselines.json"
    )[region]["AMAZON_LINUX"]

    resp = client.get_patch_baseline_for_patch_group(
        OperatingSystem="AMAZON_LINUX", PatchGroup=patch_group_name
    )

    assert resp["BaselineId"] == default_baseline
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
    region = "us-east-2"
    client = boto3.client("ssm", region_name=region)
    patch_group_name = "test"
    default_baseline = load_resource(
        __name__, "../../moto/ssm/resources/default_baselines.json"
    )[region]["AMAZON_LINUX"]
    resp = client.deregister_patch_baseline_for_patch_group(
        BaselineId=default_baseline, PatchGroup=patch_group_name
    )

    assert resp["BaselineId"] == default_baseline
    assert resp["PatchGroup"] == patch_group_name


@mock_aws
def test_deregister_patch_baseline_for_patch_group_invalid_id():
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
    # now try to deregister a non-registered patch baseline
    bad_baseline_id = "pb-00000000000000000"
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        client.deregister_patch_baseline_for_patch_group(
            BaselineId=bad_baseline_id, PatchGroup=patch_group_name
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "DoesNotExistException"
    assert err["Message"] == "Patch Baseline to be retrieved does not exist."
