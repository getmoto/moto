import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ssm


@mock_ssm
def test_describe_maintenance_window():
    ssm = boto3.client("ssm", region_name="us-east-1")

    resp = ssm.describe_maintenance_windows()
    resp.should.have.key("WindowIdentities").equals([])

    resp = ssm.describe_maintenance_windows(
        Filters=[{"Key": "Name", "Values": ["fake-maintenance-window-name"]}]
    )
    resp.should.have.key("WindowIdentities").equals([])


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
    resp.should.have.key("WindowId")
    _id = resp["WindowId"]  # mw-01d6bbfdf6af2c39a

    resp = ssm.describe_maintenance_windows()
    resp.should.have.key("WindowIdentities").have.length_of(1)

    my_window = resp["WindowIdentities"][0]
    my_window.should.have.key("WindowId").equal(_id)
    my_window.should.have.key("Name").equal("simple-window")
    my_window.should.have.key("Enabled").equal(True)
    my_window.should.have.key("Duration").equal(2)
    my_window.should.have.key("Cutoff").equal(1)
    my_window.should.have.key("Schedule").equal("cron(15 12 * * ? *)")
    # my_window.should.have.key("NextExecutionTime")
    my_window.shouldnt.have.key("Description")
    my_window.shouldnt.have.key("ScheduleTimezone")
    my_window.shouldnt.have.key("ScheduleOffset")
    my_window.shouldnt.have.key("EndDate")
    my_window.shouldnt.have.key("StartDate")


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
    resp.should.have.key("WindowId")
    _id = resp["WindowId"]  # mw-01d6bbfdf6af2c39a

    resp = ssm.describe_maintenance_windows()
    resp.should.have.key("WindowIdentities").have.length_of(1)

    my_window = resp["WindowIdentities"][0]
    my_window.should.have.key("WindowId").equal(_id)
    my_window.should.have.key("Name").equal("simple-window")
    my_window.should.have.key("Enabled").equal(True)
    my_window.should.have.key("Duration").equal(5)
    my_window.should.have.key("Cutoff").equal(4)
    my_window.should.have.key("Schedule").equal("cron(15 12 * * ? *)")
    # my_window.should.have.key("NextExecutionTime")
    my_window.should.have.key("Description").equals("French windows are just too fancy")
    my_window.should.have.key("ScheduleTimezone").equals("Europe/London")
    my_window.should.have.key("ScheduleOffset").equals(1)
    my_window.should.have.key("StartDate").equals("2021-11-01")
    my_window.should.have.key("EndDate").equals("2021-12-31")


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
    resp.should.have.key("WindowId")
    _id = resp["WindowId"]  # mw-01d6bbfdf6af2c39a

    my_window = ssm.get_maintenance_window(WindowId=_id)
    my_window.should.have.key("WindowId").equal(_id)
    my_window.should.have.key("Name").equal("my-window")
    my_window.should.have.key("Enabled").equal(True)
    my_window.should.have.key("Duration").equal(2)
    my_window.should.have.key("Cutoff").equal(1)
    my_window.should.have.key("Schedule").equal("cron(15 12 * * ? *)")
    # my_window.should.have.key("NextExecutionTime")
    my_window.shouldnt.have.key("Description")
    my_window.shouldnt.have.key("ScheduleTimezone")
    my_window.shouldnt.have.key("ScheduleOffset")
    my_window.shouldnt.have.key("EndDate")
    my_window.shouldnt.have.key("StartDate")


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
    resp.should.have.key("WindowIdentities").have.length_of(4)

    resp = ssm.describe_maintenance_windows(
        Filters=[{"Key": "Name", "Values": ["window_0", "window_2"]}]
    )
    resp.should.have.key("WindowIdentities").have.length_of(2)


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

    ssm.delete_maintenance_window(WindowId=(resp["WindowId"]))

    resp = ssm.describe_maintenance_windows()
    resp.should.have.key("WindowIdentities").equals([])


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
    resp.should.have.key("WindowTargetId")
    _id = resp["WindowTargetId"]

    resp = ssm.describe_maintenance_window_targets(
        WindowId=window_id,
    )
    resp.should.have.key("Targets").should.have.length_of(1)
    resp["Targets"][0].should.have.key("ResourceType").equal("INSTANCE")
    resp["Targets"][0].should.have.key("WindowTargetId").equal(_id)
    resp["Targets"][0]["Targets"][0].should.have.key("Key").equal("tag:Name")
    resp["Targets"][0]["Targets"][0].should.have.key("Values").equal(["my-instance"])


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
    resp.should.have.key("Targets").should.have.length_of(0)


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
    resp.should.have.key("Tasks").should.have.length_of(0)

    resp = ssm.describe_maintenance_window_targets(
        WindowId=window_id,
    )
    resp.should.have.key("Targets").should.have.length_of(0)


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

    resp.should.have.key("WindowTaskId")
    _id = resp["WindowTaskId"]

    resp = ssm.describe_maintenance_window_tasks(
        WindowId=window_id,
    )
    resp.should.have.key("Tasks").should.have.length_of(1)
    resp["Tasks"][0].should.have.key("WindowTaskId").equal(_id)
    resp["Tasks"][0].should.have.key("WindowId").equal(window_id)
    resp["Tasks"][0].should.have.key("TaskArn").equal("AWS-RunShellScript")
    resp["Tasks"][0].should.have.key("MaxConcurrency").equal("1")
    resp["Tasks"][0].should.have.key("MaxErrors").equal("1")


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
    resp.should.have.key("Tasks").should.have.length_of(0)
