import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_autoscaling, mock_ec2
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import EXAMPLE_AMI_ID
from uuid import uuid4
from .utils import setup_networking, setup_instance_with_networking


@mock_autoscaling
@mock_ec2
def test_propogate_tags():
    mocked_networking = setup_networking()
    conn = boto3.client("autoscaling", region_name="us-east-1")
    conn.create_launch_configuration(
        LaunchConfigurationName="TestLC",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )

    conn.create_auto_scaling_group(
        AutoScalingGroupName="TestGroup1",
        MinSize=1,
        MaxSize=2,
        LaunchConfigurationName="TestLC",
        Tags=[
            {
                "ResourceId": "TestGroup1",
                "ResourceType": "auto-scaling-group",
                "PropagateAtLaunch": True,
                "Key": "TestTagKey1",
                "Value": "TestTagValue1",
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    ec2 = boto3.client("ec2", region_name="us-east-1")
    instances = ec2.describe_instances()

    tags = instances["Reservations"][0]["Instances"][0]["Tags"]
    assert {"Value": "TestTagValue1", "Key": "TestTagKey1"} in tags
    assert {"Value": "TestGroup1", "Key": "aws:autoscaling:groupName"} in tags


@mock_autoscaling
def test_create_autoscaling_group_from_instance():
    autoscaling_group_name = "test_asg"
    image_id = EXAMPLE_AMI_ID
    instance_type = "t2.micro"

    mocked_instance_with_networking = setup_instance_with_networking(
        image_id, instance_type
    )
    client = boto3.client("autoscaling", region_name="us-east-1")
    response = client.create_auto_scaling_group(
        AutoScalingGroupName=autoscaling_group_name,
        InstanceId=mocked_instance_with_networking["instances"][0].id,
        MinSize=1,
        MaxSize=3,
        DesiredCapacity=2,
        VPCZoneIdentifier=mocked_instance_with_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=False,
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    describe_launch_configurations_response = client.describe_launch_configurations()
    assert len(describe_launch_configurations_response["LaunchConfigurations"]) == 1
    config = describe_launch_configurations_response["LaunchConfigurations"][0]
    assert config["LaunchConfigurationName"] == "test_asg"
    assert config["ImageId"] == image_id
    assert config["InstanceType"] == instance_type


@mock_autoscaling
@mock_ec2
def test_create_autoscaling_group_from_instance_with_security_groups():
    autoscaling_group_name = "test_asg"
    image_id = EXAMPLE_AMI_ID
    instance_type = "t2.micro"

    mocked_instance_with_networking = setup_instance_with_networking(
        image_id, instance_type
    )
    instance = mocked_instance_with_networking["instances"][0]

    # create sg
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    sg_id = ec2.create_security_group(GroupName=str(uuid4()), Description="d").id
    instance.modify_attribute(Groups=[sg_id])

    client = boto3.client("autoscaling", region_name="us-east-1")
    response = client.create_auto_scaling_group(
        AutoScalingGroupName=autoscaling_group_name,
        InstanceId=instance.id,
        MinSize=1,
        MaxSize=3,
        DesiredCapacity=2,
        VPCZoneIdentifier=mocked_instance_with_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=False,
    )
    # Just verifying this works - used to throw an error when supplying a instance that belonged to an SG
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_autoscaling
def test_create_autoscaling_group_from_invalid_instance_id():
    invalid_instance_id = "invalid_instance"

    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.create_auto_scaling_group(
            AutoScalingGroupName="test_asg",
            InstanceId=invalid_instance_id,
            MinSize=9,
            MaxSize=15,
            DesiredCapacity=12,
            VPCZoneIdentifier=mocked_networking["subnet1"],
            NewInstancesProtectedFromScaleIn=False,
        )
    err = ex.value.response["Error"]
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err["Code"] == "ValidationError"
    assert err["Message"] == f"Instance [{invalid_instance_id}] is invalid."


@mock_autoscaling
@mock_ec2
def test_create_autoscaling_group_from_template():
    mocked_networking = setup_networking()

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "t2.micro"},
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    response = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchTemplate={
            "LaunchTemplateId": template["LaunchTemplateId"],
            "Version": str(template["LatestVersionNumber"]),
        },
        MinSize=1,
        MaxSize=3,
        DesiredCapacity=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=False,
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_ec2
@mock_autoscaling
def test_create_auto_scaling_from_template_version__latest():
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    launch_template_name = "tester"
    ec2_client.create_launch_template(
        LaunchTemplateName=launch_template_name,
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "t2.medium"},
    )
    asg_client = boto3.client("autoscaling", region_name="us-west-1")
    asg_client.create_auto_scaling_group(
        AutoScalingGroupName="name",
        DesiredCapacity=1,
        MinSize=1,
        MaxSize=1,
        LaunchTemplate={
            "LaunchTemplateName": launch_template_name,
            "Version": "$Latest",
        },
        AvailabilityZones=["us-west-1a"],
    )

    response = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=["name"])[
        "AutoScalingGroups"
    ][0]
    assert "LaunchTemplate" in response
    assert response["LaunchTemplate"]["LaunchTemplateName"] == launch_template_name
    assert response["LaunchTemplate"]["Version"] == "$Latest"


@mock_ec2
@mock_autoscaling
def test_create_auto_scaling_from_template_version__default():
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    launch_template_name = "tester"
    ec2_client.create_launch_template(
        LaunchTemplateName=launch_template_name,
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "t2.medium"},
    )
    ec2_client.create_launch_template_version(
        LaunchTemplateName=launch_template_name,
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "t3.medium"},
        VersionDescription="v2",
    )
    asg_client = boto3.client("autoscaling", region_name="us-west-1")
    asg_client.create_auto_scaling_group(
        AutoScalingGroupName="name",
        DesiredCapacity=1,
        MinSize=1,
        MaxSize=1,
        LaunchTemplate={
            "LaunchTemplateName": launch_template_name,
            "Version": "$Default",
        },
        AvailabilityZones=["us-west-1a"],
    )

    response = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=["name"])[
        "AutoScalingGroups"
    ][0]
    assert "LaunchTemplate" in response
    assert response["LaunchTemplate"]["LaunchTemplateName"] == launch_template_name
    assert response["LaunchTemplate"]["Version"] == "$Default"


