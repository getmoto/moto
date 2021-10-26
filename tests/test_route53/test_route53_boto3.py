import boto3
import sure  # noqa # pylint: disable=unused-import
from moto import mock_route53


@mock_route53
def test_create_health_check():
    client = boto3.client("route53", region_name="us-east-1")

    response = client.create_health_check(
        CallerReference="test-route53-health-HealthCheck-asdf",
        HealthCheckConfig={
            "IPAddress": "93.184.216.34",
            "Port": 80,
            "Type": "HTTP",
            "ResourcePath": "/",
            "FullyQualifiedDomainName": "example.com",
            "RequestInterval": 10,
            "FailureThreshold": 2,
        },
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)
    #
    check = response["HealthCheck"]
    check.should.have.key("Id")
    check.should.have.key("CallerReference").being.equal(
        "test-route53-health-HealthCheck-asdf"
    )
    check.should.have.key("HealthCheckConfig")
    #
    config = check["HealthCheckConfig"]
    config.should.have.key("IPAddress").being.equal("93.184.216.34")
    config.should.have.key("Port").being.equal(80)
    config.should.have.key("Type").being.equal("HTTP")
    config.should.have.key("ResourcePath").being.equal("/")
    config.should.have.key("FullyQualifiedDomainName").being.equal("example.com")
    config.should.have.key("RequestInterval").being.equal(10)
    config.should.have.key("FailureThreshold").being.equal(2)
    config.should.have.key("MeasureLatency").being.equal(False)
    config.should.have.key("Inverted").being.equal(False)
    config.should.have.key("Disabled").being.equal(False)
    config.should.have.key("EnableSNI").being.equal(False)

    config.shouldnt.have.key("ChildHealthChecks")
    config.shouldnt.have.key("HealthThreshold")


@mock_route53
def test_create_health_check_with_additional_options():
    client = boto3.client("route53", region_name="us-east-1")

    response = client.create_health_check(
        CallerReference="test-route53-health-HealthCheck-asdf",
        HealthCheckConfig={
            "IPAddress": "93.184.216.34",
            "Port": 80,
            "Type": "HTTP",
            "ResourcePath": "/",
            "FullyQualifiedDomainName": "example.com",
            "RequestInterval": 10,
            "FailureThreshold": 2,
            "MeasureLatency": True,
            "Inverted": True,
            "Disabled": True,
            "EnableSNI": True,
        },
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)
    #
    check = response["HealthCheck"]
    check.should.have.key("CallerReference").being.equal(
        "test-route53-health-HealthCheck-asdf"
    )
    check.should.have.key("HealthCheckConfig")
    #
    config = check["HealthCheckConfig"]
    config.should.have.key("MeasureLatency").being.equal(True)
    config.should.have.key("Inverted").being.equal(True)
    config.should.have.key("Disabled").being.equal(True)
    config.should.have.key("EnableSNI").being.equal(True)


@mock_route53
def test_create_calculated_health_check():
    client = boto3.client("route53", region_name="us-east-1")

    response = client.create_health_check(
        CallerReference="test-route53-health-HealthCheck-ZHV123",
        HealthCheckConfig={
            "Type": "CALCULATED",
            "Inverted": False,
            "Disabled": False,
            "HealthThreshold": 1,
        },
    )

    check = response["HealthCheck"]
    check.should.have.key("Id")
    check.should.have.key("CallerReference").being.equal(
        "test-route53-health-HealthCheck-ZHV123"
    )
    #
    config = check["HealthCheckConfig"]
    config.should.have.key("Type").being.equal("CALCULATED")
    config.should.have.key("Inverted").being.equal(False)
    config.should.have.key("Disabled").being.equal(False)
    config.should.have.key("HealthThreshold").being.equal(1)
    #
    config.shouldnt.have.key("IPAddress")
    config.shouldnt.have.key("Port")
    config.shouldnt.have.key("ResourcePath")
    config.shouldnt.have.key("FullyQualifiedDomainName")
    config.shouldnt.have.key("RequestInterval")
    config.shouldnt.have.key("FailureThreshold")
    config.shouldnt.have.key("MeasureLatency")


@mock_route53
def test_create_calculated_health_check_with_children():
    client = boto3.client("route53", region_name="us-east-1")

    child1 = client.create_health_check(
        CallerReference="test-route53-health-HealthCheck-child1",
        HealthCheckConfig={
            "Type": "CALCULATED",
            "Inverted": False,
            "Disabled": False,
            "HealthThreshold": 1,
        },
    )

    child2 = client.create_health_check(
        CallerReference="test-route53-health-HealthCheck-child2",
        HealthCheckConfig={
            "Type": "CALCULATED",
            "Inverted": False,
            "Disabled": False,
            "HealthThreshold": 1,
        },
    )

    parent = client.create_health_check(
        CallerReference="test-route53-health-HealthCheck-parent",
        HealthCheckConfig={
            "Type": "CALCULATED",
            "Inverted": False,
            "Disabled": False,
            "HealthThreshold": 1,
            "ChildHealthChecks": [
                child1["HealthCheck"]["Id"],
                child2["HealthCheck"]["Id"],
            ],
        },
    )

    check = parent["HealthCheck"]
    check.should.have.key("Id")
    check.should.have.key("CallerReference").being.equal(
        "test-route53-health-HealthCheck-parent"
    )
    #
    config = check["HealthCheckConfig"]
    config.should.have.key("Type").being.equal("CALCULATED")
    config.should.have.key("Inverted").being.equal(False)
    config.should.have.key("Disabled").being.equal(False)
    config.should.have.key("HealthThreshold").being.equal(1)
    config.should.have.key("ChildHealthChecks").being.equal(
        [child1["HealthCheck"]["Id"], child2["HealthCheck"]["Id"]]
    )
