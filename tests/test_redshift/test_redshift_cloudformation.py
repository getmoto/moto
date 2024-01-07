import json

import boto3

from moto import mock_aws
from tests.test_cloudformation.fixtures import redshift


@mock_aws
def test_redshift_stack():
    redshift_template_json = json.dumps(redshift.template)

    ec2 = boto3.client("ec2", region_name="us-west-2")
    cf = boto3.client("cloudformation", region_name="us-west-2")
    cf.create_stack(
        StackName="redshift_stack",
        TemplateBody=redshift_template_json,
        Parameters=[
            {"ParameterKey": "DatabaseName", "ParameterValue": "mydb"},
            {"ParameterKey": "ClusterType", "ParameterValue": "multi-node"},
            {"ParameterKey": "NumberOfNodes", "ParameterValue": "2"},
            {"ParameterKey": "NodeType", "ParameterValue": "dw1.xlarge"},
            {"ParameterKey": "MasterUsername", "ParameterValue": "myuser"},
            {"ParameterKey": "MasterUserPassword", "ParameterValue": "mypass"},
            {"ParameterKey": "InboundTraffic", "ParameterValue": "10.0.0.1/16"},
            {"ParameterKey": "PortNumber", "ParameterValue": "5439"},
        ],
    )

    redshift_conn = boto3.client("redshift", region_name="us-west-2")

    cluster_res = redshift_conn.describe_clusters()
    clusters = cluster_res["Clusters"]
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster["DBName"] == "mydb"
    assert cluster["NumberOfNodes"] == 2
    assert cluster["NodeType"] == "dw1.xlarge"
    assert cluster["MasterUsername"] == "myuser"
    assert cluster["Endpoint"]["Port"] == 5439
    assert len(cluster["VpcSecurityGroups"]) == 1
    security_group_id = cluster["VpcSecurityGroups"][0]["VpcSecurityGroupId"]

    groups = ec2.describe_security_groups(GroupIds=[security_group_id])[
        "SecurityGroups"
    ]
    assert len(groups) == 1
    group = groups[0]
    assert len(group["IpPermissions"]) == 1
    assert group["IpPermissions"][0]["IpRanges"][0]["CidrIp"] == "10.0.0.1/16"
