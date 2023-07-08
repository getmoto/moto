import boto3
import pytest
from botocore.exceptions import ClientError
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
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201
    #
    check = response["HealthCheck"]
    assert "Id" in check
    assert check["CallerReference"] == "test-route53-health-HealthCheck-asdf"
    assert "HealthCheckConfig" in check
    #
    config = check["HealthCheckConfig"]
    assert config["IPAddress"] == "93.184.216.34"
    assert config["Port"] == 80
    assert config["Type"] == "HTTP"
    assert config["ResourcePath"] == "/"
    assert config["FullyQualifiedDomainName"] == "example.com"
    assert config["RequestInterval"] == 10
    assert config["FailureThreshold"] == 2
    assert config["MeasureLatency"] is False
    assert config["Inverted"] is False
    assert config["Disabled"] is False
    assert config["EnableSNI"] is False

    assert "ChildHealthChecks" not in config
    assert "HealthThreshold" not in config


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
            "SearchString": "a good response",
            "RequestInterval": 10,
            "FailureThreshold": 2,
            "MeasureLatency": True,
            "Inverted": True,
            "Disabled": True,
            "EnableSNI": True,
        },
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201
    #
    check = response["HealthCheck"]
    assert check["CallerReference"] == "test-route53-health-HealthCheck-asdf"
    assert check["HealthCheckVersion"] == 1
    assert "HealthCheckConfig" in check
    #
    config = check["HealthCheckConfig"]
    assert check["HealthCheckConfig"]["SearchString"] == "a good response"
    assert config["MeasureLatency"] is True
    assert config["Inverted"] is True
    assert config["Disabled"] is True
    assert config["EnableSNI"] is True


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
    assert "Id" in check
    assert check["CallerReference"] == "test-route53-health-HealthCheck-ZHV123"
    #
    config = check["HealthCheckConfig"]
    assert config["Type"] == "CALCULATED"
    assert config["Inverted"] is False
    assert config["Disabled"] is False
    assert config["HealthThreshold"] == 1
    #
    assert "IPAddress" not in config
    assert "Port" not in config
    assert "ResourcePath" not in config
    assert "FullyQualifiedDomainName" not in config
    assert "RequestInterval" not in config
    assert "FailureThreshold" not in config
    assert "MeasureLatency" not in config


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
    assert "Id" in check
    assert check["CallerReference"] == "test-route53-health-HealthCheck-parent"
    #
    config = check["HealthCheckConfig"]
    assert config["Type"] == "CALCULATED"
    assert config["Inverted"] is False
    assert config["Disabled"] is False
    assert config["HealthThreshold"] == 1
    assert config["ChildHealthChecks"] == [
        child1["HealthCheck"]["Id"],
        child2["HealthCheck"]["Id"],
    ]


@mock_route53
def test_get_health_check():
    client = boto3.client("route53", region_name="us-east-1")

    hc_id = client.create_health_check(
        CallerReference="callref",
        HealthCheckConfig={
            "Type": "CALCULATED",
            "Inverted": False,
            "Disabled": False,
            "HealthThreshold": 1,
        },
    )["HealthCheck"]["Id"]

    resp = client.get_health_check(HealthCheckId=hc_id)["HealthCheck"]
    assert resp["Id"] == hc_id
    assert resp["CallerReference"] == "callref"
    assert resp["HealthCheckVersion"] == 1


@mock_route53
def test_get_unknown_health_check():
    client = boto3.client("route53", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_health_check(HealthCheckId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchHealthCheck"
    assert err["Message"] == "A health check with id unknown does not exist."


@mock_route53
def test_list_health_checks():
    conn = boto3.client("route53", region_name="us-east-1")

    assert len(conn.list_health_checks()["HealthChecks"]) == 0

    check = conn.create_health_check(
        CallerReference="?",
        HealthCheckConfig={
            "IPAddress": "10.0.0.25",
            "Port": 80,
            "Type": "HTTP",
            "ResourcePath": "/",
            "FullyQualifiedDomainName": "example.com",
            "SearchString": "a good response",
            "RequestInterval": 10,
            "FailureThreshold": 2,
        },
    )["HealthCheck"]

    assert conn.list_health_checks()["HealthChecks"] == [check]


@mock_route53
def test_delete_health_checks():
    conn = boto3.client("route53", region_name="us-east-1")

    assert len(conn.list_health_checks()["HealthChecks"]) == 0

    check = conn.create_health_check(
        CallerReference="?",
        HealthCheckConfig={
            "IPAddress": "10.0.0.25",
            "Port": 80,
            "Type": "HTTP",
            "ResourcePath": "/",
            "FullyQualifiedDomainName": "example.com",
            "SearchString": "a good response",
            "RequestInterval": 10,
            "FailureThreshold": 2,
        },
    )["HealthCheck"]

    conn.delete_health_check(HealthCheckId=check["Id"])

    checks = conn.list_health_checks()["HealthChecks"]
    assert len(checks) == 0


@mock_route53
def test_update_health_check():
    client = boto3.client("route53", region_name="us-east-1")

    hc_id = client.create_health_check(
        CallerReference="callref",
        HealthCheckConfig={
            "Type": "CALCULATED",
            "Inverted": False,
            "Disabled": False,
            "HealthThreshold": 1,
        },
    )["HealthCheck"]["Id"]

    client.update_health_check(
        HealthCheckId=hc_id,
        IPAddress="0.0.0.0",
        Port=80,
        ResourcePath="rp",
        FullyQualifiedDomainName="example.com",
        SearchString="search",
        FailureThreshold=123,
        Inverted=False,
        Disabled=False,
        HealthThreshold=13,
        ChildHealthChecks=["child"],
        Regions=["us-east-1", "us-east-2", "us-west-1"],
    )

    config = client.get_health_check(HealthCheckId=hc_id)["HealthCheck"][
        "HealthCheckConfig"
    ]
    assert config["Type"] == "CALCULATED"
    assert config["ResourcePath"] == "rp"
    assert config["FullyQualifiedDomainName"] == "example.com"
    assert config["SearchString"] == "search"
    assert config["Inverted"] is False
    assert config["Disabled"] is False
    assert config["ChildHealthChecks"] == ["child"]
    assert config["Regions"] == ["us-east-1", "us-east-2", "us-west-1"]


@mock_route53
def test_health_check_status():
    client = boto3.client("route53", region_name="us-east-1")

    hc_id = client.create_health_check(
        CallerReference="callref",
        HealthCheckConfig={
            "Type": "CALCULATED",
            "Inverted": False,
            "Disabled": False,
            "HealthThreshold": 1,
        },
    )["HealthCheck"]["Id"]

    resp = client.get_health_check_status(HealthCheckId=hc_id)
    assert len(resp["HealthCheckObservations"]) == 1

    observation = resp["HealthCheckObservations"][0]
    assert observation["Region"] == "us-east-1"
    assert observation["IPAddress"] == "127.0.13.37"
    assert "StatusReport" in observation
    assert (
        observation["StatusReport"]["Status"]
        == "Success: HTTP Status Code: 200. Resolved IP: 127.0.13.37. OK"
    )

    with pytest.raises(ClientError) as exc:
        client.get_health_check_status(HealthCheckId="bad-id")

    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchHealthCheck"
    assert err["Message"] == "A health check with id bad-id does not exist."
