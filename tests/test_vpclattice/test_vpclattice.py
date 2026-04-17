import json

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
def test_get_service():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    resp = client.create_service(name="my-service", authType="NONE")

    service_arn = resp["arn"]
    service_id = resp["id"]

    # lookup by id
    service_by_id = client.get_service(serviceIdentifier=service_id)
    assert service_by_id["id"].startswith("svc-")
    assert service_by_id["status"] == "ACTIVE"
    assert service_by_id["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")
    assert service_by_id["dnsEntry"]["hostedZoneId"].startswith("Z")
    assert service_by_id["authType"] == "NONE"
    assert service_by_id["certificateArn"] == ""
    assert service_by_id["customDomainName"] == ""

    # lookup by arn
    service_by_arn = client.get_service(serviceIdentifier=service_arn)
    assert service_by_arn["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")


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
    assert resp["id"].startswith("sn-")
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

    # lookup by id
    service_by_id = client.get_service_network(serviceNetworkIdentifier=service_id)
    assert service_by_id["name"] == "my-sn"
    assert service_by_id["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")
    assert service_by_id["id"].startswith("sn-")
    assert service_by_id["authType"] == "NONE"
    assert service_by_id["sharingConfig"] == {"enabled": False}

    # lookup by arn
    service_by_arn = client.get_service_network(serviceNetworkIdentifier=service_arn)
    assert service_by_arn["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")


@mock_aws
def test_get_nonexistent_service_network():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.get_service_network(
            serviceNetworkIdentifier="NONEXISTENTSERVICENETWORKID"
        )


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


@mock_aws
def test_snva_tag_resource():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    tags = {"tag1": "value1", "tag2": "value2"}

    resp_sn = client.create_service_network(
        name="my-sn",
        authType="NONE",
    )
    resp = client.create_service_network_vpc_association(
        serviceNetworkIdentifier=resp_sn["id"],
        vpcIdentifier="vpc-12345678",
        tags=tags,
    )

    returned_tags = client.list_tags_for_resource(resourceArn=resp["arn"])
    assert returned_tags["tags"] == tags

    client.untag_resource(resourceArn=resp["arn"], tagKeys=["tag1"])
    returned_tags = client.list_tags_for_resource(resourceArn=resp["arn"])
    assert returned_tags["tags"] == {"tag2": "value2"}


@mock_aws
def test_rule_tag_resource():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    tags = {"tag1": "value1", "tag2": "value2"}

    resp_svc = client.create_service(
        name="my-service",
        authType="NONE",
    )

    resp = client.create_rule(
        listenerIdentifier="listener-1234567890123456",
        serviceIdentifier=resp_svc["id"],
        name="my-rule",
        priority=1,
        match={
            "httpMatch": {
                "pathMatch": {"caseSensitive": False, "match": {"exact": "/my-path"}}
            }
        },
        action={
            "forward": {
                "targetGroups": [{"targetGroupIdentifier": "tg-1234567890abcdef"}]
            }
        },
        tags=tags,
    )

    returned_tags = client.list_tags_for_resource(resourceArn=resp["arn"])
    assert returned_tags["tags"] == tags

    client.untag_resource(resourceArn=resp["arn"], tagKeys=["tag1"])
    returned_tags = client.list_tags_for_resource(resourceArn=resp["arn"])
    assert returned_tags["tags"] == {"tag2": "value2"}


@mock_aws
def test_als_tag_resource():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    tags = {"tag1": "value1", "tag2": "value2"}

    resp_sn = client.create_service_network(
        name="my-sn",
        authType="NONE",
    )

    resp = client.create_access_log_subscription(
        resourceIdentifier=resp_sn["id"],
        destinationArn="arn:aws:s3:::my-log-bucket",
        serviceNetworkLogType="RESOURCE",
        tags=tags,
    )

    returned_tags = client.list_tags_for_resource(resourceArn=resp["arn"])
    assert returned_tags["tags"] == tags

    client.untag_resource(resourceArn=resp["arn"], tagKeys=["tag1"])
    returned_tags = client.list_tags_for_resource(resourceArn=resp["arn"])
    assert returned_tags["tags"] == {"tag2": "value2"}


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


