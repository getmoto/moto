import boto3

from moto import mock_inspector2
from tests import DEFAULT_ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_inspector2
def test_organization_configuration():
    client = boto3.client("inspector2", region_name="us-west-1")

    resp = client.enable(accountIds=[DEFAULT_ACCOUNT_ID], resourceTypes=["EC2", "ECR"])
    assert resp["accounts"] == [
        {
            "accountId": DEFAULT_ACCOUNT_ID,
            "resourceStatus": {
                "ec2": "ENABLED",
                "ecr": "ENABLED",
                "lambda": "DISABLED",
                "lambdaCode": "DISABLED",
            },
            "status": "ENABLED",
        }
    ]
    assert resp["failedAccounts"] == []

    resp = client.batch_get_account_status(accountIds=[DEFAULT_ACCOUNT_ID])
    assert resp["accounts"] == [
        {
            "accountId": "123456789012",
            "resourceState": {
                "ec2": {"status": "ENABLED"},
                "ecr": {"status": "ENABLED"},
                "lambda": {"status": "DISABLED"},
                "lambdaCode": {"status": "DISABLED"},
            },
            "state": {"status": "ENABLED"},
        }
    ]
    assert resp["failedAccounts"] == []

    resp = client.disable(
        accountIds=[DEFAULT_ACCOUNT_ID], resourceTypes=["LAMBDA", "ECR"]
    )
    assert resp["accounts"] == [
        {
            "accountId": DEFAULT_ACCOUNT_ID,
            "resourceStatus": {
                "ec2": "ENABLED",
                "ecr": "DISABLED",
                "lambda": "DISABLED",
                "lambdaCode": "DISABLED",
            },
            "status": "ENABLED",
        }
    ]

    client.disable(accountIds=[DEFAULT_ACCOUNT_ID], resourceTypes=["EC2"])

    resp = client.batch_get_account_status(accountIds=[DEFAULT_ACCOUNT_ID])
    assert resp["accounts"][0]["state"] == {"status": "DISABLED"}
