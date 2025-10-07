import boto3
import pytest

from moto import mock_aws


@mock_aws
def test_create_service():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    resp = client.create_service(name="my-service", authType="NONE")

    assert resp["name"] == "my-service"
    assert resp["status"] == "ACTIVE"
    assert resp["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")
    assert resp["dnsEntry"]["hostedZoneId"].startswith("Z")
    assert resp["id"].startswith("srv-")
    assert resp["authType"] == "NONE"
    assert resp["certificateArn"] == ""
    assert resp["customDomainName"] == ""

@mock_aws
def test_get_service():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    resp = client.create_service(name="my-service", authType="NONE")

    service_arn = resp["arn"]
    service_id = resp["id"]
    service_by_arn = client.get_service(serviceIdentifier=service_arn)
    assert service_by_arn["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")

    service_by_id = client.get_service(serviceIdentifier=service_id)
    assert service_by_id["id"].startswith("svc-")

@mock_aws
def test_get_nonexistent_service():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.get_service(serviceIdentifier="NONEXISTENTSERVICEID")


@mock_aws
def test_list_services():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    client.create_service(name="my-service1", authType="NONE")
    client.create_service(name="my-service2", authType="NONE")

    services = client.list_services()
    assert len(services["items"]) == 2
    assert services["items"][0]["name"] == "my-service1"
    assert services["items"][1]["name"] == "my-service2"

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
    assert resp["id"].startswith("snet-")
    assert resp["authType"] == "NONE"
    assert resp["sharingConfig"] == {"enabled": False}

@mock_aws
def test_get_service_network():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    resp = client.create_service_network(
        name="my-sn",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )

    service_arn = resp["arn"]
    service_id = resp["id"]
    service_by_arn = client.get_service_network(serviceNetworkIdentifier=service_arn)
    assert service_by_arn["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")

    service_by_id = client.get_service_network(serviceNetworkIdentifier=service_id)
    assert service_by_id["id"].startswith("sn-")

@mock_aws
def test_get_nonexistent_service():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.get_service_network(serviceNetworkIdentifier="NONEXISTENTSERVICENETWORKID")

@mock_aws
def test_list_service_networks():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    client.create_service_network(
        name="my-sn1",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )
    client.create_service_network(
        name="my-sn2",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )

    service_networks = client.list_service_networks()
    assert len(service_networks["items"]) == 2
    assert service_networks["items"][0]["name"] == "my-sn1"
    assert service_networks["items"][1]["name"] == "my-sn2"

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
def test_list_tags_for_resource():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    tags = {"tag1": "value1", "tag2": "value2"}
    resp = client.create_service(name="my-service", authType="NONE", tags=tags)
    returned_tags = client.list_tags_for_resource(resourceArn=resp["arn"])
    assert returned_tags["tags"] == tags


@mock_aws
def test_tag_resource():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    tags = {"tag1": "value1", "tag2": "value2"}
    resp = client.create_service(name="my-service", authType="NONE")

    client.tag_resource(resourceArn=resp["arn"], tags=tags)

    returned_tags = client.list_tags_for_resource(resourceArn=resp["arn"])
    assert returned_tags["tags"] == tags


@mock_aws
def test_untag_resource():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    tags = {"tag1": "value1", "tag2": "value2"}
    resp = client.create_service(name="my-service", authType="NONE", tags=tags)
    

    returned_tags = client.list_tags_for_resource(resourceArn=resp["arn"])
    assert returned_tags["tags"] == tags

    client.untag_resource(resourceArn=resp["arn"], tagKeys=["tag1"])

    returned_tags = client.list_tags_for_resource(resourceArn=resp["arn"])
    assert returned_tags["tags"] == {"tag2": "value2"}
