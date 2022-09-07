import unittest
import boto3
from moto import mock_sts, mock_sqs
from uuid import uuid4


class TestStsAssumeRole(unittest.TestCase):
    @mock_sqs
    @mock_sts
    def test_list_queues_in_different_account(self):

        sqs = boto3.client("sqs", region_name="us-east-1")
        queue_url = sqs.create_queue(QueueName=str(uuid4()))["QueueUrl"]

        # verify function exists
        all_urls = sqs.list_queues()["QueueUrls"]
        all_urls.should.contain(queue_url)

        # assume role to another aws account
        account_b = "111111111111"
        sts = boto3.client("sts", region_name="us-east-1")
        response = sts.assume_role(
            RoleArn=f"arn:aws:iam::{account_b}:role/my-role",
            RoleSessionName="test-session-name",
            ExternalId="test-external-id",
        )
        client2 = boto3.client(
            "sqs",
            aws_access_key_id=response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
            aws_session_token=response["Credentials"]["SessionToken"],
            region_name="us-east-1",
        )

        # client2 belongs to another account, where there are no queues
        client2.list_queues().shouldnt.have.key("QueueUrls")
