from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID
from tests import EXAMPLE_AMI_ID


@pytest.mark.parametrize("region_name", ["us-east-1", "ap-south-1"])
@pytest.mark.parametrize("zones", [["a"], ["a", "b"]])
@mock_aws
def test_create_load_balancer(zones, region_name):
    zones = [f"{region_name}{z}" for z in zones]
    # Both regions and availability zones are parametrized
    # This does not seem to have an effect on the DNS name
    client = boto3.client("elb", region_name=region_name)
    ec2 = boto3.resource("ec2", region_name=region_name)

    security_group = ec2.create_security_group(
        GroupName="sg01", Description="Test security group sg01"
    )

    lb = client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[
            {"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080},
            {"Protocol": "http", "LoadBalancerPort": 81, "InstancePort": 9000},
        ],
        AvailabilityZones=zones,
        Scheme="internal",
        SecurityGroups=[security_group.id],
    )
    assert lb["DNSName"] == "my-lb.us-east-1.elb.amazonaws.com"

    describe = client.describe_load_balancers(LoadBalancerNames=["my-lb"])[
        "LoadBalancerDescriptions"
    ][0]
    assert describe["LoadBalancerName"] == "my-lb"
    assert describe["DNSName"] == "my-lb.us-east-1.elb.amazonaws.com"
    assert describe["CanonicalHostedZoneName"] == "my-lb.us-east-1.elb.amazonaws.com"
    assert describe["AvailabilityZones"] == zones
    assert "VPCId" in describe
    assert len(describe["Subnets"]) == len(zones)  # Default subnet for each zone
    assert describe["SecurityGroups"] == [security_group.id]
    assert describe["Scheme"] == "internal"

    assert len(describe["ListenerDescriptions"]) == 2

    tcp = [
        desc["Listener"]
        for desc in describe["ListenerDescriptions"]
        if desc["Listener"]["Protocol"] == "TCP"
    ][0]
    http = [
        desc["Listener"]
        for desc in describe["ListenerDescriptions"]
        if desc["Listener"]["Protocol"] == "HTTP"
    ][0]
    assert tcp == {
        "Protocol": "TCP",
        "LoadBalancerPort": 80,
        "InstanceProtocol": "TCP",
        "InstancePort": 8080,
        "SSLCertificateId": "None",
    }
    assert http == {
        "Protocol": "HTTP",
        "LoadBalancerPort": 81,
        "InstanceProtocol": "HTTP",
        "InstancePort": 9000,
        "SSLCertificateId": "None",
    }


