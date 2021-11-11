import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_ssm


@mock_ssm
def test_describe_maintenance_window():
    ssm = boto3.client("ssm", region_name="us-east-1")

    resp = ssm.describe_maintenance_windows()
    resp.should.have.key("WindowIdentities").equals([])

    resp = ssm.describe_maintenance_windows(
        Filters=[{"Key": "Name", "Values": ["fake-maintenance-window-name",]},],
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
        Filters=[{"Key": "Name", "Values": ["window_0", "window_2",]},],
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
