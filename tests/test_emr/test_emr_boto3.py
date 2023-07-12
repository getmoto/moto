# -*- coding: utf-8 -*-
import time
from copy import deepcopy
from datetime import datetime, timezone

import boto3
import json
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
import pytest

from moto import mock_emr
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


run_job_flow_args = dict(
    Instances={
        "InstanceCount": 3,
        "KeepJobFlowAliveWhenNoSteps": True,
        "MasterInstanceType": "c3.medium",
        "Placement": {"AvailabilityZone": "us-east-1a"},
        "SlaveInstanceType": "c3.xlarge",
    },
    JobFlowRole="EMR_EC2_DefaultRole",
    LogUri="s3://mybucket/log",
    Name="cluster",
    ServiceRole="EMR_DefaultRole",
    VisibleToAllUsers=True,
)


input_instance_groups = [
    {
        "InstanceCount": 1,
        "InstanceRole": "MASTER",
        "InstanceType": "c1.medium",
        "Market": "ON_DEMAND",
        "Name": "master",
    },
    {
        "InstanceCount": 3,
        "InstanceRole": "CORE",
        "InstanceType": "c1.medium",
        "Market": "ON_DEMAND",
        "Name": "core",
    },
    {
        "InstanceCount": 6,
        "InstanceRole": "TASK",
        "InstanceType": "c3.large",
        "Market": "SPOT",
        "Name": "task-1",
        "BidPrice": "0.07",
    },
    {
        "InstanceCount": 10,
        "InstanceRole": "TASK",
        "InstanceType": "c1.xlarge",
        "Market": "SPOT",
        "Name": "task-2",
        "BidPrice": "0.05",
        "EbsConfiguration": {
            "EbsBlockDeviceConfigs": [
                {
                    "VolumeSpecification": {"VolumeType": "gp2", "SizeInGB": 800},
                    "VolumesPerInstance": 6,
                },
            ],
            "EbsOptimized": True,
        },
    },
]


@mock_emr
@pytest.mark.filterwarnings("ignore")
def test_describe_cluster():
    region_name = "us-east-1"
    client = boto3.client("emr", region_name=region_name)

    args = deepcopy(run_job_flow_args)
    args["Applications"] = [{"Name": "Spark", "Version": "2.4.2"}]
    args["Configurations"] = [
        {
            "Classification": "yarn-site",
            "Properties": {
                "someproperty": "somevalue",
                "someotherproperty": "someothervalue",
            },
        },
        {
            "Classification": "nested-configs",
            "Properties": {},
            "Configurations": [
                {
                    "Classification": "nested-config",
                    "Properties": {"nested-property": "nested-value"},
                }
            ],
        },
    ]
    args["Instances"]["AdditionalMasterSecurityGroups"] = ["additional-master"]
    args["Instances"]["AdditionalSlaveSecurityGroups"] = ["additional-slave"]
    args["Instances"]["Ec2KeyName"] = "mykey"
    args["Instances"]["Ec2SubnetId"] = "subnet-8be41cec"
    args["Instances"]["EmrManagedMasterSecurityGroup"] = "master-security-group"
    args["Instances"]["EmrManagedSlaveSecurityGroup"] = "slave-security-group"
    args["Instances"]["KeepJobFlowAliveWhenNoSteps"] = False
    args["Instances"]["ServiceAccessSecurityGroup"] = "service-access-security-group"
    args["KerberosAttributes"] = {
        "Realm": "MY-REALM.COM",
        "KdcAdminPassword": "SuperSecretPassword2",
        "CrossRealmTrustPrincipalPassword": "SuperSecretPassword3",
        "ADDomainJoinUser": "Bob",
        "ADDomainJoinPassword": "SuperSecretPassword4",
    }
    args["Tags"] = [{"Key": "tag1", "Value": "val1"}, {"Key": "tag2", "Value": "val2"}]
    args["SecurityConfiguration"] = "my-security-configuration"
    args["AutoScalingRole"] = "EMR_AutoScaling_DefaultRole"
    args["AutoTerminationPolicy"] = {"IdleTimeout": 123}

    cluster_id = client.run_job_flow(**args)["JobFlowId"]

    cl = client.describe_cluster(ClusterId=cluster_id)["Cluster"]
    cl["Applications"][0]["Name"].should.equal("Spark")
    cl["Applications"][0]["Version"].should.equal("2.4.2")
    cl["AutoTerminate"].should.equal(True)

    config = cl["Configurations"][0]
    config["Classification"].should.equal("yarn-site")
    config["Properties"].should.equal(args["Configurations"][0]["Properties"])

    nested_config = cl["Configurations"][1]
    nested_config["Classification"].should.equal("nested-configs")
    nested_config["Properties"].should.equal(args["Configurations"][1]["Properties"])

    attrs = cl["Ec2InstanceAttributes"]
    attrs["AdditionalMasterSecurityGroups"].should.equal(
        args["Instances"]["AdditionalMasterSecurityGroups"]
    )
    attrs["AdditionalSlaveSecurityGroups"].should.equal(
        args["Instances"]["AdditionalSlaveSecurityGroups"]
    )
    attrs["Ec2AvailabilityZone"].should.equal("us-east-1a")
    attrs["Ec2KeyName"].should.equal(args["Instances"]["Ec2KeyName"])
    attrs["Ec2SubnetId"].should.equal(args["Instances"]["Ec2SubnetId"])
    attrs["EmrManagedMasterSecurityGroup"].should.equal(
        args["Instances"]["EmrManagedMasterSecurityGroup"]
    )
    attrs["EmrManagedSlaveSecurityGroup"].should.equal(
        args["Instances"]["EmrManagedSlaveSecurityGroup"]
    )
    attrs["IamInstanceProfile"].should.equal(args["JobFlowRole"])
    attrs["ServiceAccessSecurityGroup"].should.equal(
        args["Instances"]["ServiceAccessSecurityGroup"]
    )
    cl["Id"].should.equal(cluster_id)
    cl["KerberosAttributes"].should.equal(args["KerberosAttributes"])
    cl["LogUri"].should.equal(args["LogUri"])
    cl["MasterPublicDnsName"].should.be.a(str)
    cl["Name"].should.equal(args["Name"])
    cl["NormalizedInstanceHours"].should.equal(0)
    # cl['ReleaseLabel'].should.equal('emr-5.0.0')
    cl.shouldnt.have.key("RequestedAmiVersion")
    cl["RunningAmiVersion"].should.equal("1.0.0")
    cl["SecurityConfiguration"].should.be.a(str)
    cl["SecurityConfiguration"].should.equal(args["SecurityConfiguration"])
    cl["ServiceRole"].should.equal(args["ServiceRole"])
    cl["AutoScalingRole"].should.equal(args["AutoScalingRole"])

    status = cl["Status"]
    status["State"].should.equal("TERMINATED")
    # cluster['Status']['StateChangeReason']
    status["Timeline"]["CreationDateTime"].should.be.a("datetime.datetime")
    # status['Timeline']['EndDateTime'].should.equal(datetime(2014, 1, 24, 2, 19, 46, tzinfo=timezone.utc))
    status["Timeline"]["ReadyDateTime"].should.be.a("datetime.datetime")

    dict((t["Key"], t["Value"]) for t in cl["Tags"]).should.equal(
        dict((t["Key"], t["Value"]) for t in args["Tags"])
    )

    cl["TerminationProtected"].should.equal(False)
    cl["VisibleToAllUsers"].should.equal(True)
    cl["ClusterArn"].should.equal(
        f"arn:aws:elasticmapreduce:{region_name}:{ACCOUNT_ID}:cluster/{cluster_id}"
    )


