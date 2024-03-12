import json
import time
from copy import deepcopy
from datetime import datetime, timezone

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
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


@mock_aws
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
    assert cl["Applications"][0]["Name"] == "Spark"
    assert cl["Applications"][0]["Version"] == "2.4.2"
    assert cl["AutoTerminate"] is True

    config = cl["Configurations"][0]
    assert config["Classification"] == "yarn-site"
    assert config["Properties"] == args["Configurations"][0]["Properties"]

    nested_config = cl["Configurations"][1]
    assert nested_config["Classification"] == "nested-configs"
    assert nested_config["Properties"] == args["Configurations"][1]["Properties"]

    attrs = cl["Ec2InstanceAttributes"]
    assert (
        attrs["AdditionalMasterSecurityGroups"]
        == args["Instances"]["AdditionalMasterSecurityGroups"]
    )
    assert (
        attrs["AdditionalSlaveSecurityGroups"]
        == args["Instances"]["AdditionalSlaveSecurityGroups"]
    )
    assert attrs["Ec2AvailabilityZone"] == "us-east-1a"
    assert attrs["Ec2KeyName"] == args["Instances"]["Ec2KeyName"]
    assert attrs["Ec2SubnetId"] == args["Instances"]["Ec2SubnetId"]
    assert (
        attrs["EmrManagedMasterSecurityGroup"]
        == args["Instances"]["EmrManagedMasterSecurityGroup"]
    )
    assert (
        attrs["EmrManagedSlaveSecurityGroup"]
        == args["Instances"]["EmrManagedSlaveSecurityGroup"]
    )
    assert attrs["IamInstanceProfile"] == args["JobFlowRole"]
    assert (
        attrs["ServiceAccessSecurityGroup"]
        == args["Instances"]["ServiceAccessSecurityGroup"]
    )
    assert cl["Id"] == cluster_id
    assert cl["KerberosAttributes"] == args["KerberosAttributes"]
    assert cl["LogUri"] == args["LogUri"]
    assert isinstance(cl["MasterPublicDnsName"], str)
    assert cl["Name"] == args["Name"]
    assert cl["NormalizedInstanceHours"] == 0
    # assert cl['ReleaseLabel'] == 'emr-5.0.0'
    assert "RequestedAmiVersion" not in cl
    assert cl["RunningAmiVersion"] == "1.0.0"
    assert isinstance(cl["SecurityConfiguration"], str)
    assert cl["SecurityConfiguration"] == args["SecurityConfiguration"]
    assert cl["ServiceRole"] == args["ServiceRole"]
    assert cl["AutoScalingRole"] == args["AutoScalingRole"]

    status = cl["Status"]
    assert status["State"] == "TERMINATED"
    # cluster['Status']['StateChangeReason']
    assert isinstance(status["Timeline"]["CreationDateTime"], datetime)
    # assert status['Timeline']['EndDateTime'] == datetime(2014, 1, 24, 2, 19, 46, tzinfo=timezone.utc)
    assert isinstance(status["Timeline"]["ReadyDateTime"], datetime)

    assert {t["Key"]: t["Value"] for t in cl["Tags"]} == {
        t["Key"]: t["Value"] for t in args["Tags"]
    }

    assert cl["TerminationProtected"] is False
    assert cl["VisibleToAllUsers"] is True
    assert (
        cl["ClusterArn"]
        == f"arn:aws:elasticmapreduce:{region_name}:{ACCOUNT_ID}:cluster/{cluster_id}"
    )


