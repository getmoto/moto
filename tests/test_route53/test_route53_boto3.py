import boto3
import sure  # noqa
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