@mock_emr
def test_describe_cluster_not_found():
    conn = boto3.client("emr", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        conn.describe_cluster(ClusterId="DummyId")

    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_emr
def test_describe_job_flows():
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    expected = {}

    for idx in range(4):
        cluster_name = "cluster" + str(idx)
        args["Name"] = cluster_name
        cluster_id = client.run_job_flow(**args)["JobFlowId"]
        expected[cluster_id] = {
            "Id": cluster_id,
            "Name": cluster_name,
            "State": "WAITING",
        }

    # need sleep since it appears the timestamp is always rounded to
    # the nearest second internally
    time.sleep(1)
    timestamp = datetime.now(timezone.utc)
    time.sleep(1)

    for idx in range(4, 6):
        cluster_name = "cluster" + str(idx)
        args["Name"] = cluster_name
        cluster_id = client.run_job_flow(**args)["JobFlowId"]
        client.terminate_job_flows(JobFlowIds=[cluster_id])
        expected[cluster_id] = {
            "Id": cluster_id,
            "Name": cluster_name,
            "State": "TERMINATED",
        }

    resp = client.describe_job_flows()
    resp["JobFlows"].should.have.length_of(6)

    for cluster_id in expected:
        resp = client.describe_job_flows(JobFlowIds=[cluster_id])
        resp["JobFlows"].should.have.length_of(1)
        resp["JobFlows"][0]["JobFlowId"].should.equal(cluster_id)

    resp = client.describe_job_flows(JobFlowStates=["WAITING"])
    resp["JobFlows"].should.have.length_of(4)
    for x in resp["JobFlows"]:
        x["ExecutionStatusDetail"]["State"].should.equal("WAITING")

    resp = client.describe_job_flows(CreatedBefore=timestamp)
    resp["JobFlows"].should.have.length_of(4)

    resp = client.describe_job_flows(CreatedAfter=timestamp)
    resp["JobFlows"].should.have.length_of(2)


@mock_emr
@pytest.mark.filterwarnings("ignore")
def test_describe_job_flow():
    client = boto3.client("emr", region_name="us-east-1")

    args = deepcopy(run_job_flow_args)
    args["AmiVersion"] = "3.8.1"
    args["Instances"].update(
        {
            "Ec2KeyName": "ec2keyname",
            "Ec2SubnetId": "subnet-8be41cec",
            "HadoopVersion": "2.4.0",
        }
    )
    args["VisibleToAllUsers"] = True

    cluster_id = client.run_job_flow(**args)["JobFlowId"]

    jf = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]

    jf["AmiVersion"].should.equal(args["AmiVersion"])
    jf.shouldnt.have.key("BootstrapActions")
    esd = jf["ExecutionStatusDetail"]
    esd["CreationDateTime"].should.be.a("datetime.datetime")
    # esd['EndDateTime'].should.be.a('datetime.datetime')
    # esd['LastStateChangeReason'].should.be.a(str)
    esd["ReadyDateTime"].should.be.a("datetime.datetime")
    esd["StartDateTime"].should.be.a("datetime.datetime")
    esd["State"].should.equal("WAITING")
    attrs = jf["Instances"]
    attrs["Ec2KeyName"].should.equal(args["Instances"]["Ec2KeyName"])
    attrs["Ec2SubnetId"].should.equal(args["Instances"]["Ec2SubnetId"])
    attrs["HadoopVersion"].should.equal(args["Instances"]["HadoopVersion"])
    attrs["InstanceCount"].should.equal(args["Instances"]["InstanceCount"])
    for ig in attrs["InstanceGroups"]:
        # ig['BidPrice']
        ig["CreationDateTime"].should.be.a("datetime.datetime")
        # ig['EndDateTime'].should.be.a('datetime.datetime')
        ig["InstanceGroupId"].should.be.a(str)
        ig["InstanceRequestCount"].should.be.a(int)
        ig["InstanceRole"].should.be.within(["MASTER", "CORE"])
        ig["InstanceRunningCount"].should.be.a(int)
        ig["InstanceType"].should.be.within(["c3.medium", "c3.xlarge"])
        # ig['LastStateChangeReason'].should.be.a(str)
        ig["Market"].should.equal("ON_DEMAND")
        ig["Name"].should.be.a(str)
        ig["ReadyDateTime"].should.be.a("datetime.datetime")
        ig["StartDateTime"].should.be.a("datetime.datetime")
        ig["State"].should.equal("RUNNING")
    attrs["KeepJobFlowAliveWhenNoSteps"].should.equal(True)
    # attrs['MasterInstanceId'].should.be.a(str)
    attrs["MasterInstanceType"].should.equal(args["Instances"]["MasterInstanceType"])
    attrs["MasterPublicDnsName"].should.be.a(str)
    attrs["NormalizedInstanceHours"].should.equal(0)
    attrs["Placement"]["AvailabilityZone"].should.equal(
        args["Instances"]["Placement"]["AvailabilityZone"]
    )
    attrs["SlaveInstanceType"].should.equal(args["Instances"]["SlaveInstanceType"])
    attrs["TerminationProtected"].should.equal(False)
    jf["JobFlowId"].should.equal(cluster_id)
    jf["JobFlowRole"].should.equal(args["JobFlowRole"])
    jf["LogUri"].should.equal(args["LogUri"])
    jf["Name"].should.equal(args["Name"])
    jf["ServiceRole"].should.equal(args["ServiceRole"])
    jf["Steps"].should.equal([])
    jf["SupportedProducts"].should.equal([])
    jf["VisibleToAllUsers"].should.equal(True)


