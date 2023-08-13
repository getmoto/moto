import boto3

from moto import mock_ssm


@mock_ssm
def test_describe_maintenance_window():
    ssm = boto3.client("ssm", region_name="us-east-1")

    resp = ssm.describe_maintenance_windows()
    assert resp["WindowIdentities"] == []

    resp = ssm.describe_maintenance_windows(
        Filters=[{"Key": "Name", "Values": ["fake-maintenance-window-name"]}]
    )
    assert resp["WindowIdentities"] == []


@mock_ssm
def test_create_maintenance_windows_simple():
    ssm = boto3.client("ssm", region_name="us-east-1")

    resp = ssm.create_maintenance_window(
        Name="simple-window",
        Schedule="cron(15 12 * * ? *)",
        Duration=2,
        Cutoff=1,
        AllowUnassociatedTargets=False,
    )
    assert "WindowId" in resp
    _id = resp["WindowId"]  # mw-01d6bbfdf6af2c39a

    resp = ssm.describe_maintenance_windows()
    assert len(resp["WindowIdentities"]) == 1

    my_window = resp["WindowIdentities"][0]
    assert my_window["WindowId"] == _id
    assert my_window["Name"] == "simple-window"
    assert my_window["Enabled"] is True
    assert my_window["Duration"] == 2
    assert my_window["Cutoff"] == 1
    assert my_window["Schedule"] == "cron(15 12 * * ? *)"
    # assert "NextExecutionTime" in my_window
    assert "Description" not in my_window
    assert "ScheduleTimezone" not in my_window
    assert "ScheduleOffset" not in my_window
    assert "EndDate" not in my_window
    assert "StartDate" not in my_window


@mock_ssm
def test_create_maintenance_windows_advanced():
    ssm = boto3.client("ssm", region_name="us-east-1")

    resp = ssm.create_maintenance_window(
        Name="simple-window",
        Description="French windows are just too fancy",
        Schedule="cron(15 12 * * ? *)",
        ScheduleTimezone="Europe/London",
        ScheduleOffset=1,
        Duration=5,
        Cutoff=4,
        AllowUnassociatedTargets=False,
        StartDate="2021-11-01",
        EndDate="2021-12-31",
    )
    assert "WindowId" in resp
    _id = resp["WindowId"]  # mw-01d6bbfdf6af2c39a

    resp = ssm.describe_maintenance_windows()
    assert len(resp["WindowIdentities"]) == 1

    my_window = resp["WindowIdentities"][0]
    assert my_window["WindowId"] == _id
    assert my_window["Name"] == "simple-window"
    assert my_window["Enabled"] is True
    assert my_window["Duration"] == 5
    assert my_window["Cutoff"] == 4
    assert my_window["Schedule"] == "cron(15 12 * * ? *)"
    # assert "NextExecutionTime" in my_window
    assert my_window["Description"] == "French windows are just too fancy"
    assert my_window["ScheduleTimezone"] == "Europe/London"
    assert my_window["ScheduleOffset"] == 1
    assert my_window["StartDate"] == "2021-11-01"
    assert my_window["EndDate"] == "2021-12-31"


@mock_ssm
def test_get_maintenance_windows():
    ssm = boto3.client("ssm", region_name="us-east-1")

    resp = ssm.create_maintenance_window(
        Name="my-window",
        Schedule="cron(15 12 * * ? *)",
        Duration=2,
        Cutoff=1,
        AllowUnassociatedTargets=False,
    )
    assert "WindowId" in resp
    _id = resp["WindowId"]  # mw-01d6bbfdf6af2c39a

    my_window = ssm.get_maintenance_window(WindowId=_id)
    assert my_window["WindowId"] == _id
    assert my_window["Name"] == "my-window"
    assert my_window["Enabled"] is True
    assert my_window["Duration"] == 2
    assert my_window["Cutoff"] == 1
    assert my_window["Schedule"] == "cron(15 12 * * ? *)"
    # assert "NextExecutionTime" in my_window
    assert "Description" not in my_window
    assert "ScheduleTimezone" not in my_window
    assert "ScheduleOffset" not in my_window
    assert "EndDate" not in my_window
    assert "StartDate" not in my_window