@mock_aws
def test_describe_cluster_not_found():
    conn = boto3.client("emr", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        conn.describe_cluster(ClusterId="DummyId")

    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
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
    assert len(resp["JobFlows"]) == 6

    for cluster_id in expected:
        resp = client.describe_job_flows(JobFlowIds=[cluster_id])
        assert len(resp["JobFlows"]) == 1
        assert resp["JobFlows"][0]["JobFlowId"] == cluster_id

    resp = client.describe_job_flows(JobFlowStates=["WAITING"])
    assert len(resp["JobFlows"]) == 4
    for x in resp["JobFlows"]:
        assert x["ExecutionStatusDetail"]["State"] == "WAITING"

    resp = client.describe_job_flows(CreatedBefore=timestamp)
    assert len(resp["JobFlows"]) == 4

    resp = client.describe_job_flows(CreatedAfter=timestamp)
    assert len(resp["JobFlows"]) == 2


@mock_aws
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

    assert jf["AmiVersion"] == args["AmiVersion"]
    assert "BootstrapActions" not in jf
    esd = jf["ExecutionStatusDetail"]
    assert isinstance(esd["CreationDateTime"], datetime)
    # assert isinstance(esd['EndDateTime'], 'datetime.datetime')
    # assert isinstance(esd['LastStateChangeReason'], str)
    assert isinstance(esd["ReadyDateTime"], datetime)
    assert isinstance(esd["StartDateTime"], datetime)
    assert esd["State"] == "WAITING"
    attrs = jf["Instances"]
    assert attrs["Ec2KeyName"] == args["Instances"]["Ec2KeyName"]
    assert attrs["Ec2SubnetId"] == args["Instances"]["Ec2SubnetId"]
    assert attrs["HadoopVersion"] == args["Instances"]["HadoopVersion"]
    assert attrs["InstanceCount"] == args["Instances"]["InstanceCount"]
    for ig in attrs["InstanceGroups"]:
        # ig['BidPrice']
        assert isinstance(ig["CreationDateTime"], datetime)
        # assert isinstance(ig['EndDateTime'], 'datetime.datetime')
        assert isinstance(ig["InstanceGroupId"], str)
        assert isinstance(ig["InstanceRequestCount"], int)
        assert ig["InstanceRole"] in ["MASTER", "CORE"]
        assert isinstance(ig["InstanceRunningCount"], int)
        assert ig["InstanceType"] in ["c3.medium", "c3.xlarge"]
        # assert isinstance(ig['LastStateChangeReason'], str)
        assert ig["Market"] == "ON_DEMAND"
        assert isinstance(ig["Name"], str)
        assert isinstance(ig["ReadyDateTime"], datetime)
        assert isinstance(ig["StartDateTime"], datetime)
        assert ig["State"] == "RUNNING"
    assert attrs["KeepJobFlowAliveWhenNoSteps"] is True
    # assert isinstance(attrs['MasterInstanceId'], str)
    assert attrs["MasterInstanceType"] == args["Instances"]["MasterInstanceType"]
    assert isinstance(attrs["MasterPublicDnsName"], str)
    assert attrs["NormalizedInstanceHours"] == 0
    assert (
        attrs["Placement"]["AvailabilityZone"]
        == args["Instances"]["Placement"]["AvailabilityZone"]
    )
    assert attrs["SlaveInstanceType"] == args["Instances"]["SlaveInstanceType"]
    assert attrs["TerminationProtected"] is False
    assert jf["JobFlowId"] == cluster_id
    assert jf["JobFlowRole"] == args["JobFlowRole"]
    assert jf["LogUri"] == args["LogUri"]
    assert jf["Name"] == args["Name"]
    assert jf["ServiceRole"] == args["ServiceRole"]
    assert jf["Steps"] == []
    assert jf["SupportedProducts"] == []
    assert jf["VisibleToAllUsers"] is True


@mock_aws
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
        assert len(clusters) <= 50
        for x in clusters:
            y = expected[x["Id"]]
            assert x["Id"] == y["Id"]
            assert x["Name"] == y["Name"]
            assert x["NormalizedInstanceHours"] == y["NormalizedInstanceHours"]
            assert x["Status"]["State"] == y["State"]
            assert isinstance(x["Status"]["Timeline"]["CreationDateTime"], datetime)
            if y["State"] == "TERMINATED":
                assert isinstance(x["Status"]["Timeline"]["EndDateTime"], datetime)
            else:
                assert "EndDateTime" not in x["Status"]["Timeline"]
            assert isinstance(x["Status"]["Timeline"]["ReadyDateTime"], datetime)
        marker = resp.get("Marker")
        if marker is None:
            break
        args = {"Marker": marker}

    resp = client.list_clusters(ClusterStates=["TERMINATED"])
    assert len(resp["Clusters"]) == 30
    for x in resp["Clusters"]:
        assert x["Status"]["State"] == "TERMINATED"

    resp = client.list_clusters(CreatedBefore=timestamp)
    assert len(resp["Clusters"]) == 40

    resp = client.list_clusters(CreatedAfter=timestamp)
    assert len(resp["Clusters"]) == 30


@mock_aws
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
    assert resp["ExecutionStatusDetail"]["State"] == "WAITING"
    assert resp["JobFlowId"] == job_flow_id
    assert resp["Name"] == args["Name"]
    assert (
        resp["Instances"]["MasterInstanceType"]
        == args["Instances"]["MasterInstanceType"]
    )
    assert (
        resp["Instances"]["SlaveInstanceType"] == args["Instances"]["SlaveInstanceType"]
    )
    assert resp["LogUri"] == args["LogUri"]
    assert resp["VisibleToAllUsers"] == args["VisibleToAllUsers"]
    assert resp["Instances"]["NormalizedInstanceHours"] == 0
    assert resp["Steps"] == []


@mock_aws
def test_run_job_flow_with_invalid_params():
    client = boto3.client("emr", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        # cannot set both AmiVersion and ReleaseLabel
        args = deepcopy(run_job_flow_args)
        args["AmiVersion"] = "2.4"
        args["ReleaseLabel"] = "emr-5.0.0"
        client.run_job_flow(**args)
    assert ex.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
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
        assert resp["Cluster"]["Name"] == region


@mock_aws
def test_run_job_flow_with_new_params():
    client = boto3.client("emr", region_name="us-east-1")
    resp = client.run_job_flow(**run_job_flow_args)
    assert "JobFlowId" in resp


@mock_aws
def test_run_job_flow_with_visible_to_all_users():
    client = boto3.client("emr", region_name="us-east-1")
    for expected in (True, False):
        args = deepcopy(run_job_flow_args)
        args["VisibleToAllUsers"] = expected
        resp = client.run_job_flow(**args)
        cluster_id = resp["JobFlowId"]
        resp = client.describe_cluster(ClusterId=cluster_id)
        assert resp["Cluster"]["VisibleToAllUsers"] == expected


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
    assert len(x["EbsBlockDevices"]) == total_volumes
    assert comp_total_size == comp_total_size


@mock_aws
def test_run_job_flow_with_instance_groups():
    input_groups = dict((g["Name"], g) for g in input_instance_groups)
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["Instances"] = {"InstanceGroups": input_instance_groups}
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    groups = client.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"]
    for x in groups:
        y = input_groups[x["Name"]]
        assert "Id" in x
        assert x["RequestedInstanceCount"] == y["InstanceCount"]
        assert x["InstanceGroupType"] == y["InstanceRole"]
        assert x["InstanceType"] == y["InstanceType"]
        assert x["Market"] == y["Market"]
        if "BidPrice" in y:
            assert x["BidPrice"] == y["BidPrice"]

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


@mock_aws
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
            assert x["AutoScalingPolicy"]["Status"]["State"] == "ATTACHED"
            returned_policy = deepcopy(x["AutoScalingPolicy"])
            auto_scaling_policy_with_cluster_id = (
                _patch_cluster_id_placeholder_in_autoscaling_policy(
                    y["AutoScalingPolicy"], cluster_id
                )
            )
            del returned_policy["Status"]
            assert returned_policy == auto_scaling_policy_with_cluster_id


@mock_aws
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
    assert resp["AutoScalingPolicy"] == auto_scaling_policy_with_cluster_id
    assert (
        resp["ClusterArn"]
        == f"arn:aws:elasticmapreduce:{region_name}:{ACCOUNT_ID}:cluster/{cluster_id}"
    )

    core_instance_group = [
        ig
        for ig in client.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"]
        if ig["InstanceGroupType"] == "CORE"
    ][0]

    assert "AutoScalingPolicy" in core_instance_group

    client.remove_auto_scaling_policy(
        ClusterId=cluster_id, InstanceGroupId=core_instance_group["Id"]
    )

    core_instance_group = [
        ig
        for ig in client.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"]
        if ig["InstanceGroupType"] == "CORE"
    ][0]

    assert "AutoScalingPolicy" not in core_instance_group


def _patch_cluster_id_placeholder_in_autoscaling_policy(policy, cluster_id):
    policy_copy = deepcopy(policy)
    for rule in policy_copy["Rules"]:
        for dimension in rule["Trigger"]["CloudWatchAlarmDefinition"]["Dimensions"]:
            dimension["Value"] = cluster_id
    return policy_copy


@mock_aws
def test_run_job_flow_with_custom_ami():
    client = boto3.client("emr", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        # CustomAmiId available in Amazon EMR 5.7.0 and later
        args = deepcopy(run_job_flow_args)
        args["CustomAmiId"] = "MyEmrCustomId"
        args["ReleaseLabel"] = "emr-5.6.0"
        client.run_job_flow(**args)
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["Error"]["Message"] == "Custom AMI is not allowed"

    with pytest.raises(ClientError) as ex:
        args = deepcopy(run_job_flow_args)
        args["CustomAmiId"] = "MyEmrCustomId"
        args["AmiVersion"] = "3.8.1"
        client.run_job_flow(**args)
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Custom AMI is not supported in this version of EMR"

    with pytest.raises(ClientError) as ex:
        # AMI version and release label exception  raises before CustomAmi exception
        args = deepcopy(run_job_flow_args)
        args["CustomAmiId"] = "MyEmrCustomId"
        args["ReleaseLabel"] = "emr-5.6.0"
        args["AmiVersion"] = "3.8.1"
        client.run_job_flow(**args)
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "Only one AMI version and release label may be specified." in err["Message"]

    args = deepcopy(run_job_flow_args)
    args["CustomAmiId"] = "MyEmrCustomAmi"
    args["ReleaseLabel"] = "emr-5.31.0"
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)
    assert resp["Cluster"]["CustomAmiId"] == "MyEmrCustomAmi"


@mock_aws
def test_run_job_flow_with_step_concurrency():
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["StepConcurrencyLevel"] = 2
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)["Cluster"]
    assert resp["Name"] == args["Name"]
    assert resp["Status"]["State"] == "WAITING"
    assert resp["StepConcurrencyLevel"] == 2


@mock_aws
def test_modify_cluster():
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["StepConcurrencyLevel"] = 2
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)["Cluster"]
    assert resp["Name"] == args["Name"]
    assert resp["Status"]["State"] == "WAITING"
    assert resp["StepConcurrencyLevel"] == 2

    resp = client.modify_cluster(ClusterId=cluster_id, StepConcurrencyLevel=4)
    assert resp["StepConcurrencyLevel"] == 4

    resp = client.describe_cluster(ClusterId=cluster_id)["Cluster"]
    assert resp["StepConcurrencyLevel"] == 4