@mock_emr
def test_list_clusters():
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    expected = {}

    for idx in range(40):
        cluster_name = "jobflow" + str(idx)
        args["Name"] = cluster_name
        cluster_id = client.run_job_flow(**args)["JobFlowId"]
        expected[cluster_id] = {
            "Id": cluster_id,
            "Name": cluster_name,
            "NormalizedInstanceHours": 0,
            "State": "WAITING",
        }

    # need sleep since it appears the timestamp is always rounded to
    # the nearest second internally
    time.sleep(1)
    timestamp = datetime.now(timezone.utc)
    time.sleep(1)

    for idx in range(40, 70):
        cluster_name = "jobflow" + str(idx)
        args["Name"] = cluster_name
        cluster_id = client.run_job_flow(**args)["JobFlowId"]
        client.terminate_job_flows(JobFlowIds=[cluster_id])
        expected[cluster_id] = {
            "Id": cluster_id,
            "Name": cluster_name,
            "NormalizedInstanceHours": 0,
            "State": "TERMINATED",
        }

    args = {}
    while 1:
        resp = client.list_clusters(**args)
        clusters = resp["Clusters"]
        len(clusters).should.be.lower_than_or_equal_to(50)
        for x in clusters:
            y = expected[x["Id"]]
            x["Id"].should.equal(y["Id"])
            x["Name"].should.equal(y["Name"])
            x["NormalizedInstanceHours"].should.equal(y["NormalizedInstanceHours"])
            x["Status"]["State"].should.equal(y["State"])
            x["Status"]["Timeline"]["CreationDateTime"].should.be.a("datetime.datetime")
            if y["State"] == "TERMINATED":
                x["Status"]["Timeline"]["EndDateTime"].should.be.a("datetime.datetime")
            else:
                x["Status"]["Timeline"].shouldnt.have.key("EndDateTime")
            x["Status"]["Timeline"]["ReadyDateTime"].should.be.a("datetime.datetime")
        marker = resp.get("Marker")
        if marker is None:
            break
        args = {"Marker": marker}

    resp = client.list_clusters(ClusterStates=["TERMINATED"])
    resp["Clusters"].should.have.length_of(30)
    for x in resp["Clusters"]:
        x["Status"]["State"].should.equal("TERMINATED")

    resp = client.list_clusters(CreatedBefore=timestamp)
    resp["Clusters"].should.have.length_of(40)

    resp = client.list_clusters(CreatedAfter=timestamp)
    resp["Clusters"].should.have.length_of(30)


@mock_emr
def test_run_job_flow():
    region_name = "us-east-1"
    client = boto3.client("emr", region_name=region_name)
    args = deepcopy(run_job_flow_args)
    resp = client.run_job_flow(**args)
    resp["ClusterArn"].startswith(
        f"arn:aws:elasticmapreduce:{region_name}:{ACCOUNT_ID}:cluster/"
    )
    job_flow_id = resp["JobFlowId"]
    resp = client.describe_job_flows(JobFlowIds=[job_flow_id])["JobFlows"][0]
    resp["ExecutionStatusDetail"]["State"].should.equal("WAITING")
    resp["JobFlowId"].should.equal(job_flow_id)
    resp["Name"].should.equal(args["Name"])
    resp["Instances"]["MasterInstanceType"].should.equal(
        args["Instances"]["MasterInstanceType"]
    )
    resp["Instances"]["SlaveInstanceType"].should.equal(
        args["Instances"]["SlaveInstanceType"]
    )
    resp["LogUri"].should.equal(args["LogUri"])
    resp["VisibleToAllUsers"].should.equal(args["VisibleToAllUsers"])
    resp["Instances"]["NormalizedInstanceHours"].should.equal(0)
    resp["Steps"].should.equal([])


