import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_datasync


def create_locations(client, create_smb=False, create_s3=False):
    """
    Convenience function for creating locations.
    Locations must exist before tasks can be created.
    """
    smb_arn = None
    s3_arn = None
    if create_smb:
        response = client.create_location_smb(
            ServerHostname="host",
            Subdirectory="somewhere",
            User="",
            Password="",
            AgentArns=["stuff"],
        )
        smb_arn = response["LocationArn"]
    if create_s3:
        response = client.create_location_s3(
            S3BucketArn="arn:aws:s3:::my_bucket",
            Subdirectory="dir",
            S3Config={"BucketAccessRoleArn": "role"},
        )
        s3_arn = response["LocationArn"]
    return {"smb_arn": smb_arn, "s3_arn": s3_arn}


@mock_datasync
def test_create_location_smb():
    client = boto3.client("datasync", region_name="us-east-1")
    response = client.create_location_smb(
        ServerHostname="host",
        Subdirectory="somewhere",
        User="",
        Password="",
        AgentArns=["stuff"],
    )
    assert "LocationArn" in response


@mock_datasync
def test_describe_location_smb():
    client = boto3.client("datasync", region_name="us-east-1")
    agent_arns = ["stuff"]
    user = "user"
    response = client.create_location_smb(
        ServerHostname="host",
        Subdirectory="somewhere",
        User=user,
        Password="",
        AgentArns=agent_arns,
    )
    response = client.describe_location_smb(LocationArn=response["LocationArn"])
    assert "LocationArn" in response
    assert "LocationUri" in response
    assert response["User"] == user
    assert response["AgentArns"] == agent_arns


@mock_datasync
def test_create_location_s3():
    client = boto3.client("datasync", region_name="us-east-1")
    response = client.create_location_s3(
        S3BucketArn="arn:aws:s3:::my_bucket",
        Subdirectory="dir",
        S3Config={"BucketAccessRoleArn": "role"},
    )
    assert "LocationArn" in response


@mock_datasync
def test_describe_location_s3():
    client = boto3.client("datasync", region_name="us-east-1")
    s3_config = {"BucketAccessRoleArn": "role"}
    response = client.create_location_s3(
        S3BucketArn="arn:aws:s3:::my_bucket", Subdirectory="dir", S3Config=s3_config
    )
    response = client.describe_location_s3(LocationArn=response["LocationArn"])
    assert "LocationArn" in response
    assert "LocationUri" in response
    assert response["S3Config"] == s3_config


@mock_datasync
def test_describe_location_wrong():
    client = boto3.client("datasync", region_name="us-east-1")
    agent_arns = ["stuff"]
    user = "user"
    response = client.create_location_smb(
        ServerHostname="host",
        Subdirectory="somewhere",
        User=user,
        Password="",
        AgentArns=agent_arns,
    )
    with pytest.raises(ClientError) as e:
        client.describe_location_s3(LocationArn=response["LocationArn"])
    err = e.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert err["Message"] == "Invalid Location type: SMB"


@mock_datasync
def test_list_locations():
    client = boto3.client("datasync", region_name="us-east-1")
    response = client.list_locations()
    assert len(response["Locations"]) == 0

    create_locations(client, create_smb=True)
    response = client.list_locations()
    assert len(response["Locations"]) == 1
    assert response["Locations"][0]["LocationUri"] == "smb://host/somewhere"

    create_locations(client, create_s3=True)
    response = client.list_locations()
    assert len(response["Locations"]) == 2
    assert response["Locations"][1]["LocationUri"] == "s3://my_bucket/dir"

    create_locations(client, create_s3=True)
    response = client.list_locations()
    assert len(response["Locations"]) == 3
    assert response["Locations"][2]["LocationUri"] == "s3://my_bucket/dir"


@mock_datasync
def test_delete_location():
    client = boto3.client("datasync", region_name="us-east-1")
    locations = create_locations(client, create_smb=True)
    response = client.list_locations()
    assert len(response["Locations"]) == 1
    location_arn = locations["smb_arn"]

    client.delete_location(LocationArn=location_arn)
    response = client.list_locations()
    assert len(response["Locations"]) == 0

    with pytest.raises(ClientError):
        client.delete_location(LocationArn=location_arn)


@mock_datasync
def test_create_task():
    client = boto3.client("datasync", region_name="us-east-1")
    locations = create_locations(client, create_smb=True, create_s3=True)
    response = client.create_task(
        SourceLocationArn=locations["smb_arn"],
        DestinationLocationArn=locations["s3_arn"],
    )
    assert "TaskArn" in response


