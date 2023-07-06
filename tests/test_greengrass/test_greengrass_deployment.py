import json

import boto3
from botocore.client import ClientError
import freezegun
import pytest

from moto import mock_greengrass
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.settings import TEST_SERVER_MODE


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
    assert "DeploymentArn" in res
    assert "DeploymentId" in res
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 200


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
    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == "Your request is missing the following required parameter(s): {DeploymentId}."
    )
    assert err["Code"] == "InvalidInputException"


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
    err = ex.value.response["Error"]
    assert err["Message"] == f"Deployment ID '{deployment_id}' is invalid."
    assert err["Code"] == "InvalidInputException"


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

    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.value.response["Error"]["Code"] == "MissingCoreException"
    err = json.loads(ex.value.response["Error"]["Message"])
    err_details = err["ErrorDetails"]

    assert err_details[0]["DetailedErrorCode"] == "GG-303"
    assert (
        err_details[0]["DetailedErrorMessage"]
        == "You need a Greengrass Core in this Group before you can deploy."
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

    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        ex.value.response["Error"]["Message"] == "That group definition does not exist."
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

    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        ex.value.response["Error"]["Message"]
        == f"Version {group_version_id} of Group Definition {group_id} does not exist."
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

    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidInputException"
    assert (
        err["Message"]
        == "That deployment type is not valid.  Please specify one of the following types: {NewDeployment,Redeployment,ResetDeployment,ForceResetDeployment}."
    )


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_list_deployments():
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
    latest_grp_ver_arn = create_group_res["LatestVersionArn"]
    deployment_type = "NewDeployment"
    client.create_deployment(
        GroupId=group_id, GroupVersionId=latest_grp_ver, DeploymentType=deployment_type
    )

    res = client.list_deployments(GroupId=group_id)
    assert "Deployments" in res
    deployments = res["Deployments"][0]

    assert "CreatedAt" in deployments
    assert "DeploymentArn" in deployments
    assert "DeploymentId" in deployments
    assert deployments["DeploymentType"] == deployment_type
    assert deployments["GroupArn"] == latest_grp_ver_arn

    if not TEST_SERVER_MODE:
        assert deployments["CreatedAt"] == "2022-06-01T12:00:00.000Z"


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_get_deployment_status():
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
    deployment_type = "NewDeployment"
    create_deployment_res = client.create_deployment(
        GroupId=group_id, GroupVersionId=latest_grp_ver, DeploymentType=deployment_type
    )

    deployment_id = create_deployment_res["DeploymentId"]
    res = client.get_deployment_status(GroupId=group_id, DeploymentId=deployment_id)

    assert res["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert res["DeploymentStatus"] == "InProgress"
    assert res["DeploymentType"] == deployment_type
    assert "UpdatedAt" in res

    if not TEST_SERVER_MODE:
        assert res["UpdatedAt"] == "2022-06-01T12:00:00.000Z"


@mock_greengrass
def test_get_deployment_status_with_invalid_deployment_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    create_group_res = client.create_group(Name="TestGroup")
    group_id = create_group_res["Id"]

    deployment_id = "7b0bdeae-54c7-47cf-9f93-561e672efd9c"

    with pytest.raises(ClientError) as ex:
        client.get_deployment_status(GroupId=group_id, DeploymentId=deployment_id)
    err = ex.value.response["Error"]
    assert err["Message"] == f"Deployment '{deployment_id}' does not exist."
    assert err["Code"] == "InvalidInputException"


@mock_greengrass
def test_get_deployment_status_with_invalid_group_id():
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
    deployment_type = "NewDeployment"
    create_deployment_res = client.create_deployment(
        GroupId=group_id, GroupVersionId=latest_grp_ver, DeploymentType=deployment_type
    )

    deployment_id = create_deployment_res["DeploymentId"]

    with pytest.raises(ClientError) as ex:
        client.get_deployment_status(
            GroupId="7b0bdeae-54c7-47cf-9f93-561e672efd9c", DeploymentId=deployment_id
        )
    err = ex.value.response["Error"]
    assert err["Message"] == f"Deployment '{deployment_id}' does not exist."
    assert err["Code"] == "InvalidInputException"


@pytest.mark.skipif(
    TEST_SERVER_MODE,
    reason="Can't handle path that contains $ in server mode.So ResetGroup api can't use in server mode",
)
@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_reset_deployments():
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
    group_arn = create_group_res["Arn"]
    latest_grp_ver = create_group_res["LatestVersion"]
    client.create_deployment(
        GroupId=group_id, GroupVersionId=latest_grp_ver, DeploymentType="NewDeployment"
    )

    reset_res = client.reset_deployments(GroupId=group_id)

    assert reset_res["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "DeploymentId" in reset_res
    assert "DeploymentArn" in reset_res

    list_res = client.list_deployments(GroupId=group_id)
    reset_deployment = list_res["Deployments"][1]
    assert "CreatedAt" in reset_deployment
    assert "DeploymentArn" in reset_deployment
    assert "DeploymentId" in reset_deployment
    assert reset_deployment["DeploymentType"] == "ResetDeployment"
    assert reset_deployment["GroupArn"] == group_arn

    if not TEST_SERVER_MODE:
        assert reset_deployment["CreatedAt"] == "2022-06-01T12:00:00.000Z"


@pytest.mark.skipif(
    TEST_SERVER_MODE,
    reason="Can't handle path that contains $ in server mode.So ResetGroup api can't use in server mode",
)
@mock_greengrass
def test_reset_deployments_with_invalid_group_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.reset_deployments(GroupId="7b0bdeae-54c7-47cf-9f93-561e672efd9c")
    err = ex.value.response["Error"]
    assert err["Message"] == "That Group Definition does not exist."
    assert err["Code"] == "ResourceNotFoundException"


@pytest.mark.skipif(
    TEST_SERVER_MODE,
    reason="Can't handle path that contains $ in server mode.So ResetGroup api can't use in server mode",
)
@mock_greengrass
def test_reset_deployments_with_never_deployed_group():
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

    with pytest.raises(ClientError) as ex:
        client.reset_deployments(GroupId=group_id)
    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == f"Group id: {group_id} has not been deployed or has already been reset."
    )
    assert err["Code"] == "ResourceNotFoundException"


@pytest.mark.skipif(
    TEST_SERVER_MODE,
    reason="Can't handle path that contains $ in server mode.So ResetGroup api can't use in server mode",
)
@mock_greengrass
def test_reset_deployments_with_already_reset_group():
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

    client.create_deployment(
        GroupId=group_id, GroupVersionId=latest_grp_ver, DeploymentType="NewDeployment"
    )
    client.reset_deployments(GroupId=group_id)

    with pytest.raises(ClientError) as ex:
        client.reset_deployments(GroupId=group_id)
    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == f"Group id: {group_id} has not been deployed or has already been reset."
    )
    assert err["Code"] == "ResourceNotFoundException"
