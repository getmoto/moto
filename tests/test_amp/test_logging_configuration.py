"""Unit tests for amp-supported APIs."""
import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_amp

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


# @mock_amp
# def test_create_rule_alertmanager():
#     client = boto3.client("amp", region_name="us-east-2")

#     workspace = client.create_workspace(alias="test", tags={"t": "v"})
#     workspace_id = workspace["workspaceId"]
#     resp = client.create_alert_manager_definition(
#         data=b"asdfff", workspaceId=workspace_id
#     )

#     assert "status" in resp
#     assert resp["status"]["statusCode"] == "ACTIVE"
#     assert resp["status"]["statusReason"] == ""


@mock_amp
def test_delete_alertmanager():
    client = boto3.client("amp", region_name="us-east-2")
    workspace_id = client.create_workspace()["workspaceId"]
    create_resp = client.create_alert_manager_definition(data=b"asdf", workspaceId=workspace_id)
    alert_manager_exists_resp = client.describe_alert_manager_definition(workspaceId=workspace_id)
    pytest.set_trace()
    delete_resp = client.delete_alert_manager_definition(workspaceId=workspace_id)
    alert_manager_is_deleted_resp = client.describe_alert_manager_definition(workspaceId=workspace_id)
    pytest.set_trace()

# @mock_amp
# def test_describe_rule_groups_namespace():
#     client = boto3.client("amp", region_name="us-east-2")

#     workspace_id = client.create_workspace()["workspaceId"]
#     client.create_rule_groups_namespace(
#         data=b"asdf", name="myname", workspaceId=workspace_id
#     )

#     resp = client.describe_rule_groups_namespace(
#         name="myname", workspaceId=workspace_id
#     )
#     assert "ruleGroupsNamespace" in resp
#     ns = resp["ruleGroupsNamespace"]

#     assert "arn" in ns
#     assert "createdAt" in ns
#     assert ns["data"] == b"asdf"
#     assert "modifiedAt" in ns
#     assert ns["name"] == "myname"
#     assert "status" in ns


# @mock_amp
# def test_put_rule_groups_namespace():
#     client = boto3.client("amp", region_name="eu-west-1")

#     workspace_id = client.create_workspace()["workspaceId"]
#     client.create_rule_groups_namespace(
#         data=b"asdf", name="myname", workspaceId=workspace_id
#     )

#     client.put_rule_groups_namespace(
#         name="myname", workspaceId=workspace_id, data=b"updated"
#     )

#     resp = client.describe_rule_groups_namespace(
#         name="myname", workspaceId=workspace_id
#     )
#     assert "ruleGroupsNamespace" in resp
#     ns = resp["ruleGroupsNamespace"]

#     assert "arn" in ns
#     assert "createdAt" in ns
#     assert ns["data"] == b"updated"


# @mock_amp
# def test_list_rule_groups_namespaces():
#     client = boto3.client("amp", region_name="ap-southeast-1")
#     w_id = client.create_workspace()["workspaceId"]
#     for idx in range(15):
#         client.create_rule_groups_namespace(
#             data=b"a", name=f"ns{idx}", workspaceId=w_id
#         )

#     resp = client.list_rule_groups_namespaces(workspaceId=w_id)
#     assert len(resp["ruleGroupsNamespaces"]) == 15
#     assert "nextToken" not in resp

#     resp = client.list_rule_groups_namespaces(workspaceId=w_id, name="ns1")
#     assert len(resp["ruleGroupsNamespaces"]) == 6
#     names = [ns["name"] for ns in resp["ruleGroupsNamespaces"]]
#     assert set(names) == {"ns10", "ns13", "ns1", "ns12", "ns11", "ns14"}

#     resp = client.list_rule_groups_namespaces(workspaceId=w_id, name="ns10")
#     assert len(resp["ruleGroupsNamespaces"]) == 1
#     names = [ns["name"] for ns in resp["ruleGroupsNamespaces"]]
#     assert set(names) == {"ns10"}