@mock_ec2
@mock_autoscaling
def test_create_auto_scaling_from_template_version__no_version():
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    launch_template_name = "tester"
    ec2_client.create_launch_template(
        LaunchTemplateName=launch_template_name,
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "t2.medium"},
    )
    asg_client = boto3.client("autoscaling", region_name="us-west-1")
    asg_client.create_auto_scaling_group(
        AutoScalingGroupName="name",
        DesiredCapacity=1,
        MinSize=1,
        MaxSize=1,
        LaunchTemplate={"LaunchTemplateName": launch_template_name},
        AvailabilityZones=["us-west-1a"],
    )

    response = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=["name"])[
        "AutoScalingGroups"
    ][0]
    assert "LaunchTemplate" in response
    # We never specified the version - and AWS will not return anything if we don't
    assert "Version" not in response["LaunchTemplate"]


@mock_autoscaling
@mock_ec2
def test_create_autoscaling_group_no_template_ref():
    mocked_networking = setup_networking()

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "t2.micro"},
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_auto_scaling_group(
            AutoScalingGroupName="test_asg",
            LaunchTemplate={"Version": str(template["LatestVersionNumber"])},
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5,
            VPCZoneIdentifier=mocked_networking["subnet1"],
            NewInstancesProtectedFromScaleIn=False,
        )
    err = ex.value.response["Error"]
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "Valid requests must contain either launchTemplateId or LaunchTemplateName"
    )


@mock_autoscaling
@mock_ec2
def test_create_autoscaling_group_multiple_template_ref():
    mocked_networking = setup_networking()

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "t2.micro"},
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_auto_scaling_group(
            AutoScalingGroupName="test_asg",
            LaunchTemplate={
                "LaunchTemplateId": template["LaunchTemplateId"],
                "LaunchTemplateName": template["LaunchTemplateName"],
                "Version": str(template["LatestVersionNumber"]),
            },
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5,
            VPCZoneIdentifier=mocked_networking["subnet1"],
            NewInstancesProtectedFromScaleIn=False,
        )
    err = ex.value.response["Error"]
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "Valid requests must contain either launchTemplateId or LaunchTemplateName"
    )