@mock_emr
def test_run_job_flow_with_invalid_params():
    client = boto3.client("emr", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        # cannot set both AmiVersion and ReleaseLabel
        args = deepcopy(run_job_flow_args)
        args["AmiVersion"] = "2.4"
        args["ReleaseLabel"] = "emr-5.0.0"
        client.run_job_flow(**args)
    ex.value.response["Error"]["Code"].should.equal("ValidationException")


@mock_emr
def test_run_job_flow_in_multiple_regions():
    regions = {}
    for region in ["us-east-1", "eu-west-1"]:
        client = boto3.client("emr", region_name=region)
        args = deepcopy(run_job_flow_args)
        args["Name"] = region
        cluster_id = client.run_job_flow(**args)["JobFlowId"]
        regions[region] = {"client": client, "cluster_id": cluster_id}

    for region in regions.keys():
        client = regions[region]["client"]
        resp = client.describe_cluster(ClusterId=regions[region]["cluster_id"])
        resp["Cluster"]["Name"].should.equal(region)


@mock_emr
def test_run_job_flow_with_new_params():
    client = boto3.client("emr", region_name="us-east-1")
    resp = client.run_job_flow(**run_job_flow_args)
    resp.should.have.key("JobFlowId")


@mock_emr
def test_run_job_flow_with_visible_to_all_users():
    client = boto3.client("emr", region_name="us-east-1")
    for expected in (True, False):
        args = deepcopy(run_job_flow_args)
        args["VisibleToAllUsers"] = expected
        resp = client.run_job_flow(**args)
        cluster_id = resp["JobFlowId"]
        resp = client.describe_cluster(ClusterId=cluster_id)
        resp["Cluster"]["VisibleToAllUsers"].should.equal(expected)


def _do_assertion_ebs_configuration(x, y):
    total_volumes = 0
    total_size = 0
    for ebs_block in y["EbsConfiguration"]["EbsBlockDeviceConfigs"]:
        total_volumes += ebs_block["VolumesPerInstance"]
        total_size += ebs_block["VolumeSpecification"]["SizeInGB"]
    # Multiply by total volumes
    total_size = total_size * total_volumes
    comp_total_size = 0
    for ebs_block in x["EbsBlockDevices"]:
        comp_total_size += ebs_block["VolumeSpecification"]["SizeInGB"]
    len(x["EbsBlockDevices"]).should.equal(total_volumes)
    comp_total_size.should.equal(comp_total_size)


@mock_emr
def test_run_job_flow_with_instance_groups():
    input_groups = dict((g["Name"], g) for g in input_instance_groups)
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["Instances"] = {"InstanceGroups": input_instance_groups}
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    groups = client.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"]
    for x in groups:
        y = input_groups[x["Name"]]
        x.should.have.key("Id")
        x["RequestedInstanceCount"].should.equal(y["InstanceCount"])
        x["InstanceGroupType"].should.equal(y["InstanceRole"])
        x["InstanceType"].should.equal(y["InstanceType"])
        x["Market"].should.equal(y["Market"])
        if "BidPrice" in y:
            x["BidPrice"].should.equal(y["BidPrice"])

        if "EbsConfiguration" in y:
            _do_assertion_ebs_configuration(x, y)


auto_scaling_policy = {
    "Constraints": {"MinCapacity": 2, "MaxCapacity": 10},
    "Rules": [
        {
            "Name": "Default-scale-out",
            "Description": "Replicates the default scale-out rule in the console for YARN memory.",
            "Action": {
                "SimpleScalingPolicyConfiguration": {
                    "AdjustmentType": "CHANGE_IN_CAPACITY",
                    "ScalingAdjustment": 1,
                    "CoolDown": 300,
                }
            },
            "Trigger": {
                "CloudWatchAlarmDefinition": {
                    "ComparisonOperator": "LESS_THAN",
                    "EvaluationPeriods": 1,
                    "MetricName": "YARNMemoryAvailablePercentage",
                    "Namespace": "AWS/ElasticMapReduce",
                    "Period": 300,
                    "Threshold": 15.0,
                    "Statistic": "AVERAGE",
                    "Unit": "PERCENT",
                    "Dimensions": [{"Key": "JobFlowId", "Value": "${emr.clusterId}"}],
                }
            },
        }
    ],
}


@mock_emr
def test_run_job_flow_with_instance_groups_with_autoscaling():
    input_groups = dict((g["Name"], g) for g in input_instance_groups)

    input_groups["core"]["AutoScalingPolicy"] = auto_scaling_policy
    input_groups["task-1"]["AutoScalingPolicy"] = auto_scaling_policy

    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["Instances"] = {"InstanceGroups": input_instance_groups}
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    groups = client.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"]
    for x in groups:
        y = deepcopy(input_groups[x["Name"]])
        if "AutoScalingPolicy" in y:
            x["AutoScalingPolicy"]["Status"]["State"].should.equal("ATTACHED")
            returned_policy = deepcopy(x["AutoScalingPolicy"])
            auto_scaling_policy_with_cluster_id = (
                _patch_cluster_id_placeholder_in_autoscaling_policy(
                    y["AutoScalingPolicy"], cluster_id
                )
            )
            del returned_policy["Status"]
            returned_policy.should.equal(auto_scaling_policy_with_cluster_id)


@mock_emr
def test_put_remove_auto_scaling_policy():
    region_name = "us-east-1"
    client = boto3.client("emr", region_name=region_name)
    args = deepcopy(run_job_flow_args)
    args["Instances"] = {"InstanceGroups": input_instance_groups}
    cluster_id = client.run_job_flow(**args)["JobFlowId"]

    core_instance_group = [
        ig
        for ig in client.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"]
        if ig["InstanceGroupType"] == "CORE"
    ][0]

    resp = client.put_auto_scaling_policy(
        ClusterId=cluster_id,
        InstanceGroupId=core_instance_group["Id"],
        AutoScalingPolicy=auto_scaling_policy,
    )

    auto_scaling_policy_with_cluster_id = (
        _patch_cluster_id_placeholder_in_autoscaling_policy(
            auto_scaling_policy, cluster_id
        )
    )
    del resp["AutoScalingPolicy"]["Status"]
    resp["AutoScalingPolicy"].should.equal(auto_scaling_policy_with_cluster_id)
    resp["ClusterArn"].should.equal(
        f"arn:aws:elasticmapreduce:{region_name}:{ACCOUNT_ID}:cluster/{cluster_id}"
    )

    core_instance_group = [
        ig
        for ig in client.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"]
        if ig["InstanceGroupType"] == "CORE"
    ][0]

    ("AutoScalingPolicy" in core_instance_group).should.equal(True)

    client.remove_auto_scaling_policy(
        ClusterId=cluster_id, InstanceGroupId=core_instance_group["Id"]
    )

    core_instance_group = [
        ig
        for ig in client.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"]
        if ig["InstanceGroupType"] == "CORE"
    ][0]

    ("AutoScalingPolicy" not in core_instance_group).should.equal(True)


def _patch_cluster_id_placeholder_in_autoscaling_policy(policy, cluster_id):
    policy_copy = deepcopy(policy)
    for rule in policy_copy["Rules"]:
        for dimension in rule["Trigger"]["CloudWatchAlarmDefinition"]["Dimensions"]:
            dimension["Value"] = cluster_id
    return policy_copy


@mock_emr
def test_run_job_flow_with_custom_ami():
    client = boto3.client("emr", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        # CustomAmiId available in Amazon EMR 5.7.0 and later
        args = deepcopy(run_job_flow_args)
        args["CustomAmiId"] = "MyEmrCustomId"
        args["ReleaseLabel"] = "emr-5.6.0"
        client.run_job_flow(**args)
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.equal("Custom AMI is not allowed")

    with pytest.raises(ClientError) as ex:
        args = deepcopy(run_job_flow_args)
        args["CustomAmiId"] = "MyEmrCustomId"
        args["AmiVersion"] = "3.8.1"
        client.run_job_flow(**args)
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.equal(
        "Custom AMI is not supported in this version of EMR"
    )

    with pytest.raises(ClientError) as ex:
        # AMI version and release label exception  raises before CustomAmi exception
        args = deepcopy(run_job_flow_args)
        args["CustomAmiId"] = "MyEmrCustomId"
        args["ReleaseLabel"] = "emr-5.6.0"
        args["AmiVersion"] = "3.8.1"
        client.run_job_flow(**args)
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.contain(
        "Only one AMI version and release label may be specified."
    )

    args = deepcopy(run_job_flow_args)
    args["CustomAmiId"] = "MyEmrCustomAmi"
    args["ReleaseLabel"] = "emr-5.31.0"
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)
    resp["Cluster"]["CustomAmiId"].should.equal("MyEmrCustomAmi")


@mock_emr
def test_run_job_flow_with_step_concurrency():
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["StepConcurrencyLevel"] = 2
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)["Cluster"]
    resp["Name"].should.equal(args["Name"])
    resp["Status"]["State"].should.equal("WAITING")
    resp["StepConcurrencyLevel"].should.equal(2)