@mock_aws
def test_set_termination_protection():
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["Instances"]["TerminationProtected"] = False
    resp = client.run_job_flow(**args)
    cluster_id = resp["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)
    assert resp["Cluster"]["TerminationProtected"] is False

    for expected in (True, False):
        resp = client.set_termination_protection(
            JobFlowIds=[cluster_id], TerminationProtected=expected
        )
        resp = client.describe_cluster(ClusterId=cluster_id)
        assert resp["Cluster"]["TerminationProtected"] == expected


@mock_aws
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
    assert error["Code"] == "ValidationException"
    assert (
        error["Message"]
        == "Could not shut down one or more job flows since they are termination protected."
    )


@mock_aws
def test_set_visible_to_all_users():
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["VisibleToAllUsers"] = False
    resp = client.run_job_flow(**args)
    cluster_id = resp["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)
    assert resp["Cluster"]["VisibleToAllUsers"] is False

    for expected in (True, False):
        resp = client.set_visible_to_all_users(
            JobFlowIds=[cluster_id], VisibleToAllUsers=expected
        )
        resp = client.describe_cluster(ClusterId=cluster_id)
        assert resp["Cluster"]["VisibleToAllUsers"] == expected


@mock_aws
def test_terminate_job_flows():
    client = boto3.client("emr", region_name="us-east-1")

    resp = client.run_job_flow(**run_job_flow_args)
    cluster_id = resp["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)
    assert resp["Cluster"]["Status"]["State"] == "WAITING"

    resp = client.terminate_job_flows(JobFlowIds=[cluster_id])
    resp = client.describe_cluster(ClusterId=cluster_id)
    assert resp["Cluster"]["Status"]["State"] == "TERMINATED"


# testing multiple end points for each feature


@mock_aws
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
        assert x["BootstrapActionConfig"] == y

    resp = client.list_bootstrap_actions(ClusterId=cluster_id)
    for x, y in zip(resp["BootstrapActions"], bootstrap_actions):
        assert x["Name"] == y["Name"]
        if "Args" in y["ScriptBootstrapAction"]:
            assert x["Args"] == y["ScriptBootstrapAction"]["Args"]
        assert x["ScriptPath"] == y["ScriptBootstrapAction"]["Path"]


@mock_aws
def test_instances():
    input_groups = dict((g["Name"], g) for g in input_instance_groups)
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    args["Instances"] = {"InstanceGroups": input_instance_groups}
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    jf = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]
    instances = client.list_instances(ClusterId=cluster_id)["Instances"]
    assert len(instances) == sum(g["InstanceCount"] for g in input_instance_groups)
    for x in instances:
        assert "InstanceGroupId" in x
        instance_group = [
            j
            for j in jf["Instances"]["InstanceGroups"]
            if j["InstanceGroupId"] == x["InstanceGroupId"]
        ]
        assert len(instance_group) == 1
        y = input_groups[instance_group[0]["Name"]]
        assert "Id" in x
        assert "Ec2InstanceId" in x
        assert "PublicDnsName" in x
        assert "PublicIpAddress" in x
        assert "PrivateDnsName" in x
        assert "PrivateIpAddress" in x
        assert "InstanceFleetId" in x
        assert x["InstanceType"] == y["InstanceType"]
        assert x["Market"] == y["Market"]
        assert isinstance(x["Status"]["Timeline"]["ReadyDateTime"], datetime)
        assert isinstance(x["Status"]["Timeline"]["CreationDateTime"], datetime)
        assert x["Status"]["State"] == "RUNNING"

    for x in [["MASTER"], ["CORE"], ["TASK"], ["MASTER", "TASK"]]:
        instances = client.list_instances(ClusterId=cluster_id, InstanceGroupTypes=x)[
            "Instances"
        ]
        assert len(instances) == sum(
            g["InstanceCount"] for g in input_instance_groups if g["InstanceRole"] in x
        )


@mock_aws
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
    assert jf["Instances"]["InstanceCount"] == sum(
        g["InstanceCount"] for g in input_instance_groups
    )
    for x in jf["Instances"]["InstanceGroups"]:
        y = input_groups[x["Name"]]
        if "BidPrice" in y:
            assert x["BidPrice"] == y["BidPrice"]
        assert isinstance(x["CreationDateTime"], datetime)
        # assert isinstance(x['EndDateTime'], 'datetime.datetime')
        assert "InstanceGroupId" in x
        assert x["InstanceRequestCount"] == y["InstanceCount"]
        assert x["InstanceRole"] == y["InstanceRole"]
        assert x["InstanceRunningCount"] == y["InstanceCount"]
        assert x["InstanceType"] == y["InstanceType"]
        # assert x['LastStateChangeReason'] == y['LastStateChangeReason']
        assert x["Market"] == y["Market"]
        assert x["Name"] == y["Name"]
        assert isinstance(x["ReadyDateTime"], datetime)
        assert isinstance(x["StartDateTime"], datetime)
        assert x["State"] == "RUNNING"
    groups = client.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"]
    for x in groups:
        y = deepcopy(input_groups[x["Name"]])
        if "BidPrice" in y:
            assert x["BidPrice"] == y["BidPrice"]
        if "AutoScalingPolicy" in y:
            assert x["AutoScalingPolicy"]["Status"]["State"] == "ATTACHED"
            returned_policy = dict(x["AutoScalingPolicy"])
            del returned_policy["Status"]
            policy = json.loads(
                json.dumps(y["AutoScalingPolicy"]).replace(
                    "${emr.clusterId}", cluster_id
                )
            )
            assert returned_policy == policy
        if "EbsConfiguration" in y:
            _do_assertion_ebs_configuration(x, y)
        # Configurations
        # EbsBlockDevices
        # EbsOptimized
        assert "Id" in x
        assert x["InstanceGroupType"] == y["InstanceRole"]
        assert x["InstanceType"] == y["InstanceType"]
        assert x["Market"] == y["Market"]
        assert x["Name"] == y["Name"]
        assert x["RequestedInstanceCount"] == y["InstanceCount"]
        assert x["RunningInstanceCount"] == y["InstanceCount"]
        # ShrinkPolicy
        assert x["Status"]["State"] == "RUNNING"
        assert isinstance(x["Status"]["StateChangeReason"]["Code"], str)
        # assert isinstance(x['Status']['StateChangeReason']['Message'], str)
        assert isinstance(x["Status"]["Timeline"]["CreationDateTime"], datetime)
        # assert isinstance(x['Status']['Timeline']['EndDateTime'], 'datetime.datetime')
        assert isinstance(x["Status"]["Timeline"]["ReadyDateTime"], datetime)

    igs = dict((g["Name"], g) for g in groups)
    client.modify_instance_groups(
        InstanceGroups=[
            {"InstanceGroupId": igs["task-1"]["Id"], "InstanceCount": 2},
            {"InstanceGroupId": igs["task-2"]["Id"], "InstanceCount": 3},
        ]
    )
    jf = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]
    assert jf["Instances"]["InstanceCount"] == base_instance_count + 5
    igs = dict((g["Name"], g) for g in jf["Instances"]["InstanceGroups"])
    assert igs["task-1"]["InstanceRunningCount"] == 2
    assert igs["task-2"]["InstanceRunningCount"] == 3


@mock_aws
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
    assert len(jf["Steps"]) == 1

    client.add_job_flow_steps(JobFlowId=cluster_id, Steps=[input_steps[1]])

    jf = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]
    assert len(jf["Steps"]) == 2
    for idx, (x, y) in enumerate(zip(jf["Steps"], input_steps)):
        assert "CreationDateTime" in x["ExecutionStatusDetail"]
        # assert 'EndDateTime' in x['ExecutionStatusDetail']
        # assert 'LastStateChangeReason' in x['ExecutionStatusDetail']
        # assert 'StartDateTime' in x['ExecutionStatusDetail']
        assert (
            x["ExecutionStatusDetail"]["State"] == "RUNNING" if idx == 0 else "PENDING"
        )
        assert x["StepConfig"]["ActionOnFailure"] == "TERMINATE_CLUSTER"
        assert x["StepConfig"]["HadoopJarStep"]["Args"] == y["HadoopJarStep"]["Args"]
        assert x["StepConfig"]["HadoopJarStep"]["Jar"] == y["HadoopJarStep"]["Jar"]
        if "MainClass" in y["HadoopJarStep"]:
            assert (
                x["StepConfig"]["HadoopJarStep"]["MainClass"]
                == y["HadoopJarStep"]["MainClass"]
            )
        if "Properties" in y["HadoopJarStep"]:
            assert (
                x["StepConfig"]["HadoopJarStep"]["Properties"]
                == y["HadoopJarStep"]["Properties"]
            )
        assert x["StepConfig"]["Name"] == y["Name"]

    expected = dict((s["Name"], s) for s in input_steps)

    steps = client.list_steps(ClusterId=cluster_id)["Steps"]
    assert len(steps) == 2
    # Steps should be returned in reverse order.
    assert (
        sorted(
            steps,
            key=lambda o: o["Status"]["Timeline"]["CreationDateTime"],
            reverse=True,
        )
        == steps
    )
    for x in steps:
        y = expected[x["Name"]]
        assert x["ActionOnFailure"] == "TERMINATE_CLUSTER"
        assert x["Config"]["Args"] == y["HadoopJarStep"]["Args"]
        assert x["Config"]["Jar"] == y["HadoopJarStep"]["Jar"]
        # assert x['Config']['MainClass'] == y['HadoopJarStep']['MainClass']
        # Properties
        assert isinstance(x["Id"], str)
        assert x["Name"] == y["Name"]
        assert x["Status"]["State"] in ["RUNNING", "PENDING"]
        # StateChangeReason
        assert isinstance(x["Status"]["Timeline"]["CreationDateTime"], datetime)
        # assert isinstance(x['Status']['Timeline']['EndDateTime'], 'datetime.datetime')
        # Only the first step will have started - we don't know anything about when it finishes, so the second step never starts
        if x["Name"] == "My wordcount example":
            assert isinstance(x["Status"]["Timeline"]["StartDateTime"], datetime)

        x = client.describe_step(ClusterId=cluster_id, StepId=x["Id"])["Step"]
        assert x["ActionOnFailure"] == "TERMINATE_CLUSTER"
        assert x["Config"]["Args"] == y["HadoopJarStep"]["Args"]
        assert x["Config"]["Jar"] == y["HadoopJarStep"]["Jar"]
        # assert x['Config']['MainClass'] == y['HadoopJarStep']['MainClass']
        # Properties
        assert isinstance(x["Id"], str)
        assert x["Name"] == y["Name"]
        assert x["Status"]["State"] in ["RUNNING", "PENDING"]
        # StateChangeReason
        assert isinstance(x["Status"]["Timeline"]["CreationDateTime"], datetime)
        # assert isinstance(x['Status']['Timeline']['EndDateTime'], 'datetime.datetime')
        # assert isinstance(x['Status']['Timeline']['StartDateTime'], 'datetime.datetime')

    step_id = steps[-1]["Id"]  # Last step is first created step.
    steps = client.list_steps(ClusterId=cluster_id, StepIds=[step_id])["Steps"]
    assert len(steps) == 1
    assert steps[0]["Id"] == step_id

    steps = client.list_steps(ClusterId=cluster_id, StepStates=["RUNNING"])["Steps"]
    assert len(steps) == 1
    assert steps[0]["Id"] == step_id


