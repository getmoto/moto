from . import _get_clients

from moto import mock_batch
from uuid import uuid4

container_properties = {
    "image": "busybox",
    "command": ["sleep", "1"],
    "memory": 128,
    "vcpus": 1,
}


@mock_batch
def test_list_tags_with_job_definition():
    _, _, _, _, batch_client = _get_clients()

    definition_name = str(uuid4())[0:6]

    job_def_arn = batch_client.register_job_definition(
        jobDefinitionName=definition_name,
        type="container",
        containerProperties=container_properties,
        tags={"foo": "123", "bar": "456"},
    )["jobDefinitionArn"]

    my_queue = batch_client.list_tags_for_resource(resourceArn=job_def_arn)
    assert my_queue["tags"] == {"foo": "123", "bar": "456"}


@mock_batch
def test_tag_job_definition():
    _, _, _, _, batch_client = _get_clients()

    definition_name = str(uuid4())[0:6]

    job_def_arn = batch_client.register_job_definition(
        jobDefinitionName=definition_name,
        type="container",
        containerProperties=container_properties,
    )["jobDefinitionArn"]

    batch_client.tag_resource(resourceArn=job_def_arn, tags={"k1": "v1", "k2": "v2"})

    my_queue = batch_client.list_tags_for_resource(resourceArn=job_def_arn)
    assert my_queue["tags"] == {"k1": "v1", "k2": "v2"}


@mock_batch
def test_untag_job_queue():
    _, _, _, _, batch_client = _get_clients()

    definition_name = str(uuid4())[0:6]

    job_def_arn = batch_client.register_job_definition(
        jobDefinitionName=definition_name,
        type="container",
        containerProperties=container_properties,
        tags={"k1": "v1", "k2": "v2"},
    )["jobDefinitionArn"]

    batch_client.tag_resource(resourceArn=job_def_arn, tags={"k3": "v3"})
    batch_client.untag_resource(resourceArn=job_def_arn, tagKeys=["k2"])

    my_queue = batch_client.list_tags_for_resource(resourceArn=job_def_arn)
    assert my_queue["tags"] == {"k1": "v1", "k3": "v3"}
