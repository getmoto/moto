# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import time
from copy import deepcopy
from datetime import datetime

import boto3
import pytz
import six
import sure  # noqa
from botocore.exceptions import ClientError
from nose.tools import assert_raises

from moto import mock_emr


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
        "InstanceType": "c1.large",
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
def test_describe_cluster():
    client = boto3.client("emr", region_name="us-east-1")

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
    args["Tags"] = [{"Key": "tag1", "Value": "val1"}, {"Key": "tag2", "Value": "val2"}]

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
    cl["LogUri"].should.equal(args["LogUri"])
    cl["MasterPublicDnsName"].should.be.a(six.string_types)
    cl["Name"].should.equal(args["Name"])
    cl["NormalizedInstanceHours"].should.equal(0)
    # cl['ReleaseLabel'].should.equal('emr-5.0.0')
    cl.shouldnt.have.key("RequestedAmiVersion")
    cl["RunningAmiVersion"].should.equal("1.0.0")
    # cl['SecurityConfiguration'].should.be.a(six.string_types)
    cl["ServiceRole"].should.equal(args["ServiceRole"])

    status = cl["Status"]
    status["State"].should.equal("TERMINATED")
    # cluster['Status']['StateChangeReason']
    status["Timeline"]["CreationDateTime"].should.be.a("datetime.datetime")
    # status['Timeline']['EndDateTime'].should.equal(datetime(2014, 1, 24, 2, 19, 46, tzinfo=pytz.utc))
    status["Timeline"]["ReadyDateTime"].should.be.a("datetime.datetime")

    dict((t["Key"], t["Value"]) for t in cl["Tags"]).should.equal(
        dict((t["Key"], t["Value"]) for t in args["Tags"])
    )

    cl["TerminationProtected"].should.equal(False)
    cl["VisibleToAllUsers"].should.equal(True)


@mock_emr
def test_describe_cluster_not_found():
    conn = boto3.client("emr", region_name="us-east-1")
    raised = False
    try:
        cluster = conn.describe_cluster(ClusterId="DummyId")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            raised = True
    raised.should.equal(True)


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
    timestamp = datetime.now(pytz.utc)
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

    for cluster_id, y in expected.items():
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
    # esd['LastStateChangeReason'].should.be.a(six.string_types)
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
        ig["InstanceGroupId"].should.be.a(six.string_types)
        ig["InstanceRequestCount"].should.be.a(int)
        ig["InstanceRole"].should.be.within(["MASTER", "CORE"])
        ig["InstanceRunningCount"].should.be.a(int)
        ig["InstanceType"].should.be.within(["c3.medium", "c3.xlarge"])
        # ig['LastStateChangeReason'].should.be.a(six.string_types)
        ig["Market"].should.equal("ON_DEMAND")
        ig["Name"].should.be.a(six.string_types)
        ig["ReadyDateTime"].should.be.a("datetime.datetime")
        ig["StartDateTime"].should.be.a("datetime.datetime")
        ig["State"].should.equal("RUNNING")
    attrs["KeepJobFlowAliveWhenNoSteps"].should.equal(True)
    # attrs['MasterInstanceId'].should.be.a(six.string_types)
    attrs["MasterInstanceType"].should.equal(args["Instances"]["MasterInstanceType"])
    attrs["MasterPublicDnsName"].should.be.a(six.string_types)
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
    timestamp = datetime.now(pytz.utc)
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
    client = boto3.client("emr", region_name="us-east-1")
    args = deepcopy(run_job_flow_args)
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    resp = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]
    resp["ExecutionStatusDetail"]["State"].should.equal("WAITING")
    resp["JobFlowId"].should.equal(cluster_id)
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
    with assert_raises(ClientError) as ex:
        # cannot set both AmiVersion and ReleaseLabel
        args = deepcopy(run_job_flow_args)
        args["AmiVersion"] = "2.4"
        args["ReleaseLabel"] = "emr-5.0.0"
        client.run_job_flow(**args)
    ex.exception.response["Error"]["Code"].should.equal("ValidationException")


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


