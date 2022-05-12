import boto3
import sure  # noqa # pylint: disable=unused-import

import pytest
from botocore.client import ClientError

from moto import mock_ec2, settings
from uuid import uuid4


@mock_ec2
def test_launch_template_create():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())
    resp = cli.create_launch_template(
        LaunchTemplateName=template_name,
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
    lt["LaunchTemplateName"].should.equal(template_name)
    lt["DefaultVersionNumber"].should.equal(1)
    lt["LatestVersionNumber"].should.equal(1)

    with pytest.raises(ClientError) as ex:
        cli.create_launch_template(
            LaunchTemplateName=template_name,
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

    template_name = str(uuid4())
    create_resp = cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData=template_data
    )

    # test using name
    resp = cli.describe_launch_template_versions(
        LaunchTemplateName=template_name, Versions=["1"]
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

    template_name = str(uuid4())
    create_resp = cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    version_resp = cli.create_launch_template_version(
        LaunchTemplateName=template_name,
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

    template_name = str(uuid4())
    create_resp = cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
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

    template_name = str(uuid4())
    cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    resp = cli.describe_launch_template_versions(LaunchTemplateName=template_name)

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

    template_name = str(uuid4())
    cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-hij789"},
        VersionDescription="new ami, again",
    )

    resp = cli.describe_launch_template_versions(
        LaunchTemplateName=template_name, Versions=["2", "3"]
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

    template_name = str(uuid4())
    cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-hij789"},
        VersionDescription="new ami, again",
    )

    resp = cli.describe_launch_template_versions(
        LaunchTemplateName=template_name, MinVersion="2"
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

    template_name = str(uuid4())
    cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-hij789"},
        VersionDescription="new ami, again",
    )

    resp = cli.describe_launch_template_versions(
        LaunchTemplateName=template_name, MaxVersion="2"
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

    template_name = str(uuid4())
    cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-hij789"},
        VersionDescription="new ami, again",
    )

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-345abc"},
        VersionDescription="new ami, because why not",
    )

    resp = cli.describe_launch_template_versions(
        LaunchTemplateName=template_name, MinVersion="2", MaxVersion="3"
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
    template_name = str(uuid4())
    r = cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )
    lt_ids.append(r["LaunchTemplate"]["LaunchTemplateId"])

    template_name2 = str(uuid4())
    r = cli.create_launch_template(
        LaunchTemplateName=template_name2, LaunchTemplateData={"ImageId": "ami-abc123"}
    )
    lt_ids.append(r["LaunchTemplate"]["LaunchTemplateId"])

    # general call, all templates
    if not settings.TEST_SERVER_MODE:
        # Bug: Only 15 launch templates are returned, ever
        # ServerMode may have many more templates, created in parallel
        all_templates = retrieve_all_templates(cli)
        my_templates = [t for t in all_templates if t["LaunchTemplateId"] in lt_ids]
        my_templates[0]["LaunchTemplateName"].should.equal(template_name)
        my_templates[1]["LaunchTemplateName"].should.equal(template_name2)

    # filter by names
    resp = cli.describe_launch_templates(
        LaunchTemplateNames=[template_name2, template_name]
    )
    resp.should.have.key("LaunchTemplates")
    resp["LaunchTemplates"].should.have.length_of(2)
    resp["LaunchTemplates"][0]["LaunchTemplateName"].should.equal(template_name2)
    resp["LaunchTemplates"][1]["LaunchTemplateName"].should.equal(template_name)

    # filter by ids
    resp = cli.describe_launch_templates(LaunchTemplateIds=lt_ids)
    resp.should.have.key("LaunchTemplates")
    resp["LaunchTemplates"].should.have.length_of(2)
    resp["LaunchTemplates"][0]["LaunchTemplateName"].should.equal(template_name)
    resp["LaunchTemplates"][1]["LaunchTemplateName"].should.equal(template_name2)


@mock_ec2
def test_describe_launch_templates_with_filters():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())
    r = cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    tag_value = str(uuid4())
    cli.create_tags(
        Resources=[r["LaunchTemplate"]["LaunchTemplateId"]],
        Tags=[
            {"Key": "tag1", "Value": tag_value},
            {"Key": "another-key", "Value": "this value"},
        ],
    )

    template_name_no_tags = str(uuid4())
    cli.create_launch_template(
        LaunchTemplateName=template_name_no_tags,
        LaunchTemplateData={"ImageId": "ami-abc123"},
    )

    resp = cli.describe_launch_templates(
        Filters=[{"Name": "tag:tag1", "Values": [tag_value]}]
    )

    resp["LaunchTemplates"].should.have.length_of(1)
    resp["LaunchTemplates"][0]["LaunchTemplateName"].should.equal(template_name)

    resp = cli.describe_launch_templates(
        Filters=[{"Name": "launch-template-name", "Values": [template_name_no_tags]}]
    )
    resp["LaunchTemplates"].should.have.length_of(1)
    resp["LaunchTemplates"][0]["LaunchTemplateName"].should.equal(template_name_no_tags)


