import copy
import datetime
from datetime import timezone
import hashlib
import json
import pkgutil
import yaml

import boto3
import botocore.exceptions
from botocore.exceptions import ClientError
import pytest

from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto import mock_ssm


def _get_yaml_template():
    return pkgutil.get_data(__name__, "test_templates/good.yaml")


def _validate_document_description(
    doc_name,
    doc_description,
    json_doc,
    expected_document_version,
    expected_latest_version,
    expected_default_version,
    expected_format,
):

    if expected_format == "JSON":
        assert doc_description["Hash"] == (
            hashlib.sha256(json.dumps(json_doc).encode("utf-8")).hexdigest()
        )
    else:
        assert doc_description["Hash"] == (
            hashlib.sha256(yaml.dump(json_doc).encode("utf-8")).hexdigest()
        )

    assert doc_description["HashType"] == "Sha256"
    assert doc_description["Name"] == doc_name
    assert doc_description["Owner"] == ACCOUNT_ID

    difference = datetime.datetime.now(tz=timezone.utc) - doc_description["CreatedDate"]
    if difference.min > datetime.timedelta(minutes=1):
        assert False

    assert doc_description["Status"] == "Active"
    assert doc_description["DocumentVersion"] == expected_document_version
    assert doc_description["Description"] == json_doc["description"]

    doc_description["Parameters"] = sorted(
        doc_description["Parameters"], key=lambda doc: doc["Name"]
    )

    assert doc_description["Parameters"][0]["Name"] == "Parameter1"
    assert doc_description["Parameters"][0]["Type"] == "Integer"
    assert doc_description["Parameters"][0]["Description"] == "Command Duration."
    assert doc_description["Parameters"][0]["DefaultValue"] == "3"

    assert doc_description["Parameters"][1]["Name"] == "Parameter2"
    assert doc_description["Parameters"][1]["Type"] == "String"
    assert doc_description["Parameters"][1]["DefaultValue"] == "def"

    assert doc_description["Parameters"][2]["Name"] == "Parameter3"
    assert doc_description["Parameters"][2]["Type"] == "Boolean"
    assert doc_description["Parameters"][2]["Description"] == "A boolean"
    assert doc_description["Parameters"][2]["DefaultValue"] == "False"

    assert doc_description["Parameters"][3]["Name"] == "Parameter4"
    assert doc_description["Parameters"][3]["Type"] == "StringList"
    assert doc_description["Parameters"][3]["Description"] == "A string list"
    assert doc_description["Parameters"][3]["DefaultValue"] == '["abc", "def"]'

    assert doc_description["Parameters"][4]["Name"] == "Parameter5"
    assert doc_description["Parameters"][4]["Type"] == "StringMap"

    assert doc_description["Parameters"][5]["Name"] == "Parameter6"
    assert doc_description["Parameters"][5]["Type"] == "MapList"

    if expected_format == "JSON":
        # We have to replace single quotes from the response to package it back up
        assert json.loads(doc_description["Parameters"][4]["DefaultValue"]) == {
            "NotificationArn": "$dependency.topicArn",
            "NotificationEvents": ["Failed"],
            "NotificationType": "Command",
        }

        assert json.loads(doc_description["Parameters"][5]["DefaultValue"]) == [
            {"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": "50"}},
            {"DeviceName": "/dev/sdm", "Ebs": {"VolumeSize": "100"}},
        ]
    else:
        assert yaml.safe_load(doc_description["Parameters"][4]["DefaultValue"]) == {
            "NotificationArn": "$dependency.topicArn",
            "NotificationEvents": ["Failed"],
            "NotificationType": "Command",
        }
        assert yaml.safe_load(doc_description["Parameters"][5]["DefaultValue"]) == [
            {"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": "50"}},
            {"DeviceName": "/dev/sdm", "Ebs": {"VolumeSize": "100"}},
        ]

    assert doc_description["DocumentType"] == "Command"
    assert doc_description["SchemaVersion"] == "2.2"
    assert doc_description["LatestVersion"] == expected_latest_version
    assert doc_description["DefaultVersion"] == expected_default_version
    assert doc_description["DocumentFormat"] == expected_format


