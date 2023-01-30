import boto3

from moto import mock_ec2, mock_eks
from .test_eks_constants import NODEROLE_ARN_VALUE, SUBNET_IDS


@mock_eks
def test_passing_an_unknown_launchtemplate_is_supported():
    eks = boto3.client("eks", "us-east-2")
    eks.create_cluster(name="a", roleArn=NODEROLE_ARN_VALUE, resourcesVpcConfig={})
    group = eks.create_nodegroup(
        clusterName="a",
        nodegroupName="b",
        launchTemplate={"name": "random"},
        nodeRole=NODEROLE_ARN_VALUE,
        subnets=SUBNET_IDS,
    )["nodegroup"]

    group["launchTemplate"].should.equal({"name": "random"})


@mock_ec2
@mock_eks
def test_passing_a_known_launchtemplate_by_name():
    ec2 = boto3.client("ec2", region_name="us-east-2")
    eks = boto3.client("eks", "us-east-2")

    lt_id = ec2.create_launch_template(
        LaunchTemplateName="ltn",
        LaunchTemplateData={
            "TagSpecifications": [
                {"ResourceType": "instance", "Tags": [{"Key": "t", "Value": "v"}]}
            ]
        },
    )["LaunchTemplate"]["LaunchTemplateId"]

    eks.create_cluster(name="a", roleArn=NODEROLE_ARN_VALUE, resourcesVpcConfig={})
    group = eks.create_nodegroup(
        clusterName="a",
        nodegroupName="b",
        launchTemplate={"name": "ltn"},
        nodeRole=NODEROLE_ARN_VALUE,
        subnets=SUBNET_IDS,
    )["nodegroup"]

    group["launchTemplate"].should.equal({"name": "ltn", "id": lt_id})


@mock_ec2
@mock_eks
def test_passing_a_known_launchtemplate_by_id():
    ec2 = boto3.client("ec2", region_name="us-east-2")
    eks = boto3.client("eks", "us-east-2")

    lt_id = ec2.create_launch_template(
        LaunchTemplateName="ltn",
        LaunchTemplateData={
            "TagSpecifications": [
                {"ResourceType": "instance", "Tags": [{"Key": "t", "Value": "v"}]}
            ]
        },
    )["LaunchTemplate"]["LaunchTemplateId"]

    eks.create_cluster(name="a", roleArn=NODEROLE_ARN_VALUE, resourcesVpcConfig={})
    group = eks.create_nodegroup(
        clusterName="a",
        nodegroupName="b",
        launchTemplate={"id": lt_id},
        nodeRole=NODEROLE_ARN_VALUE,
        subnets=SUBNET_IDS,
    )["nodegroup"]

    group["launchTemplate"].should.equal({"name": "ltn", "id": lt_id})