@mock_datasync
def test_create_task_fail():
    """Test that Locations must exist before a Task can be created"""
    client = boto3.client("datasync", region_name="us-east-1")
    locations = create_locations(client, create_smb=True, create_s3=True)
    with pytest.raises(ClientError) as e:
        client.create_task(
            SourceLocationArn="1", DestinationLocationArn=locations["s3_arn"]
        )
    err = e.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert err["Message"] == "Location 1 not found."

    with pytest.raises(ClientError) as e:
        client.create_task(
            SourceLocationArn=locations["smb_arn"], DestinationLocationArn="2"
        )
    err = e.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert err["Message"] == "Location 2 not found."


@mock_datasync
def test_list_tasks():
    client = boto3.client("datasync", region_name="us-east-1")
    locations = create_locations(client, create_s3=True, create_smb=True)

    client.create_task(
        SourceLocationArn=locations["smb_arn"],
        DestinationLocationArn=locations["s3_arn"],
    )
    client.create_task(
        SourceLocationArn=locations["s3_arn"],
        DestinationLocationArn=locations["smb_arn"],
        Name="task_name",
    )
    response = client.list_tasks()
    tasks = response["Tasks"]
    assert len(tasks) == 2

    task = tasks[0]
    assert task["Status"] == "AVAILABLE"
    assert "Name" not in task

    task = tasks[1]
    assert task["Status"] == "AVAILABLE"
    assert task["Name"] == "task_name"


@mock_datasync
def test_describe_task():
    client = boto3.client("datasync", region_name="us-east-1")
    locations = create_locations(client, create_s3=True, create_smb=True)

    response = client.create_task(
        SourceLocationArn=locations["smb_arn"],
        DestinationLocationArn=locations["s3_arn"],
        Name="task_name",
    )
    task_arn = response["TaskArn"]

    response = client.describe_task(TaskArn=task_arn)

    assert "TaskArn" in response
    assert "Status" in response
    assert "SourceLocationArn" in response
    assert "DestinationLocationArn" in response