def _get_doc_validator(
    response, version_name, doc_version, json_doc_content, document_format
):
    assert response["Name"] == "TestDocument3"
    if version_name:
        assert response["VersionName"] == version_name
    assert response["DocumentVersion"] == doc_version
    assert response["Status"] == "Active"
    if document_format == "JSON":
        assert json.loads(response["Content"]) == json_doc_content
    else:
        assert yaml.safe_load(response["Content"]) == json_doc_content
    assert response["DocumentType"] == "Command"
    assert response["DocumentFormat"] == document_format


@mock_ssm
def test_create_document():
    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)

    client = boto3.client("ssm", region_name="us-east-1")

    response = client.create_document(
        Content=yaml.dump(json_doc),
        Name="TestDocument",
        DocumentType="Command",
        DocumentFormat="YAML",
    )
    doc_description = response["DocumentDescription"]
    _validate_document_description(
        "TestDocument", doc_description, json_doc, "1", "1", "1", "YAML"
    )

    response = client.create_document(
        Content=json.dumps(json_doc),
        Name="TestDocument2",
        DocumentType="Command",
        DocumentFormat="JSON",
    )
    doc_description = response["DocumentDescription"]
    _validate_document_description(
        "TestDocument2", doc_description, json_doc, "1", "1", "1", "JSON"
    )

    response = client.create_document(
        Content=json.dumps(json_doc),
        Name="TestDocument3",
        DocumentType="Command",
        DocumentFormat="JSON",
        VersionName="Base",
        TargetType="/AWS::EC2::Instance",
        Tags=[{"Key": "testing", "Value": "testingValue"}],
    )
    doc_description = response["DocumentDescription"]
    assert doc_description["VersionName"] == "Base"
    assert doc_description["TargetType"] == "/AWS::EC2::Instance"
    assert doc_description["Tags"] == [{"Key": "testing", "Value": "testingValue"}]

    _validate_document_description(
        "TestDocument3", doc_description, json_doc, "1", "1", "1", "JSON"
    )

    try:
        client.create_document(
            Content=json.dumps(json_doc),
            Name="TestDocument3",
            DocumentType="Command",
            DocumentFormat="JSON",
        )
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "CreateDocument"
        assert (
            err.response["Error"]["Message"] == "The specified document already exists."
        )

    try:
        client.create_document(
            Content=yaml.dump(json_doc),
            Name="TestDocument4",
            DocumentType="Command",
            DocumentFormat="JSON",
        )
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "CreateDocument"
        assert (
            err.response["Error"]["Message"]
            == "The content for the document is not valid."
        )

    del json_doc["parameters"]
    response = client.create_document(
        Content=yaml.dump(json_doc),
        Name="EmptyParamDoc",
        DocumentType="Command",
        DocumentFormat="YAML",
    )
    doc_description = response["DocumentDescription"]

    assert doc_description["Hash"] == (
        hashlib.sha256(yaml.dump(json_doc).encode("utf-8")).hexdigest()
    )
    assert doc_description["HashType"] == "Sha256"
    assert doc_description["Name"] == "EmptyParamDoc"
    assert doc_description["Owner"] == ACCOUNT_ID

    difference = datetime.datetime.now(tz=timezone.utc) - doc_description["CreatedDate"]
    if difference.min > datetime.timedelta(minutes=1):
        assert False

    assert doc_description["Status"] == "Active"
    assert doc_description["DocumentVersion"] == "1"
    assert doc_description["Description"] == json_doc["description"]
    assert doc_description["DocumentType"] == "Command"
    assert doc_description["SchemaVersion"] == "2.2"
    assert doc_description["LatestVersion"] == "1"
    assert doc_description["DefaultVersion"] == "1"
    assert doc_description["DocumentFormat"] == "YAML"


