import boto3
import botocore.exceptions
import sure  # noqa # pylint: disable=unused-import
import datetime
from datetime import timezone
import json
import yaml
import hashlib
import copy
import pkgutil
import pytest

from botocore.exceptions import ClientError

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
        doc_description["Hash"].should.equal(
            hashlib.sha256(json.dumps(json_doc).encode("utf-8")).hexdigest()
        )
    else:
        doc_description["Hash"].should.equal(
            hashlib.sha256(yaml.dump(json_doc).encode("utf-8")).hexdigest()
        )

    doc_description["HashType"].should.equal("Sha256")
    doc_description["Name"].should.equal(doc_name)
    doc_description["Owner"].should.equal(ACCOUNT_ID)

    difference = datetime.datetime.now(tz=timezone.utc) - doc_description["CreatedDate"]
    if difference.min > datetime.timedelta(minutes=1):
        assert False

    doc_description["Status"].should.equal("Active")
    doc_description["DocumentVersion"].should.equal(expected_document_version)
    doc_description["Description"].should.equal(json_doc["description"])

    doc_description["Parameters"] = sorted(
        doc_description["Parameters"], key=lambda doc: doc["Name"]
    )

    doc_description["Parameters"][0]["Name"].should.equal("Parameter1")
    doc_description["Parameters"][0]["Type"].should.equal("Integer")
    doc_description["Parameters"][0]["Description"].should.equal("Command Duration.")
    doc_description["Parameters"][0]["DefaultValue"].should.equal("3")

    doc_description["Parameters"][1]["Name"].should.equal("Parameter2")
    doc_description["Parameters"][1]["Type"].should.equal("String")
    doc_description["Parameters"][1]["DefaultValue"].should.equal("def")

    doc_description["Parameters"][2]["Name"].should.equal("Parameter3")
    doc_description["Parameters"][2]["Type"].should.equal("Boolean")
    doc_description["Parameters"][2]["Description"].should.equal("A boolean")
    doc_description["Parameters"][2]["DefaultValue"].should.equal("False")

    doc_description["Parameters"][3]["Name"].should.equal("Parameter4")
    doc_description["Parameters"][3]["Type"].should.equal("StringList")
    doc_description["Parameters"][3]["Description"].should.equal("A string list")
    doc_description["Parameters"][3]["DefaultValue"].should.equal('["abc", "def"]')

    doc_description["Parameters"][4]["Name"].should.equal("Parameter5")
    doc_description["Parameters"][4]["Type"].should.equal("StringMap")

    doc_description["Parameters"][5]["Name"].should.equal("Parameter6")
    doc_description["Parameters"][5]["Type"].should.equal("MapList")

    if expected_format == "JSON":
        # We have to replace single quotes from the response to package it back up
        json.loads(doc_description["Parameters"][4]["DefaultValue"]).should.equal(
            {
                "NotificationArn": "$dependency.topicArn",
                "NotificationEvents": ["Failed"],
                "NotificationType": "Command",
            }
        )

        json.loads(doc_description["Parameters"][5]["DefaultValue"]).should.equal(
            [
                {"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": "50"}},
                {"DeviceName": "/dev/sdm", "Ebs": {"VolumeSize": "100"}},
            ]
        )
    else:
        yaml.safe_load(doc_description["Parameters"][4]["DefaultValue"]).should.equal(
            {
                "NotificationArn": "$dependency.topicArn",
                "NotificationEvents": ["Failed"],
                "NotificationType": "Command",
            }
        )
        yaml.safe_load(doc_description["Parameters"][5]["DefaultValue"]).should.equal(
            [
                {"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": "50"}},
                {"DeviceName": "/dev/sdm", "Ebs": {"VolumeSize": "100"}},
            ]
        )

    doc_description["DocumentType"].should.equal("Command")
    doc_description["SchemaVersion"].should.equal("2.2")
    doc_description["LatestVersion"].should.equal(expected_latest_version)
    doc_description["DefaultVersion"].should.equal(expected_default_version)
    doc_description["DocumentFormat"].should.equal(expected_format)