@mock_emr
def test_run_job_flow_with_custom_ami():
    client = boto3.client("emr", region_name="us-east-1")

    with assert_raises(ClientError) as ex:
        # CustomAmiId available in Amazon EMR 5.7.0 and later
        args = deepcopy(run_job_flow_args)
        args["CustomAmiId"] = "MyEmrCustomId"
        args["ReleaseLabel"] = "emr-5.6.0"
        client.run_job_flow(**args)
    ex.exception.response["Error"]["Code"].should.equal("ValidationException")
    ex.exception.response["Error"]["Message"].should.equal("Custom AMI is not allowed")

    with assert_raises(ClientError) as ex:
        args = deepcopy(run_job_flow_args)
        args["CustomAmiId"] = "MyEmrCustomId"
        args["AmiVersion"] = "3.8.1"
        client.run_job_flow(**args)
    ex.exception.response["Error"]["Code"].should.equal("ValidationException")
    ex.exception.response["Error"]["Message"].should.equal(
        "Custom AMI is not supported in this version of EMR"
    )

    with assert_raises(ClientError) as ex:
        # AMI version and release label exception  raises before CustomAmi exception
        args = deepcopy(run_job_flow_args)
        args["CustomAmiId"] = "MyEmrCustomId"
        args["ReleaseLabel"] = "emr-5.6.0"
        args["AmiVersion"] = "3.8.1"
        client.run_job_flow(**args)
    ex.exception.response["Error"]["Code"].should.equal("ValidationException")
    ex.exception.response["Error"]["Message"].should.contain(
        "Only one AMI version and release label may be specified."
    )

    args = deepcopy(run_job_flow_args)
    args["CustomAmiId"] = "MyEmrCustomAmi"
    args["ReleaseLabel"] = "emr-5.7.0"
    cluster_id = client.run_job_flow(**args)["JobFlowId"]
    resp = client.describe_cluster(ClusterId=cluster_id)
    resp["Cluster"]["CustomAmiId"].should.equal("MyEmrCustomAmi")


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

    client.add_instance_groups(
        JobFlowId=cluster_id, InstanceGroups=input_instance_groups[2:]
    )

    jf = client.describe_job_flows(JobFlowIds=[cluster_id])["JobFlows"][0]
    jf["Instances"]["InstanceCount"].should.equal(
        sum(g["InstanceCount"] for g in input_instance_groups)
    )
    for x in jf["Instances"]["InstanceGroups"]:
        y = input_groups[x["Name"]]
        if hasattr(y, "BidPrice"):
            x["BidPrice"].should.equal("BidPrice")
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
        y = input_groups[x["Name"]]
        if hasattr(y, "BidPrice"):
            x["BidPrice"].should.equal("BidPrice")
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
        x["Status"]["StateChangeReason"]["Code"].should.be.a(six.string_types)
        # x['Status']['StateChangeReason']['Message'].should.be.a(six.string_types)
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
            "STARTING" if idx == 0 else "PENDING"
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
    for x in steps:
        y = expected[x["Name"]]
        x["ActionOnFailure"].should.equal("TERMINATE_CLUSTER")
        x["Config"]["Args"].should.equal(y["HadoopJarStep"]["Args"])
        x["Config"]["Jar"].should.equal(y["HadoopJarStep"]["Jar"])
        # x['Config']['MainClass'].should.equal(y['HadoopJarStep']['MainClass'])
        # Properties
        x["Id"].should.be.a(six.string_types)
        x["Name"].should.equal(y["Name"])
        x["Status"]["State"].should.be.within(["STARTING", "PENDING"])
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
        x["Id"].should.be.a(six.string_types)
        x["Name"].should.equal(y["Name"])
        x["Status"]["State"].should.be.within(["STARTING", "PENDING"])
        # StateChangeReason
        x["Status"]["Timeline"]["CreationDateTime"].should.be.a("datetime.datetime")
        # x['Status']['Timeline']['EndDateTime'].should.be.a('datetime.datetime')
        # x['Status']['Timeline']['StartDateTime'].should.be.a('datetime.datetime')

    step_id = steps[0]["Id"]
    steps = client.list_steps(ClusterId=cluster_id, StepIds=[step_id])["Steps"]
    steps.should.have.length_of(1)
    steps[0]["Id"].should.equal(step_id)

    steps = client.list_steps(ClusterId=cluster_id, StepStates=["STARTING"])["Steps"]
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
