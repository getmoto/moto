import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_organization_configuration():
    client = boto3.client("inspector2", region_name="us-west-1")

    resp = client.describe_organization_configuration()

    assert resp["autoEnable"] == {
        "ec2": False,
        "ecr": False,
        "lambda": False,
        "lambdaCode": False,
    }
    assert resp["maxAccountLimitReached"] is False

    resp = client.update_organization_configuration(
        autoEnable={
            "ec2": True,
            "ecr": False,
            "lambda": True,
            "lambdaCode": False,
        }
    )
    assert resp["autoEnable"] == {
        "ec2": True,
        "ecr": False,
        "lambda": True,
        "lambdaCode": False,
    }

    resp = client.describe_organization_configuration()

    assert resp["autoEnable"] == {
        "ec2": True,
        "ecr": False,
        "lambda": True,
        "lambdaCode": False,
    }