@mock_ssm
def test_get_document():
    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)

    client = boto3.client("ssm", region_name="us-east-1")

    try:
        client.get_document(Name="DNE")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "GetDocument"
        assert (
            err.response["Error"]["Message"] == "The specified document does not exist."
        )

    client.create_document(
        Content=yaml.dump(json_doc),
        Name="TestDocument3",
        DocumentType="Command",
        DocumentFormat="YAML",
        VersionName="Base",
    )

    new_json_doc = copy.copy(json_doc)
    new_json_doc["description"] = "a new description"

    client.update_document(
        Content=json.dumps(new_json_doc),
        Name="TestDocument3",
        DocumentVersion="$LATEST",
        VersionName="NewBase",
    )

    response = client.get_document(Name="TestDocument3")
    _get_doc_validator(response, "Base", "1", json_doc, "JSON")

    response = client.get_document(Name="TestDocument3", DocumentFormat="YAML")
    _get_doc_validator(response, "Base", "1", json_doc, "YAML")

    response = client.get_document(Name="TestDocument3", DocumentFormat="JSON")
    _get_doc_validator(response, "Base", "1", json_doc, "JSON")

    response = client.get_document(Name="TestDocument3", VersionName="Base")
    _get_doc_validator(response, "Base", "1", json_doc, "JSON")

    response = client.get_document(Name="TestDocument3", DocumentVersion="1")
    _get_doc_validator(response, "Base", "1", json_doc, "JSON")

    response = client.get_document(Name="TestDocument3", DocumentVersion="2")
    _get_doc_validator(response, "NewBase", "2", new_json_doc, "JSON")

    response = client.get_document(Name="TestDocument3", VersionName="NewBase")
    _get_doc_validator(response, "NewBase", "2", new_json_doc, "JSON")

    response = client.get_document(
        Name="TestDocument3", VersionName="NewBase", DocumentVersion="2"
    )
    _get_doc_validator(response, "NewBase", "2", new_json_doc, "JSON")

    try:
        response = client.get_document(
            Name="TestDocument3", VersionName="BadName", DocumentVersion="2"
        )
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "GetDocument"
        assert (
            err.response["Error"]["Message"] == "The specified document does not exist."
        )

    try:
        response = client.get_document(Name="TestDocument3", DocumentVersion="3")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "GetDocument"
        assert (
            err.response["Error"]["Message"] == "The specified document does not exist."
        )

    # Updating default should update normal get
    client.update_document_default_version(Name="TestDocument3", DocumentVersion="2")

    response = client.get_document(Name="TestDocument3", DocumentFormat="JSON")
    _get_doc_validator(response, "NewBase", "2", new_json_doc, "JSON")


