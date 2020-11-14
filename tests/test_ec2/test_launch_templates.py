import boto3
import sure  # noqa

import pytest
from botocore.client import ClientError

from moto import mock_ec2


@mock_ec2
def test_launch_template_create():
    cli = boto3.client("ec2", region_name="us-east-1")

    resp = cli.create_launch_template(
        LaunchTemplateName="test-template",
        # the absolute minimum needed to create a template without other resources
        LaunchTemplateData={
            "TagSpecifications": [
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": "test", "Value": "value"}],
                }
            ]
        },
    )

    resp.should.have.key("LaunchTemplate")
    lt = resp["LaunchTemplate"]
    lt["LaunchTemplateName"].should.equal("test-template")
    lt["DefaultVersionNumber"].should.equal(1)
    lt["LatestVersionNumber"].should.equal(1)

    with pytest.raises(ClientError) as ex:
        cli.create_launch_template(
            LaunchTemplateName="test-template",
            LaunchTemplateData={
                "TagSpecifications": [
                    {
                        "ResourceType": "instance",
                        "Tags": [{"Key": "test", "Value": "value"}],
                    }
                ]
            },
        )

    str(ex.value).should.equal(
        "An error occurred (InvalidLaunchTemplateName.AlreadyExistsException) when calling the CreateLaunchTemplate operation: Launch template name already in use."
    )


@mock_ec2
def test_describe_launch_template_versions():
    template_data = {
        "ImageId": "ami-abc123",
        "DisableApiTermination": False,
        "TagSpecifications": [
            {"ResourceType": "instance", "Tags": [{"Key": "test", "Value": "value"}]}
        ],
        "SecurityGroupIds": ["sg-1234", "sg-ab5678"],
    }

    cli = boto3.client("ec2", region_name="us-east-1")

    create_resp = cli.create_launch_template(
        LaunchTemplateName="test-template", LaunchTemplateData=template_data
    )

    # test using name
    resp = cli.describe_launch_template_versions(
        LaunchTemplateName="test-template", Versions=["1"]
    )

    templ = resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]
    templ.should.equal(template_data)

    # test using id
    resp = cli.describe_launch_template_versions(
        LaunchTemplateId=create_resp["LaunchTemplate"]["LaunchTemplateId"],
        Versions=["1"],
    )

    templ = resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]
    templ.should.equal(template_data)


