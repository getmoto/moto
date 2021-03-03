import boto3
import sure  # noqa
from botocore.exceptions import ClientError

from moto import mock_elasticbeanstalk


@mock_elasticbeanstalk
def test_create_application():
    # Create Elastic Beanstalk Application
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    app = conn.create_application(ApplicationName="myapp",)
    app["Application"]["ApplicationName"].should.equal("myapp")
    app["Application"]["ApplicationArn"].should.contain("myapp")


@mock_elasticbeanstalk
def test_create_application_dup():
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    conn.create_application(ApplicationName="myapp",)
    conn.create_application.when.called_with(ApplicationName="myapp",).should.throw(
        ClientError
    )


@mock_elasticbeanstalk
def test_describe_applications():
    # Create Elastic Beanstalk Application
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    conn.create_application(ApplicationName="myapp",)

    apps = conn.describe_applications()
    len(apps["Applications"]).should.equal(1)
    apps["Applications"][0]["ApplicationName"].should.equal("myapp")
    apps["Applications"][0]["ApplicationArn"].should.contain("myapp")


@mock_elasticbeanstalk
def test_create_environment():
    # Create Elastic Beanstalk Environment
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    app = conn.create_application(ApplicationName="myapp",)
    env = conn.create_environment(ApplicationName="myapp", EnvironmentName="myenv",)
    env["EnvironmentName"].should.equal("myenv")
    env["EnvironmentArn"].should.contain("myapp/myenv")


@mock_elasticbeanstalk
def test_describe_environments():
    # List Elastic Beanstalk Envs
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    conn.create_application(ApplicationName="myapp",)
    conn.create_environment(
        ApplicationName="myapp", EnvironmentName="myenv",
    )

    envs = conn.describe_environments()
    envs = envs["Environments"]
    len(envs).should.equal(1)
    envs[0]["ApplicationName"].should.equal("myapp")
    envs[0]["EnvironmentName"].should.equal("myenv")
    envs[0]["EnvironmentArn"].should.contain("myapp/myenv")


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
    conn.create_application(ApplicationName="myapp",)
    env_tags = {"initial key": "initial value"}
    env = conn.create_environment(
        ApplicationName="myapp",
        EnvironmentName="myenv",
        Tags=tags_dict_to_list(env_tags),
    )

    tags = conn.list_tags_for_resource(ResourceArn=env["EnvironmentArn"],)
    tags["ResourceArn"].should.equal(env["EnvironmentArn"])
    tags_list_to_dict(tags["ResourceTags"]).should.equal(env_tags)


@mock_elasticbeanstalk
def test_update_tags():
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    conn.create_application(ApplicationName="myapp",)
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

    tags = conn.list_tags_for_resource(ResourceArn=env["EnvironmentArn"],)
    tags["ResourceArn"].should.equal(env["EnvironmentArn"])
    tags_list_to_dict(tags["ResourceTags"]).should.equal(total_env_tags)


@mock_elasticbeanstalk
def test_list_available_solution_stacks():
    conn = boto3.client("elasticbeanstalk", region_name="us-east-1")
    stacks = conn.list_available_solution_stacks()
    len(stacks["SolutionStacks"]).should.be.greater_than(0)
    len(stacks["SolutionStacks"]).should.be.equal(len(stacks["SolutionStackDetails"]))