@mock_ssm
def test_delete_document():
    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)
    client = boto3.client("ssm", region_name="us-east-1")

    try:
        client.delete_document(Name="DNE")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "DeleteDocument"
        assert (
            err.response["Error"]["Message"] == "The specified document does not exist."
        )

    # Test simple
    client.create_document(
        Content=yaml.dump(json_doc),
        Name="TestDocument3",
        DocumentType="Command",
        DocumentFormat="YAML",
        VersionName="Base",
        TargetType="/AWS::EC2::Instance",
    )
    client.delete_document(Name="TestDocument3")

    try:
        client.get_document(Name="TestDocument3")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "GetDocument"
        assert (
            err.response["Error"]["Message"] == "The specified document does not exist."
        )

    # Delete default version with other version is bad
    client.create_document(
        Content=yaml.dump(json_doc),
        Name="TestDocument3",
        DocumentType="Command",
        DocumentFormat="YAML",
        VersionName="Base",
        TargetType="/AWS::EC2::Instance",
    )

    new_json_doc = copy.copy(json_doc)
    new_json_doc["description"] = "a new description"

    client.update_document(
        Content=json.dumps(new_json_doc),
        Name="TestDocument3",
        DocumentVersion="$LATEST",
        VersionName="NewBase",
    )

    new_json_doc["description"] = "a new description2"
    client.update_document(
        Content=json.dumps(new_json_doc),
        Name="TestDocument3",
        DocumentVersion="$LATEST",
    )

    new_json_doc["description"] = "a new description3"
    client.update_document(
        Content=json.dumps(new_json_doc),
        Name="TestDocument3",
        DocumentVersion="$LATEST",
    )

    new_json_doc["description"] = "a new description4"
    client.update_document(
        Content=json.dumps(new_json_doc),
        Name="TestDocument3",
        DocumentVersion="$LATEST",
    )

    try:
        client.delete_document(Name="TestDocument3", DocumentVersion="1")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "DeleteDocument"
        assert err.response["Error"]["Message"] == (
            "Default version of the document can't be deleted."
        )

    try:
        client.delete_document(Name="TestDocument3", VersionName="Base")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "DeleteDocument"
        assert err.response["Error"]["Message"] == (
            "Default version of the document can't be deleted."
        )

    # Make sure no ill side effects
    response = client.get_document(Name="TestDocument3")
    _get_doc_validator(response, "Base", "1", json_doc, "JSON")

    client.delete_document(Name="TestDocument3", DocumentVersion="5")

    # Check that latest version is changed
    response = client.describe_document(Name="TestDocument3")
    assert response["Document"]["LatestVersion"] == "4"

    client.delete_document(Name="TestDocument3", VersionName="NewBase")

    # Make sure other versions okay
    client.get_document(Name="TestDocument3", DocumentVersion="1")
    client.get_document(Name="TestDocument3", DocumentVersion="3")
    client.get_document(Name="TestDocument3", DocumentVersion="4")

    client.delete_document(Name="TestDocument3")

    try:
        client.get_document(Name="TestDocument3", DocumentVersion="1")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "GetDocument"
        assert (
            err.response["Error"]["Message"] == "The specified document does not exist."
        )

    try:
        client.get_document(Name="TestDocument3", DocumentVersion="3")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "GetDocument"
        assert (
            err.response["Error"]["Message"] == "The specified document does not exist."
        )

    try:
        client.get_document(Name="TestDocument3", DocumentVersion="4")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "GetDocument"
        assert (
            err.response["Error"]["Message"] == "The specified document does not exist."
        )

    response = client.list_documents()
    assert len(response["DocumentIdentifiers"]) == 0


@mock_ssm
def test_update_document_default_version():
    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)
    client = boto3.client("ssm", region_name="us-east-1")

    try:
        client.update_document_default_version(Name="DNE", DocumentVersion="1")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "UpdateDocumentDefaultVersion"
        assert (
            err.response["Error"]["Message"] == "The specified document does not exist."
        )

    client.create_document(
        Content=json.dumps(json_doc),
        Name="TestDocument",
        DocumentType="Command",
        VersionName="Base",
    )

    json_doc["description"] = "a new description"

    client.update_document(
        Content=json.dumps(json_doc),
        Name="TestDocument",
        DocumentVersion="$LATEST",
        DocumentFormat="JSON",
    )

    json_doc["description"] = "a new description2"

    client.update_document(
        Content=json.dumps(json_doc), Name="TestDocument", DocumentVersion="$LATEST"
    )

    response = client.update_document_default_version(
        Name="TestDocument", DocumentVersion="2"
    )
    assert response["Description"]["Name"] == "TestDocument"
    assert response["Description"]["DefaultVersion"] == "2"

    json_doc["description"] = "a new description3"

    client.update_document(
        Content=json.dumps(json_doc),
        Name="TestDocument",
        DocumentVersion="$LATEST",
        VersionName="NewBase",
    )

    response = client.update_document_default_version(
        Name="TestDocument", DocumentVersion="4"
    )
    assert response["Description"]["Name"] == "TestDocument"
    assert response["Description"]["DefaultVersion"] == "4"
    assert response["Description"]["DefaultVersionName"] == "NewBase"