def _get_doc_validator(
    response, version_name, doc_version, json_doc_content, document_format
):
    response["Name"].should.equal("TestDocument3")
    if version_name:
        response["VersionName"].should.equal(version_name)
    response["DocumentVersion"].should.equal(doc_version)
    response["Status"].should.equal("Active")
    if document_format == "JSON":
        json.loads(response["Content"]).should.equal(json_doc_content)
    else:
        yaml.safe_load(response["Content"]).should.equal(json_doc_content)
    response["DocumentType"].should.equal("Command")
    response["DocumentFormat"].should.equal(document_format)


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
    doc_description["VersionName"].should.equal("Base")
    doc_description["TargetType"].should.equal("/AWS::EC2::Instance")
    doc_description["Tags"].should.equal([{"Key": "testing", "Value": "testingValue"}])

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
        err.operation_name.should.equal("CreateDocument")
        err.response["Error"]["Message"].should.equal(
            "The specified document already exists."
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
        err.operation_name.should.equal("CreateDocument")
        err.response["Error"]["Message"].should.equal(
            "The content for the document is not valid."
        )

    del json_doc["parameters"]
    response = client.create_document(
        Content=yaml.dump(json_doc),
        Name="EmptyParamDoc",
        DocumentType="Command",
        DocumentFormat="YAML",
    )
    doc_description = response["DocumentDescription"]

    doc_description["Hash"].should.equal(
        hashlib.sha256(yaml.dump(json_doc).encode("utf-8")).hexdigest()
    )
    doc_description["HashType"].should.equal("Sha256")
    doc_description["Name"].should.equal("EmptyParamDoc")
    doc_description["Owner"].should.equal(ACCOUNT_ID)

    difference = datetime.datetime.now(tz=timezone.utc) - doc_description["CreatedDate"]
    if difference.min > datetime.timedelta(minutes=1):
        assert False

    doc_description["Status"].should.equal("Active")
    doc_description["DocumentVersion"].should.equal("1")
    doc_description["Description"].should.equal(json_doc["description"])
    doc_description["DocumentType"].should.equal("Command")
    doc_description["SchemaVersion"].should.equal("2.2")
    doc_description["LatestVersion"].should.equal("1")
    doc_description["DefaultVersion"].should.equal("1")
    doc_description["DocumentFormat"].should.equal("YAML")


@mock_ssm
def test_get_document():
    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)

    client = boto3.client("ssm", region_name="us-east-1")

    try:
        client.get_document(Name="DNE")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        err.operation_name.should.equal("GetDocument")
        err.response["Error"]["Message"].should.equal(
            "The specified document does not exist."
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
        err.operation_name.should.equal("GetDocument")
        err.response["Error"]["Message"].should.equal(
            "The specified document does not exist."
        )

    try:
        response = client.get_document(Name="TestDocument3", DocumentVersion="3")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        err.operation_name.should.equal("GetDocument")
        err.response["Error"]["Message"].should.equal(
            "The specified document does not exist."
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
        err.operation_name.should.equal("DeleteDocument")
        err.response["Error"]["Message"].should.equal(
            "The specified document does not exist."
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
        err.operation_name.should.equal("GetDocument")
        err.response["Error"]["Message"].should.equal(
            "The specified document does not exist."
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
        err.operation_name.should.equal("DeleteDocument")
        err.response["Error"]["Message"].should.equal(
            "Default version of the document can't be deleted."
        )

    try:
        client.delete_document(Name="TestDocument3", VersionName="Base")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        err.operation_name.should.equal("DeleteDocument")
        err.response["Error"]["Message"].should.equal(
            "Default version of the document can't be deleted."
        )

    # Make sure no ill side effects
    response = client.get_document(Name="TestDocument3")
    _get_doc_validator(response, "Base", "1", json_doc, "JSON")

    client.delete_document(Name="TestDocument3", DocumentVersion="5")

    # Check that latest version is changed
    response = client.describe_document(Name="TestDocument3")
    response["Document"]["LatestVersion"].should.equal("4")

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
        err.operation_name.should.equal("GetDocument")
        err.response["Error"]["Message"].should.equal(
            "The specified document does not exist."
        )

    try:
        client.get_document(Name="TestDocument3", DocumentVersion="3")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        err.operation_name.should.equal("GetDocument")
        err.response["Error"]["Message"].should.equal(
            "The specified document does not exist."
        )

    try:
        client.get_document(Name="TestDocument3", DocumentVersion="4")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        err.operation_name.should.equal("GetDocument")
        err.response["Error"]["Message"].should.equal(
            "The specified document does not exist."
        )

    response = client.list_documents()
    len(response["DocumentIdentifiers"]).should.equal(0)


@mock_ssm
def test_update_document_default_version():
    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)
    client = boto3.client("ssm", region_name="us-east-1")

    try:
        client.update_document_default_version(Name="DNE", DocumentVersion="1")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        err.operation_name.should.equal("UpdateDocumentDefaultVersion")
        err.response["Error"]["Message"].should.equal(
            "The specified document does not exist."
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
    response["Description"]["Name"].should.equal("TestDocument")
    response["Description"]["DefaultVersion"].should.equal("2")

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
    response["Description"]["Name"].should.equal("TestDocument")
    response["Description"]["DefaultVersion"].should.equal("4")
    response["Description"]["DefaultVersionName"].should.equal("NewBase")


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
        err.operation_name.should.equal("UpdateDocument")
        err.response["Error"]["Message"].should.equal(
            "The specified document does not exist."
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
        err.operation_name.should.equal("UpdateDocument")
        err.response["Error"]["Message"].should.equal(
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
        err.operation_name.should.equal("UpdateDocument")
        err.response["Error"]["Message"].should.equal(
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
        err.operation_name.should.equal("UpdateDocument")
        err.response["Error"]["Message"].should.equal(
            "The specified version name is a duplicate."
        )

    response = client.update_document(
        Content=json.dumps(json_doc),
        Name="TestDocument",
        VersionName="Base2",
        DocumentVersion="1",
        DocumentFormat="JSON",
    )
    response["DocumentDescription"]["Description"].should.equal("a new description")
    response["DocumentDescription"]["DocumentVersion"].should.equal("2")
    response["DocumentDescription"]["LatestVersion"].should.equal("2")
    response["DocumentDescription"]["DefaultVersion"].should.equal("1")

    json_doc["description"] = "a new description2"

    response = client.update_document(
        Content=json.dumps(json_doc),
        Name="TestDocument",
        DocumentVersion="$LATEST",
        DocumentFormat="JSON",
        VersionName="NewBase",
    )
    response["DocumentDescription"]["Description"].should.equal("a new description2")
    response["DocumentDescription"]["DocumentVersion"].should.equal("3")
    response["DocumentDescription"]["LatestVersion"].should.equal("3")
    response["DocumentDescription"]["DefaultVersion"].should.equal("1")
    response["DocumentDescription"]["VersionName"].should.equal("NewBase")


@mock_ssm
def test_describe_document():
    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)
    client = boto3.client("ssm", region_name="us-east-1")

    try:
        client.describe_document(Name="DNE")
        raise RuntimeError("Should fail")
    except botocore.exceptions.ClientError as err:
        err.operation_name.should.equal("DescribeDocument")
        err.response["Error"]["Message"].should.equal(
            "The specified document does not exist."
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
    len(response["DocumentIdentifiers"]).should.equal(3)
    response["DocumentIdentifiers"][0]["Name"].should.equal("TestDocument")
    response["DocumentIdentifiers"][1]["Name"].should.equal("TestDocument2")
    response["DocumentIdentifiers"][2]["Name"].should.equal("TestDocument3")
    response["NextToken"].should.equal("")

    response = client.list_documents(MaxResults=1)
    len(response["DocumentIdentifiers"]).should.equal(1)
    response["DocumentIdentifiers"][0]["Name"].should.equal("TestDocument")
    response["DocumentIdentifiers"][0]["DocumentVersion"].should.equal("1")
    response["NextToken"].should.equal("1")

    response = client.list_documents(MaxResults=1, NextToken=response["NextToken"])
    len(response["DocumentIdentifiers"]).should.equal(1)
    response["DocumentIdentifiers"][0]["Name"].should.equal("TestDocument2")
    response["DocumentIdentifiers"][0]["DocumentVersion"].should.equal("1")
    response["NextToken"].should.equal("2")

    response = client.list_documents(MaxResults=1, NextToken=response["NextToken"])
    len(response["DocumentIdentifiers"]).should.equal(1)
    response["DocumentIdentifiers"][0]["Name"].should.equal("TestDocument3")
    response["DocumentIdentifiers"][0]["DocumentVersion"].should.equal("1")
    response["NextToken"].should.equal("")

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
    len(response["DocumentIdentifiers"]).should.equal(3)
    response["DocumentIdentifiers"][0]["Name"].should.equal("TestDocument")
    response["DocumentIdentifiers"][0]["DocumentVersion"].should.equal("2")

    response["DocumentIdentifiers"][1]["Name"].should.equal("TestDocument2")
    response["DocumentIdentifiers"][1]["DocumentVersion"].should.equal("1")

    response["DocumentIdentifiers"][2]["Name"].should.equal("TestDocument3")
    response["DocumentIdentifiers"][2]["DocumentVersion"].should.equal("1")
    response["NextToken"].should.equal("")

    response = client.list_documents(Filters=[{"Key": "Owner", "Values": ["Self"]}])
    len(response["DocumentIdentifiers"]).should.equal(3)

    response = client.list_documents(
        Filters=[{"Key": "TargetType", "Values": ["/AWS::EC2::Instance"]}]
    )
    len(response["DocumentIdentifiers"]).should.equal(1)


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