@mock_aws
def test_get_missing_elb():
    client = boto3.client("elb", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        client.describe_load_balancers(LoadBalancerNames=["unknown-lb"])
    err = ex.value.response["Error"]
    assert err["Code"] == "LoadBalancerNotFound"
    assert err["Message"] == "The specified load balancer does not exist: unknown-lb"


@mock_aws
def test_create_elb_in_multiple_region():
    client_east = boto3.client("elb", region_name="us-east-2")
    client_west = boto3.client("elb", region_name="us-west-2")

    name_east = str(uuid4())[0:6]
    name_west = str(uuid4())[0:6]

    client_east.create_load_balancer(
        LoadBalancerName=name_east,
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-2a"],
    )
    client_west.create_load_balancer(
        LoadBalancerName=name_west,
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-west-2a"],
    )

    east_names = [
        lb["LoadBalancerName"]
        for lb in client_east.describe_load_balancers()["LoadBalancerDescriptions"]
    ]
    assert name_east in east_names
    assert name_west not in east_names

    west_names = [
        lb["LoadBalancerName"]
        for lb in client_west.describe_load_balancers()["LoadBalancerDescriptions"]
    ]
    assert name_west in west_names
    assert name_east not in west_names


@mock_aws
def test_create_load_balancer_with_certificate():
    acm_client = boto3.client("acm", region_name="us-east-2")
    acm_request_response = acm_client.request_certificate(
        DomainName="fake.domain.com",
        DomainValidationOptions=[
            {"DomainName": "fake.domain.com", "ValidationDomain": "domain.com"},
        ],
    )
    certificate_arn = acm_request_response["CertificateArn"]

    client = boto3.client("elb", region_name="us-east-2")

    name = str(uuid4())[0:6]

    client.create_load_balancer(
        LoadBalancerName=name,
        Listeners=[
            {
                "Protocol": "https",
                "LoadBalancerPort": 8443,
                "InstancePort": 443,
                "SSLCertificateId": certificate_arn,
            }
        ],
        AvailabilityZones=["us-east-2a"],
    )
    describe = client.describe_load_balancers(LoadBalancerNames=[name])[
        "LoadBalancerDescriptions"
    ][0]
    assert describe["Scheme"] == "internet-facing"

    listener = describe["ListenerDescriptions"][0]["Listener"]
    assert listener["Protocol"] == "HTTPS"
    assert listener["SSLCertificateId"] == certificate_arn


@mock_aws
def test_create_load_balancer_with_invalid_certificate():
    client = boto3.client("elb", region_name="us-east-2")

    name = str(uuid4())[0:6]

    with pytest.raises(ClientError) as exc:
        client.create_load_balancer(
            LoadBalancerName=name,
            Listeners=[
                {
                    "Protocol": "https",
                    "LoadBalancerPort": 8443,
                    "InstancePort": 443,
                    "SSLCertificateId": "invalid_arn",
                }
            ],
            AvailabilityZones=["us-east-2a"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "CertificateNotFoundException"


@mock_aws
def test_create_and_delete_load_balancer():
    client = boto3.client("elb", region_name="us-east-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )
    assert len(client.describe_load_balancers()["LoadBalancerDescriptions"]) == 1

    client.delete_load_balancer(LoadBalancerName="my-lb")
    assert len(client.describe_load_balancers()["LoadBalancerDescriptions"]) == 0


@mock_aws
def test_create_load_balancer_with_no_listeners_defined():
    client = boto3.client("elb", region_name="us-east-1")

    with pytest.raises(ClientError):
        client.create_load_balancer(
            LoadBalancerName="my-lb",
            Listeners=[],
            AvailabilityZones=["us-east-1a", "us-east-1b"],
        )


@mock_aws
def test_create_load_balancer_without_security_groups():
    lb_name = str(uuid4())[0:6]
    client = boto3.client("elb", region_name="us-east-1")
    ec2 = boto3.client("ec2", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        AvailabilityZones=["us-east-1a"],
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
    )
    describe = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    assert len(describe["SecurityGroups"]) == 1
    sec_group_id = describe["SecurityGroups"][0]
    sg = ec2.describe_security_groups(GroupIds=[sec_group_id])["SecurityGroups"][0]
    assert sg["GroupName"].startswith("default_elb_")


@mock_aws
def test_describe_paginated_balancers():
    client = boto3.client("elb", region_name="us-east-1")

    for i in range(51):
        client.create_load_balancer(
            LoadBalancerName=f"my-lb{i}",
            Listeners=[
                {"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}
            ],
            AvailabilityZones=["us-east-1a", "us-east-1b"],
        )

    resp = client.describe_load_balancers()
    assert len(resp["LoadBalancerDescriptions"]) == 50
    assert (
        resp["NextMarker"] == resp["LoadBalancerDescriptions"][-1]["LoadBalancerName"]
    )
    resp2 = client.describe_load_balancers(Marker=resp["NextMarker"])
    assert len(resp2["LoadBalancerDescriptions"]) == 1
    assert "NextToken" not in resp2.keys()


@mock_aws
def test_apply_security_groups_to_load_balancer():
    client = boto3.client("elb", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    security_group = ec2.create_security_group(
        GroupName="sg01", Description="Test security group sg01", VpcId=vpc.id
    )

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    response = client.apply_security_groups_to_load_balancer(
        LoadBalancerName="my-lb", SecurityGroups=[security_group.id]
    )

    assert response["SecurityGroups"] == [security_group.id]
    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    assert balancer["SecurityGroups"] == [security_group.id]

    # Using a not-real security group raises an error
    with pytest.raises(ClientError) as error:
        response = client.apply_security_groups_to_load_balancer(
            LoadBalancerName="my-lb", SecurityGroups=["not-really-a-security-group"]
        )
    assert "One or more of the specified security groups do not exist." in str(
        error.value
    )


@mock_aws
def test_create_and_delete_listener():
    client = boto3.client("elb", region_name="us-east-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )
    assert len(client.describe_load_balancers()["LoadBalancerDescriptions"]) == 1

    client.create_load_balancer_listeners(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 443, "InstancePort": 8443}],
    )
    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    assert len(balancer["ListenerDescriptions"]) == 2
    assert balancer["ListenerDescriptions"][0]["Listener"]["Protocol"] == "HTTP"
    assert balancer["ListenerDescriptions"][0]["Listener"]["LoadBalancerPort"] == 80
    assert balancer["ListenerDescriptions"][0]["Listener"]["InstancePort"] == 8080
    assert balancer["ListenerDescriptions"][1]["Listener"]["Protocol"] == "TCP"
    assert balancer["ListenerDescriptions"][1]["Listener"]["LoadBalancerPort"] == 443
    assert balancer["ListenerDescriptions"][1]["Listener"]["InstancePort"] == 8443

    client.delete_load_balancer_listeners(
        LoadBalancerName="my-lb", LoadBalancerPorts=[443]
    )

    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    assert len(balancer["ListenerDescriptions"]) == 1


@mock_aws
@pytest.mark.parametrize("first,second", [["tcp", "http"], ["http", "TCP"]])
def test_create_duplicate_listener_different_protocols(first, second):
    client = boto3.client("elb", region_name="us-east-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": first, "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    # Creating this listener with an conflicting definition throws error
    with pytest.raises(ClientError) as exc:
        client.create_load_balancer_listeners(
            LoadBalancerName="my-lb",
            Listeners=[
                {"Protocol": second, "LoadBalancerPort": 80, "InstancePort": 8080}
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "DuplicateListener"
    assert (
        err["Message"]
        == "A listener already exists for my-lb with LoadBalancerPort 80, but with a different InstancePort, Protocol, or SSLCertificateId"
    )


@mock_aws
@pytest.mark.parametrize(
    "first,second", [["tcp", "tcp"], ["tcp", "TcP"], ["http", "HTTP"]]
)
def test_create_duplicate_listener_same_details(first, second):
    client = boto3.client("elb", region_name="us-east-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": first, "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    # Creating this listener with the same definition succeeds
    client.create_load_balancer_listeners(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": second, "LoadBalancerPort": 80, "InstancePort": 8080}],
    )

    # We still only have one though
    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    assert len(balancer["ListenerDescriptions"]) == 1


@mock_aws
def test_create_lb_listener_with_ssl_certificate_from_acm():
    acm_client = boto3.client("acm", region_name="eu-west-1")
    acm_request_response = acm_client.request_certificate(
        DomainName="fake.domain.com",
        DomainValidationOptions=[
            {"DomainName": "fake.domain.com", "ValidationDomain": "domain.com"},
        ],
    )
    certificate_arn = acm_request_response["CertificateArn"]

    client = boto3.client("elb", region_name="eu-west-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["eu-west-1a", "eu-west-1b"],
    )

    client.create_load_balancer_listeners(
        LoadBalancerName="my-lb",
        Listeners=[
            {
                "Protocol": "tcp",
                "LoadBalancerPort": 443,
                "InstancePort": 8443,
                "SSLCertificateId": certificate_arn,
            }
        ],
    )
    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    listeners = balancer["ListenerDescriptions"]
    assert len(listeners) == 2

    assert listeners[0]["Listener"]["Protocol"] == "HTTP"
    assert listeners[0]["Listener"]["SSLCertificateId"] == "None"

    assert listeners[1]["Listener"]["Protocol"] == "TCP"
    assert listeners[1]["Listener"]["SSLCertificateId"] == certificate_arn


@mock_aws
def test_create_lb_listener_with_ssl_certificate_from_iam():
    iam_client = boto3.client("iam", region_name="eu-west-2")
    iam_cert_response = iam_client.upload_server_certificate(
        ServerCertificateName="test-cert",
        CertificateBody="cert-body",
        PrivateKey="private-key",
    )
    certificate_arn = iam_cert_response["ServerCertificateMetadata"]["Arn"]

    client = boto3.client("elb", region_name="eu-west-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["eu-west-1a", "eu-west-1b"],
    )

    client.create_load_balancer_listeners(
        LoadBalancerName="my-lb",
        Listeners=[
            {
                "Protocol": "tcp",
                "LoadBalancerPort": 443,
                "InstancePort": 8443,
                "SSLCertificateId": certificate_arn,
            }
        ],
    )
    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    listeners = balancer["ListenerDescriptions"]
    assert len(listeners) == 2

    assert listeners[0]["Listener"]["Protocol"] == "HTTP"
    assert listeners[0]["Listener"]["SSLCertificateId"] == "None"

    assert listeners[1]["Listener"]["Protocol"] == "TCP"
    assert listeners[1]["Listener"]["SSLCertificateId"] == certificate_arn


@mock_aws
def test_create_lb_listener_with_invalid_ssl_certificate():
    client = boto3.client("elb", region_name="eu-west-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["eu-west-1a", "eu-west-1b"],
    )

    with pytest.raises(ClientError) as exc:
        client.create_load_balancer_listeners(
            LoadBalancerName="my-lb",
            Listeners=[
                {
                    "Protocol": "tcp",
                    "LoadBalancerPort": 443,
                    "InstancePort": 8443,
                    "SSLCertificateId": "unknownarn",
                }
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "CertificateNotFoundException"


@mock_aws
def test_set_sslcertificate():
    acm_client = boto3.client("acm", region_name="us-east-1")
    acm_request_response = acm_client.request_certificate(
        DomainName="fake.domain.com",
        DomainValidationOptions=[
            {"DomainName": "fake.domain.com", "ValidationDomain": "domain.com"},
        ],
    )
    certificate_arn = acm_request_response["CertificateArn"]

    client = boto3.client("elb", region_name="us-east-1")
    lb_name = str(uuid4())[0:6]

    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[
            {"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080},
            {"Protocol": "https", "LoadBalancerPort": 81, "InstancePort": 8081},
        ],
        AvailabilityZones=["us-east-1a"],
    )

    client.set_load_balancer_listener_ssl_certificate(
        LoadBalancerName=lb_name, LoadBalancerPort=81, SSLCertificateId=certificate_arn
    )

    elb = client.describe_load_balancers()["LoadBalancerDescriptions"][0]

    listener = elb["ListenerDescriptions"][0]["Listener"]
    assert listener["LoadBalancerPort"] == 80
    assert listener["SSLCertificateId"] == "None"

    listener = elb["ListenerDescriptions"][1]["Listener"]
    assert listener["LoadBalancerPort"] == 81
    assert listener["SSLCertificateId"] == certificate_arn


@mock_aws
def test_get_load_balancers_by_name():
    client = boto3.client("elb", region_name="us-east-1")
    lb_name1 = str(uuid4())[0:6]
    lb_name2 = str(uuid4())[0:6]

    client.create_load_balancer(
        LoadBalancerName=lb_name1,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    client.create_load_balancer(
        LoadBalancerName=lb_name2,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    lbs = client.describe_load_balancers(LoadBalancerNames=[lb_name1])
    assert len(lbs["LoadBalancerDescriptions"]) == 1

    lbs = client.describe_load_balancers(LoadBalancerNames=[lb_name2])
    assert len(lbs["LoadBalancerDescriptions"]) == 1

    lbs = client.describe_load_balancers(LoadBalancerNames=[lb_name1, lb_name2])
    assert len(lbs["LoadBalancerDescriptions"]) == 2

    with pytest.raises(ClientError) as ex:
        client.describe_load_balancers(LoadBalancerNames=["unknownlb"])
    err = ex.value.response["Error"]
    assert err["Code"] == "LoadBalancerNotFound"
    assert err["Message"] == "The specified load balancer does not exist: unknownlb"

    with pytest.raises(ClientError) as ex:
        client.describe_load_balancers(LoadBalancerNames=[lb_name1, "unknownlb"])
    err = ex.value.response["Error"]
    assert err["Code"] == "LoadBalancerNotFound"
    # Bug - message sometimes shows the lb that does exist
    assert "The specified load balancer does not exist:" in err["Message"]


@mock_aws
def test_delete_load_balancer():
    client = boto3.client("elb", region_name="us-east-1")
    lb_name1 = str(uuid4())[0:6]
    lb_name2 = str(uuid4())[0:6]

    client.create_load_balancer(
        LoadBalancerName=lb_name1,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    client.create_load_balancer(
        LoadBalancerName=lb_name2,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    lbs = client.describe_load_balancers()["LoadBalancerDescriptions"]
    lb_names = [lb["LoadBalancerName"] for lb in lbs]
    assert lb_name1 in lb_names
    assert lb_name2 in lb_names

    client.delete_load_balancer(LoadBalancerName=lb_name1)

    lbs = client.describe_load_balancers()["LoadBalancerDescriptions"]
    lb_names = [lb["LoadBalancerName"] for lb in lbs]
    assert lb_name1 not in lb_names
    assert lb_name2 in lb_names


@mock_aws
def test_create_health_check():
    client = boto3.client("elb", region_name="us-east-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )
    client.configure_health_check(
        LoadBalancerName="my-lb",
        HealthCheck={
            "Target": "HTTP:8080/health",
            "Interval": 20,
            "Timeout": 23,
            "HealthyThreshold": 3,
            "UnhealthyThreshold": 5,
        },
    )

    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    assert balancer["HealthCheck"]["Target"] == "HTTP:8080/health"
    assert balancer["HealthCheck"]["Interval"] == 20
    assert balancer["HealthCheck"]["Timeout"] == 23
    assert balancer["HealthCheck"]["HealthyThreshold"] == 3
    assert balancer["HealthCheck"]["UnhealthyThreshold"] == 5


@mock_aws
def test_register_instances():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    instance_id1 = response[0].id
    instance_id2 = response[1].id

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )
    client.register_instances_with_load_balancer(
        LoadBalancerName="my-lb",
        Instances=[{"InstanceId": instance_id1}, {"InstanceId": instance_id2}],
    )
    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    instance_ids = [instance["InstanceId"] for instance in balancer["Instances"]]
    assert set(instance_ids) == set([instance_id1, instance_id2])


@mock_aws
def test_deregister_instances():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    instance_id1 = response[0].id
    instance_id2 = response[1].id

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )
    client.register_instances_with_load_balancer(
        LoadBalancerName="my-lb",
        Instances=[{"InstanceId": instance_id1}, {"InstanceId": instance_id2}],
    )

    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    assert len(balancer["Instances"]) == 2

    client.deregister_instances_from_load_balancer(
        LoadBalancerName="my-lb", Instances=[{"InstanceId": instance_id1}]
    )

    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    assert len(balancer["Instances"]) == 1
    assert balancer["Instances"][0]["InstanceId"] == instance_id2


@mock_aws
def test_default_attributes():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    attributes = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    assert attributes["CrossZoneLoadBalancing"] == {"Enabled": False}
    assert attributes["AccessLog"] == {"Enabled": False}
    assert attributes["ConnectionDraining"] == {"Enabled": False}
    assert attributes["ConnectionSettings"] == {"IdleTimeout": 60}


@mock_aws
def test_cross_zone_load_balancing_attribute():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    client.modify_load_balancer_attributes(
        LoadBalancerName=lb_name,
        LoadBalancerAttributes={"CrossZoneLoadBalancing": {"Enabled": True}},
    )

    attributes = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    assert attributes["CrossZoneLoadBalancing"] == {"Enabled": True}
    assert attributes["AccessLog"] == {"Enabled": False}
    assert attributes["ConnectionDraining"] == {"Enabled": False}
    assert attributes["ConnectionSettings"] == {"IdleTimeout": 60}

    client.modify_load_balancer_attributes(
        LoadBalancerName=lb_name,
        LoadBalancerAttributes={"CrossZoneLoadBalancing": {"Enabled": False}},
    )

    attributes = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    assert attributes["CrossZoneLoadBalancing"] == {"Enabled": False}


@mock_aws
def test_connection_draining_attribute():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    client.modify_load_balancer_attributes(
        LoadBalancerName=lb_name,
        LoadBalancerAttributes={"ConnectionDraining": {"Enabled": True, "Timeout": 42}},
    )

    attributes = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    assert attributes["ConnectionDraining"] == {"Enabled": True, "Timeout": 42}

    client.modify_load_balancer_attributes(
        LoadBalancerName=lb_name,
        LoadBalancerAttributes={"ConnectionDraining": {"Enabled": False}},
    )

    attributes = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    assert attributes["ConnectionDraining"] == {"Enabled": False, "Timeout": 300}


@mock_aws
def test_access_log_attribute():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    lb_attrs = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    access_log = lb_attrs["AccessLog"]
    assert access_log == {"Enabled": False}

    # Specify our AccessLog attributes
    client.modify_load_balancer_attributes(
        LoadBalancerName=lb_name,
        LoadBalancerAttributes={
            "AccessLog": {
                "Enabled": True,
                "S3BucketName": "mb",
                "EmitInterval": 42,
                "S3BucketPrefix": "s3bf",
            }
        },
    )
    lb_attrs = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    access_log = lb_attrs["AccessLog"]
    assert access_log == {
        "Enabled": True,
        "S3BucketName": "mb",
        "EmitInterval": 42,
        "S3BucketPrefix": "s3bf",
    }

    # Verify the attribute can be reset
    client.modify_load_balancer_attributes(
        LoadBalancerName=lb_name,
        LoadBalancerAttributes={"AccessLog": {"Enabled": False}},
    )
    lb_attrs = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    access_log = lb_attrs["AccessLog"]
    assert access_log == {"Enabled": False}


@mock_aws
def test_connection_settings_attribute():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    lb_attrs = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    conn_settings = lb_attrs["ConnectionSettings"]
    assert conn_settings == {"IdleTimeout": 60}

    # Specify our AccessLog attributes
    client.modify_load_balancer_attributes(
        LoadBalancerName=lb_name,
        LoadBalancerAttributes={"ConnectionSettings": {"IdleTimeout": 123}},
    )
    lb_attrs = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    conn_settings = lb_attrs["ConnectionSettings"]
    assert conn_settings == {"IdleTimeout": 123}


@mock_aws
def test_describe_instance_health():
    elb = boto3.client("elb", region_name="us-east-1")
    ec2 = boto3.client("ec2", region_name="us-east-1")
    # Create three instances
    resp = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    instance_ids = [i["InstanceId"] for i in resp["Instances"]]

    # Register two instances with an LB
    lb_name = "my_load_balancer"
    elb.create_load_balancer(
        Listeners=[{"InstancePort": 80, "LoadBalancerPort": 8080, "Protocol": "HTTP"}],
        LoadBalancerName=lb_name,
    )
    elb.register_instances_with_load_balancer(
        LoadBalancerName=lb_name,
        Instances=[{"InstanceId": instance_ids[0]}, {"InstanceId": instance_ids[1]}],
    )

    # Describe the Health of all instances
    instances_health = elb.describe_instance_health(LoadBalancerName=lb_name)[
        "InstanceStates"
    ]
    assert len(instances_health) == 2


@mock_aws
def test_describe_instance_health__with_instance_ids():
    elb = boto3.client("elb", region_name="us-east-1")
    ec2 = boto3.client("ec2", region_name="us-east-1")
    # Create three instances
    resp = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=3, MaxCount=3)
    instance_ids = [i["InstanceId"] for i in resp["Instances"]]

    # Register two instances with an LB
    lb_name = "my_load_balancer"
    elb.create_load_balancer(
        Listeners=[{"InstancePort": 80, "LoadBalancerPort": 8080, "Protocol": "HTTP"}],
        LoadBalancerName=lb_name,
    )
    elb.register_instances_with_load_balancer(
        LoadBalancerName=lb_name,
        Instances=[{"InstanceId": instance_ids[0]}, {"InstanceId": instance_ids[2]}],
    )

    # Stop one instance
    ec2.stop_instances(InstanceIds=[instance_ids[2]])

    # Describe the Health of instances
    instances_health = elb.describe_instance_health(
        LoadBalancerName=lb_name,
        Instances=[{"InstanceId": iid} for iid in instance_ids],
    )["InstanceStates"]
    assert len(instances_health) == 3

    # The first instance is healthy
    assert instances_health[0]["InstanceId"] == instance_ids[0]
    assert instances_health[0]["State"] == "InService"

    # The second instance was never known to ELB
    assert instances_health[1]["InstanceId"] == instance_ids[1]
    assert instances_health[1]["State"] == "Unknown"

    # The third instance was stopped
    assert instances_health[2]["InstanceId"] == instance_ids[2]
    assert instances_health[2]["State"] == "OutOfService"


@mock_aws
def test_describe_instance_health_of_unknown_lb():
    elb = boto3.client("elb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        elb.describe_instance_health(LoadBalancerName="what")
    err = exc.value.response["Error"]
    assert err["Code"] == "LoadBalancerNotFound"
    assert err["Message"] == "There is no ACTIVE Load Balancer named 'what'"


@mock_aws
def test_add_remove_tags():
    client = boto3.client("elb", region_name="us-east-1")

    with pytest.raises(ClientError):
        client.add_tags(LoadBalancerNames=["my-lb"], Tags=[{"Key": "a", "Value": "b"}])

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    assert len(client.describe_load_balancers()["LoadBalancerDescriptions"]) == 1

    client.add_tags(LoadBalancerNames=["my-lb"], Tags=[{"Key": "a", "Value": "b"}])

    tags = dict(
        [
            (d["Key"], d["Value"])
            for d in client.describe_tags(LoadBalancerNames=["my-lb"])[
                "TagDescriptions"
            ][0]["Tags"]
        ]
    )
    assert tags["a"] == "b"

    client.add_tags(
        LoadBalancerNames=["my-lb"],
        Tags=[
            {"Key": "a", "Value": "b"},
            {"Key": "b", "Value": "b"},
            {"Key": "c", "Value": "b"},
            {"Key": "d", "Value": "b"},
            {"Key": "e", "Value": "b"},
            {"Key": "f", "Value": "b"},
            {"Key": "g", "Value": "b"},
            {"Key": "h", "Value": "b"},
            {"Key": "i", "Value": "b"},
            {"Key": "j", "Value": "b"},
        ],
    )

    with pytest.raises(ClientError):
        client.add_tags(LoadBalancerNames=["my-lb"], Tags=[{"Key": "k", "Value": "b"}])

    client.add_tags(LoadBalancerNames=["my-lb"], Tags=[{"Key": "j", "Value": "c"}])

    tags = dict(
        [
            (d["Key"], d["Value"])
            for d in client.describe_tags(LoadBalancerNames=["my-lb"])[
                "TagDescriptions"
            ][0]["Tags"]
        ]
    )

    assert tags["a"] == "b"
    assert tags["b"] == "b"
    assert tags["c"] == "b"
    assert tags["d"] == "b"
    assert tags["e"] == "b"
    assert tags["f"] == "b"
    assert tags["g"] == "b"
    assert tags["h"] == "b"
    assert tags["i"] == "b"
    assert tags["j"] == "c"
    assert "k" not in tags

    client.remove_tags(LoadBalancerNames=["my-lb"], Tags=[{"Key": "a"}])

    tags = dict(
        [
            (d["Key"], d["Value"])
            for d in client.describe_tags(LoadBalancerNames=["my-lb"])[
                "TagDescriptions"
            ][0]["Tags"]
        ]
    )

    assert "a" not in tags
    assert tags["b"] == "b"
    assert tags["c"] == "b"
    assert tags["d"] == "b"
    assert tags["e"] == "b"
    assert tags["f"] == "b"
    assert tags["g"] == "b"
    assert tags["h"] == "b"
    assert tags["i"] == "b"
    assert tags["j"] == "c"

    client.create_load_balancer(
        LoadBalancerName="other-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 433, "InstancePort": 8433}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    client.add_tags(
        LoadBalancerNames=["other-lb"], Tags=[{"Key": "other", "Value": "something"}]
    )

    lb_tags = dict(
        [
            (lb["LoadBalancerName"], dict([(d["Key"], d["Value"]) for d in lb["Tags"]]))
            for lb in client.describe_tags(LoadBalancerNames=["my-lb", "other-lb"])[
                "TagDescriptions"
            ]
        ]
    )

    assert "my-lb" in lb_tags
    assert "other-lb" in lb_tags

    assert "other" not in lb_tags["my-lb"]
    assert lb_tags["other-lb"]["other"] == "something"


@mock_aws
def test_create_with_tags():
    client = boto3.client("elb", region_name="us-east-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
        Tags=[{"Key": "k", "Value": "v"}],
    )

    tags = dict(
        (d["Key"], d["Value"])
        for d in client.describe_tags(LoadBalancerNames=["my-lb"])["TagDescriptions"][
            0
        ]["Tags"]
    )
    assert tags["k"] == "v"


@mock_aws
def test_modify_attributes():
    client = boto3.client("elb", region_name="us-east-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    # Default ConnectionDraining timeout of 300 seconds
    client.modify_load_balancer_attributes(
        LoadBalancerName="my-lb",
        LoadBalancerAttributes={"ConnectionDraining": {"Enabled": True}},
    )
    lb_attrs = client.describe_load_balancer_attributes(LoadBalancerName="my-lb")
    assert lb_attrs["LoadBalancerAttributes"]["ConnectionDraining"]["Enabled"] is True
    assert lb_attrs["LoadBalancerAttributes"]["ConnectionDraining"]["Timeout"] == 300

    # specify a custom ConnectionDraining timeout
    client.modify_load_balancer_attributes(
        LoadBalancerName="my-lb",
        LoadBalancerAttributes={"ConnectionDraining": {"Enabled": True, "Timeout": 45}},
    )
    lb_attrs = client.describe_load_balancer_attributes(LoadBalancerName="my-lb")
    assert lb_attrs["LoadBalancerAttributes"]["ConnectionDraining"]["Enabled"] is True
    assert lb_attrs["LoadBalancerAttributes"]["ConnectionDraining"]["Timeout"] == 45


@mock_aws
def test_subnets():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="172.28.7.192/26")
    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        Subnets=[subnet.id],
    )

    lb = client.describe_load_balancers()["LoadBalancerDescriptions"][0]

    assert len(lb["Subnets"]) == 1
    assert lb["Subnets"][0] == subnet.id

    assert lb["VPCId"] == vpc.id
    assert lb["SourceSecurityGroup"] == {
        "OwnerAlias": f"{DEFAULT_ACCOUNT_ID}",
        "GroupName": "default",
    }


@mock_aws
def test_create_load_balancer_duplicate():
    lb_name = str(uuid4())[0:6]
    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
    )

    with pytest.raises(ClientError) as ex:
        client.create_load_balancer(
            LoadBalancerName=lb_name,
            Listeners=[
                {"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}
            ],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "DuplicateLoadBalancerName"
    assert (
        err["Message"]
        == f"The specified load balancer name already exists for this account: {lb_name}"
    )