@mock_datasync
def test_describe_task_not_exist():
    client = boto3.client("datasync", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.describe_task(TaskArn="abc")
    err = e.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert err["Message"] == "The request is not valid."


@mock_datasync
def test_update_task():
    client = boto3.client("datasync", region_name="us-east-1")
    locations = create_locations(client, create_s3=True, create_smb=True)

    initial_name = "Initial_Name"
    updated_name = "Updated_Name"
    initial_options = {
        "VerifyMode": "NONE",
        "Atime": "BEST_EFFORT",
        "Mtime": "PRESERVE",
    }
    updated_options = {
        "VerifyMode": "POINT_IN_TIME_CONSISTENT",
        "Atime": "BEST_EFFORT",
        "Mtime": "PRESERVE",
    }
    response = client.create_task(
        SourceLocationArn=locations["smb_arn"],
        DestinationLocationArn=locations["s3_arn"],
        Name=initial_name,
        Options=initial_options,
    )
    task_arn = response["TaskArn"]
    response = client.describe_task(TaskArn=task_arn)
    assert response["TaskArn"] == task_arn
    assert response["Name"] == initial_name
    assert response["Options"] == initial_options

    client.update_task(TaskArn=task_arn, Name=updated_name, Options=updated_options)

    response = client.describe_task(TaskArn=task_arn)
    assert response["TaskArn"] == task_arn
    assert response["Name"] == updated_name
    assert response["Options"] == updated_options

    with pytest.raises(ClientError):
        client.update_task(TaskArn="doesnt_exist")


@mock_datasync
def test_delete_task():
    client = boto3.client("datasync", region_name="us-east-1")
    locations = create_locations(client, create_s3=True, create_smb=True)

    client.create_task(
        SourceLocationArn=locations["smb_arn"],
        DestinationLocationArn=locations["s3_arn"],
        Name="task_name",
    )

    response = client.list_tasks()
    assert len(response["Tasks"]) == 1
    task_arn = response["Tasks"][0]["TaskArn"]
    assert task_arn is not None

    client.delete_task(TaskArn=task_arn)
    response = client.list_tasks()
    assert len(response["Tasks"]) == 0

    with pytest.raises(ClientError):
        client.delete_task(TaskArn=task_arn)


@mock_datasync
def test_start_task_execution():
    client = boto3.client("datasync", region_name="us-east-1")
    locations = create_locations(client, create_s3=True, create_smb=True)

    response = client.create_task(
        SourceLocationArn=locations["smb_arn"],
        DestinationLocationArn=locations["s3_arn"],
        Name="task_name",
    )
    task_arn = response["TaskArn"]
    response = client.describe_task(TaskArn=task_arn)
    assert "CurrentTaskExecutionArn" not in response

    response = client.start_task_execution(TaskArn=task_arn)
    assert "TaskExecutionArn" in response
    task_execution_arn = response["TaskExecutionArn"]

    response = client.describe_task(TaskArn=task_arn)
    assert response["CurrentTaskExecutionArn"] == task_execution_arn


@mock_datasync
def test_start_task_execution_twice():
    client = boto3.client("datasync", region_name="us-east-1")
    locations = create_locations(client, create_s3=True, create_smb=True)

    response = client.create_task(
        SourceLocationArn=locations["smb_arn"],
        DestinationLocationArn=locations["s3_arn"],
        Name="task_name",
    )
    task_arn = response["TaskArn"]

    response = client.start_task_execution(TaskArn=task_arn)
    assert "TaskExecutionArn" in response

    with pytest.raises(ClientError) as exc:
        client.start_task_execution(TaskArn=task_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"


@mock_datasync
def test_describe_task_execution():
    client = boto3.client("datasync", region_name="us-east-1")
    locations = create_locations(client, create_s3=True, create_smb=True)

    response = client.create_task(
        SourceLocationArn=locations["smb_arn"],
        DestinationLocationArn=locations["s3_arn"],
        Name="task_name",
    )
    task_arn = response["TaskArn"]
    response = client.describe_task(TaskArn=task_arn)
    assert response["Status"] == "AVAILABLE"

    response = client.start_task_execution(TaskArn=task_arn)
    task_execution_arn = response["TaskExecutionArn"]

    # Each time task_execution is described the Status will increment
    # This is a simple way to simulate a task being executed
    response = client.describe_task_execution(TaskExecutionArn=task_execution_arn)
    assert response["TaskExecutionArn"] == task_execution_arn
    assert response["Status"] == "INITIALIZING"
    response = client.describe_task(TaskArn=task_arn)
    assert response["Status"] == "RUNNING"

    response = client.describe_task_execution(TaskExecutionArn=task_execution_arn)
    assert response["TaskExecutionArn"] == task_execution_arn
    assert response["Status"] == "PREPARING"
    response = client.describe_task(TaskArn=task_arn)
    assert response["Status"] == "RUNNING"

    response = client.describe_task_execution(TaskExecutionArn=task_execution_arn)
    assert response["TaskExecutionArn"] == task_execution_arn
    assert response["Status"] == "TRANSFERRING"
    response = client.describe_task(TaskArn=task_arn)
    assert response["Status"] == "RUNNING"

    response = client.describe_task_execution(TaskExecutionArn=task_execution_arn)
    assert response["TaskExecutionArn"] == task_execution_arn
    assert response["Status"] == "VERIFYING"
    response = client.describe_task(TaskArn=task_arn)
    assert response["Status"] == "RUNNING"

    response = client.describe_task_execution(TaskExecutionArn=task_execution_arn)
    assert response["TaskExecutionArn"] == task_execution_arn
    assert response["Status"] == "SUCCESS"
    response = client.describe_task(TaskArn=task_arn)
    assert response["Status"] == "AVAILABLE"

    response = client.describe_task_execution(TaskExecutionArn=task_execution_arn)
    assert response["TaskExecutionArn"] == task_execution_arn
    assert response["Status"] == "SUCCESS"
    response = client.describe_task(TaskArn=task_arn)
    assert response["Status"] == "AVAILABLE"


@mock_datasync
def test_describe_task_execution_not_exist():
    client = boto3.client("datasync", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.describe_task_execution(TaskExecutionArn="abc")
    err = e.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert err["Message"] == "The request is not valid."


@mock_datasync
def test_cancel_task_execution():
    client = boto3.client("datasync", region_name="us-east-1")
    locations = create_locations(client, create_s3=True, create_smb=True)

    response = client.create_task(
        SourceLocationArn=locations["smb_arn"],
        DestinationLocationArn=locations["s3_arn"],
        Name="task_name",
    )
    task_arn = response["TaskArn"]

    response = client.start_task_execution(TaskArn=task_arn)
    task_execution_arn = response["TaskExecutionArn"]

    response = client.describe_task(TaskArn=task_arn)
    assert response["CurrentTaskExecutionArn"] == task_execution_arn
    assert response["Status"] == "RUNNING"

    client.cancel_task_execution(TaskExecutionArn=task_execution_arn)

    response = client.describe_task(TaskArn=task_arn)
    assert "CurrentTaskExecutionArn" not in response
    assert response["Status"] == "AVAILABLE"

    response = client.describe_task_execution(TaskExecutionArn=task_execution_arn)
    assert response["Status"] == "ERROR"
