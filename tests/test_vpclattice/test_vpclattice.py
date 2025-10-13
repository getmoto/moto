import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_service():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    resp = client.create_service(name="my-service", authType="NONE")

    assert resp["name"] == "my-service"
    assert resp["status"] == "ACTIVE"
    assert resp["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")
    assert resp["dnsEntry"]["hostedZoneId"].startswith("Z")
    assert resp["id"].startswith("svc-")
    assert resp["authType"] == "NONE"
    assert resp["certificateArn"] == ""
    assert resp["customDomainName"] == ""


@mock_aws
def test_create_service_network():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    resp = client.create_service_network(
        name="my-sn",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )

    assert resp["name"] == "my-sn"
    assert resp["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")
    assert resp["id"].startswith("sn-")
    assert resp["authType"] == "NONE"
    assert resp["sharingConfig"] == {"enabled": False}


@mock_aws
def test_create_service_network_vpc_association():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    resp_sn = client.create_service_network(
        name="my-sn",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )
    resp = client.create_service_network_vpc_association(
        serviceNetworkIdentifier=resp_sn["id"],
        vpcIdentifier="vpc-12345678",
        securityGroupIds=["sg-12345678"],
        clientToken="token456",
    )
    assert resp["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")
    assert resp["id"].startswith("snva-")
    assert resp["createdBy"] == "user"
    assert resp["securityGroupIds"] == ["sg-12345678"]
    assert resp["status"] == "ACTIVE"


@mock_aws
def test_create_rule():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    client.create_service_network(
        name="my-sn",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )
    resp_svc = client.create_service(
        name="my-service",
        authType="NONE",
    )

    resp = client.create_rule(
        listenerIdentifier="listener-1234567890123456",  # must be >=20 chars
        serviceIdentifier=resp_svc["id"],
        name="my-rule",
        priority=1,
        action={
            "forward": {
                "targetGroups": [{"targetGroupIdentifier": "tg-1234567890abcdef"}]
            }
        },
        match={
            "httpMatch": {
                "pathMatch": {"caseSensitive": False, "match": {"exact": "/my-path"}}
            }
        },
        clientToken="token789",
    )

    assert resp["name"] == "my-rule"
    assert resp["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")
    assert resp["id"].startswith("rule-")
    assert resp["priority"] == 1
    assert (
        resp["action"]["forward"]["targetGroups"][0]["targetGroupIdentifier"]
        == "tg-1234567890abcdef"
    )
    assert resp["match"]["httpMatch"]["pathMatch"]["match"]["exact"] == "/my-path"


@mock_aws
def test_create_access_log_subscription():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    resp_sn = client.create_service_network(
        name="my-sn",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )

    resp = client.create_access_log_subscription(
        resourceIdentifier=resp_sn["id"],
        destinationArn="arn:aws:s3:::my-log-bucket",
        clientToken="token456",
        serviceNetworkLogType="RESOURCE",
    )

    assert resp["arn"].startswith("arn:aws:vpc-lattice:us-west-2:")
    assert resp["destinationArn"] == "arn:aws:s3:::my-log-bucket"
    assert resp["id"].startswith("als-")
    assert resp["resourceArn"] == resp_sn["arn"]
    assert resp["resourceId"] == resp_sn["id"]
    assert resp["serviceNetworkLogType"] == "RESOURCE"