@mock_aws
def test_tags():
    input_tags = [
        {"Key": "newkey1", "Value": "newval1"},
        {"Key": "newkey2", "Value": "newval2"},
    ]

    client = boto3.client("emr", region_name="us-east-1")
    cluster_id = client.run_job_flow(**run_job_flow_args)["JobFlowId"]

    client.add_tags(ResourceId=cluster_id, Tags=input_tags)
    resp = client.describe_cluster(ClusterId=cluster_id)["Cluster"]
    assert len(resp["Tags"]) == 2
    assert {t["Key"]: t["Value"] for t in resp["Tags"]} == {
        t["Key"]: t["Value"] for t in input_tags
    }

    client.remove_tags(ResourceId=cluster_id, TagKeys=[t["Key"] for t in input_tags])
    resp = client.describe_cluster(ClusterId=cluster_id)["Cluster"]
    assert resp["Tags"] == []


@mock_aws
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

    assert resp["Name"] == security_configuration_name
    assert isinstance(resp["CreationDateTime"], datetime)

    resp = client.describe_security_configuration(Name=security_configuration_name)
    assert resp["Name"] == security_configuration_name
    assert resp["SecurityConfiguration"] == security_configuration
    assert isinstance(resp["CreationDateTime"], datetime)

    client.delete_security_configuration(Name=security_configuration_name)

    with pytest.raises(ClientError) as ex:
        client.describe_security_configuration(Name=security_configuration_name)
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert (
        err["Message"]
        == "Security configuration with name 'MySecurityConfiguration' does not exist."
    )

    with pytest.raises(ClientError) as ex:
        client.delete_security_configuration(Name=security_configuration_name)
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert (
        err["Message"]
        == "Security configuration with name 'MySecurityConfiguration' does not exist."
    )


@mock_aws
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
    assert error["Code"] == "ValidationException"
    assert (
        error["Message"]
        == "Master instance group must have exactly 3 instances for HA clusters."
    )


@mock_aws
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
    assert cluster["AutoTerminate"] is False
    assert cluster["TerminationProtected"] is True
    groups = client.list_instance_groups(ClusterId=cluster_id)["InstanceGroups"]
    master_instance_group = next(
        group for group in groups if group["InstanceGroupType"] == "MASTER"
    )
    assert master_instance_group["RequestedInstanceCount"] == 3
    assert master_instance_group["RunningInstanceCount"] == 3