@mock_autoscaling
def test_create_autoscaling_group_no_launch_configuration():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.create_auto_scaling_group(
            AutoScalingGroupName="test_asg",
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5,
            VPCZoneIdentifier=mocked_networking["subnet1"],
            NewInstancesProtectedFromScaleIn=False,
        )
    err = ex.value.response["Error"]
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "Valid requests must contain either LaunchTemplate, LaunchConfigurationName, InstanceId or MixedInstancesPolicy parameter."
    )


@mock_autoscaling
@mock_ec2
def test_create_autoscaling_group_multiple_launch_configurations():
    mocked_networking = setup_networking()

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "t2.micro"},
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )

    with pytest.raises(ClientError) as ex:
        client.create_auto_scaling_group(
            AutoScalingGroupName="test_asg",
            LaunchConfigurationName="test_launch_configuration",
            LaunchTemplate={
                "LaunchTemplateId": template["LaunchTemplateId"],
                "Version": str(template["LatestVersionNumber"]),
            },
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5,
            VPCZoneIdentifier=mocked_networking["subnet1"],
            NewInstancesProtectedFromScaleIn=False,
        )
    err = ex.value.response["Error"]
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "Valid requests must contain either LaunchTemplate, LaunchConfigurationName, InstanceId or MixedInstancesPolicy parameter."
    )


@mock_autoscaling
@mock_ec2
def test_describe_autoscaling_groups_launch_template():
    mocked_networking = setup_networking()
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "t2.micro"},
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchTemplate={"LaunchTemplateName": "test_launch_template", "Version": "1"},
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )
    expected_launch_template = {
        "LaunchTemplateId": template["LaunchTemplateId"],
        "LaunchTemplateName": "test_launch_template",
        "Version": "1",
    }

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    group = response["AutoScalingGroups"][0]
    assert group["AutoScalingGroupName"] == "test_asg"
    assert group["LaunchTemplate"] == expected_launch_template
    assert "LaunchConfigurationName" not in group
    assert group["AvailabilityZones"] == ["us-east-1a"]
    assert group["VPCZoneIdentifier"] == mocked_networking["subnet1"]
    assert group["NewInstancesProtectedFromScaleIn"] is True
    for instance in group["Instances"]:
        assert instance["LaunchTemplate"] == expected_launch_template
        assert "LaunchConfigurationName" not in instance
        assert instance["AvailabilityZone"] == "us-east-1a"
        assert instance["ProtectedFromScaleIn"] is True
        assert instance["InstanceType"] == "t2.micro"


@mock_autoscaling
def test_describe_autoscaling_instances_launch_config():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        InstanceType="t2.micro",
        ImageId=EXAMPLE_AMI_ID,
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_instances()
    assert len(response["AutoScalingInstances"]) == 5
    for instance in response["AutoScalingInstances"]:
        assert instance["LaunchConfigurationName"] == "test_launch_configuration"
        assert "LaunchTemplate" not in instance
        assert instance["AutoScalingGroupName"] == "test_asg"
        assert instance["AvailabilityZone"] == "us-east-1a"
        assert instance["ProtectedFromScaleIn"] is True
        assert instance["InstanceType"] == "t2.micro"


@mock_autoscaling
@mock_ec2
def test_describe_autoscaling_instances_launch_template():
    mocked_networking = setup_networking()
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "t2.micro"},
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchTemplate={"LaunchTemplateName": "test_launch_template", "Version": "1"},
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )
    expected_launch_template = {
        "LaunchTemplateId": template["LaunchTemplateId"],
        "LaunchTemplateName": "test_launch_template",
        "Version": "1",
    }

    response = client.describe_auto_scaling_instances()
    assert len(response["AutoScalingInstances"]) == 5
    for instance in response["AutoScalingInstances"]:
        assert instance["LaunchTemplate"] == expected_launch_template
        assert "LaunchConfigurationName" not in instance
        assert instance["AutoScalingGroupName"] == "test_asg"
        assert instance["AvailabilityZone"] == "us-east-1a"
        assert instance["ProtectedFromScaleIn"] is True
        assert instance["InstanceType"] == "t2.micro"