@mock_ec2
def test_create_launch_template_version():
    cli = boto3.client("ec2", region_name="us-east-1")

    create_resp = cli.create_launch_template(
        LaunchTemplateName="test-template", LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    version_resp = cli.create_launch_template_version(
        LaunchTemplateName="test-template",
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    version_resp.should.have.key("LaunchTemplateVersion")
    version = version_resp["LaunchTemplateVersion"]
    version["DefaultVersion"].should.equal(False)
    version["LaunchTemplateId"].should.equal(
        create_resp["LaunchTemplate"]["LaunchTemplateId"]
    )
    version["VersionDescription"].should.equal("new ami")
    version["VersionNumber"].should.equal(2)


@mock_ec2
def test_create_launch_template_version_by_id():
    cli = boto3.client("ec2", region_name="us-east-1")

    create_resp = cli.create_launch_template(
        LaunchTemplateName="test-template", LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    version_resp = cli.create_launch_template_version(
        LaunchTemplateId=create_resp["LaunchTemplate"]["LaunchTemplateId"],
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    version_resp.should.have.key("LaunchTemplateVersion")
    version = version_resp["LaunchTemplateVersion"]
    version["DefaultVersion"].should.equal(False)
    version["LaunchTemplateId"].should.equal(
        create_resp["LaunchTemplate"]["LaunchTemplateId"]
    )
    version["VersionDescription"].should.equal("new ami")
    version["VersionNumber"].should.equal(2)


@mock_ec2
def test_describe_launch_template_versions_with_multiple_versions():
    cli = boto3.client("ec2", region_name="us-east-1")

    cli.create_launch_template(
        LaunchTemplateName="test-template", LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    cli.create_launch_template_version(
        LaunchTemplateName="test-template",
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    resp = cli.describe_launch_template_versions(LaunchTemplateName="test-template")

    resp["LaunchTemplateVersions"].should.have.length_of(2)
    resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]["ImageId"].should.equal(
        "ami-abc123"
    )
    resp["LaunchTemplateVersions"][1]["LaunchTemplateData"]["ImageId"].should.equal(
        "ami-def456"
    )


@mock_ec2
def test_describe_launch_template_versions_with_versions_option():
    cli = boto3.client("ec2", region_name="us-east-1")

    cli.create_launch_template(
        LaunchTemplateName="test-template", LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    cli.create_launch_template_version(
        LaunchTemplateName="test-template",
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    cli.create_launch_template_version(
        LaunchTemplateName="test-template",
        LaunchTemplateData={"ImageId": "ami-hij789"},
        VersionDescription="new ami, again",
    )

    resp = cli.describe_launch_template_versions(
        LaunchTemplateName="test-template", Versions=["2", "3"]
    )

    resp["LaunchTemplateVersions"].should.have.length_of(2)
    resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]["ImageId"].should.equal(
        "ami-def456"
    )
    resp["LaunchTemplateVersions"][1]["LaunchTemplateData"]["ImageId"].should.equal(
        "ami-hij789"
    )


@mock_ec2
def test_describe_launch_template_versions_with_min():
    cli = boto3.client("ec2", region_name="us-east-1")

    cli.create_launch_template(
        LaunchTemplateName="test-template", LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    cli.create_launch_template_version(
        LaunchTemplateName="test-template",
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    cli.create_launch_template_version(
        LaunchTemplateName="test-template",
        LaunchTemplateData={"ImageId": "ami-hij789"},
        VersionDescription="new ami, again",
    )

    resp = cli.describe_launch_template_versions(
        LaunchTemplateName="test-template", MinVersion="2"
    )

    resp["LaunchTemplateVersions"].should.have.length_of(2)
    resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]["ImageId"].should.equal(
        "ami-def456"
    )
    resp["LaunchTemplateVersions"][1]["LaunchTemplateData"]["ImageId"].should.equal(
        "ami-hij789"
    )


@mock_ec2
def test_describe_launch_template_versions_with_max():
    cli = boto3.client("ec2", region_name="us-east-1")

    cli.create_launch_template(
        LaunchTemplateName="test-template", LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    cli.create_launch_template_version(
        LaunchTemplateName="test-template",
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    cli.create_launch_template_version(
        LaunchTemplateName="test-template",
        LaunchTemplateData={"ImageId": "ami-hij789"},
        VersionDescription="new ami, again",
    )

    resp = cli.describe_launch_template_versions(
        LaunchTemplateName="test-template", MaxVersion="2"
    )

    resp["LaunchTemplateVersions"].should.have.length_of(2)
    resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]["ImageId"].should.equal(
        "ami-abc123"
    )
    resp["LaunchTemplateVersions"][1]["LaunchTemplateData"]["ImageId"].should.equal(
        "ami-def456"
    )


@mock_ec2
def test_describe_launch_template_versions_with_min_and_max():
    cli = boto3.client("ec2", region_name="us-east-1")

    cli.create_launch_template(
        LaunchTemplateName="test-template", LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    cli.create_launch_template_version(
        LaunchTemplateName="test-template",
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    cli.create_launch_template_version(
        LaunchTemplateName="test-template",
        LaunchTemplateData={"ImageId": "ami-hij789"},
        VersionDescription="new ami, again",
    )

    cli.create_launch_template_version(
        LaunchTemplateName="test-template",
        LaunchTemplateData={"ImageId": "ami-345abc"},
        VersionDescription="new ami, because why not",
    )

    resp = cli.describe_launch_template_versions(
        LaunchTemplateName="test-template", MinVersion="2", MaxVersion="3"
    )

    resp["LaunchTemplateVersions"].should.have.length_of(2)
    resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]["ImageId"].should.equal(
        "ami-def456"
    )
    resp["LaunchTemplateVersions"][1]["LaunchTemplateData"]["ImageId"].should.equal(
        "ami-hij789"
    )


@mock_ec2
def test_describe_launch_templates():
    cli = boto3.client("ec2", region_name="us-east-1")

    lt_ids = []
    r = cli.create_launch_template(
        LaunchTemplateName="test-template", LaunchTemplateData={"ImageId": "ami-abc123"}
    )
    lt_ids.append(r["LaunchTemplate"]["LaunchTemplateId"])

    r = cli.create_launch_template(
        LaunchTemplateName="test-template2",
        LaunchTemplateData={"ImageId": "ami-abc123"},
    )
    lt_ids.append(r["LaunchTemplate"]["LaunchTemplateId"])

    # general call, all templates
    resp = cli.describe_launch_templates()
    resp.should.have.key("LaunchTemplates")
    resp["LaunchTemplates"].should.have.length_of(2)
    resp["LaunchTemplates"][0]["LaunchTemplateName"].should.equal("test-template")
    resp["LaunchTemplates"][1]["LaunchTemplateName"].should.equal("test-template2")

    # filter by names
    resp = cli.describe_launch_templates(
        LaunchTemplateNames=["test-template2", "test-template"]
    )
    resp.should.have.key("LaunchTemplates")
    resp["LaunchTemplates"].should.have.length_of(2)
    resp["LaunchTemplates"][0]["LaunchTemplateName"].should.equal("test-template2")
    resp["LaunchTemplates"][1]["LaunchTemplateName"].should.equal("test-template")

    # filter by ids
    resp = cli.describe_launch_templates(LaunchTemplateIds=lt_ids)
    resp.should.have.key("LaunchTemplates")
    resp["LaunchTemplates"].should.have.length_of(2)
    resp["LaunchTemplates"][0]["LaunchTemplateName"].should.equal("test-template")
    resp["LaunchTemplates"][1]["LaunchTemplateName"].should.equal("test-template2")


@mock_ec2
def test_describe_launch_templates_with_filters():
    cli = boto3.client("ec2", region_name="us-east-1")

    r = cli.create_launch_template(
        LaunchTemplateName="test-template", LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    cli.create_tags(
        Resources=[r["LaunchTemplate"]["LaunchTemplateId"]],
        Tags=[
            {"Key": "tag1", "Value": "a value"},
            {"Key": "another-key", "Value": "this value"},
        ],
    )

    cli.create_launch_template(
        LaunchTemplateName="no-tags", LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    resp = cli.describe_launch_templates(
        Filters=[{"Name": "tag:tag1", "Values": ["a value"]}]
    )

    resp["LaunchTemplates"].should.have.length_of(1)
    resp["LaunchTemplates"][0]["LaunchTemplateName"].should.equal("test-template")

    resp = cli.describe_launch_templates(
        Filters=[{"Name": "launch-template-name", "Values": ["no-tags"]}]
    )
    resp["LaunchTemplates"].should.have.length_of(1)
    resp["LaunchTemplates"][0]["LaunchTemplateName"].should.equal("no-tags")


@mock_ec2
def test_create_launch_template_with_tag_spec():
    cli = boto3.client("ec2", region_name="us-east-1")

    cli.create_launch_template(
        LaunchTemplateName="test-template",
        LaunchTemplateData={"ImageId": "ami-abc123"},
        TagSpecifications=[
            {"ResourceType": "instance", "Tags": [{"Key": "key", "Value": "value"}]}
        ],
    )

    resp = cli.describe_launch_template_versions(
        LaunchTemplateName="test-template", Versions=["1"]
    )
    version = resp["LaunchTemplateVersions"][0]

    version["LaunchTemplateData"].should.have.key("TagSpecifications")
    version["LaunchTemplateData"]["TagSpecifications"].should.have.length_of(1)
    version["LaunchTemplateData"]["TagSpecifications"][0].should.equal(
        {"ResourceType": "instance", "Tags": [{"Key": "key", "Value": "value"}]}
    )
