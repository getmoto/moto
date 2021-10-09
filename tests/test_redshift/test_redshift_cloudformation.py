import boto3
import json
import sure  # noqa

from moto import mock_cloudformation, mock_ec2, mock_redshift
from tests.test_cloudformation.fixtures import redshift


@mock_ec2
@mock_redshift
@mock_cloudformation
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
    clusters.should.have.length_of(1)
    cluster = clusters[0]
    cluster["DBName"].should.equal("mydb")
    cluster["NumberOfNodes"].should.equal(2)
    cluster["NodeType"].should.equal("dw1.xlarge")
    cluster["MasterUsername"].should.equal("myuser")
    cluster["Endpoint"]["Port"].should.equal(5439)
    cluster["VpcSecurityGroups"].should.have.length_of(1)
    security_group_id = cluster["VpcSecurityGroups"][0]["VpcSecurityGroupId"]

    groups = ec2.describe_security_groups(GroupIds=[security_group_id])[
        "SecurityGroups"
    ]
    groups.should.have.length_of(1)
    group = groups[0]
    group["IpPermissions"].should.have.length_of(1)
    group["IpPermissions"][0]["IpRanges"][0]["CidrIp"].should.equal("10.0.0.1/16")