@mock_ssm
def test_describe_maintenance_windows():
    ssm = boto3.client("ssm", region_name="us-east-1")

    for idx in range(0, 4):
        ssm.create_maintenance_window(
            Name=f"window_{idx}",
            Schedule="cron(15 12 * * ? *)",
            Duration=2,
            Cutoff=1,
            AllowUnassociatedTargets=False,
        )

    resp = ssm.describe_maintenance_windows()
    assert len(resp["WindowIdentities"]) == 4

    resp = ssm.describe_maintenance_windows(
        Filters=[{"Key": "Name", "Values": ["window_0", "window_2"]}]
    )
    assert len(resp["WindowIdentities"]) == 2


@mock_ssm
def test_delete_maintenance_windows():
    ssm = boto3.client("ssm", region_name="us-east-1")

    resp = ssm.create_maintenance_window(
        Name="simple-window",
        Schedule="cron(15 12 * * ? *)",
        Duration=2,
        Cutoff=1,
        AllowUnassociatedTargets=False,
    )

    ssm.delete_maintenance_window(WindowId=resp["WindowId"])

    resp = ssm.describe_maintenance_windows()
    assert resp["WindowIdentities"] == []


@mock_ssm
def test_tags():
    ssm = boto3.client("ssm", region_name="us-east-1")

    # create without & list
    mw_id = ssm.create_maintenance_window(
        Name="simple-window",
        Schedule="cron(15 12 * * ? *)",
        Duration=2,
        Cutoff=1,
        AllowUnassociatedTargets=False,
    )["WindowId"]

    # add & list
    ssm.add_tags_to_resource(
        ResourceType="MaintenanceWindow",
        ResourceId=mw_id,
        Tags=[{"Key": "k1", "Value": "v1"}],
    )
    tags = ssm.list_tags_for_resource(
        ResourceType="MaintenanceWindow", ResourceId=mw_id
    )["TagList"]
    assert tags == [{"Key": "k1", "Value": "v1"}]

    # create & list
    mw_id = ssm.create_maintenance_window(
        Name="simple-window",
        Schedule="cron(15 12 * * ? *)",
        Duration=2,
        Cutoff=1,
        AllowUnassociatedTargets=False,
        Tags=[{"Key": "k2", "Value": "v2"}],
    )["WindowId"]
    tags = ssm.list_tags_for_resource(
        ResourceType="MaintenanceWindow", ResourceId=mw_id
    )["TagList"]
    assert tags == [{"Key": "k2", "Value": "v2"}]

    # add more & list
    ssm.add_tags_to_resource(
        ResourceType="MaintenanceWindow",
        ResourceId=mw_id,
        Tags=[{"Key": "k3", "Value": "v3"}],
    )
    tags = ssm.list_tags_for_resource(
        ResourceType="MaintenanceWindow", ResourceId=mw_id
    )["TagList"]
    assert tags == [{"Key": "k2", "Value": "v2"}, {"Key": "k3", "Value": "v3"}]

    # remove & list
    ssm.remove_tags_from_resource(
        ResourceType="MaintenanceWindow", ResourceId=mw_id, TagKeys=["k3"]
    )
    tags = ssm.list_tags_for_resource(
        ResourceType="MaintenanceWindow", ResourceId=mw_id
    )["TagList"]
    assert tags == [{"Key": "k2", "Value": "v2"}]


@mock_ssm
def test_register_maintenance_window_target():
    ssm = boto3.client("ssm", region_name="us-east-1")

    resp = ssm.create_maintenance_window(
        Name="simple-window",
        Schedule="cron(15 12 * * ? *)",
        Duration=2,
        Cutoff=1,
        AllowUnassociatedTargets=False,
    )
    window_id = resp["WindowId"]

    resp = ssm.register_target_with_maintenance_window(
        WindowId=window_id,
        ResourceType="INSTANCE",
        Targets=[{"Key": "tag:Name", "Values": ["my-instance"]}],
    )
    assert "WindowTargetId" in resp
    _id = resp["WindowTargetId"]

    resp = ssm.describe_maintenance_window_targets(
        WindowId=window_id,
    )
    assert len(resp["Targets"]) == 1
    assert resp["Targets"][0]["ResourceType"] == "INSTANCE"
    assert resp["Targets"][0]["WindowTargetId"] == _id
    assert resp["Targets"][0]["Targets"][0]["Key"] == "tag:Name"
    assert resp["Targets"][0]["Targets"][0]["Values"] == ["my-instance"]