@mock_emr
def test_modify_cluster():
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["StepConcurrencyLevel"] = 2
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)["Cluster"]
    resp["Name"].should.equal(args["Name"])
    resp["Status"]["State"].should.equal("WAITING")
    resp["StepConcurrencyLevel"].should.equal(2)

    resp = client.modify_cluster(ClusterId=cluster_id, StepConcurrencyLevel=4)
    resp["StepConcurrencyLevel"].should.equal(4)

    resp = client.describe_cluster(ClusterId=cluster_id)["Cluster"]
    resp["StepConcurrencyLevel"].should.equal(4)


@mock_emr
def test_set_termination_protection():
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["Instances"]["TerminationProtected"] = False
    resp = client.run_job_flow(**args)
    cluster_id = resp["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)
    resp["Cluster"]["TerminationProtected"].should.equal(False)

    for expected in (True, False):
        resp = client.set_termination_protection(
            JobFlowIds=[cluster_id], TerminationProtected=expected
        )
        resp = client.describe_cluster(ClusterId=cluster_id)
        resp["Cluster"]["TerminationProtected"].should.equal(expected)


@mock_emr
def test_terminate_protected_job_flow_raises_error():
    client = boto3.client("emr", region_name="us-east-1")
    resp = client.run_job_flow(**run_job_flow_args)
    cluster_id = resp["JobFlowId"]
    client.set_termination_protection(
        JobFlowIds=[cluster_id], TerminationProtected=True
    )
    with pytest.raises(ClientError) as ex:
        client.terminate_job_flows(JobFlowIds=[cluster_id])
    error = ex.value.response["Error"]
    error["Code"].should.equal("ValidationException")
    error["Message"].should.equal(
        "Could not shut down one or more job flows since they are termination protected."
    )


@mock_emr
def test_set_visible_to_all_users():
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["VisibleToAllUsers"] = False
    resp = client.run_job_flow(**args)
    cluster_id = resp["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)
    resp["Cluster"]["VisibleToAllUsers"].should.equal(False)

    for expected in (True, False):
        resp = client.set_visible_to_all_users(
            JobFlowIds=[cluster_id], VisibleToAllUsers=expected
        )
        resp = client.describe_cluster(ClusterId=cluster_id)
        resp["Cluster"]["VisibleToAllUsers"].should.equal(expected)


@mock_emr
def test_terminate_job_flows():
    client = boto3.client("emr", region_name="us-east-1")

    resp = client.run_job_flow(**run_job_flow_args)
    cluster_id = resp["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)
    resp["Cluster"]["Status"]["State"].should.equal("WAITING")

    resp = client.terminate_job_flows(JobFlowIds=[cluster_id])
    resp = client.describe_cluster(ClusterId=cluster_id)
    resp["Cluster"]["Status"]["State"].should.equal("TERMINATED")


# testing multiple end points for each feature


@mock_emr
def test_bootstrap_actions():
    bootstrap_actions = [
        {
            "Name": "bs1",
            "ScriptBootstrapAction": {
                "Args": ["arg1", "arg2"],
                "Path": "s3://path/to/script",
            },
        },
        {
            "Name": "bs2",
            "ScriptBootstrapAction": {"Args": [], "Path": "s3://path/to/anotherscript"},
        },
    ]

    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["BootstrapActions"] = bootstrap_actions
    cluster_id = client.run_job_flow(**args)["JobFlowId"]

    cl = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]
    for x, y in zip(cl["BootstrapActions"], bootstrap_actions):
        x["BootstrapActionConfig"].should.equal(y)

    resp = client.list_bootstrap_actions(ClusterId=cluster_id)
    for x, y in zip(resp["BootstrapActions"], bootstrap_actions):
        x["Name"].should.equal(y["Name"])
        if "Args" in y["ScriptBootstrapAction"]:
            x["Args"].should.equal(y["ScriptBootstrapAction"]["Args"])
        x["ScriptPath"].should.equal(y["ScriptBootstrapAction"]["Path"])


@mock_emr
def test_instances():
    input_groups = dict((g["Name"], g) for g in input_instance_groups)
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["Instances"] = {"InstanceGroups": input_instance_groups}
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    jf = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]
    instances = client.list_instances(ClusterId=cluster_id)["Instances"]
    len(instances).should.equal(sum(g["InstanceCount"] for g in input_instance_groups))
    for x in instances:
        x.should.have.key("InstanceGroupId")
        instance_group = [
            j
            for j in jf["Instances"]["InstanceGroups"]
            if j["InstanceGroupId"] == x["InstanceGroupId"]
        ]
        len(instance_group).should.equal(1)
        y = input_groups[instance_group[0]["Name"]]
        x.should.have.key("Id")
        x.should.have.key("Ec2InstanceId")
        x.should.have.key("PublicDnsName")
        x.should.have.key("PublicIpAddress")
        x.should.have.key("PrivateDnsName")
        x.should.have.key("PrivateIpAddress")
        x.should.have.key("InstanceFleetId")
        x["InstanceType"].should.equal(y["InstanceType"])
        x["Market"].should.equal(y["Market"])
        x["Status"]["Timeline"]["ReadyDateTime"].should.be.a("datetime.datetime")
        x["Status"]["Timeline"]["CreationDateTime"].should.be.a("datetime.datetime")
        x["Status"]["State"].should.equal("RUNNING")

    for x in [["MASTER"], ["CORE"], ["TASK"], ["MASTER", "TASK"]]:
        instances = client.list_instances(ClusterId=cluster_id, InstanceGroupTypes=x)[
            "Instances"
        ]
        len(instances).should.equal(
            sum(
                g["InstanceCount"]
                for g in input_instance_groups
                if g["InstanceRole"] in x
            )
        )


@mock_emr
def test_instance_groups():
    input_groups = dict((g["Name"], g) for g in input_instance_groups)

    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    for key in ["MasterInstanceType", "SlaveInstanceType", "InstanceCount"]:
        del args["Instances"][key]
    args["Instances"]["InstanceGroups"] = input_instance_groups[:2]
    cluster_id = client.run_job_flow(**args)["JobFlowId"]

    jf = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]
    base_instance_count = jf["Instances"]["InstanceCount"]

    instance_groups_to_add = deepcopy(input_instance_groups[2:])
    instance_groups_to_add[0]["AutoScalingPolicy"] = auto_scaling_policy
    instance_groups_to_add[1]["AutoScalingPolicy"] = auto_scaling_policy
    client.add_instance_groups(
        JobFlowId=cluster_id, InstanceGroups=instance_groups_to_add
    )

    jf = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]
    jf["Instances"]["InstanceCount"].should.equal(
        sum(g["InstanceCount"] for g in input_instance_groups)
    )
    for x in jf["Instances"]["InstanceGroups"]:
        y = input_groups[x["Name"]]
        if "BidPrice" in y:
            x["BidPrice"].should.equal(y["BidPrice"])
        x["CreationDateTime"].should.be.a("datetime.datetime")
        # x['EndDateTime'].should.be.a('datetime.datetime')
        x.should.have.key("InstanceGroupId")
        x["InstanceRequestCount"].should.equal(y["InstanceCount"])
        x["InstanceRole"].should.equal(y["InstanceRole"])
        x["InstanceRunningCount"].should.equal(y["InstanceCount"])
        x["InstanceType"].should.equal(y["InstanceType"])
        # x['LastStateChangeReason'].should.equal(y['LastStateChangeReason'])
        x["Market"].should.equal(y["Market"])
        x["Name"].should.equal(y["Name"])
        x["ReadyDateTime"].should.be.a("datetime.datetime")
        x["StartDateTime"].should.be.a("datetime.datetime")
        x["State"].should.equal("RUNNING")
    groups = client.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"]
    for x in groups:
        y = deepcopy(input_groups[x["Name"]])
        if "BidPrice" in y:
            x["BidPrice"].should.equal(y["BidPrice"])
        if "AutoScalingPolicy" in y:
            x["AutoScalingPolicy"]["Status"]["State"].should.equal("ATTACHED")
            returned_policy = dict(x["AutoScalingPolicy"])
            del returned_policy["Status"]
            policy = json.loads(
                json.dumps(y["AutoScalingPolicy"]).replace(
                    "${emr.clusterId}", cluster_id
                )
            )
            returned_policy.should.equal(policy)
        if "EbsConfiguration" in y:
            _do_assertion_ebs_configuration(x, y)
        # Configurations
        # EbsBlockDevices
        # EbsOptimized
        x.should.have.key("Id")
        x["InstanceGroupType"].should.equal(y["InstanceRole"])
        x["InstanceType"].should.equal(y["InstanceType"])
        x["Market"].should.equal(y["Market"])
        x["Name"].should.equal(y["Name"])
        x["RequestedInstanceCount"].should.equal(y["InstanceCount"])
        x["RunningInstanceCount"].should.equal(y["InstanceCount"])
        # ShrinkPolicy
        x["Status"]["State"].should.equal("RUNNING")
        x["Status"]["StateChangeReason"]["Code"].should.be.a(str)
        # x['Status']['StateChangeReason']['Message'].should.be.a(str)
        x["Status"]["Timeline"]["CreationDateTime"].should.be.a("datetime.datetime")
        # x['Status']['Timeline']['EndDateTime'].should.be.a('datetime.datetime')
        x["Status"]["Timeline"]["ReadyDateTime"].should.be.a("datetime.datetime")

    igs = dict((g["Name"], g) for g in groups)
    client.modify_instance_groups(
        InstanceGroups=[
            {"InstanceGroupId": igs["task-1"]["Id"], "InstanceCount": 2},
            {"InstanceGroupId": igs["task-2"]["Id"], "InstanceCount": 3},
        ]
    )
    jf = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]
    jf["Instances"]["InstanceCount"].should.equal(base_instance_count + 5)
    igs = dict((g["Name"], g) for g in jf["Instances"]["InstanceGroups"])
    igs["task-1"]["InstanceRunningCount"].should.equal(2)
    igs["task-2"]["InstanceRunningCount"].should.equal(3)