@mock_autoscaling
def test_describe_autoscaling_instances_instanceid_filter():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_ids = [
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    ]

    response = client.describe_auto_scaling_instances(
        InstanceIds=instance_ids[0:2]
    )  # Filter by first 2 of 5
    assert len(response["AutoScalingInstances"]) == 2
    for instance in response["AutoScalingInstances"]:
        assert instance["AutoScalingGroupName"] == "test_asg"
        assert instance["AvailabilityZone"] == "us-east-1a"
        assert instance["ProtectedFromScaleIn"] is True


@mock_autoscaling
def test_update_autoscaling_group_launch_config():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration_new",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    client.update_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration_new",
        MinSize=1,
        VPCZoneIdentifier=f"{mocked_networking['subnet1']},{mocked_networking['subnet2']}",
        NewInstancesProtectedFromScaleIn=False,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    assert group["LaunchConfigurationName"] == "test_launch_configuration_new"
    assert group["MinSize"] == 1
    assert set(group["AvailabilityZones"]) == {"us-east-1a", "us-east-1b"}
    assert group["NewInstancesProtectedFromScaleIn"] is False


@mock_autoscaling
@mock_ec2
def test_update_autoscaling_group_launch_template():
    mocked_networking = setup_networking()
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template",
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID, "InstanceType": "t2.micro"},
    )
    template = ec2_client.create_launch_template(
        LaunchTemplateName="test_launch_template_new",
        LaunchTemplateData={
            "ImageId": "ami-1ea5b10a3d8867db4",
            "InstanceType": "t2.micro",
        },
    )["LaunchTemplate"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchTemplate={"LaunchTemplateName": "test_launch_template", "Version": "1"},
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    client.update_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchTemplate={
            "LaunchTemplateName": "test_launch_template_new",
            "Version": "1",
        },
        MinSize=1,
        VPCZoneIdentifier=f"{mocked_networking['subnet1']},{mocked_networking['subnet2']}",
        NewInstancesProtectedFromScaleIn=False,
    )

    expected_launch_template = {
        "LaunchTemplateId": template["LaunchTemplateId"],
        "LaunchTemplateName": "test_launch_template_new",
        "Version": "1",
    }

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    assert group["LaunchTemplate"] == expected_launch_template
    assert group["MinSize"] == 1
    assert set(group["AvailabilityZones"]) == {"us-east-1a", "us-east-1b"}
    assert group["NewInstancesProtectedFromScaleIn"] is False


@mock_autoscaling
def test_update_autoscaling_group_min_size_desired_capacity_change():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")

    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=2,
        MaxSize=20,
        DesiredCapacity=3,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )
    client.update_auto_scaling_group(AutoScalingGroupName="test_asg", MinSize=5)
    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    assert group["DesiredCapacity"] == 5
    assert group["MinSize"] == 5
    assert len(group["Instances"]) == 5


@mock_autoscaling
def test_update_autoscaling_group_max_size_desired_capacity_change():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")

    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=2,
        MaxSize=20,
        DesiredCapacity=10,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )
    client.update_auto_scaling_group(AutoScalingGroupName="test_asg", MaxSize=5)
    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    assert group["DesiredCapacity"] == 5
    assert group["MaxSize"] == 5
    assert len(group["Instances"]) == 5