@mock_ec2
def test_create_launch_template_with_tag_spec():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())
    cli.create_launch_template(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-abc123"},
        TagSpecifications=[
            {"ResourceType": "instance", "Tags": [{"Key": "key", "Value": "value"}]}
        ],
    )

    resp = cli.describe_launch_template_versions(
        LaunchTemplateName=template_name, Versions=["1"]
    )
    version = resp["LaunchTemplateVersions"][0]

    version["LaunchTemplateData"].should.have.key("TagSpecifications")
    version["LaunchTemplateData"]["TagSpecifications"].should.have.length_of(1)
    version["LaunchTemplateData"]["TagSpecifications"][0].should.equal(
        {"ResourceType": "instance", "Tags": [{"Key": "key", "Value": "value"}]}
    )


@mock_ec2
def test_delete_launch_template__dryrun():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())
    cli.create_launch_template(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-abc123"},
        TagSpecifications=[
            {"ResourceType": "instance", "Tags": [{"Key": "key", "Value": "value"}]}
        ],
    )

    cli.describe_launch_templates(LaunchTemplateNames=[template_name])[
        "LaunchTemplates"
    ].should.have.length_of(1)

    with pytest.raises(ClientError) as exc:
        cli.delete_launch_template(DryRun=True, LaunchTemplateName=template_name)
    err = exc.value.response["Error"]
    err.should.have.key("Code").equals("DryRunOperation")

    # Template still exists
    cli.describe_launch_templates(LaunchTemplateNames=[template_name])[
        "LaunchTemplates"
    ].should.have.length_of(1)


@mock_ec2
def test_delete_launch_template__by_name():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())
    cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    cli.describe_launch_templates(LaunchTemplateNames=[template_name])[
        "LaunchTemplates"
    ].should.have.length_of(1)

    cli.delete_launch_template(LaunchTemplateName=template_name)

    cli.describe_launch_templates(LaunchTemplateNames=[template_name])[
        "LaunchTemplates"
    ].should.have.length_of(0)


@mock_ec2
def test_delete_launch_template__by_id():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())
    template_id = cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )["LaunchTemplate"]["LaunchTemplateId"]

    cli.describe_launch_templates(LaunchTemplateNames=[template_name])[
        "LaunchTemplates"
    ].should.have.length_of(1)

    cli.delete_launch_template(LaunchTemplateId=template_id)

    cli.describe_launch_templates(LaunchTemplateNames=[template_name])[
        "LaunchTemplates"
    ].should.have.length_of(0)


def retrieve_all_templates(client, filters=[]):  # pylint: disable=W0102
    resp = client.describe_launch_templates(Filters=filters)
    all_templates = resp["LaunchTemplates"]
    next_token = resp.get("NextToken")
    while next_token:
        resp = client.describe_launch_templates(Filters=filters, NextToken=next_token)
        all_templates.extend(resp["LaunchTemplates"])
        next_token = resp.get("NextToken")
    return all_templates
