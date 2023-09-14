import boto3

from moto import mock_ecs


@mock_ecs
def test_describe_task_definition_with_tags():
    client = boto3.client("ecs", region_name="us-east-1")
    task_def = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
            }
        ],
        tags=[{"key": "k1", "value": "v1"}],
    )["taskDefinition"]
    task_def_arn = task_def["taskDefinitionArn"]

    response = client.describe_task_definition(
        taskDefinition="test_ecs_task:1", include=["TAGS"]
    )
    assert response["tags"] == [{"key": "k1", "value": "v1"}]

    client.tag_resource(resourceArn=task_def_arn, tags=[{"key": "k2", "value": "v2"}])

    response = client.describe_task_definition(
        taskDefinition="test_ecs_task:1", include=["TAGS"]
    )
    assert len(response["tags"]) == 2
    assert {"key": "k1", "value": "v1"} in response["tags"]
    assert {"key": "k2", "value": "v2"} in response["tags"]

    client.untag_resource(resourceArn=task_def_arn, tagKeys=["k2"])

    resp = client.list_tags_for_resource(resourceArn=task_def_arn)
    assert resp["tags"] == [{"key": "k1", "value": "v1"}]