@mock_emr
def test_steps():
    input_steps = [
        {
            "HadoopJarStep": {
                "Args": [
                    "hadoop-streaming",
                    "-files",
                    "s3://elasticmapreduce/samples/wordcount/wordSplitter.py#wordSplitter.py",
                    "-mapper",
                    "python wordSplitter.py",
                    "-input",
                    "s3://elasticmapreduce/samples/wordcount/input",
                    "-output",
                    "s3://output_bucket/output/wordcount_output",
                    "-reducer",
                    "aggregate",
                ],
                "Jar": "command-runner.jar",
                "Properties": [
                    {"Key": "mapred.tasktracker.map.tasks.maximum", "Value": "2"}
                ],
            },
            "Name": "My wordcount example",
        },
        {
            "HadoopJarStep": {
                "Args": [
                    "hadoop-streaming",
                    "-files",
                    "s3://elasticmapreduce/samples/wordcount/wordSplitter2.py#wordSplitter2.py",
                    "-mapper",
                    "python wordSplitter2.py",
                    "-input",
                    "s3://elasticmapreduce/samples/wordcount/input2",
                    "-output",
                    "s3://output_bucket/output/wordcount_output2",
                    "-reducer",
                    "aggregate",
                ],
                "Jar": "command-runner.jar",
                "Properties": [
                    {"Key": "mapred.reduce.tasks", "Value": "0"},
                    {"Key": "stream.map.output.field.separator", "Value": "."},
                ],
            },
            "Name": "My wordcount example2",
        },
    ]

    # TODO: implementation and test for cancel_steps

    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["Steps"] = [input_steps[0]]
    cluster_id = client.run_job_flow(**args)["JobFlowId"]

    jf = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]
    jf["Steps"].should.have.length_of(1)

    client.add_job_flow_steps(JobFlowId=cluster_id, Steps=[input_steps[1]])

    jf = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]
    jf["Steps"].should.have.length_of(2)
    for idx, (x, y) in enumerate(zip(jf["Steps"], input_steps)):
        x["ExecutionStatusDetail"].should.have.key("CreationDateTime")
        # x['ExecutionStatusDetail'].should.have.key('EndDateTime')
        # x['ExecutionStatusDetail'].should.have.key('LastStateChangeReason')
        # x['ExecutionStatusDetail'].should.have.key('StartDateTime')
        x["ExecutionStatusDetail"]["State"].should.equal(
            "RUNNING" if idx == 0 else "PENDING"
        )
        x["StepConfig"]["ActionOnFailure"].should.equal("TERMINATE_CLUSTER")
        x["StepConfig"]["HadoopJarStep"]["Args"].should.equal(
            y["HadoopJarStep"]["Args"]
        )
        x["StepConfig"]["HadoopJarStep"]["Jar"].should.equal(y["HadoopJarStep"]["Jar"])
        if "MainClass" in y["HadoopJarStep"]:
            x["StepConfig"]["HadoopJarStep"]["MainClass"].should.equal(
                y["HadoopJarStep"]["MainClass"]
            )
        if "Properties" in y["HadoopJarStep"]:
            x["StepConfig"]["HadoopJarStep"]["Properties"].should.equal(
                y["HadoopJarStep"]["Properties"]
            )
        x["StepConfig"]["Name"].should.equal(y["Name"])

    expected = dict((s["Name"], s) for s in input_steps)

    steps = client.list_steps(ClusterId=cluster_id)["Steps"]
    steps.should.have.length_of(2)
    # Steps should be returned in reverse order.
    sorted(
        steps, key=lambda o: o["Status"]["Timeline"]["CreationDateTime"], reverse=True
    ).should.equal(steps)
    for x in steps:
        y = expected[x["Name"]]
        x["ActionOnFailure"].should.equal("TERMINATE_CLUSTER")
        x["Config"]["Args"].should.equal(y["HadoopJarStep"]["Args"])
        x["Config"]["Jar"].should.equal(y["HadoopJarStep"]["Jar"])
        # x['Config']['MainClass'].should.equal(y['HadoopJarStep']['MainClass'])
        # Properties
        x["Id"].should.be.a(str)
        x["Name"].should.equal(y["Name"])
        x["Status"]["State"].should.be.within(["RUNNING", "PENDING"])
        # StateChangeReason
        x["Status"]["Timeline"]["CreationDateTime"].should.be.a("datetime.datetime")
        # x['Status']['Timeline']['EndDateTime'].should.be.a('datetime.datetime')
        # Only the first step will have started - we don't know anything about when it finishes, so the second step never starts
        if x["Name"] == "My wordcount example":
            x["Status"]["Timeline"]["StartDateTime"].should.be.a("datetime.datetime")

        x = client.describe_step(ClusterId=cluster_id, StepId=x["Id"])["Step"]
        x["ActionOnFailure"].should.equal("TERMINATE_CLUSTER")
        x["Config"]["Args"].should.equal(y["HadoopJarStep"]["Args"])
        x["Config"]["Jar"].should.equal(y["HadoopJarStep"]["Jar"])
        # x['Config']['MainClass'].should.equal(y['HadoopJarStep']['MainClass'])
        # Properties
        x["Id"].should.be.a(str)
        x["Name"].should.equal(y["Name"])
        x["Status"]["State"].should.be.within(["RUNNING", "PENDING"])
        # StateChangeReason
        x["Status"]["Timeline"]["CreationDateTime"].should.be.a("datetime.datetime")
        # x['Status']['Timeline']['EndDateTime'].should.be.a('datetime.datetime')
        # x['Status']['Timeline']['StartDateTime'].should.be.a('datetime.datetime')

    step_id = steps[-1]["Id"]  # Last step is first created step.
    steps = client.list_steps(ClusterId=cluster_id, StepIds=[step_id])["Steps"]
    steps.should.have.length_of(1)
    steps[0]["Id"].should.equal(step_id)

    steps = client.list_steps(ClusterId=cluster_id, StepStates=["RUNNING"])["Steps"]
    steps.should.have.length_of(1)
    steps[0]["Id"].should.equal(step_id)


