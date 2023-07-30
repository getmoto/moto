import boto3

from moto import mock_glue, mock_resourcegroupstaggingapi
from moto.core import DEFAULT_ACCOUNT_ID
from uuid import uuid4


@mock_glue
@mock_resourcegroupstaggingapi
def test_glue_jobs():
    glue = boto3.client("glue", region_name="us-west-1")
    job_name = glue.create_job(
        Name=str(uuid4()),
        Role="test_role",
        Command=dict(Name="test_command"),
        Tags={"k1": "v1"},
    )["Name"]
    job_arn = f"arn:aws:glue:us-west-1:{DEFAULT_ACCOUNT_ID}:job/{job_name}"

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-west-1")
    resources = rtapi.get_resources(ResourceTypeFilters=["glue"])[
        "ResourceTagMappingList"
    ]
    assert resources == [
        {"ResourceARN": job_arn, "Tags": [{"Key": "k1", "Value": "v1"}]}
    ]

    resources = rtapi.get_resources(ResourceTypeFilters=["glue:job"])[
        "ResourceTagMappingList"
    ]
    assert resources == [
        {"ResourceARN": job_arn, "Tags": [{"Key": "k1", "Value": "v1"}]}
    ]

    resources = rtapi.get_resources(TagFilters=[{"Key": "k1", "Values": ["v1"]}])[
        "ResourceTagMappingList"
    ]
    assert resources == [
        {"ResourceARN": job_arn, "Tags": [{"Key": "k1", "Value": "v1"}]}
    ]

    resources = rtapi.get_resources(ResourceTypeFilters=["glue:table"])[
        "ResourceTagMappingList"
    ]
    assert resources == []

    resources = rtapi.get_resources(ResourceTypeFilters=["ec2"])[
        "ResourceTagMappingList"
    ]
    assert resources == []

    assert rtapi.get_tag_keys()["TagKeys"] == ["k1"]

    assert rtapi.get_tag_values(Key="k1")["TagValues"] == ["v1"]
    assert rtapi.get_tag_values(Key="unknown")["TagValues"] == []