@mock_ssm
def test_deregister_target_from_maintenance_window():
    ssm = boto3.client("ssm", region_name="us-east-1")

    resp = ssm.create_maintenance_window(
        Name="simple-window",
        Schedule="cron(15 12 * * ? *)",
        Duration=2,
        Cutoff=1,
        AllowUnassociatedTargets=False,
    )
    window_id = resp["WindowId"]

    resp = ssm.register_target_with_maintenance_window(
        WindowId=window_id,
        ResourceType="INSTANCE",
        Targets=[{"Key": "tag:Name", "Values": ["my-instance"]}],
    )
    _id = resp["WindowTargetId"]

    ssm.deregister_target_from_maintenance_window(
        WindowId=window_id,
        WindowTargetId=_id,
    )

    resp = ssm.describe_maintenance_window_targets(
        WindowId=window_id,
    )
    assert len(resp["Targets"]) == 0


@mock_ssm
def test_describe_maintenance_window_with_no_task_or_targets():
    ssm = boto3.client("ssm", region_name="us-east-1")

    resp = ssm.create_maintenance_window(
        Name="simple-window",
        Schedule="cron(15 12 * * ? *)",
        Duration=2,
        Cutoff=1,
        AllowUnassociatedTargets=False,
    )
    window_id = resp["WindowId"]

    resp = ssm.describe_maintenance_window_tasks(
        WindowId=window_id,
    )
    assert len(resp["Tasks"]) == 0

    resp = ssm.describe_maintenance_window_targets(
        WindowId=window_id,
    )
    assert len(resp["Targets"]) == 0


@mock_ssm
def test_register_maintenance_window_task():
    ssm = boto3.client("ssm", region_name="us-east-1")

    resp = ssm.create_maintenance_window(
        Name="simple-window",
        Schedule="cron(15 12 * * ? *)",
        Duration=2,
        Cutoff=1,
        AllowUnassociatedTargets=False,
    )
    window_id = resp["WindowId"]

    resp = ssm.register_target_with_maintenance_window(
        WindowId=window_id,
        ResourceType="INSTANCE",
        Targets=[{"Key": "tag:Name", "Values": ["my-instance"]}],
    )
    window_target_id = resp["WindowTargetId"]

    resp = ssm.register_task_with_maintenance_window(
        WindowId=window_id,
        Targets=[{"Key": "WindowTargetIds", "Values": [window_target_id]}],
        TaskArn="AWS-RunShellScript",
        TaskType="RUN_COMMAND",
        MaxConcurrency="1",
        MaxErrors="1",
    )

    assert "WindowTaskId" in resp
    _id = resp["WindowTaskId"]

    resp = ssm.describe_maintenance_window_tasks(
        WindowId=window_id,
    )
    assert len(resp["Tasks"]) == 1
    assert resp["Tasks"][0]["WindowTaskId"] == _id
    assert resp["Tasks"][0]["WindowId"] == window_id
    assert resp["Tasks"][0]["TaskArn"] == "AWS-RunShellScript"
    assert resp["Tasks"][0]["MaxConcurrency"] == "1"
    assert resp["Tasks"][0]["MaxErrors"] == "1"


@mock_ssm
def test_deregister_maintenance_window_task():
    ssm = boto3.client("ssm", region_name="us-east-1")

    resp = ssm.create_maintenance_window(
        Name="simple-window",
        Schedule="cron(15 12 * * ? *)",
        Duration=2,
        Cutoff=1,
        AllowUnassociatedTargets=False,
    )
    window_id = resp["WindowId"]

    resp = ssm.register_target_with_maintenance_window(
        WindowId=window_id,
        ResourceType="INSTANCE",
        Targets=[{"Key": "tag:Name", "Values": ["my-instance"]}],
    )
    window_target_id = resp["WindowTargetId"]

    resp = ssm.register_task_with_maintenance_window(
        WindowId=window_id,
        Targets=[{"Key": "WindowTargetIds", "Values": [window_target_id]}],
        TaskArn="AWS-RunShellScript",
        TaskType="RUN_COMMAND",
        MaxConcurrency="1",
        MaxErrors="1",
    )
    window_task_id = resp["WindowTaskId"]

    ssm.deregister_task_from_maintenance_window(
        WindowId=window_id,
        WindowTaskId=window_task_id,
    )

    resp = ssm.describe_maintenance_window_tasks(
        WindowId=window_id,
    )
    assert len(resp["Tasks"]) == 0
