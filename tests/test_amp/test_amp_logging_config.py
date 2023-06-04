import boto3
import unittest
from moto import mock_amp


@mock_amp
class TestAmpLoggingConfig(unittest.TestCase):
    def setUp(self) -> None:
        self.client = boto3.client("amp", region_name="us-east-2")

        workspace = self.client.create_workspace(alias="test", tags={"t": "v"})
        self.workspace_id = workspace["workspaceId"]

    def test_describe_logging(self):
        resp = self.client.describe_logging_configuration(workspaceId=self.workspace_id)
        assert resp["loggingConfiguration"] == {}

    def test_create_logging(self):
        resp = self.client.create_logging_configuration(
            workspaceId=self.workspace_id, logGroupArn="log/arn"
        )
        assert resp["status"] == {"statusCode": "ACTIVE"}

        resp = self.client.describe_logging_configuration(
            workspaceId=self.workspace_id
        )["loggingConfiguration"]
        assert "createdAt" in resp
        assert resp["logGroupArn"] == "log/arn"
        assert resp["status"] == {"statusCode": "ACTIVE"}
        assert resp["workspace"] == self.workspace_id

    def test_update_logging(self):
        self.client.create_logging_configuration(
            workspaceId=self.workspace_id, logGroupArn="log/arn"
        )

        resp = self.client.update_logging_configuration(
            workspaceId=self.workspace_id, logGroupArn="log/arn2"
        )
        assert resp["status"] == {"statusCode": "ACTIVE"}

        resp = self.client.describe_logging_configuration(
            workspaceId=self.workspace_id
        )["loggingConfiguration"]
        assert "modifiedAt" in resp
        assert resp["logGroupArn"] == "log/arn2"

    def test_delete_logging(self):
        resp = self.client.create_logging_configuration(
            workspaceId=self.workspace_id, logGroupArn="log/arn"
        )

        self.client.delete_logging_configuration(workspaceId=self.workspace_id)

        resp = self.client.describe_logging_configuration(workspaceId=self.workspace_id)
        assert resp["loggingConfiguration"] == {}
