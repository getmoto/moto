from functools import wraps
from uuid import uuid4

import boto3
import pytest
from botocore.client import ClientError

from moto import mock_aws, settings
from tests import EXAMPLE_AMI_ID, allow_aws_request, aws_verified

from .helpers import assert_dryrun_error

MINIMAL_LAUNCH_TEMPLATE_DATE = {
    "TagSpecifications": [
        {
            "ResourceType": "instance",
            "Tags": [{"Key": "test", "Value": "value"}],
        }
    ]
}


def ec2_launch_template_aws_verified(
    launch_template_data: dict = MINIMAL_LAUNCH_TEMPLATE_DATE,
    pass_creation_response: bool = False,
):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.

    This decorator will:
      - Create a launch template
      - Run the test and pass the name as an argument
      - Delete the launch template
    """

    def inner(func):
        @wraps(func)
        def pagination_wrapper(**kwargs):
            template_name = str(uuid4())

            def create_launch_template_and_test():
                client = boto3.client("ec2", region_name="us-east-1")

                creation = client.create_launch_template(
                    LaunchTemplateName=template_name,
                    LaunchTemplateData=launch_template_data,
                )
                kwargs["template_name"] = template_name
                if pass_creation_response:
                    kwargs["creation"] = creation
                try:
                    resp = func(**kwargs)
                finally:
                    client.delete_launch_template(LaunchTemplateName=template_name)

                return resp

            if allow_aws_request():
                return create_launch_template_and_test()
            else:
                with mock_aws():
                    return create_launch_template_and_test()

        return pagination_wrapper

    return inner


@ec2_launch_template_aws_verified(pass_creation_response=True)
@pytest.mark.aws_verified
def test_launch_template_create(template_name=None, creation=None):
    cli = boto3.client("ec2", region_name="us-east-1")

    assert "LaunchTemplate" in creation
    lt = creation["LaunchTemplate"]
    assert lt["LaunchTemplateName"] == template_name
    assert lt["DefaultVersionNumber"] == 1
    assert lt["LatestVersionNumber"] == 1

    with pytest.raises(ClientError) as ex:
        cli.create_launch_template(
            LaunchTemplateName=template_name,
            LaunchTemplateData=MINIMAL_LAUNCH_TEMPLATE_DATE,
        )

    assert (
        str(ex.value)
        == "An error occurred (InvalidLaunchTemplateName.AlreadyExistsException) when calling the CreateLaunchTemplate operation: Launch template name already in use."
    )


@mock_aws
def test_create_launch_template__dryrun():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        cli.create_launch_template(
            DryRun=True,
            LaunchTemplateName=template_name,
            LaunchTemplateData={"ImageId": "ami-abc123"},
            TagSpecifications=[
                {"ResourceType": "instance", "Tags": [{"Key": "key", "Value": "value"}]}
            ],
        )
    assert_dryrun_error(exc)


@ec2_launch_template_aws_verified(pass_creation_response=True)
@pytest.mark.aws_verified
def test_describe_launch_template_versions(template_name=None, creation=None):
    cli = boto3.client("ec2", region_name="us-east-1")

    # test using name
    resp = cli.describe_launch_template_versions(
        LaunchTemplateName=template_name, Versions=["1"]
    )

    templ = resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]
    assert templ == MINIMAL_LAUNCH_TEMPLATE_DATE

    # test using id
    resp = cli.describe_launch_template_versions(
        LaunchTemplateId=creation["LaunchTemplate"]["LaunchTemplateId"],
        Versions=["1"],
    )

    templ = resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]
    assert templ == MINIMAL_LAUNCH_TEMPLATE_DATE

    # test using $Latest version
    resp = cli.describe_launch_template_versions(
        LaunchTemplateName=template_name, Versions=["$Latest"]
    )

    templ = resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]
    assert templ == MINIMAL_LAUNCH_TEMPLATE_DATE

    # test using $Default version
    resp = cli.describe_launch_template_versions(
        LaunchTemplateName=template_name, Versions=["$Default"]
    )

    templ = resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]
    assert templ == MINIMAL_LAUNCH_TEMPLATE_DATE


@mock_aws
def test_describe_launch_template_versions_by_name_when_absent():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = "foo"

    # test using name
    with pytest.raises(
        ClientError,
        match=f"The specified launch template, with template name {template_name}, does not exist",
    ):
        cli.describe_launch_template_versions(LaunchTemplateName=template_name)

    # test default response
    resp = cli.describe_launch_template_versions()
    assert resp["LaunchTemplateVersions"] == []

    # test using $Latest version
    resp = cli.describe_launch_template_versions(Versions=["$Latest"])
    assert resp["LaunchTemplateVersions"] == []


@ec2_launch_template_aws_verified(pass_creation_response=True)
@pytest.mark.aws_verified
def test_create_launch_template_version(template_name=None, creation=None):
    cli = boto3.client("ec2", region_name="us-east-1")

    launch_template_id = creation["LaunchTemplate"]["LaunchTemplateId"]
    version_resp = cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    assert "LaunchTemplateVersion" in version_resp
    version = version_resp["LaunchTemplateVersion"]
    assert version["DefaultVersion"] is False
    assert version["LaunchTemplateId"] == launch_template_id
    assert version["VersionDescription"] == "new ami"
    assert version["VersionNumber"] == 2
    assert version["LaunchTemplateData"] == {"ImageId": "ami-def456"}


@mock_aws
def test_create_launch_template_version__dryrun():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())
    cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    with pytest.raises(ClientError) as exc:
        cli.create_launch_template_version(
            DryRun=True,
            LaunchTemplateName=template_name,
            LaunchTemplateData={"ImageId": "ami-def456"},
            VersionDescription="new ami",
        )
    assert_dryrun_error(exc)


@ec2_launch_template_aws_verified(pass_creation_response=True)
@pytest.mark.aws_verified
def test_create_launch_template_version_by_id(template_name=None, creation=None):
    cli = boto3.client("ec2", region_name="us-east-1")

    launch_template_id = creation["LaunchTemplate"]["LaunchTemplateId"]

    version_resp = cli.create_launch_template_version(
        LaunchTemplateId=launch_template_id,
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    assert "LaunchTemplateVersion" in version_resp
    version = version_resp["LaunchTemplateVersion"]
    assert version["DefaultVersion"] is False
    assert version["LaunchTemplateId"] == launch_template_id
    assert version["VersionDescription"] == "new ami"
    assert version["VersionNumber"] == 2


@ec2_launch_template_aws_verified()
@pytest.mark.aws_verified
def test_describe_launch_template_versions_with_multiple_versions(template_name=None):
    cli = boto3.client("ec2", region_name="us-east-1")

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    versions = cli.describe_launch_template_versions(LaunchTemplateName=template_name)[
        "LaunchTemplateVersions"
    ]

    assert len(versions) == 2
    version1 = next(v for v in versions if v["VersionNumber"] == 1)
    version2 = next(v for v in versions if v["VersionNumber"] == 2)

    assert version1["LaunchTemplateId"] == version2["LaunchTemplateId"]
    assert version1["LaunchTemplateName"] == template_name
    assert version1["LaunchTemplateName"] == version2["LaunchTemplateName"]

    assert version1["LaunchTemplateData"] == MINIMAL_LAUNCH_TEMPLATE_DATE
    assert version2["LaunchTemplateData"] == {"ImageId": "ami-def456"}

    assert version1["DefaultVersion"] is True
    assert version2["DefaultVersion"] is False


@ec2_launch_template_aws_verified()
@pytest.mark.aws_verified
def test_describe_launch_template_versions_with_versions_option(
    valid_ami, template_name=None
):
    cli = boto3.client("ec2", region_name="us-east-1")

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-def456"},
        VersionDescription="new ami",
    )

    cli.create_launch_template_version(
        LaunchTemplateName=template_name,
        # AWS will happily accept a fake AMI for the first version
        # But passing in a fake AMI for the second version, it will complain about the format (?)
        LaunchTemplateData={"ImageId": valid_ami},
        VersionDescription="new ami, again",
    )

    versions = cli.describe_launch_template_versions(
        LaunchTemplateName=template_name, Versions=["3"]
    )["LaunchTemplateVersions"]
    assert len(versions) == 1
    assert versions[0]["LaunchTemplateData"]["ImageId"] == valid_ami
    assert versions[0]["DefaultVersion"] is False
    assert versions[0]["VersionDescription"] == "new ami, again"

    versions = cli.describe_launch_template_versions(
        LaunchTemplateName=template_name, Versions=["2", "3"]
    )["LaunchTemplateVersions"]

    assert len(versions) == 2
    version2 = next(v for v in versions if v["VersionNumber"] == 2)
    version3 = next(v for v in versions if v["VersionNumber"] == 3)

    assert version2["LaunchTemplateData"]["ImageId"] == "ami-def456"
    assert version2["DefaultVersion"] is False
    assert version2["VersionDescription"] == "new ami"

    assert version3["LaunchTemplateData"]["ImageId"] == valid_ami
    assert version3["DefaultVersion"] is False
    assert version3["VersionDescription"] == "new ami, again"


@mock_aws
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

    assert len(resp["LaunchTemplateVersions"]) == 2
    assert (
        resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]["ImageId"]
        == "ami-def456"
    )
    assert (
        resp["LaunchTemplateVersions"][1]["LaunchTemplateData"]["ImageId"]
        == "ami-hij789"
    )


@mock_aws
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

    assert len(resp["LaunchTemplateVersions"]) == 2
    assert (
        resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]["ImageId"]
        == "ami-abc123"
    )
    assert (
        resp["LaunchTemplateVersions"][1]["LaunchTemplateData"]["ImageId"]
        == "ami-def456"
    )


@mock_aws
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

    assert len(resp["LaunchTemplateVersions"]) == 2
    assert (
        resp["LaunchTemplateVersions"][0]["LaunchTemplateData"]["ImageId"]
        == "ami-def456"
    )
    assert (
        resp["LaunchTemplateVersions"][1]["LaunchTemplateData"]["ImageId"]
        == "ami-hij789"
    )


@aws_verified
@pytest.mark.aws_verified
def test_describe_launch_templates_with_non_existent_name():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        cli.describe_launch_templates(LaunchTemplateNames=[template_name])
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidLaunchTemplateName.NotFoundException"
    assert (
        err["Message"]
        == "At least one of the launch templates specified in the request does not exist."
    )


@mock_aws
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
        assert my_templates[0]["LaunchTemplateName"] == template_name
        assert my_templates[1]["LaunchTemplateName"] == template_name2

    # filter by names
    resp = cli.describe_launch_templates(
        LaunchTemplateNames=[template_name2, template_name]
    )
    assert "LaunchTemplates" in resp
    assert len(resp["LaunchTemplates"]) == 2
    assert resp["LaunchTemplates"][0]["LaunchTemplateName"] == template_name2
    assert resp["LaunchTemplates"][1]["LaunchTemplateName"] == template_name

    # filter by ids
    resp = cli.describe_launch_templates(LaunchTemplateIds=lt_ids)
    assert "LaunchTemplates" in resp
    assert len(resp["LaunchTemplates"]) == 2
    assert resp["LaunchTemplates"][0]["LaunchTemplateName"] == template_name
    assert resp["LaunchTemplates"][1]["LaunchTemplateName"] == template_name2


@mock_aws
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

    assert len(resp["LaunchTemplates"]) == 1
    assert resp["LaunchTemplates"][0]["LaunchTemplateName"] == template_name

    resp = cli.describe_launch_templates(
        Filters=[{"Name": "launch-template-name", "Values": [template_name_no_tags]}]
    )
    assert len(resp["LaunchTemplates"]) == 1
    assert resp["LaunchTemplates"][0]["LaunchTemplateName"] == template_name_no_tags


@mock_aws
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

    assert "TagSpecifications" in version["LaunchTemplateData"]
    assert len(version["LaunchTemplateData"]["TagSpecifications"]) == 1
    assert version["LaunchTemplateData"]["TagSpecifications"][0] == {
        "ResourceType": "instance",
        "Tags": [{"Key": "key", "Value": "value"}],
    }


@mock_aws
def test_get_launch_template_data():
    client = boto3.client("ec2", region_name="us-east-1")

    reservation = client.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]

    launch_template_data = client.get_launch_template_data(
        InstanceId=instance["InstanceId"]
    )["LaunchTemplateData"]

    # Ensure launch template data matches instance
    assert launch_template_data["ImageId"] == instance["ImageId"]
    assert launch_template_data["InstanceType"] == instance["InstanceType"]

    # Ensure a launch template can be created from this data
    client.create_launch_template(
        LaunchTemplateName=str(uuid4()),
        LaunchTemplateData=launch_template_data,
    )


@mock_aws
@pytest.mark.parametrize(
    "tag_specification_input",
    [
        [],
        [
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "foo", "Value": "bar"},
                ],
            },
        ],
        [
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "foo", "Value": "bar"},
                    {"Key": "baz", "Value": "qux"},
                ],
            },
        ],
    ],
    ids=[
        "No Tags",
        "Single Tag",
        "Multiple Tags",
    ],
)
def test_get_launch_template_data_with_tags(tag_specification_input):
    client = boto3.client("ec2", region_name="us-east-1")
    reservation = client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        TagSpecifications=tag_specification_input,
    )
    instance = reservation["Instances"][0]
    resp = client.get_launch_template_data(InstanceId=instance["InstanceId"])
    launch_template_data = resp["LaunchTemplateData"]
    # Ensure launch template data matches instance
    assert launch_template_data["ImageId"] == instance["ImageId"]
    assert launch_template_data["InstanceType"] == instance["InstanceType"]
    tag_specifications = launch_template_data["TagSpecifications"]
    for tag_specification in tag_specifications:
        if tag_specification["ResourceType"] == "instance":
            assert tag_specification == tag_specification_input[0]
            break
    else:
        assert tag_specifications == tag_specification_input
    # Ensure a launch template can be created from this data
    client.create_launch_template(
        LaunchTemplateName=str(uuid4()),
        LaunchTemplateData=launch_template_data,
    )


@mock_aws
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

    assert (
        len(
            cli.describe_launch_templates(LaunchTemplateNames=[template_name])[
                "LaunchTemplates"
            ]
        )
        == 1
    )

    with pytest.raises(ClientError) as exc:
        cli.delete_launch_template(DryRun=True, LaunchTemplateName=template_name)
    assert_dryrun_error(exc)

    # Template still exists
    assert (
        len(
            cli.describe_launch_templates(LaunchTemplateNames=[template_name])[
                "LaunchTemplates"
            ]
        )
        == 1
    )


@mock_aws
def test_delete_launch_template__by_name():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())
    cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    assert (
        len(
            cli.describe_launch_templates(LaunchTemplateNames=[template_name])[
                "LaunchTemplates"
            ]
        )
        == 1
    )

    cli.delete_launch_template(LaunchTemplateName=template_name)

    with pytest.raises(ClientError) as exc:
        cli.describe_launch_templates(LaunchTemplateNames=[template_name])[
            "LaunchTemplates"
        ]
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidLaunchTemplateName.NotFoundException"
    assert (
        err["Message"]
        == "At least one of the launch templates specified in the request does not exist."
    )

    # Ensure deleted template name can be reused
    cli.create_launch_template(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-abc123"},
    )


@mock_aws
def test_delete_launch_template__by_id():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        cli.delete_launch_template()
    err = exc.value.response["Error"]
    assert err["Code"] == "MissingParameter"
    assert (
        err["Message"]
        == "The request must contain the parameter launch template ID or launch template name"
    )

    template_id = cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )["LaunchTemplate"]["LaunchTemplateId"]

    assert (
        len(
            cli.describe_launch_templates(LaunchTemplateNames=[template_name])[
                "LaunchTemplates"
            ]
        )
        == 1
    )

    cli.delete_launch_template(LaunchTemplateId=template_id)

    with pytest.raises(ClientError) as exc:
        cli.describe_launch_templates(LaunchTemplateNames=[template_name])
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidLaunchTemplateName.NotFoundException"
    assert (
        err["Message"]
        == "At least one of the launch templates specified in the request does not exist."
    )

    # Ensure deleted template name can be reused
    cli.create_launch_template(
        LaunchTemplateName=template_name,
        LaunchTemplateData={"ImageId": "ami-abc123"},
    )


def retrieve_all_templates(client, filters=None):
    resp = client.describe_launch_templates(Filters=filters or [])
    all_templates = resp["LaunchTemplates"]
    next_token = resp.get("NextToken")
    while next_token:
        resp = client.describe_launch_templates(
            Filters=filters or [], NextToken=next_token
        )
        all_templates.extend(resp["LaunchTemplates"])
        next_token = resp.get("NextToken")
    return all_templates


@mock_aws
def test_launch_template_create_with_tags():
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
        TagSpecifications=[
            {
                "ResourceType": "launch-template",
                "Tags": [{"Key": "test1", "Value": "value1"}],
            }
        ],
    )

    assert "LaunchTemplate" in resp
    lt = resp["LaunchTemplate"]
    assert lt["LaunchTemplateName"] == template_name
    assert lt["DefaultVersionNumber"] == 1
    assert lt["LatestVersionNumber"] == 1
    assert len(lt["Tags"]) == 1
    assert lt["Tags"][0] == {"Key": "test1", "Value": "value1"}


@mock_aws
def test_launch_template_describe_with_tags():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())
    cli.create_launch_template(
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
        TagSpecifications=[
            {
                "ResourceType": "launch-template",
                "Tags": [{"Key": "test1", "Value": "value1"}],
            }
        ],
    )

    lt = cli.describe_launch_templates(LaunchTemplateNames=[template_name])[
        "LaunchTemplates"
    ][0]

    assert lt["LaunchTemplateName"] == template_name
    assert lt["DefaultVersionNumber"] == 1
    assert lt["LatestVersionNumber"] == 1
    assert len(lt["Tags"]) == 1
    assert lt["Tags"][0] == {"Key": "test1", "Value": "value1"}


@mock_aws
def test_modify_launch_template_by_name():
    cli = boto3.client("ec2", region_name="us-east-1")

    template_name = str(uuid4())
    create_resp = cli.create_launch_template(
        LaunchTemplateName=template_name, LaunchTemplateData={"ImageId": "ami-abc123"}
    )

    version_resp = cli.create_launch_template_version(
        LaunchTemplateId=create_resp["LaunchTemplate"]["LaunchTemplateId"],
        LaunchTemplateData={"ImageId": "ami-def456"},
    )

    resp = cli.modify_launch_template(
        LaunchTemplateId=create_resp["LaunchTemplate"]["LaunchTemplateId"],
        DefaultVersion="2",
    )

    assert "DefaultVersionNumber" in resp["LaunchTemplate"]
    version = version_resp["LaunchTemplateVersion"]
    assert resp["LaunchTemplate"]["DefaultVersionNumber"] == 2
    assert (
        version["LaunchTemplateId"] == create_resp["LaunchTemplate"]["LaunchTemplateId"]
    )


@mock_aws
def test_create_launch_template_with_non_base64_encoded_user_data_fails():
    # XXX: This doesn't actually fail against AWS.
    # Maybe it only fails when trying to create an instance from it? Something to play around with
    client = boto3.client("ec2", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_launch_template(
            LaunchTemplateName="test-template",
            LaunchTemplateData={
                "ImageId": "ami-12345678",
                "InstanceType": "t2.nano",
                "UserData": "not base64 encoded",
            },
        )
    error = exc.value.response["Error"]
    assert error["Code"] == "InvalidUserData.Malformed"
    assert error["Message"] == "Invalid BASE64 encoding of user data."
