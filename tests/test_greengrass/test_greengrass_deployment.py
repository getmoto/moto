import json

import boto3
from botocore.client import ClientError
import pytest

from moto import mock_greengrass
from moto.core import get_account_id

ACCOUNT_ID = get_account_id()


@mock_greengrass
def test_create_deployment():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    cores = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123456789",
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
        }
    ]

    create_core_res = client.create_core_definition(
        InitialVersion={"Cores": cores}, Name="TestCore"
    )
    core_def_ver_arn = create_core_res["LatestVersionArn"]

    create_group_res = client.create_group(
        Name="TestGroup", InitialVersion={"CoreDefinitionVersionArn": core_def_ver_arn}
    )
    group_id = create_group_res["Id"]
    latest_grp_ver = create_group_res["LatestVersion"]

    res = client.create_deployment(
        GroupId=group_id, GroupVersionId=latest_grp_ver, DeploymentType="NewDeployment"
    )
    res.should.have.key("DeploymentArn")
    res.should.have.key("DeploymentId")
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_greengrass
def test_re_deployment_with_no_deployment_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    cores = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123456789",
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
        }
    ]

    create_core_res = client.create_core_definition(
        InitialVersion={"Cores": cores}, Name="TestCore"
    )
    core_def_ver_arn = create_core_res["LatestVersionArn"]

    create_group_res = client.create_group(
        Name="TestGroup", InitialVersion={"CoreDefinitionVersionArn": core_def_ver_arn}
    )
    group_id = create_group_res["Id"]
    latest_grp_ver = create_group_res["LatestVersion"]

    with pytest.raises(ClientError) as ex:
        client.create_deployment(
            GroupId=group_id,
            GroupVersionId=latest_grp_ver,
            DeploymentType="Redeployment",
        )
    ex.value.response["Error"]["Message"].should.equal(
        "Your request is missing the following required parameter(s): {DeploymentId}."
    )
    ex.value.response["Error"]["Code"].should.equal("InvalidInputException")


@mock_greengrass
def test_re_deployment_with_invalid_deployment_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    cores = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123456789",
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
        }
    ]

    create_core_res = client.create_core_definition(
        InitialVersion={"Cores": cores}, Name="TestCore"
    )
    core_def_ver_arn = create_core_res["LatestVersionArn"]

    create_group_res = client.create_group(
        Name="TestGroup", InitialVersion={"CoreDefinitionVersionArn": core_def_ver_arn}
    )
    group_id = create_group_res["Id"]
    latest_grp_ver = create_group_res["LatestVersion"]

    deployment_id = "7b0bdeae-54c7-47cf-9f93-561e672efd9c"
    with pytest.raises(ClientError) as ex:
        client.create_deployment(
            GroupId=group_id,
            GroupVersionId=latest_grp_ver,
            DeploymentType="Redeployment",
            DeploymentId=deployment_id,
        )
    ex.value.response["Error"]["Message"].should.equal(
        f"Deployment ID '{deployment_id}' is invalid."
    )
    ex.value.response["Error"]["Code"].should.equal("InvalidInputException")


@mock_greengrass
def test_create_deployment_with_no_core_group():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    create_group_res = client.create_group(Name="TestGroup")
    group_id = create_group_res["Id"]
    latest_grp_ver = create_group_res["LatestVersion"]

    with pytest.raises(ClientError) as ex:
        client.create_deployment(
            GroupId=group_id,
            GroupVersionId=latest_grp_ver,
            DeploymentType="NewDeployment",
        )

    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Code"].should.equal("MissingCoreException")
    err = json.loads(ex.value.response["Error"]["Message"])
    err_details = err["ErrorDetails"]

    err_details[0].should.have.key("DetailedErrorCode").equals("GG-303")
    err_details[0].should.have.key("DetailedErrorMessage").equals(
        "You need a Greengrass Core in this Group before you can deploy."
    )


@mock_greengrass
def test_create_deployment_with_invalid_group_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.create_deployment(
            GroupId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
            GroupVersionId="dfd06e54-6531-4a9b-9505-3c1036b6906a",
            DeploymentType="NewDeployment",
        )

    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    ex.value.response["Error"]["Message"].should.equal(
        "That group definition does not exist."
    )


@mock_greengrass
def test_create_deployment_with_invalid_group_version_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    cores = [
        {
            "CertificateArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/36ed61be9c6271ae8da174e29d0e033c06af149d7b21672f3800fe322044554d",
            "Id": "123456789",
            "ThingArn": f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:thing/CoreThing",
        }
    ]

    create_core_res = client.create_core_definition(
        InitialVersion={"Cores": cores}, Name="TestCore"
    )
    core_def_ver_arn = create_core_res["LatestVersionArn"]

    create_group_res = client.create_group(
        Name="TestGroup", InitialVersion={"CoreDefinitionVersionArn": core_def_ver_arn}
    )
    group_id = create_group_res["Id"]
    group_version_id = "dfd06e54-6531-4a9b-9505-3c1036b6906a"

    with pytest.raises(ClientError) as ex:
        client.create_deployment(
            GroupId=group_id,
            GroupVersionId=group_version_id,
            DeploymentType="NewDeployment",
        )

    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(404)
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    ex.value.response["Error"]["Message"].should.equal(
        f"Version {group_version_id} of Group Definition {group_id} does not exist."
    )


@mock_greengrass
def test_create_deployment_with_invalid_deployment_type():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    create_group_res = client.create_group(Name="TestGroup")
    group_id = create_group_res["Id"]
    latest_grp_ver = create_group_res["LatestVersion"]

    with pytest.raises(ClientError) as ex:
        client.create_deployment(
            GroupId=group_id,
            GroupVersionId=latest_grp_ver,
            DeploymentType="InvalidDeploymentType",
        )

    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Code"].should.equal("InvalidInputException")
    ex.value.response["Error"]["Message"].should.equal(
        "That deployment type is not valid.  Please specify one of the following types: {NewDeployment,Redeployment,ResetDeployment,ForceResetDeployment}."
    )
