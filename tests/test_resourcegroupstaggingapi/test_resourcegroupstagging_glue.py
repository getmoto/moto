from uuid import uuid4

import boto3

from moto import mock_glue, mock_resourcegroupstaggingapi
from moto.core import DEFAULT_ACCOUNT_ID


@mock_glue
@mock_resourcegroupstaggingapi
def test_glue_jobs():
    glue = boto3.client("glue", region_name="us-west-1")
    tag_key = str(uuid4())[0:6]
    tag_val = str(uuid4())[0:6]
    job_name = glue.create_job(
        Name=str(uuid4()),
        Role="test_role",
        Command={"Name": "test_command"},
        Tags={tag_key: tag_val},
    )["Name"]
    job_arn = f"arn:aws:glue:us-west-1:{DEFAULT_ACCOUNT_ID}:job/{job_name}"

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-west-1")
    resources = rtapi.get_resources(ResourceTypeFilters=["glue"])[
        "ResourceTagMappingList"
    ]
    assert resources == [
        {"ResourceARN": job_arn, "Tags": [{"Key": tag_key, "Value": tag_val}]}
    ]

    resources = rtapi.get_resources(ResourceTypeFilters=["glue:job"])[
        "ResourceTagMappingList"
    ]
    assert resources == [
        {"ResourceARN": job_arn, "Tags": [{"Key": tag_key, "Value": tag_val}]}
    ]

    resources = rtapi.get_resources(TagFilters=[{"Key": tag_key, "Values": [tag_val]}])[
        "ResourceTagMappingList"
    ]
    assert resources == [
        {"ResourceARN": job_arn, "Tags": [{"Key": tag_key, "Value": tag_val}]}
    ]

    resources = rtapi.get_resources(ResourceTypeFilters=["glue:table"])[
        "ResourceTagMappingList"
    ]
    assert resources == []

    assert rtapi.get_tag_keys()["TagKeys"] == [tag_key]

    assert rtapi.get_tag_values(Key=tag_key)["TagValues"] == [tag_val]
    assert rtapi.get_tag_values(Key="unknown")["TagValues"] == []
