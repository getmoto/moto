import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ssm


@mock_ssm
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
    response.should.have.key("BaselineIdentities").have.length_of(1)
    baseline = response["BaselineIdentities"][0]
    baseline.should.have.key("BaselineId").equal(_id)
    baseline.should.have.key("BaselineName").equal(baseline_name)
    baseline.should.have.key("DefaultBaseline").equal(False)
    baseline.should.have.key("OperatingSystem").equal("AMAZON_LINUX")
    baseline.should.have.key("BaselineDescription").equal(baseline_description)


@mock_ssm
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
    response.should.have.key("BaselineIdentities").have.length_of(0)