@mock_autoscaling
def test_autoscaling_describe_policies():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        Tags=[
            {
                "ResourceId": "test_asg",
                "Key": "test_key",
                "Value": "test_value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    client.put_scaling_policy(
        AutoScalingGroupName="test_asg",
        PolicyName="test_policy_down",
        PolicyType="SimpleScaling",
        MetricAggregationType="Minimum",
        AdjustmentType="PercentChangeInCapacity",
        ScalingAdjustment=-10,
        Cooldown=60,
        MinAdjustmentMagnitude=1,
    )
    client.put_scaling_policy(
        AutoScalingGroupName="test_asg",
        PolicyName="test_policy_up",
        PolicyType="SimpleScaling",
        AdjustmentType="PercentChangeInCapacity",
        ScalingAdjustment=10,
        Cooldown=60,
        MinAdjustmentMagnitude=1,
    )

    response = client.describe_policies()
    assert len(response["ScalingPolicies"]) == 2

    response = client.describe_policies(AutoScalingGroupName="test_asg")
    assert len(response["ScalingPolicies"]) == 2

    response = client.describe_policies(PolicyTypes=["StepScaling"])
    assert len(response["ScalingPolicies"]) == 0

    response = client.describe_policies(
        AutoScalingGroupName="test_asg",
        PolicyNames=["test_policy_down"],
        PolicyTypes=["SimpleScaling"],
    )
    assert len(response["ScalingPolicies"]) == 1
    policy = response["ScalingPolicies"][0]
    assert policy["PolicyType"] == "SimpleScaling"
    assert policy["MetricAggregationType"] == "Minimum"
    assert policy["AdjustmentType"] == "PercentChangeInCapacity"
    assert policy["ScalingAdjustment"] == -10
    assert policy["Cooldown"] == 60
    assert (
        policy["PolicyARN"]
        == f"arn:aws:autoscaling:us-east-1:{ACCOUNT_ID}:scalingPolicy:c322761b-3172-4d56-9a21-0ed9d6161d67:autoScalingGroupName/test_asg:policyName/test_policy_down"
    )
    assert policy["PolicyName"] == "test_policy_down"
    assert "TargetTrackingConfiguration" not in policy


@mock_autoscaling
@mock_ec2
def test_create_autoscaling_policy_with_policytype__targettrackingscaling():
    mocked_networking = setup_networking(region_name="us-west-1")
    client = boto3.client("autoscaling", region_name="us-west-1")
    configuration_name = "test"
    asg_name = "asg_test"

    client.create_launch_configuration(
        LaunchConfigurationName=configuration_name,
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="m1.small",
    )
    client.create_auto_scaling_group(
        LaunchConfigurationName=configuration_name,
        AutoScalingGroupName=asg_name,
        MinSize=1,
        MaxSize=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    client.put_scaling_policy(
        AutoScalingGroupName=asg_name,
        PolicyName=configuration_name,
        PolicyType="TargetTrackingScaling",
        EstimatedInstanceWarmup=100,
        TargetTrackingConfiguration={
            "PredefinedMetricSpecification": {
                "PredefinedMetricType": "ASGAverageNetworkIn",
            },
            "TargetValue": 1000000.0,
            "CustomizedMetricSpecification": {
                "Metrics": [
                    {
                        "Label": "Get ASGAverageCPUUtilization",
                        "Id": "cpu",
                        "MetricStat": {
                            "Metric": {
                                "MetricName": "CPUUtilization",
                                "Namespace": "AWS/EC2",
                                "Dimensions": [
                                    {"Name": "AutoScalingGroupName", "Value": asg_name}
                                ],
                            },
                            "Stat": "Average",
                        },
                        "ReturnData": False,
                    },
                    {
                        "Label": "Calculate square cpu",
                        "Id": "load",
                        "Expression": "cpu^2",
                    },
                ],
            },
        },
    )

    resp = client.describe_policies(AutoScalingGroupName=asg_name)
    policy = resp["ScalingPolicies"][0]
    assert policy["PolicyName"] == configuration_name
    assert (
        policy["PolicyARN"]
        == f"arn:aws:autoscaling:us-west-1:{ACCOUNT_ID}:scalingPolicy:c322761b-3172-4d56-9a21-0ed9d6161d67:autoScalingGroupName/{asg_name}:policyName/{configuration_name}"
    )
    assert policy["PolicyType"] == "TargetTrackingScaling"
    assert policy["TargetTrackingConfiguration"] == {
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ASGAverageNetworkIn",
        },
        "CustomizedMetricSpecification": {
            "MetricName": "None",
            "Namespace": "None",
            "Dimensions": [],
            "Statistic": "None",
            "Metrics": [
                {
                    "Label": "Get ASGAverageCPUUtilization",
                    "Id": "cpu",
                    "MetricStat": {
                        "Metric": {
                            "MetricName": "CPUUtilization",
                            "Namespace": "AWS/EC2",
                            "Dimensions": [
                                {"Name": "AutoScalingGroupName", "Value": asg_name}
                            ],
                        },
                        "Stat": "Average",
                        "Unit": "None",
                    },
                    "ReturnData": False,
                },
                {
                    "Label": "Calculate square cpu",
                    "Id": "load",
                    "Expression": "cpu^2",
                    "ReturnData": True,
                },
            ],
        },
        "TargetValue": 1000000.0,
    }
    assert "ScalingAdjustment" not in policy
    assert "Cooldown" not in policy


@mock_autoscaling
@mock_ec2
def test_create_autoscaling_policy_with_policytype__stepscaling():
    mocked_networking = setup_networking(region_name="eu-west-1")
    client = boto3.client("autoscaling", region_name="eu-west-1")
    launch_config_name = "lg_name"
    asg_name = "asg_test"

    client.create_launch_configuration(
        LaunchConfigurationName=launch_config_name,
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="m1.small",
    )
    client.create_auto_scaling_group(
        LaunchConfigurationName=launch_config_name,
        AutoScalingGroupName=asg_name,
        MinSize=1,
        MaxSize=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    client.put_scaling_policy(
        AutoScalingGroupName=asg_name,
        PolicyName=launch_config_name,
        PolicyType="StepScaling",
        StepAdjustments=[
            {
                "MetricIntervalLowerBound": 2,
                "MetricIntervalUpperBound": 8,
                "ScalingAdjustment": 1,
            }
        ],
    )

    resp = client.describe_policies(AutoScalingGroupName=asg_name)
    policy = resp["ScalingPolicies"][0]
    assert policy["PolicyName"] == launch_config_name
    assert (
        policy["PolicyARN"]
        == f"arn:aws:autoscaling:eu-west-1:{ACCOUNT_ID}:scalingPolicy:c322761b-3172-4d56-9a21-0ed9d6161d67:autoScalingGroupName/{asg_name}:policyName/{launch_config_name}"
    )
    assert policy["PolicyType"] == "StepScaling"
    assert policy["StepAdjustments"] == [
        {
            "MetricIntervalLowerBound": 2,
            "MetricIntervalUpperBound": 8,
            "ScalingAdjustment": 1,
        }
    ]
    assert "TargetTrackingConfiguration" not in policy
    assert "ScalingAdjustment" not in policy
    assert "Cooldown" not in policy


@mock_autoscaling
@mock_ec2
def test_create_autoscaling_policy_with_predictive_scaling_config():
    mocked_networking = setup_networking(region_name="eu-west-1")
    client = boto3.client("autoscaling", region_name="eu-west-1")
    launch_config_name = "lg_name"
    asg_name = "asg_test"

    client.create_launch_configuration(
        LaunchConfigurationName=launch_config_name,
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="m1.small",
    )
    client.create_auto_scaling_group(
        LaunchConfigurationName=launch_config_name,
        AutoScalingGroupName=asg_name,
        MinSize=1,
        MaxSize=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    client.put_scaling_policy(
        AutoScalingGroupName=asg_name,
        PolicyName=launch_config_name,
        PolicyType="PredictiveScaling",
        PredictiveScalingConfiguration={
            "MetricSpecifications": [{"TargetValue": 5}],
            "SchedulingBufferTime": 7,
        },
    )

    resp = client.describe_policies(AutoScalingGroupName=asg_name)
    policy = resp["ScalingPolicies"][0]
    assert policy["PredictiveScalingConfiguration"] == {
        "MetricSpecifications": [{"TargetValue": 5.0}],
        "SchedulingBufferTime": 7,
    }


@mock_autoscaling
@mock_ec2
def test_create_auto_scaling_group_with_mixed_instances_policy():
    mocked_networking = setup_networking(region_name="eu-west-1")
    client = boto3.client("autoscaling", region_name="eu-west-1")
    ec2_client = boto3.client("ec2", region_name="eu-west-1")
    asg_name = "asg_test"

    lt = ec2_client.create_launch_template(
        LaunchTemplateName="launchie",
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID},
    )["LaunchTemplate"]
    client.create_auto_scaling_group(
        MixedInstancesPolicy={
            "LaunchTemplate": {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateName": "launchie",
                    "Version": "$DEFAULT",
                }
            }
        },
        AutoScalingGroupName=asg_name,
        MinSize=2,
        MaxSize=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    # Assert we can describe MixedInstancesPolicy
    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
    group = response["AutoScalingGroups"][0]
    assert group["MixedInstancesPolicy"] == {
        "LaunchTemplate": {
            "LaunchTemplateSpecification": {
                "LaunchTemplateId": lt["LaunchTemplateId"],
                "LaunchTemplateName": "launchie",
                "Version": "$DEFAULT",
            }
        }
    }

    # Assert the LaunchTemplate is known for the resulting instances
    response = client.describe_auto_scaling_instances()
    assert len(response["AutoScalingInstances"]) == 2
    for instance in response["AutoScalingInstances"]:
        assert instance["LaunchTemplate"] == {
            "LaunchTemplateId": lt["LaunchTemplateId"],
            "LaunchTemplateName": "launchie",
            "Version": "$DEFAULT",
        }


@mock_autoscaling
@mock_ec2
def test_create_auto_scaling_group_with_mixed_instances_policy_overrides():
    mocked_networking = setup_networking(region_name="eu-west-1")
    client = boto3.client("autoscaling", region_name="eu-west-1")
    ec2_client = boto3.client("ec2", region_name="eu-west-1")
    asg_name = "asg_test"

    lt = ec2_client.create_launch_template(
        LaunchTemplateName="launchie",
        LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID},
    )["LaunchTemplate"]
    client.create_auto_scaling_group(
        MixedInstancesPolicy={
            "LaunchTemplate": {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateName": "launchie",
                    "Version": "$DEFAULT",
                },
                "Overrides": [
                    {
                        "InstanceType": "t2.medium",
                        "WeightedCapacity": "50",
                    }
                ],
            }
        },
        AutoScalingGroupName=asg_name,
        MinSize=2,
        MaxSize=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    # Assert we can describe MixedInstancesPolicy
    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
    group = response["AutoScalingGroups"][0]
    assert group["MixedInstancesPolicy"] == {
        "LaunchTemplate": {
            "LaunchTemplateSpecification": {
                "LaunchTemplateId": lt["LaunchTemplateId"],
                "LaunchTemplateName": "launchie",
                "Version": "$DEFAULT",
            },
            "Overrides": [
                {
                    "InstanceType": "t2.medium",
                    "WeightedCapacity": "50",
                }
            ],
        }
    }


@mock_autoscaling
def test_set_instance_protection():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=False,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_ids = [
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    ]
    protected = instance_ids[:3]

    _ = client.set_instance_protection(
        AutoScalingGroupName="test_asg",
        InstanceIds=protected,
        ProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    for instance in response["AutoScalingGroups"][0]["Instances"]:
        assert instance["ProtectedFromScaleIn"] is (instance["InstanceId"] in protected)


@mock_autoscaling
def test_set_desired_capacity_up():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    _ = client.set_desired_capacity(AutoScalingGroupName="test_asg", DesiredCapacity=10)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instances = response["AutoScalingGroups"][0]["Instances"]
    assert len(instances) == 10
    for instance in instances:
        assert instance["ProtectedFromScaleIn"] is True


@mock_autoscaling
def test_set_desired_capacity_down():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=True,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    instance_ids = [
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    ]
    unprotected, protected = instance_ids[:2], instance_ids[2:]

    _ = client.set_instance_protection(
        AutoScalingGroupName="test_asg",
        InstanceIds=unprotected,
        ProtectedFromScaleIn=False,
    )

    _ = client.set_desired_capacity(AutoScalingGroupName="test_asg", DesiredCapacity=1)

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    group = response["AutoScalingGroups"][0]
    assert group["DesiredCapacity"] == 1
    instance_ids = {instance["InstanceId"] for instance in group["Instances"]}
    assert set(protected) == instance_ids
    for x in unprotected:
        assert x not in instance_ids  # only unprotected killed


@mock_autoscaling
@mock_ec2
def test_terminate_instance_via_ec2_in_autoscaling_group():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=1,
        MaxSize=20,
        VPCZoneIdentifier=mocked_networking["subnet1"],
        NewInstancesProtectedFromScaleIn=False,
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    original_instance_id = next(
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    )
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    ec2_client.terminate_instances(InstanceIds=[original_instance_id])

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    replaced_instance_id = next(
        instance["InstanceId"]
        for instance in response["AutoScalingGroups"][0]["Instances"]
    )
    assert replaced_instance_id != original_instance_id


@mock_ec2
@mock_autoscaling
def test_attach_instances():
    asg_client = boto3.client("autoscaling", region_name="us-east-1")
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    kwargs = {
        "KeyName": "foobar",
        "ImageId": EXAMPLE_AMI_ID,
        "MinCount": 1,
        "MaxCount": 1,
        "InstanceType": "c4.2xlarge",
        "TagSpecifications": [
            {"ResourceType": "instance", "Tags": [{"Key": "key", "Value": "val"}]},
        ],
    }
    fake_instance = ec2_client.run_instances(**kwargs)["Instances"][0]
    asg_client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId="ami-pytest",
        InstanceType="t3.micro",
        KeyName="foobar",
    )
    asg_client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=1,
        AvailabilityZones=[fake_instance["Placement"]["AvailabilityZone"]],
    )
    asg_client.attach_instances(
        InstanceIds=[fake_instance["InstanceId"]], AutoScalingGroupName="test_asg"
    )
    response = asg_client.describe_auto_scaling_instances()
    assert len(response["AutoScalingInstances"]) == 1
    for instance in response["AutoScalingInstances"]:
        assert instance["LaunchConfigurationName"] == "test_launch_configuration"
        assert instance["AutoScalingGroupName"] == "test_asg"
        assert instance["InstanceType"] == "c4.2xlarge"


