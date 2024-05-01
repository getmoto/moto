import datetime

import boto3

from moto import mock_aws


@mock_aws
def test_create_node_from_template_job() -> None:
    # Given
    panorama_client = boto3.client("panorama", "us-east-1")

    # When
    response = panorama_client.create_node_from_template_job(
        JobTags=[
            {"ResourceType": "PACKAGE", "Tags": {"key": "value"}},
        ],
        NodeDescription="a description",
        NodeName="a-camera-node",
        OutputPackageName="an-output-package-name",
        OutputPackageVersion="1.0",
        TemplateParameters={
            "Username": "a-user-name",
            "Password": "a-password",
            "StreamUrl": "rtsp://",
        },
        TemplateType="RTSP_CAMERA_STREAM",
    )

    # Then
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "JobId" in response
    assert isinstance(response["JobId"], str)


@mock_aws
def test_describe_node_from_template_job() -> None:
    # Given
    panorama_client = boto3.client("panorama", "us-east-1")

    # When
    response = panorama_client.create_node_from_template_job(
        JobTags=[
            {"ResourceType": "PACKAGE", "Tags": {"key": "value"}},
        ],
        NodeDescription="a description",
        NodeName="not-a-camera-node",
        OutputPackageName="not-an-output-package-name",
        OutputPackageVersion="1.0",
        TemplateParameters={
            "Username": "not-a-user-name",
            "Password": "not-a-password",
            "StreamUrl": "rtsp://192.168.0.201/1",
        },
        TemplateType="RTSP_CAMERA_STREAM",
    )
    describe_response = panorama_client.describe_node_from_template_job(
        JobId=response["JobId"]
    )

    # Then
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "JobId" in response
    assert isinstance(response["JobId"], str)
    assert isinstance(describe_response["CreatedTime"], datetime.datetime)
    assert describe_response["JobId"] == response["JobId"]
    assert describe_response["JobTags"] == [
        {"ResourceType": "PACKAGE", "Tags": {"key": "value"}}
    ]
    assert isinstance(describe_response["LastUpdatedTime"], datetime.datetime)
    # Weird, seems to be a bug in panorama
    assert describe_response["NodeDescription"] == "not-a-camera-node"
    assert describe_response["NodeName"] == "not-a-camera-node"
    assert describe_response["OutputPackageName"] == "not-an-output-package-name"
    assert describe_response["OutputPackageVersion"] == "1.0"
    assert describe_response["Status"] == "PENDING"
    assert describe_response["TemplateParameters"] == {
        "Username": "SAVED_AS_SECRET",
        "Password": "SAVED_AS_SECRET",
        "StreamUrl": "rtsp://192.168.0.201/1",
    }
    assert describe_response["TemplateType"] == "RTSP_CAMERA_STREAM"


@mock_aws
def test_list_nodes() -> None:
    # Given
    panorama_client = boto3.client("panorama", "us-east-1")
    panorama_client.create_node_from_template_job(
        JobTags=[
            {"ResourceType": "PACKAGE", "Tags": {"key": "value"}},
        ],
        NodeDescription="a description",
        NodeName="not-a-camera-node",
        OutputPackageName="not-an-output-package-name",
        OutputPackageVersion="1.0",
        TemplateParameters={
            "Username": "not-a-user-name",
            "Password": "not-a-password",
            "StreamUrl": "rtsp://",
        },
        TemplateType="RTSP_CAMERA_STREAM",
    )
    panorama_client.create_node_from_template_job(
        JobTags=[
            {"ResourceType": "PACKAGE", "Tags": {"key": "value"}},
        ],
        NodeDescription="a description",
        NodeName="not-another-camera-node",
        OutputPackageName="not-another-output-package-name",
        OutputPackageVersion="1.0",
        TemplateParameters={
            "Username": "not-another-user-name",
            "Password": "not-another-password",
            "StreamUrl": "rtsp://",
        },
        TemplateType="RTSP_CAMERA_STREAM",
    )
    given_category = "MEDIA_SOURCE"

    # When
    response_page_1 = panorama_client.list_nodes(Category=given_category, MaxResults=1)
    response_page_2 = panorama_client.list_nodes(
        Category=given_category, MaxResults=1, NextToken=response_page_1["NextToken"]
    )

    # Then
    assert response_page_1["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "Nodes" in response_page_1
    assert isinstance(response_page_1["Nodes"], list)
    assert len(response_page_1["Nodes"]) == 1
    assert "NextToken" in response_page_1
    assert isinstance(response_page_1["NextToken"], str)
    node = response_page_1["Nodes"][0]
    assert node["Category"] == given_category
    assert isinstance(node["CreatedTime"], datetime.datetime)
    assert node["Description"] == "a description"
    assert node["Name"] == "not-a-camera-node"
    assert node["OwnerAccount"] == "123456789012"
    assert (
        node["PackageArn"]
        == "arn:aws:panorama:us-east-1:123456789012:package/package-+Y6+ycqU+ogoBTHuibMzGg=="
    )
    assert node["PackageId"] == "package-+Y6+ycqU+ogoBTHuibMzGg=="
    assert node["PackageName"] == "not-an-output-package-name"
    assert node["PackageVersion"] == "1.0"
    assert (
        node["PatchVersion"]
        == "y6ycquogobthuibmzggy6ycquogobthuibmzggy6ycquogobthuibmzggy6ycquo"
    )

    assert response_page_2["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "Nodes" in response_page_2
    assert isinstance(response_page_2["Nodes"], list)
    assert len(response_page_2["Nodes"]) == 1
    assert "NextToken" not in response_page_2


"""
botocore.errorfactory.ValidationException: An error occurred (ValidationException) when calling the CreateNodeFromTemplateJob operation: {"reason":"FIELD_VALIDATION_FAILED","message":"The input fails to satisfy the constraints specified by an AWS service.","fields":[{"name":"TemplateParameters","message":"Unsupported template parameters: [param]"}]}
botocore.errorfactory.ValidationException: An error occurred (ValidationException) when calling the CreateNodeFromTemplateJob operation: {"Message":[ECMA 262 regex \"^([0-9]+)\\.([0-9]+)$\" does not match input string \"not-an-output-package-version\"]}
"""