@mock_emr
def test_tags():
    input_tags = [
        {"Key": "newkey1", "Value": "newval1"},
        {"Key": "newkey2", "Value": "newval2"},
    ]

    client = boto3.client("emr", region_name="us-east-1")
    cluster_id = client.run_job_flow(**run_job_flow_args)["JobFlowId"]

    client.add_tags(ResourceId=cluster_id, Tags=input_tags)
    resp = client.describe_cluster(ClusterId=cluster_id)["Cluster"]
    resp["Tags"].should.have.length_of(2)
    dict((t["Key"], t["Value"]) for t in resp["Tags"]).should.equal(
        dict((t["Key"], t["Value"]) for t in input_tags)
    )

    client.remove_tags(ResourceId=cluster_id, TagKeys=[t["Key"] for t in input_tags])
    resp = client.describe_cluster(ClusterId=cluster_id)["Cluster"]
    resp["Tags"].should.equal([])


@mock_emr
def test_security_configurations():

    client = boto3.client("emr", region_name="us-east-1")

    security_configuration_name = "MySecurityConfiguration"

    security_configuration = """
{
  "EncryptionConfiguration": {
    "AtRestEncryptionConfiguration": {
      "S3EncryptionConfiguration": {
        "EncryptionMode": "SSE-S3"
      }
    },
    "EnableInTransitEncryption": false,
    "EnableAtRestEncryption": true
  }
}
    """.strip()

    resp = client.create_security_configuration(
        Name=security_configuration_name, SecurityConfiguration=security_configuration
    )

    resp["Name"].should.equal(security_configuration_name)
    resp["CreationDateTime"].should.be.a("datetime.datetime")

    resp = client.describe_security_configuration(Name=security_configuration_name)
    resp["Name"].should.equal(security_configuration_name)
    resp["SecurityConfiguration"].should.equal(security_configuration)
    resp["CreationDateTime"].should.be.a("datetime.datetime")

    client.delete_security_configuration(Name=security_configuration_name)

    with pytest.raises(ClientError) as ex:
        client.describe_security_configuration(Name=security_configuration_name)
    ex.value.response["Error"]["Code"].should.equal("InvalidRequestException")
    ex.value.response["Error"]["Message"].should.match(
        r"Security configuration with name .* does not exist."
    )

    with pytest.raises(ClientError) as ex:
        client.delete_security_configuration(Name=security_configuration_name)
    ex.value.response["Error"]["Code"].should.equal("InvalidRequestException")
    ex.value.response["Error"]["Message"].should.match(
        r"Security configuration with name .* does not exist."
    )