@mock_ssm
def test_update_document():
    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)

    client = boto3.client("ssm", region_name="us-east-1")

    try:
        client.update_document(
            Name="DNE",
            Content=json.dumps(json_doc),
            DocumentVersion="1",
            DocumentFormat="JSON",
        )
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "UpdateDocument"
        assert (
            err.response["Error"]["Message"] == "The specified document does not exist."
        )

    client.create_document(
        Content=json.dumps(json_doc),
        Name="TestDocument",
        DocumentType="Command",
        DocumentFormat="JSON",
        VersionName="Base",
    )

    try:
        client.update_document(
            Name="TestDocument",
            Content=json.dumps(json_doc),
            DocumentVersion="2",
            DocumentFormat="JSON",
        )
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "UpdateDocument"
        assert err.response["Error"]["Message"] == (
            "The document version is not valid or does not exist."
        )

    # Duplicate content throws an error
    try:
        client.update_document(
            Content=json.dumps(json_doc),
            Name="TestDocument",
            DocumentVersion="1",
            DocumentFormat="JSON",
        )
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "UpdateDocument"
        assert err.response["Error"]["Message"] == (
            "The content of the association document matches another "
            "document. Change the content of the document and try again."
        )

    json_doc["description"] = "a new description"
    # Duplicate version name
    try:
        client.update_document(
            Content=json.dumps(json_doc),
            Name="TestDocument",
            DocumentVersion="1",
            DocumentFormat="JSON",
            VersionName="Base",
        )
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "UpdateDocument"
        assert err.response["Error"]["Message"] == (
            "The specified version name is a duplicate."
        )

    response = client.update_document(
        Content=json.dumps(json_doc),
        Name="TestDocument",
        VersionName="Base2",
        DocumentVersion="1",
        DocumentFormat="JSON",
    )
    assert response["DocumentDescription"]["Description"] == "a new description"
    assert response["DocumentDescription"]["DocumentVersion"] == "2"
    assert response["DocumentDescription"]["LatestVersion"] == "2"
    assert response["DocumentDescription"]["DefaultVersion"] == "1"

    json_doc["description"] = "a new description2"

    response = client.update_document(
        Content=json.dumps(json_doc),
        Name="TestDocument",
        DocumentVersion="$LATEST",
        DocumentFormat="JSON",
        VersionName="NewBase",
    )
    assert response["DocumentDescription"]["Description"] == "a new description2"
    assert response["DocumentDescription"]["DocumentVersion"] == "3"
    assert response["DocumentDescription"]["LatestVersion"] == "3"
    assert response["DocumentDescription"]["DefaultVersion"] == "1"
    assert response["DocumentDescription"]["VersionName"] == "NewBase"


@mock_ssm
def test_describe_document():
    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)
    client = boto3.client("ssm", region_name="us-east-1")

    try:
        client.describe_document(Name="DNE")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == "DescribeDocument"
        assert (
            err.response["Error"]["Message"] == "The specified document does not exist."
        )

    client.create_document(
        Content=yaml.dump(json_doc),
        Name="TestDocument",
        DocumentType="Command",
        DocumentFormat="YAML",
        VersionName="Base",
        TargetType="/AWS::EC2::Instance",
        Tags=[{"Key": "testing", "Value": "testingValue"}],
    )
    response = client.describe_document(Name="TestDocument")
    doc_description = response["Document"]
    _validate_document_description(
        "TestDocument", doc_description, json_doc, "1", "1", "1", "YAML"
    )

    # Adding update to check for issues
    new_json_doc = copy.copy(json_doc)
    new_json_doc["description"] = "a new description2"

    client.update_document(
        Content=json.dumps(new_json_doc), Name="TestDocument", DocumentVersion="$LATEST"
    )
    response = client.describe_document(Name="TestDocument")
    doc_description = response["Document"]
    _validate_document_description(
        "TestDocument", doc_description, json_doc, "1", "2", "1", "YAML"
    )