@mock_aws
def test_put_auth_policy():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    svc = client.create_service(name="my-service", authType="AWS_IAM")
    sn = client.create_service_network(name="my-sn", authType="NONE")

    policy_document = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "vpc-lattice-svcs:Invoke",
                    "Resource": svc["arn"],
                }
            ],
        }
    )

    put_resp = client.put_auth_policy(
        resourceIdentifier=svc["arn"],
        policy=policy_document,
    )

    assert put_resp["policy"] == policy_document
    assert put_resp["state"] == "Active"

    put_resp = client.put_auth_policy(
        resourceIdentifier=sn["arn"],
        policy=policy_document,
    )

    assert put_resp["policy"] == policy_document
    assert put_resp["state"] == "Inactive"


@mock_aws
def test_update_auth_policy():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    resp = client.create_service(name="my-service", authType="AWS_IAM")

    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "vpc-lattice-svcs:Invoke",
                "Resource": resp["arn"],
            }
        ],
    }

    put_resp = client.put_auth_policy(
        resourceIdentifier=resp["arn"],
        policy=json.dumps(policy_document),
    )

    assert put_resp["policy"] == json.dumps(policy_document)

    policy_document["Statement"][0]["Effect"] = "Deny"

    put_resp = client.put_auth_policy(
        resourceIdentifier=resp["arn"],
        policy=json.dumps(policy_document),
    )

    assert put_resp["policy"] == json.dumps(policy_document)
    assert put_resp["state"] == "Active"


@mock_aws
def test_get_auth_policy():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    svc = client.create_service(name="my-service", authType="NONE")
    sn = client.create_service_network(name="my-sn", authType="AWS_IAM")

    policy_document = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "vpc-lattice-svcs:Invoke",
                    "Resource": svc["arn"],
                }
            ],
        }
    )

    client.put_auth_policy(
        resourceIdentifier=svc["arn"],
        policy=policy_document,
    )

    resp = client.get_auth_policy(resourceIdentifier=svc["arn"])

    assert resp["policy"] == policy_document
    assert resp["state"] == "Inactive"

    resp = client.put_auth_policy(
        resourceIdentifier=sn["arn"],
        policy=policy_document,
    )

    resp = client.get_auth_policy(resourceIdentifier=sn["arn"])

    assert resp["policy"] == policy_document
    assert resp["state"] == "Active"


@mock_aws
def test_auth_policy_resource_not_found():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    id = "svc-invalid-id123"
    with pytest.raises(ClientError) as exc:
        client.get_auth_policy(resourceIdentifier=id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"Resource {id} not found"

    with pytest.raises(ClientError) as exc:
        client.delete_auth_policy(resourceIdentifier=id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"Resource {id} not found"

    with pytest.raises(ClientError) as exc:
        client.put_auth_policy(resourceIdentifier=id, policy="{}")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"Resource {id} not found"


@mock_aws
def test_auth_policy_invalid_parameter():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    with pytest.raises(ClientError) as exc:
        client.put_auth_policy(resourceIdentifier="invalid-id1234567", policy="{}")
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Invalid parameter resourceIdentifier, must start with 'sn-' or 'svc-'"
    )


@mock_aws
def test_delete_auth_policy():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    resp = client.create_service(name="my-service", authType="NONE")

    policy_document = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "vpc-lattice-svcs:Invoke",
                    "Resource": resp["arn"],
                }
            ],
        }
    )

    client.put_auth_policy(
        resourceIdentifier=resp["arn"],
        policy=policy_document,
    )

    client.delete_auth_policy(resourceIdentifier=resp["arn"])

    with pytest.raises(ClientError) as exc:
        client.get_auth_policy(resourceIdentifier=resp["arn"])
    err = exc.value.response["Error"]

    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"Resource {resp['arn']} not found"


@mock_aws
def test_put_resource_policy():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    resp = client.create_service(name="my-service", authType="NONE")

    policy_document = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "vpc-lattice-svcs:Invoke",
                    "Resource": resp["arn"],
                }
            ],
        }
    )

    client.put_resource_policy(
        resourceArn=resp["arn"],
        policy=policy_document,
    )

    resp = client.get_resource_policy(resourceArn=resp["arn"])

    assert resp["policy"] == policy_document