@mock_aws
def test_create_access_log_subscription_resources_not_found():
    client = boto3.client("vpc-lattice", region_name="us-west-1")
    with pytest.raises(ClientError) as exc:
        client.create_access_log_subscription(
            resourceIdentifier="sn-invalid-sn-id14",
            destinationArn="arn:aws:s3:::my-log-bucket",
            serviceNetworkLogType="SERVICE",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Resource sn-invalid-sn-id14 not found"

    with pytest.raises(ClientError) as exc:
        client.create_access_log_subscription(
            resourceIdentifier="svc-invalid-svc-id14",
            destinationArn="arn:aws:s3:::my-log-bucket",
            serviceNetworkLogType="SERVICE",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Resource svc-invalid-svc-id14 not found"


@mock_aws
def test_create_access_log_subscription_invalid_resourceIdentifier():
    client = boto3.client("vpc-lattice", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_access_log_subscription(
            resourceIdentifier="invalid-sn-id1234",
            destinationArn="arn:aws:s3:::my-log-bucket",
            serviceNetworkLogType="SERVICE",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Invalid parameter resourceIdentifier, must start with 'sn-' or 'svc-'"
    )


@mock_aws
def test_get_access_log_subscription():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    resp_sn = client.create_service_network(
        name="my-sn",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )

    sub = client.create_access_log_subscription(
        resourceIdentifier=resp_sn["id"],
        destinationArn="arn:aws:s3:::my-log-bucket",
        clientToken="token456",
        serviceNetworkLogType="RESOURCE",
    )

    resp = client.get_access_log_subscription(accessLogSubscriptionIdentifier=sub["id"])
    assert resp["arn"] == sub["arn"]
    assert resp["destinationArn"] == "arn:aws:s3:::my-log-bucket"
    assert resp["id"] == sub["id"]
    assert resp["resourceArn"] == resp_sn["arn"]
    assert resp["resourceId"] == resp_sn["id"]
    assert resp["serviceNetworkLogType"] == "RESOURCE"
    assert "createdAt" in resp
    assert "lastUpdatedAt" in resp

    # Verify with arn, just check one attribute
    resp = client.get_access_log_subscription(
        accessLogSubscriptionIdentifier=sub["arn"]
    )
    assert resp["arn"] == sub["arn"]


@mock_aws
def test_get_access_log_subscription_not_found():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    with pytest.raises(ClientError) as exc:
        client.get_access_log_subscription(
            accessLogSubscriptionIdentifier="als-invalid-id123"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Access Log Subscription als-invalid-id123 not found"


@mock_aws
def test_list_access_log_subscriptions():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    resp_sn = client.create_service_network(
        name="my-sn",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )
    resp_sn_2 = client.create_service_network(
        name="my-sn2",
        authType="NONE",
        clientToken="token456",
        sharingConfig={"enabled": False},
    )

    for i in range(15):
        client.create_access_log_subscription(
            resourceIdentifier=resp_sn["id"],
            destinationArn=f"arn:aws:s3:::my-log-bucket-{i + 2}",
            clientToken=f"token{i:03}",
        )
    for i in range(10):
        client.create_access_log_subscription(
            resourceIdentifier=resp_sn_2["id"],
            destinationArn=f"arn:aws:s3:::my-log-bucket2-{i + 1}",
        )

    subs_list = client.list_access_log_subscriptions(
        resourceIdentifier=resp_sn["id"],
        maxResults=12,
    )
    assert len(subs_list["items"]) == 12
    assert subs_list["items"][0]["resourceId"] == resp_sn["id"]

    subs_list_2 = client.list_access_log_subscriptions(
        resourceIdentifier=resp_sn_2["id"]
    )
    assert len(subs_list_2["items"]) == 10
    assert subs_list_2["items"][0]["resourceId"] == resp_sn_2["id"]


@mock_aws
def test_delete_access_log_subscription():
    client = boto3.client("vpc-lattice", region_name="us-east-1")

    resp_sn = client.create_service_network(
        name="my-sn",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )

    sub = client.create_access_log_subscription(
        resourceIdentifier=resp_sn["id"],
        destinationArn="arn:aws:s3:::my-log-bucket",
        clientToken="tokenabc",
    )

    subs_list = client.list_access_log_subscriptions(
        resourceIdentifier=resp_sn["id"],
    )

    assert len(subs_list["items"]) == 1

    client.delete_access_log_subscription(accessLogSubscriptionIdentifier=sub["arn"])

    subs_list = client.list_access_log_subscriptions(
        resourceIdentifier=resp_sn["id"],
    )

    assert len(subs_list["items"]) == 0


@mock_aws
def test_delete_access_log_subscription_not_found():
    client = boto3.client("vpc-lattice", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.delete_access_log_subscription(
            accessLogSubscriptionIdentifier="als-invalid-id123"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Access Log Subscription als-invalid-id123 not found"


@mock_aws
def test_update_access_log_subscription():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    resp_sn = client.create_service_network(
        name="my-sn",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )

    sub = client.create_access_log_subscription(
        resourceIdentifier=resp_sn["id"],
        destinationArn="arn:aws:s3:::my-log-bucket",
        clientToken="token456",
        serviceNetworkLogType="RESOURCE",
    )

    resp = client.get_access_log_subscription(accessLogSubscriptionIdentifier=sub["id"])
    lastUpdatedAt = resp["lastUpdatedAt"]
    assert resp["destinationArn"] == "arn:aws:s3:::my-log-bucket"

    resp = client.update_access_log_subscription(
        accessLogSubscriptionIdentifier=sub["arn"],
        destinationArn="arn:aws:s3:::my-updated-log-bucket",
    )

    assert resp["arn"] == sub["arn"]
    assert resp["id"] == sub["id"]
    assert resp["resourceArn"] == resp_sn["arn"]
    assert resp["resourceId"] == resp_sn["id"]

    resp = client.get_access_log_subscription(
        accessLogSubscriptionIdentifier=sub["arn"]
    )
    assert resp["destinationArn"] == "arn:aws:s3:::my-updated-log-bucket"
    assert resp["lastUpdatedAt"] > lastUpdatedAt


@mock_aws
def test_update_access_log_subscription_not_found():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    with pytest.raises(ClientError) as exc:
        client.update_access_log_subscription(
            accessLogSubscriptionIdentifier="als-invalid-id123",
            destinationArn="arn:aws:s3:::my-updated-log-bucket",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Access Log Subscription als-invalid-id123 not found"