@mock_ssm
def test_list_documents():
    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)

    client = boto3.client("ssm", region_name="us-east-1")

    client.create_document(
        Content=json.dumps(json_doc),
        Name="TestDocument",
        DocumentType="Command",
        DocumentFormat="JSON",
    )
    client.create_document(
        Content=json.dumps(json_doc),
        Name="TestDocument2",
        DocumentType="Command",
        DocumentFormat="JSON",
    )
    client.create_document(
        Content=json.dumps(json_doc),
        Name="TestDocument3",
        DocumentType="Command",
        DocumentFormat="JSON",
        TargetType="/AWS::EC2::Instance",
    )

    response = client.list_documents()
    assert len(response["DocumentIdentifiers"]) == 3
    assert response["DocumentIdentifiers"][0]["Name"] == "TestDocument"
    assert response["DocumentIdentifiers"][1]["Name"] == "TestDocument2"
    assert response["DocumentIdentifiers"][2]["Name"] == "TestDocument3"
    assert response["NextToken"] == ""

    response = client.list_documents(MaxResults=1)
    assert len(response["DocumentIdentifiers"]) == 1
    assert response["DocumentIdentifiers"][0]["Name"] == "TestDocument"
    assert response["DocumentIdentifiers"][0]["DocumentVersion"] == "1"
    assert response["NextToken"] == "1"

    response = client.list_documents(MaxResults=1, NextToken=response["NextToken"])
    assert len(response["DocumentIdentifiers"]) == 1
    assert response["DocumentIdentifiers"][0]["Name"] == "TestDocument2"
    assert response["DocumentIdentifiers"][0]["DocumentVersion"] == "1"
    assert response["NextToken"] == "2"

    response = client.list_documents(MaxResults=1, NextToken=response["NextToken"])
    assert len(response["DocumentIdentifiers"]) == 1
    assert response["DocumentIdentifiers"][0]["Name"] == "TestDocument3"
    assert response["DocumentIdentifiers"][0]["DocumentVersion"] == "1"
    assert response["NextToken"] == ""

    # making sure no bad interactions with update
    json_doc["description"] = "a new description"
    client.update_document(
        Content=json.dumps(json_doc),
        Name="TestDocument",
        DocumentVersion="$LATEST",
        DocumentFormat="JSON",
    )

    client.update_document(
        Content=json.dumps(json_doc),
        Name="TestDocument2",
        DocumentVersion="$LATEST",
        DocumentFormat="JSON",
    )

    client.update_document_default_version(Name="TestDocument", DocumentVersion="2")

    response = client.list_documents()
    assert len(response["DocumentIdentifiers"]) == 3
    assert response["DocumentIdentifiers"][0]["Name"] == "TestDocument"
    assert response["DocumentIdentifiers"][0]["DocumentVersion"] == "2"

    assert response["DocumentIdentifiers"][1]["Name"] == "TestDocument2"
    assert response["DocumentIdentifiers"][1]["DocumentVersion"] == "1"

    assert response["DocumentIdentifiers"][2]["Name"] == "TestDocument3"
    assert response["DocumentIdentifiers"][2]["DocumentVersion"] == "1"
    assert response["NextToken"] == ""

    response = client.list_documents(Filters=[{"Key": "Owner", "Values": ["Self"]}])
    assert len(response["DocumentIdentifiers"]) == 3

    response = client.list_documents(
        Filters=[{"Key": "TargetType", "Values": ["/AWS::EC2::Instance"]}]
    )
    assert len(response["DocumentIdentifiers"]) == 1


@mock_ssm
def test_tags_in_list_tags_from_resource_document():
    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)

    client = boto3.client("ssm", region_name="us-east-1")

    client.create_document(
        Content=json.dumps(json_doc),
        Name="TestDocument",
        DocumentType="Command",
        DocumentFormat="JSON",
        Tags=[{"Key": "spam", "Value": "ham"}],
    )

    tags = client.list_tags_for_resource(
        ResourceId="TestDocument", ResourceType="Document"
    )
    assert tags.get("TagList") == [{"Key": "spam", "Value": "ham"}]

    client.delete_document(Name="TestDocument")

    with pytest.raises(ClientError) as ex:
        client.list_tags_for_resource(
            ResourceType="Document", ResourceId="TestDocument"
        )
    assert ex.value.response["Error"]["Code"] == "InvalidResourceId"