@mock_emr
def test_run_job_flow_with_invalid_number_of_master_nodes_raises_error():
    client = boto3.client("emr", region_name="us-east-1")
    params = dict(
        Name="test-cluster",
        Instances={
            "InstanceGroups": [
                {
                    "InstanceCount": 2,
                    "InstanceRole": "MASTER",
                    "InstanceType": "c1.medium",
                    "Market": "ON_DEMAND",
                    "Name": "master",
                }
            ]
        },
    )
    with pytest.raises(ClientError) as ex:
        client.run_job_flow(**params)
    error = ex.value.response["Error"]
    error["Code"].should.equal("ValidationException")
    error["Message"].should.equal(
        "Master instance group must have exactly 3 instances for HA clusters."
    )


@mock_emr
def test_run_job_flow_with_multiple_master_nodes():
    client = boto3.client("emr", region_name="us-east-1")
    params = dict(
        Name="test-cluster",
        Instances={
            "InstanceGroups": [
                {
                    "InstanceCount": 3,
                    "InstanceRole": "MASTER",
                    "InstanceType": "c1.medium",
                    "Market": "ON_DEMAND",
                    "Name": "master",
                }
            ],
            "KeepJobFlowAliveWhenNoSteps": False,
            "TerminationProtected": False,
        },
    )
    cluster_id = client.run_job_flow(**params)["JobFlowId"]
    cluster = client.describe_cluster(ClusterId=cluster_id)["Cluster"]
    cluster["AutoTerminate"].should.equal(False)
    cluster["TerminationProtected"].should.equal(True)
    groups = client.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"]
    master_instance_group = next(
        group for group in groups if group["InstanceGroupType"] == "MASTER"
    )
    master_instance_group["RequestedInstanceCount"].should.equal(3)
    master_instance_group["RunningInstanceCount"].should.equal(3)
