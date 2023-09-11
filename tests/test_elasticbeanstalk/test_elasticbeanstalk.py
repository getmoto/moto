import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_elasticbeanstalk


@mock_elasticbeanstalk
def test_create_application():
    # Create Elastic Beanstalk Application
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    app = conn.create_application(ApplicationName="myapp")
    assert app["Application"]["ApplicationName"] == "myapp"
    assert "myapp" in app["Application"]["ApplicationArn"]


@mock_elasticbeanstalk
def test_create_application_dup():
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    conn.create_application(ApplicationName="myapp")
    with pytest.raises(ClientError):
        conn.create_application(ApplicationName="myapp")


@mock_elasticbeanstalk
def test_describe_applications():
    # Create Elastic Beanstalk Application
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    conn.create_application(ApplicationName="myapp")

    apps = conn.describe_applications()
    assert len(apps["Applications"]) == 1
    assert apps["Applications"][0]["ApplicationName"] == "myapp"
    assert "myapp" in apps["Applications"][0]["ApplicationArn"]


@mock_elasticbeanstalk
def test_delete_application():
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")

    application_name = "myapp"

    conn.create_application(ApplicationName=application_name)

    resp = conn.delete_application(ApplicationName=application_name)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_elasticbeanstalk
def test_delete_unknown_application():
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")

    application_name = "myapp"
    unknown_application_name = "myapp1"

    conn.create_application(ApplicationName=application_name)
    with pytest.raises(ClientError) as exc:
        conn.delete_application(ApplicationName=unknown_application_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ApplicationNotFound"
    assert (
        err["Message"]
        == f"Elastic Beanstalk application {unknown_application_name} not found."
    )


@mock_elasticbeanstalk
def test_create_environment():
    # Create Elastic Beanstalk Environment
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    conn.create_application(ApplicationName="myapp")
    env = conn.create_environment(ApplicationName="myapp", EnvironmentName="myenv")
    assert env["EnvironmentName"] == "myenv"
    assert "myapp/myenv" in env["EnvironmentArn"]


@mock_elasticbeanstalk
def test_describe_environments():
    # List Elastic Beanstalk Envs
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    conn.create_application(ApplicationName="myapp")
    conn.create_environment(ApplicationName="myapp", EnvironmentName="myenv")

    envs = conn.describe_environments()
    envs = envs["Environments"]
    assert len(envs) == 1
    assert envs[0]["ApplicationName"] == "myapp"
    assert envs[0]["EnvironmentName"] == "myenv"
    assert "myapp/myenv" in envs[0]["EnvironmentArn"]


def tags_dict_to_list(tag_dict):
    tag_list = []
    for key, value in tag_dict.items():
        tag_list.append({"Key": key, "Value": value})
    return tag_list


def tags_list_to_dict(tag_list):
    tag_dict = {}
    for tag in tag_list:
        tag_dict[tag["Key"]] = tag["Value"]
    return tag_dict


@mock_elasticbeanstalk
def test_create_environment_tags():
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    conn.create_application(ApplicationName="myapp")
    env_tags = {"initial key": "initial value"}
    env = conn.create_environment(
        ApplicationName="myapp",
        EnvironmentName="myenv",
        Tags=tags_dict_to_list(env_tags),
    )

    tags = conn.list_tags_for_resource(ResourceArn=env["EnvironmentArn"])
    assert tags["ResourceArn"] == env["EnvironmentArn"]
    assert tags_list_to_dict(tags["ResourceTags"]) == env_tags


@mock_elasticbeanstalk
def test_update_tags():
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    conn.create_application(ApplicationName="myapp")
    env_tags = {
        "initial key": "initial value",
        "to remove": "delete me",
        "to update": "original",
    }
    env = conn.create_environment(
        ApplicationName="myapp",
        EnvironmentName="myenv",
        Tags=tags_dict_to_list(env_tags),
    )

    extra_env_tags = {
        "to update": "new",
        "extra key": "extra value",
    }
    conn.update_tags_for_resource(
        ResourceArn=env["EnvironmentArn"],
        TagsToAdd=tags_dict_to_list(extra_env_tags),
        TagsToRemove=["to remove"],
    )

    total_env_tags = env_tags.copy()
    total_env_tags.update(extra_env_tags)
    del total_env_tags["to remove"]

    tags = conn.list_tags_for_resource(ResourceArn=env["EnvironmentArn"])
    assert tags["ResourceArn"] == env["EnvironmentArn"]
    assert tags_list_to_dict(tags["ResourceTags"]) == total_env_tags


@mock_elasticbeanstalk
def test_list_available_solution_stacks():
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    stacks = conn.list_available_solution_stacks()
    assert len(stacks["SolutionStacks"]) > 0
    assert len(stacks["SolutionStacks"]) == len(stacks["SolutionStackDetails"])