@mock_autoscaling
def test_autoscaling_lifecyclehook():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId="ami-pytest",
        InstanceType="t3.micro",
        KeyName="foobar",
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=1,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )
    client.put_lifecycle_hook(
        LifecycleHookName="test-lifecyclehook",
        AutoScalingGroupName="test_asg",
        LifecycleTransition="autoscaling:EC2_INSTANCE_TERMINATING",
    )

    response = client.describe_lifecycle_hooks(
        AutoScalingGroupName="test_asg", LifecycleHookNames=["test-lifecyclehook"]
    )
    assert len(response["LifecycleHooks"]) == 1
    for hook in response["LifecycleHooks"]:
        assert hook["LifecycleHookName"] == "test-lifecyclehook"
        assert hook["AutoScalingGroupName"] == "test_asg"
        assert hook["LifecycleTransition"] == "autoscaling:EC2_INSTANCE_TERMINATING"

    client.delete_lifecycle_hook(
        LifecycleHookName="test-lifecyclehook", AutoScalingGroupName="test_asg"
    )

    response = client.describe_lifecycle_hooks(
        AutoScalingGroupName="test_asg", LifecycleHookNames=["test-lifecyclehook"]
    )

    assert len(response["LifecycleHooks"]) == 0


@pytest.mark.parametrize("original,new", [(2, 1), (2, 3), (1, 5), (1, 1)])
@mock_autoscaling
def test_set_desired_capacity_without_protection(original, new):
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )

    client.create_auto_scaling_group(
        AutoScalingGroupName="tester_group",
        LaunchConfigurationName="test_launch_configuration",
        AvailabilityZones=["us-east-1a"],
        MinSize=original,
        MaxSize=original,
        DesiredCapacity=original,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    group = client.describe_auto_scaling_groups()["AutoScalingGroups"][0]
    assert group["DesiredCapacity"] == original
    instances = client.describe_auto_scaling_instances()["AutoScalingInstances"]
    assert len(instances) == original

    client.update_auto_scaling_group(
        AutoScalingGroupName="tester_group", DesiredCapacity=new
    )

    group = client.describe_auto_scaling_groups()["AutoScalingGroups"][0]
    assert group["DesiredCapacity"] == new
    instances = client.describe_auto_scaling_instances()["AutoScalingInstances"]
    assert len(instances) == new


@mock_autoscaling
@mock_ec2
def test_create_template_with_block_device():
    ec2_client = boto3.client("ec2", region_name="ap-southeast-2")
    ec2_client.create_launch_template(
        LaunchTemplateName="launchie",
        LaunchTemplateData={
            "ImageId": EXAMPLE_AMI_ID,
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/sda1",
                    "Ebs": {
                        "VolumeSize": 20,
                        "DeleteOnTermination": True,
                        "VolumeType": "gp3",
                        "Encrypted": True,
                    },
                }
            ],
        },
    )

    ec2_client.run_instances(
        MaxCount=1, MinCount=1, LaunchTemplate={"LaunchTemplateName": "launchie"}
    )
    ec2_client = boto3.client("ec2", region_name="ap-southeast-2")
    volumes = ec2_client.describe_volumes()["Volumes"]
    # The standard root volume
    assert volumes[0]["VolumeType"] == "gp2"
    assert volumes[0]["Size"] == 8
    # Our Ebs-volume
    assert volumes[1]["VolumeType"] == "gp3"
    assert volumes[1]["Size"] == 20
