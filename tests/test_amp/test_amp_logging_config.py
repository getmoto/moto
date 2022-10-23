import boto3
import sys
import unittest
from moto import mock_amp


@mock_amp
class TestAmpLoggingConfig(unittest.TestCase):
    def setUp(self) -> None:
        if sys.version_info < (3, 7):
            raise unittest.SkipTest(
                "Cannot test this in Py3.6; outdated botocore dependencies do not yet support this feature"
            )
        self.client = boto3.client("amp", region_name="us-east-2")

        workspace = self.client.create_workspace(alias="test", tags={"t": "v"})
        self.workspace_id = workspace["workspaceId"]

    def test_describe_logging(self):
        resp = self.client.describe_logging_configuration(workspaceId=self.workspace_id)
        resp.should.have.key("loggingConfiguration").equals({})

    def test_create_logging(self):
        resp = self.client.create_logging_configuration(
            workspaceId=self.workspace_id, logGroupArn="log/arn"
        )
        resp.should.have.key("status").equals({"statusCode": "ACTIVE"})

        resp = self.client.describe_logging_configuration(
            workspaceId=self.workspace_id
        )["loggingConfiguration"]
        resp.should.have.key("createdAt")
        resp.should.have.key("logGroupArn").equals("log/arn")
        resp.should.have.key("status").equals({"statusCode": "ACTIVE"})
        resp.should.have.key("workspace").equals(self.workspace_id)

    def test_update_logging(self):
        self.client.create_logging_configuration(
            workspaceId=self.workspace_id, logGroupArn="log/arn"
        )

        resp = self.client.update_logging_configuration(
            workspaceId=self.workspace_id, logGroupArn="log/arn2"
        )
        resp.should.have.key("status").equals({"statusCode": "ACTIVE"})

        resp = self.client.describe_logging_configuration(
            workspaceId=self.workspace_id
        )["loggingConfiguration"]
        resp.should.have.key("modifiedAt")
        resp.should.have.key("logGroupArn").equals("log/arn2")

    def test_delete_logging(self):
        resp = self.client.create_logging_configuration(
            workspaceId=self.workspace_id, logGroupArn="log/arn"
        )

        self.client.delete_logging_configuration(workspaceId=self.workspace_id)

        resp = self.client.describe_logging_configuration(workspaceId=self.workspace_id)
        resp.should.have.key("loggingConfiguration").equals({})
