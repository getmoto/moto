import json
import boto3
from moto import mock_aws
from moto.core import enable_iam_authentication


@mock_aws
def test_dynamodb_authorization_put_item():
    """
    Test case for [Issue 9580](https://github.com/getmoto/moto/issues/9580)
    The policy in this test is using a wildcard * for the ARN resource, for now, due to a related but different issue
    https://github.com/getmoto/moto/issues/9581.
    This test could cover both cases by using the table ARN instead of the wildcard.
    """
    dynamo = boto3.resource("dynamodb")
    table = dynamo.create_table(
        TableName="example-table",
        KeySchema=[
            {'AttributeName': 'pk', 'KeyType': 'HASH'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pk', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )

    iam = boto3.client("iam")
    role_arn = iam.create_role(
        RoleName="test-role",
        AssumeRolePolicyDocument=json.dumps(dict(
            Version="2012-10-17",
            Statement=[
                dict(Effect="Allow", Principal=dict(AWS="*"), Action="sts:AssumeRole")
            ]
        ))
    )["Role"]["Arn"]

    policy_arn = iam.create_policy(
        PolicyName="test-policy",
        PolicyDocument=json.dumps(dict(
            Version="2012-10-17",
            Statement=[
                dict(Effect="Allow", Action="dynamodb:*", Resource="*") # Could be table.table_arn when #9581 is fixed
            ]
        ))
    )["Policy"]["Arn"]

    iam.attach_role_policy(
        RoleName="test-role",
        PolicyArn=policy_arn
    )

    sts = boto3.client("sts")
    crendentials = sts.assume_role(RoleArn=role_arn, RoleSessionName="test-session")["Credentials"]

    with enable_iam_authentication():
        restritced_session = boto3.Session(aws_access_key_id=crendentials["AccessKeyId"],
                                          aws_secret_access_key=crendentials["SecretAccessKey"],
                                          aws_session_token=crendentials["SessionToken"])
        restricted_table = restritced_session.resource("dynamodb").Table(table.table_name)
        restricted_table.put_item(Item={"pk": "123"})

    # If we are allowed to put the item, then this test has passed.