@mock_aws
def test_resource_policy_not_found():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    arn = "arn:aws:vpc-lattice:us-west-2:123456789012:service/svc-invalid-id123"
    with pytest.raises(ClientError) as exc:
        client.get_resource_policy(resourceArn=arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"Resource {arn} not found"

    with pytest.raises(ClientError) as exc:
        client.delete_resource_policy(resourceArn=arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"Resource {arn} not found"


@mock_aws
def test_delete_resource_policy():
    client = boto3.client("vpc-lattice", region_name="us-west-2")

    resp = client.create_service(name="my-service", authType="NONE")

    arn = resp["arn"]
    policy_document = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "vpc-lattice-svcs:Invoke",
                    "Resource": resp["arn"],
                }
            ],
        }
    )

    client.put_resource_policy(
        resourceArn=arn,
        policy=policy_document,
    )

    resp = client.get_resource_policy(resourceArn=arn)
    assert resp["policy"] == policy_document

    client.delete_resource_policy(resourceArn=arn)

    with pytest.raises(ClientError) as exc:
        client.delete_resource_policy(resourceArn=arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"Resource {arn} not found"


@mock_aws
def test_list_access_log_subscriptions_with_arn():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    resp = client.create_service(name="my-service", authType="NONE")
    client.create_access_log_subscription(
        resourceIdentifier=resp["id"],
        destinationArn="arn:aws:s3:::my-log-bucket",
        serviceNetworkLogType="SERVICE",
    )
    results = client.list_access_log_subscriptions(
        resourceIdentifier=resp["arn"],
        maxResults=12,
    )
    assert len(results["items"]) == 1


@mock_aws
def test_list_service_network_vpc_associations():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    resp = client.create_service_network(name="my-sn", authType="AWS_IAM")
    client.create_service_network_vpc_association(
        serviceNetworkIdentifier=resp["id"],
        vpcIdentifier="vpc-12345678901234567",
    )
    results = client.list_service_network_vpc_associations(
        serviceNetworkIdentifier=resp["arn"],
        maxResults=12,
    )
    assert len(results["items"]) == 1


@mock_aws
def test_list_service_network_vpc_associations_with_vpc_identifier():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")
    resp = client.create_service_network(name="my-sn", authType="AWS_IAM")

    # Association 1
    client.create_service_network_vpc_association(
        serviceNetworkIdentifier=resp["id"],
        vpcIdentifier="vpc-12345678901234567",
    )

    # Association 2 with different VPC
    client.create_service_network_vpc_association(
        serviceNetworkIdentifier=resp["id"],
        vpcIdentifier="vpc-99999999999999999",
    )

    results = client.list_service_network_vpc_associations(
        vpcIdentifier="vpc-12345678901234567",
        maxResults=12,
    )

    assert len(results["items"]) == 1
    assert results["items"][0]["vpcId"] == "vpc-12345678901234567"


# Listeners
@mock_aws
def test_create_listener():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    service_resp = client.create_service(name="my-service", authType="NONE")
    service_id = service_resp["id"]

    resp = client.create_listener(
        serviceIdentifier=service_id,
        name="my-listener",
        protocol="HTTP",
        port=80,
        defaultAction={
            "forward": {
                "targetGroups": [
                    {"targetGroupIdentifier": "targetgroupidentifier", "weight": 100}
                ]
            }
        },
        clientToken="token123",
    )

    assert resp["name"] == "my-listener"
    assert resp["protocol"] == "HTTP"
    assert resp["port"] == 80
    assert resp["serviceId"] == service_id
    assert resp["id"].startswith("listener-")
    assert resp["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")
    assert "serviceArn" in resp


@mock_aws
def test_get_listener_by_id():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    service_resp = client.create_service(name="my-service", authType="NONE")
    service_id = service_resp["id"]

    create_resp = client.create_listener(
        serviceIdentifier=service_id,
        name="my-listener",
        protocol="HTTP",
        port=80,
        defaultAction={
            "forward": {
                "targetGroups": [{"targetGroupIdentifier": "tg-1234567890abcdef"}]
            }
        },
    )
    listener_id = create_resp["id"]

    get_resp = client.get_listener(
        serviceIdentifier=service_id,
        listenerIdentifier=listener_id,
    )

    assert get_resp["id"] == listener_id
    assert get_resp["name"] == "my-listener"
    assert get_resp["protocol"] == "HTTP"


@mock_aws
def test_get_listener_by_arn():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    service_resp = client.create_service(name="my-service", authType="NONE")
    service_id = service_resp["id"]

    create_resp = client.create_listener(
        serviceIdentifier=service_id,
        name="my-listener",
        protocol="HTTP",
        port=80,
        defaultAction={
            "forward": {
                "targetGroups": [{"targetGroupIdentifier": "tg-1234567890abcdef"}]
            }
        },
    )
    listener_arn = create_resp["arn"]

    get_resp = client.get_listener(
        serviceIdentifier=service_id,
        listenerIdentifier=listener_arn,
    )

    assert get_resp["arn"] == listener_arn


@mock_aws
def test_get_nonexistent_listener():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    service_resp = client.create_service(name="my-service", authType="NONE")
    service_id = service_resp["id"]

    with pytest.raises(ClientError) as exc:
        client.get_listener(
            serviceIdentifier=service_id, listenerIdentifier="listener-nonexistent"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Listener listener-nonexistent not found"


@mock_aws
def test_list_listeners():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    service_resp = client.create_service(name="my-service", authType="NONE")
    service_id = service_resp["id"]

    for i in range(3):
        client.create_listener(
            serviceIdentifier=service_id,
            name=f"listener-{i}",
            protocol="HTTP",
            port=80 + i,
            defaultAction={
                "forward": {
                    "targetGroups": [{"targetGroupIdentifier": "tg-1234567890abcdef"}]
                }
            },
        )

    resp = client.list_listeners(serviceIdentifier=service_id)

    assert len(resp["items"]) == 3
    assert resp["items"][0]["name"] == "listener-0"
    assert resp["items"][1]["name"] == "listener-1"
    assert resp["items"][2]["name"] == "listener-2"


# Target Groups
@mock_aws
def test_create_target_group():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    resp = client.create_target_group(
        name="my-instance-target-group",
        type="INSTANCE",
        config={
            "port": 8080,
            "protocol": "HTTP",
            "vpcIdentifier": "vpc-12345678",
        },
    )

    assert resp["type"] == "INSTANCE"
    assert resp["config"]["port"] == 8080


@mock_aws
def test_get_target_group_by_id():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    create_resp = client.create_target_group(
        name="my-target-group",
        type="IP",
        config={
            "port": 80,
            "protocol": "HTTP",
            "vpcIdentifier": "vpc-12345678",
        },
    )
    tg_id = create_resp["id"]

    get_resp = client.get_target_group(targetGroupIdentifier=tg_id)

    assert get_resp["id"] == tg_id
    assert get_resp["name"] == "my-target-group"
    assert get_resp["type"] == "IP"


@mock_aws
def test_get_target_group_by_arn():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    create_resp = client.create_target_group(
        name="my-target-group",
        type="IP",
        config={
            "port": 80,
            "protocol": "HTTP",
            "vpcIdentifier": "vpc-12345678",
        },
    )
    tg_arn = create_resp["arn"]

    get_resp = client.get_target_group(targetGroupIdentifier=tg_arn)

    assert get_resp["arn"] == tg_arn


@mock_aws
def test_get_nonexistent_target_group():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_target_group(targetGroupIdentifier="nonexistent-target-group-arn")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Target group nonexistent-target-group-arn not found"


@mock_aws
def test_list_target_groups():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    for i in range(3):
        client.create_target_group(
            name=f"target-group-{i}",
            type="IP",
            config={
                "port": 80 + i,
                "protocol": "HTTP",
                "vpcIdentifier": "vpc-12345678",
            },
        )

    resp = client.list_target_groups()

    assert len(resp["items"]) == 3
    assert resp["items"][0]["name"] == "target-group-0"
    assert resp["items"][1]["name"] == "target-group-1"
    assert resp["items"][2]["name"] == "target-group-2"


# Service Network Resource Associations
@mock_aws
def test_create_service_network_resource_association():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    sn_resp = client.create_service_network(
        name="my-service-network",
        authType="NONE",
    )
    sn_id = sn_resp["id"]

    resp = client.create_service_network_resource_association(
        serviceNetworkIdentifier=sn_id,
        resourceConfigurationIdentifier="some-resource-config-id",
        clientToken="token123",
    )

    assert resp["id"].startswith("snra-")
    assert resp["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")
    assert resp["status"] == "ACTIVE"
    assert resp["createdBy"] == "user"


@mock_aws
def test_get_service_network_resource_association_by_id():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    sn_resp = client.create_service_network(
        name="my-service-network",
        authType="NONE",
    )
    sn_id = sn_resp["id"]

    create_resp = client.create_service_network_resource_association(
        serviceNetworkIdentifier=sn_id,
        resourceConfigurationIdentifier="some-resource-config-id",
    )
    assoc_id = create_resp["id"]

    get_resp = client.get_service_network_resource_association(
        serviceNetworkResourceAssociationIdentifier=assoc_id,
    )

    assert get_resp["id"] == assoc_id
    assert get_resp["status"] == "ACTIVE"


@mock_aws
def test_get_service_network_resource_association_by_arn():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    sn_resp = client.create_service_network(
        name="my-service-network",
        authType="NONE",
    )
    sn_id = sn_resp["id"]

    create_resp = client.create_service_network_resource_association(
        serviceNetworkIdentifier=sn_id,
        resourceConfigurationIdentifier="some-resource-config-id",
    )
    assoc_arn = create_resp["arn"]

    get_resp = client.get_service_network_resource_association(
        serviceNetworkResourceAssociationIdentifier=assoc_arn,
    )

    assert get_resp["arn"] == assoc_arn


@mock_aws
def test_get_nonexistent_service_network_resource_association():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_service_network_resource_association(
            serviceNetworkResourceAssociationIdentifier="nonexistent-association-arn"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "Service network resource association nonexistent-association-arn not found"
    )


@mock_aws
def test_list_service_network_resource_associations():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    sn_resp = client.create_service_network(
        name="my-service-network",
        authType="NONE",
    )
    sn_id = sn_resp["id"]

    for _i in range(3):
        client.create_service_network_resource_association(
            serviceNetworkIdentifier=sn_id,
            resourceConfigurationIdentifier="some-resource-config-id",
        )

    resp = client.list_service_network_resource_associations(
        serviceNetworkIdentifier=sn_id,
        resourceConfigurationIdentifier="some-resource-config-id",
    )

    assert len(resp["items"]) == 3


# Service Network Service Associations
@mock_aws
def test_create_service_network_service_association():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    sn_resp = client.create_service_network(
        name="my-service-network",
        authType="NONE",
    )
    sn_id = sn_resp["id"]

    service_resp = client.create_service(
        name="my-service",
        authType="NONE",
    )
    service_id = service_resp["id"]

    resp = client.create_service_network_service_association(
        serviceNetworkIdentifier=sn_id,
        serviceIdentifier=service_id,
        clientToken="token123",
    )

    assert resp["id"].startswith("snsa-")
    assert resp["arn"].startswith("arn:aws:vpc-lattice:ap-southeast-1:")
    assert resp["status"] == "ACTIVE"
    assert resp["createdBy"] == "user"


@mock_aws
def test_get_service_network_service_association_by_id():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    sn_resp = client.create_service_network(
        name="my-service-network",
        authType="NONE",
    )
    sn_id = sn_resp["id"]

    service_resp = client.create_service(
        name="my-service",
        authType="NONE",
    )
    service_id = service_resp["id"]

    create_resp = client.create_service_network_service_association(
        serviceNetworkIdentifier=sn_id,
        serviceIdentifier=service_id,
    )
    assoc_id = create_resp["id"]

    get_resp = client.get_service_network_service_association(
        serviceNetworkServiceAssociationIdentifier=assoc_id,
    )

    assert get_resp["id"] == assoc_id
    assert get_resp["status"] == "ACTIVE"


@mock_aws
def test_get_service_network_service_association_by_arn():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    sn_resp = client.create_service_network(
        name="my-service-network",
        authType="NONE",
    )
    sn_id = sn_resp["id"]

    service_resp = client.create_service(
        name="my-service",
        authType="NONE",
    )
    service_id = service_resp["id"]

    create_resp = client.create_service_network_service_association(
        serviceNetworkIdentifier=sn_id,
        serviceIdentifier=service_id,
    )
    assoc_arn = create_resp["arn"]

    get_resp = client.get_service_network_service_association(
        serviceNetworkServiceAssociationIdentifier=assoc_arn,
    )

    assert get_resp["arn"] == assoc_arn


@mock_aws
def test_get_nonexistent_service_network_service_association():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_service_network_service_association(
            serviceNetworkServiceAssociationIdentifier="nonexistent-service-network-arn"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "Service network service association nonexistent-service-network-arn not found"
    )


@mock_aws
def test_list_service_network_service_associations():
    client = boto3.client("vpc-lattice", region_name="ap-southeast-1")

    sn_resp = client.create_service_network(
        name="my-service-network",
        authType="NONE",
    )
    sn_id = sn_resp["id"]

    for i in range(3):
        service_resp = client.create_service(
            name=f"service-{i}",
            authType="NONE",
        )
        client.create_service_network_service_association(
            serviceNetworkIdentifier=sn_id,
            serviceIdentifier=service_resp["id"],
        )

    resp = client.list_service_network_service_associations(
        serviceNetworkIdentifier=sn_id,
    )

    assert len(resp["items"]) == 3
