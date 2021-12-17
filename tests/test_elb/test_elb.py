import boto3
import botocore
import boto
import boto.ec2.elb
from boto.ec2.elb import HealthCheck
from boto.ec2.elb.attributes import (
    ConnectionSettingAttribute,
    ConnectionDrainingAttribute,
    AccessLogAttribute,
)
from botocore.exceptions import ClientError
from boto.exception import BotoServerError
import pytest
import sure  # noqa # pylint: disable=unused-import

from moto import mock_acm, mock_elb, mock_ec2, mock_elb_deprecated, mock_ec2_deprecated
from tests import EXAMPLE_AMI_ID
from uuid import uuid4


# Has boto3 equivalent
@mock_elb_deprecated
@mock_ec2_deprecated
def test_create_load_balancer():
    conn = boto.connect_elb()
    ec2 = boto.ec2.connect_to_region("us-east-1")

    security_group = ec2.create_security_group("sg-abc987", "description")

    zones = ["us-east-1a", "us-east-1b"]
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    conn.create_load_balancer(
        "my-lb", zones, ports, scheme="internal", security_groups=[security_group.id]
    )

    balancers = conn.get_all_load_balancers()
    balancer = balancers[0]
    balancer.name.should.equal("my-lb")
    balancer.scheme.should.equal("internal")
    list(balancer.security_groups).should.equal([security_group.id])
    set(balancer.availability_zones).should.equal(set(["us-east-1a", "us-east-1b"]))
    listener1 = balancer.listeners[0]
    listener1.load_balancer_port.should.equal(80)
    listener1.instance_port.should.equal(8080)
    listener1.protocol.should.equal("HTTP")
    listener2 = balancer.listeners[1]
    listener2.load_balancer_port.should.equal(443)
    listener2.instance_port.should.equal(8443)
    listener2.protocol.should.equal("TCP")


@pytest.mark.parametrize("region_name", ["us-east-1", "ap-south-1"])
@pytest.mark.parametrize(
    "zones",
    [
        ["us-east-1a"],
        ["us-east-1a", "us-east-1b"],
        ["eu-north-1a", "eu-north-1b", "eu-north-1c"],
    ],
)
@mock_elb
@mock_ec2
def test_create_load_balancer_boto3(zones, region_name):
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
    lb.should.have.key("DNSName").equal("my-lb.us-east-1.elb.amazonaws.com")

    describe = client.describe_load_balancers(LoadBalancerNames=["my-lb"])[
        "LoadBalancerDescriptions"
    ][0]
    describe.should.have.key("LoadBalancerName").equal("my-lb")
    describe.should.have.key("DNSName").equal("my-lb.us-east-1.elb.amazonaws.com")
    describe.should.have.key("CanonicalHostedZoneName").equal(
        "my-lb.us-east-1.elb.amazonaws.com"
    )
    describe.should.have.key("AvailabilityZones").equal(zones)
    describe.should.have.key("VPCId")
    describe.should.have.key("SecurityGroups").equal([security_group.id])
    describe.should.have.key("Scheme").equal("internal")

    describe.should.have.key("ListenerDescriptions")
    describe["ListenerDescriptions"].should.have.length_of(2)

    tcp = [
        l["Listener"]
        for l in describe["ListenerDescriptions"]
        if l["Listener"]["Protocol"] == "TCP"
    ][0]
    http = [
        l["Listener"]
        for l in describe["ListenerDescriptions"]
        if l["Listener"]["Protocol"] == "HTTP"
    ][0]
    tcp.should.equal(
        {
            "Protocol": "TCP",
            "LoadBalancerPort": 80,
            "InstanceProtocol": "TCP",
            "InstancePort": 8080,
            "SSLCertificateId": "None",
        }
    )
    http.should.equal(
        {
            "Protocol": "HTTP",
            "LoadBalancerPort": 81,
            "InstanceProtocol": "HTTP",
            "InstancePort": 9000,
            "SSLCertificateId": "None",
        }
    )


# Has boto3 equivalent
@mock_elb_deprecated
def test_getting_missing_elb():
    conn = boto.connect_elb()
    conn.get_all_load_balancers.when.called_with(
        load_balancer_names="aaa"
    ).should.throw(BotoServerError)


@mock_elb
def test_get_missing_elb_boto3():
    client = boto3.client("elb", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        client.describe_load_balancers(LoadBalancerNames=["unknown-lb"])
    err = ex.value.response["Error"]
    err["Code"].should.equal("LoadBalancerNotFound")
    err["Message"].should.equal(
        "The specified load balancer does not exist: unknown-lb"
    )


# Has boto3 equivalent
@mock_elb_deprecated
def test_create_elb_in_multiple_region():
    zones = ["us-east-1a", "us-east-1b"]
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]

    west1_conn = boto.ec2.elb.connect_to_region("us-west-1")
    west1_conn.create_load_balancer("my-lb", zones, ports)

    west2_conn = boto.ec2.elb.connect_to_region("us-west-2")
    west2_conn.create_load_balancer("my-lb", zones, ports)

    list(west1_conn.get_all_load_balancers()).should.have.length_of(1)
    list(west2_conn.get_all_load_balancers()).should.have.length_of(1)


@mock_elb
def test_create_elb_in_multiple_region_boto3():
    client_east = boto3.client("elb", region_name="us-east-2")
    client_west = boto3.client("elb", region_name="us-west-2")

    name_east = str(uuid4())[0:6]
    name_west = str(uuid4())[0:6]

    client_east.create_load_balancer(
        LoadBalancerName=name_east,
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )
    client_west.create_load_balancer(
        LoadBalancerName=name_west,
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    east_names = [
        lb["LoadBalancerName"]
        for lb in client_east.describe_load_balancers()["LoadBalancerDescriptions"]
    ]
    east_names.should.contain(name_east)
    east_names.shouldnt.contain(name_west)

    west_names = [
        lb["LoadBalancerName"]
        for lb in client_west.describe_load_balancers()["LoadBalancerDescriptions"]
    ]
    west_names.should.contain(name_west)
    west_names.shouldnt.contain(name_east)


@mock_acm
@mock_elb
def test_create_load_balancer_with_certificate_boto3():
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
        AvailabilityZones=["us-east-1a"],
    )
    describe = client.describe_load_balancers(LoadBalancerNames=[name])[
        "LoadBalancerDescriptions"
    ][0]
    describe["Scheme"].should.equal("internet-facing")

    listener = describe["ListenerDescriptions"][0]["Listener"]
    listener.should.have.key("Protocol").equal("HTTPS")
    listener.should.have.key("SSLCertificateId").equals(certificate_arn)


@mock_elb
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
            AvailabilityZones=["us-east-1a"],
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("CertificateNotFoundException")


@mock_elb
def test_create_and_delete_boto3_support():
    client = boto3.client("elb", region_name="us-east-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )
    list(
        client.describe_load_balancers()["LoadBalancerDescriptions"]
    ).should.have.length_of(1)

    client.delete_load_balancer(LoadBalancerName="my-lb")
    list(
        client.describe_load_balancers()["LoadBalancerDescriptions"]
    ).should.have.length_of(0)


@mock_elb
def test_create_load_balancer_with_no_listeners_defined():
    client = boto3.client("elb", region_name="us-east-1")

    with pytest.raises(ClientError):
        client.create_load_balancer(
            LoadBalancerName="my-lb",
            Listeners=[],
            AvailabilityZones=["us-east-1a", "us-east-1b"],
        )


@mock_elb
def test_describe_paginated_balancers():
    client = boto3.client("elb", region_name="us-east-1")

    for i in range(51):
        client.create_load_balancer(
            LoadBalancerName="my-lb%d" % i,
            Listeners=[
                {"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}
            ],
            AvailabilityZones=["us-east-1a", "us-east-1b"],
        )

    resp = client.describe_load_balancers()
    resp["LoadBalancerDescriptions"].should.have.length_of(50)
    resp["NextMarker"].should.equal(
        resp["LoadBalancerDescriptions"][-1]["LoadBalancerName"]
    )
    resp2 = client.describe_load_balancers(Marker=resp["NextMarker"])
    resp2["LoadBalancerDescriptions"].should.have.length_of(1)
    assert "NextToken" not in resp2.keys()


@mock_elb
@mock_ec2
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


# Has boto3 equivalent
@mock_elb_deprecated
def test_add_listener():
    conn = boto.connect_elb()
    zones = ["us-east-1a", "us-east-1b"]
    ports = [(80, 8080, "http")]
    conn.create_load_balancer("my-lb", zones, ports)
    new_listener = (443, 8443, "tcp")
    conn.create_load_balancer_listeners("my-lb", [new_listener])
    balancers = conn.get_all_load_balancers()
    balancer = balancers[0]
    listener1 = balancer.listeners[0]
    listener1.load_balancer_port.should.equal(80)
    listener1.instance_port.should.equal(8080)
    listener1.protocol.should.equal("HTTP")
    listener2 = balancer.listeners[1]
    listener2.load_balancer_port.should.equal(443)
    listener2.instance_port.should.equal(8443)
    listener2.protocol.should.equal("TCP")


# Has boto3 equivalent
@mock_elb_deprecated
def test_delete_listener():
    conn = boto.connect_elb()

    zones = ["us-east-1a", "us-east-1b"]
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    conn.create_load_balancer("my-lb", zones, ports)
    conn.delete_load_balancer_listeners("my-lb", [443])
    balancers = conn.get_all_load_balancers()
    balancer = balancers[0]
    listener1 = balancer.listeners[0]
    listener1.load_balancer_port.should.equal(80)
    listener1.instance_port.should.equal(8080)
    listener1.protocol.should.equal("HTTP")
    balancer.listeners.should.have.length_of(1)


@mock_elb
def test_create_and_delete_listener_boto3_support():
    client = boto3.client("elb", region_name="us-east-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )
    list(
        client.describe_load_balancers()["LoadBalancerDescriptions"]
    ).should.have.length_of(1)

    client.create_load_balancer_listeners(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 443, "InstancePort": 8443}],
    )
    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    list(balancer["ListenerDescriptions"]).should.have.length_of(2)
    balancer["ListenerDescriptions"][0]["Listener"]["Protocol"].should.equal("HTTP")
    balancer["ListenerDescriptions"][0]["Listener"]["LoadBalancerPort"].should.equal(80)
    balancer["ListenerDescriptions"][0]["Listener"]["InstancePort"].should.equal(8080)
    balancer["ListenerDescriptions"][1]["Listener"]["Protocol"].should.equal("TCP")
    balancer["ListenerDescriptions"][1]["Listener"]["LoadBalancerPort"].should.equal(
        443
    )
    balancer["ListenerDescriptions"][1]["Listener"]["InstancePort"].should.equal(8443)

    # Creating this listener with an conflicting definition throws error
    with pytest.raises(ClientError):
        client.create_load_balancer_listeners(
            LoadBalancerName="my-lb",
            Listeners=[
                {"Protocol": "tcp", "LoadBalancerPort": 443, "InstancePort": 1234}
            ],
        )

    client.delete_load_balancer_listeners(
        LoadBalancerName="my-lb", LoadBalancerPorts=[443]
    )

    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    list(balancer["ListenerDescriptions"]).should.have.length_of(1)


@mock_acm
@mock_elb
def test_create_lb_listener_with_ssl_certificate():
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
        AvailabilityZones=["us-east-1a", "us-east-1b"],
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
    listeners.should.have.length_of(2)

    listeners[0]["Listener"]["Protocol"].should.equal("HTTP")
    listeners[0]["Listener"]["SSLCertificateId"].should.equal("None")

    listeners[1]["Listener"]["Protocol"].should.equal("TCP")
    listeners[1]["Listener"]["SSLCertificateId"].should.equal(certificate_arn)


@mock_acm
@mock_elb
def test_create_lb_listener_with_invalid_ssl_certificate():
    client = boto3.client("elb", region_name="eu-west-1")

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
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
    err["Code"].should.equal("CertificateNotFoundException")


@mock_acm
@mock_elb
def test_set_sslcertificate_boto3():
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
        LoadBalancerName=lb_name, LoadBalancerPort=81, SSLCertificateId=certificate_arn,
    )

    elb = client.describe_load_balancers()["LoadBalancerDescriptions"][0]

    listener = elb["ListenerDescriptions"][0]["Listener"]
    listener.should.have.key("LoadBalancerPort").equals(80)
    listener.should.have.key("SSLCertificateId").equals("None")

    listener = elb["ListenerDescriptions"][1]["Listener"]
    listener.should.have.key("LoadBalancerPort").equals(81)
    listener.should.have.key("SSLCertificateId").equals(certificate_arn)


# Has boto3 equivalent
@mock_elb_deprecated
def test_get_load_balancers_by_name():
    conn = boto.connect_elb()

    zones = ["us-east-1a", "us-east-1b"]
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    conn.create_load_balancer("my-lb1", zones, ports)
    conn.create_load_balancer("my-lb2", zones, ports)
    conn.create_load_balancer("my-lb3", zones, ports)

    conn.get_all_load_balancers().should.have.length_of(3)
    conn.get_all_load_balancers(load_balancer_names=["my-lb1"]).should.have.length_of(1)
    conn.get_all_load_balancers(
        load_balancer_names=["my-lb1", "my-lb2"]
    ).should.have.length_of(2)


@mock_elb
def test_get_load_balancers_by_name_boto3():
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
    lbs["LoadBalancerDescriptions"].should.have.length_of(1)

    lbs = client.describe_load_balancers(LoadBalancerNames=[lb_name2])
    lbs["LoadBalancerDescriptions"].should.have.length_of(1)

    lbs = client.describe_load_balancers(LoadBalancerNames=[lb_name1, lb_name2])
    lbs["LoadBalancerDescriptions"].should.have.length_of(2)

    with pytest.raises(ClientError) as ex:
        client.describe_load_balancers(LoadBalancerNames=["unknownlb"])
    err = ex.value.response["Error"]
    err["Code"].should.equal("LoadBalancerNotFound")
    err["Message"].should.equal(
        f"The specified load balancer does not exist: unknownlb"
    )

    with pytest.raises(ClientError) as ex:
        client.describe_load_balancers(LoadBalancerNames=[lb_name1, "unknownlb"])
    err = ex.value.response["Error"]
    err["Code"].should.equal("LoadBalancerNotFound")
    # Bug - message sometimes shows the lb that does exist
    err["Message"].should.match(f"The specified load balancer does not exist:")


# Has boto3 equivalent
@mock_elb_deprecated
def test_delete_load_balancer():
    conn = boto.connect_elb()

    zones = ["us-east-1a"]
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    conn.create_load_balancer("my-lb", zones, ports)

    balancers = conn.get_all_load_balancers()
    balancers.should.have.length_of(1)

    conn.delete_load_balancer("my-lb")
    balancers = conn.get_all_load_balancers()
    balancers.should.have.length_of(0)


@mock_elb
def test_delete_load_balancer_boto3():
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
    lb_names.should.contain(lb_name1)
    lb_names.should.contain(lb_name2)

    client.delete_load_balancer(LoadBalancerName=lb_name1)

    lbs = client.describe_load_balancers()["LoadBalancerDescriptions"]
    lb_names = [lb["LoadBalancerName"] for lb in lbs]
    lb_names.shouldnt.contain(lb_name1)
    lb_names.should.contain(lb_name2)


# Has boto3 equivalent
@mock_elb_deprecated
def test_create_health_check():
    conn = boto.connect_elb()

    hc = HealthCheck(
        interval=20,
        healthy_threshold=3,
        unhealthy_threshold=5,
        target="HTTP:8080/health",
        timeout=23,
    )

    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)
    lb.configure_health_check(hc)

    balancer = conn.get_all_load_balancers()[0]
    health_check = balancer.health_check
    health_check.interval.should.equal(20)
    health_check.healthy_threshold.should.equal(3)
    health_check.unhealthy_threshold.should.equal(5)
    health_check.target.should.equal("HTTP:8080/health")
    health_check.timeout.should.equal(23)


@mock_elb
def test_create_health_check_boto3():
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
    balancer["HealthCheck"]["Target"].should.equal("HTTP:8080/health")
    balancer["HealthCheck"]["Interval"].should.equal(20)
    balancer["HealthCheck"]["Timeout"].should.equal(23)
    balancer["HealthCheck"]["HealthyThreshold"].should.equal(3)
    balancer["HealthCheck"]["UnhealthyThreshold"].should.equal(5)


# Has boto3 equivalent
@mock_ec2_deprecated
@mock_elb_deprecated
def test_register_instances():
    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.run_instances(EXAMPLE_AMI_ID, 2)
    instance_id1 = reservation.instances[0].id
    instance_id2 = reservation.instances[1].id

    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)

    lb.register_instances([instance_id1, instance_id2])

    balancer = conn.get_all_load_balancers()[0]
    instance_ids = [instance.id for instance in balancer.instances]
    set(instance_ids).should.equal(set([instance_id1, instance_id2]))


@mock_ec2
@mock_elb
def test_register_instances_boto3():
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
    set(instance_ids).should.equal(set([instance_id1, instance_id2]))


# Has boto3 equivalent
@mock_ec2_deprecated
@mock_elb_deprecated
def test_deregister_instances():
    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.run_instances(EXAMPLE_AMI_ID, 2)
    instance_id1 = reservation.instances[0].id
    instance_id2 = reservation.instances[1].id

    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)

    lb.register_instances([instance_id1, instance_id2])

    balancer = conn.get_all_load_balancers()[0]
    balancer.instances.should.have.length_of(2)
    balancer.deregister_instances([instance_id1])

    balancer.instances.should.have.length_of(1)
    balancer.instances[0].id.should.equal(instance_id2)


@mock_ec2
@mock_elb
def test_deregister_instances_boto3():
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
    balancer["Instances"].should.have.length_of(2)

    client.deregister_instances_from_load_balancer(
        LoadBalancerName="my-lb", Instances=[{"InstanceId": instance_id1}]
    )

    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    balancer["Instances"].should.have.length_of(1)
    balancer["Instances"][0]["InstanceId"].should.equal(instance_id2)


# Has boto3 equivalent
@mock_elb_deprecated
def test_default_attributes():
    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)
    attributes = lb.get_attributes()

    attributes.cross_zone_load_balancing.enabled.should.be.false
    attributes.connection_draining.enabled.should.be.false
    attributes.access_log.enabled.should.be.false
    attributes.connecting_settings.idle_timeout.should.equal(60)


@mock_elb
def test_default_attributes_boto3():
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
    attributes.should.have.key("CrossZoneLoadBalancing").equal({"Enabled": False})
    attributes.should.have.key("AccessLog").equal({"Enabled": False})
    attributes.should.have.key("ConnectionDraining").equal({"Enabled": False})
    attributes.should.have.key("ConnectionSettings").equal({"IdleTimeout": 60})


# Has boto3 equivalent
@mock_elb_deprecated
def test_cross_zone_load_balancing_attribute():
    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)

    conn.modify_lb_attribute("my-lb", "CrossZoneLoadBalancing", True)
    attributes = lb.get_attributes(force=True)
    attributes.cross_zone_load_balancing.enabled.should.be.true

    conn.modify_lb_attribute("my-lb", "CrossZoneLoadBalancing", False)
    attributes = lb.get_attributes(force=True)
    attributes.cross_zone_load_balancing.enabled.should.be.false


@mock_elb
def test_cross_zone_load_balancing_attribute_boto3():
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
    # Bug: This property is not properly propagated
    attributes.should.have.key("CrossZoneLoadBalancing").equal({"Enabled": False})
    attributes.should.have.key("AccessLog").equal({"Enabled": False})
    attributes.should.have.key("ConnectionDraining").equal({"Enabled": False})
    attributes.should.have.key("ConnectionSettings").equal({"IdleTimeout": 60})

    client.modify_load_balancer_attributes(
        LoadBalancerName=lb_name,
        LoadBalancerAttributes={"CrossZoneLoadBalancing": {"Enabled": False}},
    )

    attributes = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    attributes.should.have.key("CrossZoneLoadBalancing").equal({"Enabled": False})


# Has boto3 equivalent
@mock_elb_deprecated
def test_connection_draining_attribute():
    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)

    connection_draining = ConnectionDrainingAttribute()
    connection_draining.enabled = True
    connection_draining.timeout = 60

    conn.modify_lb_attribute("my-lb", "ConnectionDraining", connection_draining)
    attributes = lb.get_attributes(force=True)
    attributes.connection_draining.enabled.should.be.true
    attributes.connection_draining.timeout.should.equal(60)

    connection_draining.timeout = 30
    conn.modify_lb_attribute("my-lb", "ConnectionDraining", connection_draining)
    attributes = lb.get_attributes(force=True)
    attributes.connection_draining.timeout.should.equal(30)

    connection_draining.enabled = False
    conn.modify_lb_attribute("my-lb", "ConnectionDraining", connection_draining)
    attributes = lb.get_attributes(force=True)
    attributes.connection_draining.enabled.should.be.false


@mock_elb
def test_connection_draining_attribute_boto3():
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
    attributes.should.have.key("ConnectionDraining").equal(
        {"Enabled": True, "Timeout": 42}
    )

    client.modify_load_balancer_attributes(
        LoadBalancerName=lb_name,
        LoadBalancerAttributes={"ConnectionDraining": {"Enabled": False}},
    )

    attributes = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    attributes.should.have.key("ConnectionDraining").equal({"Enabled": False})


# This does not work in Boto3, so we can't write a equivalent test
# Moto always looks for attribute 's3_bucket_name', but Boto3 sends 'S3BucketName'
# We'll need to rewrite this feature completely anyway, to get rid of the boto-objects
@mock_elb_deprecated
def test_access_log_attribute():
    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)

    access_log = AccessLogAttribute()
    access_log.enabled = True
    access_log.s3_bucket_name = "bucket"
    access_log.s3_bucket_prefix = "prefix"
    access_log.emit_interval = 60

    conn.modify_lb_attribute("my-lb", "AccessLog", access_log)
    attributes = lb.get_attributes(force=True)
    attributes.access_log.enabled.should.be.true
    attributes.access_log.s3_bucket_name.should.equal("bucket")
    attributes.access_log.s3_bucket_prefix.should.equal("prefix")
    attributes.access_log.emit_interval.should.equal(60)

    access_log.enabled = False
    conn.modify_lb_attribute("my-lb", "AccessLog", access_log)
    attributes = lb.get_attributes(force=True)
    attributes.access_log.enabled.should.be.false


# This does not work in Boto3, so we can't write a equivalent test
# Moto always looks for attribute 'idle_timeout', but Boto3 sends 'IdleTimeout'
# We'll need to rewrite this feature completely anyway, to get rid of the boto-objects
@mock_elb_deprecated
def test_connection_settings_attribute():
    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)

    connection_settings = ConnectionSettingAttribute(conn)
    connection_settings.idle_timeout = 120

    conn.modify_lb_attribute("my-lb", "ConnectingSettings", connection_settings)
    attributes = lb.get_attributes(force=True)
    attributes.connecting_settings.idle_timeout.should.equal(120)

    connection_settings.idle_timeout = 60
    conn.modify_lb_attribute("my-lb", "ConnectingSettings", connection_settings)
    attributes = lb.get_attributes(force=True)
    attributes.connecting_settings.idle_timeout.should.equal(60)


# Has boto3 equivalent
@mock_elb_deprecated
def test_create_lb_cookie_stickiness_policy():
    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)
    cookie_expiration_period = 60
    policy_name = "LBCookieStickinessPolicy"

    lb.create_cookie_stickiness_policy(cookie_expiration_period, policy_name)

    lb = conn.get_all_load_balancers()[0]
    # There appears to be a quirk about boto, whereby it returns a unicode
    # string for cookie_expiration_period, despite being stated in
    # documentation to be a long numeric.
    #
    # To work around that, this value is converted to an int and checked.
    cookie_expiration_period_response_str = lb.policies.lb_cookie_stickiness_policies[
        0
    ].cookie_expiration_period
    int(cookie_expiration_period_response_str).should.equal(cookie_expiration_period)
    lb.policies.lb_cookie_stickiness_policies[0].policy_name.should.equal(policy_name)


@mock_elb
def test_create_lb_cookie_stickiness_policy_boto3():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    lbc_policies = balancer["Policies"]["LBCookieStickinessPolicies"]
    lbc_policies.should.have.length_of(0)

    client.create_lb_cookie_stickiness_policy(
        LoadBalancerName=lb_name, PolicyName="pname", CookieExpirationPeriod=42
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    policies = balancer["Policies"]
    lbc_policies = policies["LBCookieStickinessPolicies"]
    lbc_policies.should.have.length_of(1)
    lbc_policies[0].should.equal({"PolicyName": "pname", "CookieExpirationPeriod": 42})


# Has boto3 equivalent
@mock_elb_deprecated
def test_create_lb_cookie_stickiness_policy_no_expiry():
    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)
    policy_name = "LBCookieStickinessPolicy"

    lb.create_cookie_stickiness_policy(None, policy_name)

    lb = conn.get_all_load_balancers()[0]
    lb.policies.lb_cookie_stickiness_policies[0].cookie_expiration_period.should.be.none
    lb.policies.lb_cookie_stickiness_policies[0].policy_name.should.equal(policy_name)


@mock_elb
def test_create_lb_cookie_stickiness_policy_no_expiry_boto3():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    lbc_policies = balancer["Policies"]["LBCookieStickinessPolicies"]
    lbc_policies.should.have.length_of(0)

    client.create_lb_cookie_stickiness_policy(
        LoadBalancerName=lb_name, PolicyName="pname"
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    policies = balancer["Policies"]
    lbc_policies = policies["LBCookieStickinessPolicies"]
    lbc_policies.should.have.length_of(1)
    lbc_policies[0].should.equal({"PolicyName": "pname"})


# Has boto3 equivalent
@mock_elb_deprecated
def test_create_app_cookie_stickiness_policy():
    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)
    cookie_name = "my-stickiness-policy"
    policy_name = "AppCookieStickinessPolicy"

    lb.create_app_cookie_stickiness_policy(cookie_name, policy_name)

    lb = conn.get_all_load_balancers()[0]
    lb.policies.app_cookie_stickiness_policies[0].cookie_name.should.equal(cookie_name)
    lb.policies.app_cookie_stickiness_policies[0].policy_name.should.equal(policy_name)


@mock_elb
def test_create_app_cookie_stickiness_policy_boto3():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    lbc_policies = balancer["Policies"]["AppCookieStickinessPolicies"]
    lbc_policies.should.have.length_of(0)

    client.create_app_cookie_stickiness_policy(
        LoadBalancerName=lb_name, PolicyName="pname", CookieName="cname"
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    policies = balancer["Policies"]
    lbc_policies = policies["AppCookieStickinessPolicies"]
    lbc_policies.should.have.length_of(1)
    lbc_policies[0].should.equal({"CookieName": "cname", "PolicyName": "pname"})


# Has boto3 equivalent
@mock_elb_deprecated
def test_create_lb_policy():
    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)
    policy_name = "ProxyPolicy"

    lb.create_lb_policy(policy_name, "ProxyProtocolPolicyType", {"ProxyProtocol": True})

    lb = conn.get_all_load_balancers()[0]
    lb.policies.other_policies[0].policy_name.should.equal(policy_name)


@mock_elb
def test_create_lb_policy_boto3():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    client.create_load_balancer_policy(
        LoadBalancerName=lb_name,
        PolicyName="ProxyPolicy",
        PolicyTypeName="ProxyProtocolPolicyType",
        PolicyAttributes=[
            {"AttributeName": "ProxyProtocol", "AttributeValue": "true",},
        ],
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    policies = balancer["Policies"]
    policies.should.have.key("OtherPolicies").equal(["ProxyPolicy"])


# Has boto3 equivalent
@mock_elb_deprecated
def test_set_policies_of_listener():
    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)
    listener_port = 80
    policy_name = "my-stickiness-policy"

    # boto docs currently state that zero or one policy may be associated
    # with a given listener

    # in a real flow, it is necessary first to create a policy,
    # then to set that policy to the listener
    lb.create_cookie_stickiness_policy(None, policy_name)
    lb.set_policies_of_listener(listener_port, [policy_name])

    lb = conn.get_all_load_balancers()[0]
    listener = lb.listeners[0]
    listener.load_balancer_port.should.equal(listener_port)
    # by contrast to a backend, a listener stores only policy name strings
    listener.policy_names[0].should.equal(policy_name)


@mock_elb
def test_set_policies_of_listener_boto3():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[
            {"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080},
            {"Protocol": "https", "LoadBalancerPort": 81, "InstancePort": 8081},
        ],
        AvailabilityZones=["us-east-1a"],
    )

    client.create_app_cookie_stickiness_policy(
        LoadBalancerName=lb_name, PolicyName="pname", CookieName="cname"
    )

    client.set_load_balancer_policies_of_listener(
        LoadBalancerName=lb_name, LoadBalancerPort=81, PolicyNames=["pname"]
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]

    http_l = [
        l
        for l in balancer["ListenerDescriptions"]
        if l["Listener"]["Protocol"] == "HTTP"
    ][0]
    http_l.should.have.key("PolicyNames").should.equal([])

    https_l = [
        l
        for l in balancer["ListenerDescriptions"]
        if l["Listener"]["Protocol"] == "HTTPS"
    ][0]
    https_l.should.have.key("PolicyNames").should.equal(["pname"])


# Has boto3 equivalent
@mock_elb_deprecated
def test_set_policies_of_backend_server():
    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", [], ports)
    instance_port = 8080
    policy_name = "ProxyPolicy"

    # in a real flow, it is necessary first to create a policy,
    # then to set that policy to the backend
    lb.create_lb_policy(policy_name, "ProxyProtocolPolicyType", {"ProxyProtocol": True})
    lb.set_policies_of_backend_server(instance_port, [policy_name])

    lb = conn.get_all_load_balancers()[0]
    backend = lb.backends[0]
    backend.instance_port.should.equal(instance_port)
    # by contrast to a listener, a backend stores OtherPolicy objects
    backend.policies[0].policy_name.should.equal(policy_name)


@mock_elb
def test_set_policies_of_backend_server_boto3():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[
            {"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080},
            {"Protocol": "https", "LoadBalancerPort": 81, "InstancePort": 8081},
        ],
        AvailabilityZones=["us-east-1a"],
    )

    client.create_app_cookie_stickiness_policy(
        LoadBalancerName=lb_name, PolicyName="pname", CookieName="cname"
    )

    client.set_load_balancer_policies_for_backend_server(
        LoadBalancerName=lb_name, InstancePort=8081, PolicyNames=["pname"]
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    balancer.should.have.key("BackendServerDescriptions")
    desc = balancer["BackendServerDescriptions"]
    desc.should.have.length_of(1)
    desc[0].should.equal({"InstancePort": 8081, "PolicyNames": ["pname"]})


# Has boto3 equivalent
@mock_ec2_deprecated
@mock_elb_deprecated
def test_describe_instance_health():
    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.run_instances(EXAMPLE_AMI_ID, 2)
    instance_id1 = reservation.instances[0].id
    instance_id2 = reservation.instances[1].id

    conn = boto.connect_elb()
    zones = ["us-east-1a", "us-east-1b"]
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    lb = conn.create_load_balancer("my-lb", zones, ports)

    instances_health = conn.describe_instance_health("my-lb")
    instances_health.should.be.empty

    lb.register_instances([instance_id1, instance_id2])

    instances_health = conn.describe_instance_health("my-lb")
    instances_health.should.have.length_of(2)
    for instance_health in instances_health:
        instance_health.instance_id.should.be.within([instance_id1, instance_id2])
        instance_health.state.should.equal("InService")

    instances_health = conn.describe_instance_health("my-lb", [instance_id1])
    instances_health.should.have.length_of(1)
    instances_health[0].instance_id.should.equal(instance_id1)
    instances_health[0].state.should.equal("InService")


@mock_ec2
@mock_elb
def test_describe_instance_health_boto3():
    elb = boto3.client("elb", region_name="us-east-1")
    ec2 = boto3.client("ec2", region_name="us-east-1")
    instances = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)[
        "Instances"
    ]
    lb_name = "my_load_balancer"
    elb.create_load_balancer(
        Listeners=[{"InstancePort": 80, "LoadBalancerPort": 8080, "Protocol": "HTTP"}],
        LoadBalancerName=lb_name,
    )
    elb.register_instances_with_load_balancer(
        LoadBalancerName=lb_name, Instances=[{"InstanceId": instances[0]["InstanceId"]}]
    )
    instances_health = elb.describe_instance_health(
        LoadBalancerName=lb_name,
        Instances=[{"InstanceId": instance["InstanceId"]} for instance in instances],
    )
    instances_health["InstanceStates"].should.have.length_of(2)
    instances_health["InstanceStates"][0]["InstanceId"].should.equal(
        instances[0]["InstanceId"]
    )
    instances_health["InstanceStates"][0]["State"].should.equal("InService")
    instances_health["InstanceStates"][1]["InstanceId"].should.equal(
        instances[1]["InstanceId"]
    )
    instances_health["InstanceStates"][1]["State"].should.equal("Unknown")


@mock_elb
def test_add_remove_tags():
    client = boto3.client("elb", region_name="us-east-1")

    client.add_tags.when.called_with(
        LoadBalancerNames=["my-lb"], Tags=[{"Key": "a", "Value": "b"}]
    ).should.throw(botocore.exceptions.ClientError)

    client.create_load_balancer(
        LoadBalancerName="my-lb",
        Listeners=[{"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a", "us-east-1b"],
    )

    list(
        client.describe_load_balancers()["LoadBalancerDescriptions"]
    ).should.have.length_of(1)

    client.add_tags(LoadBalancerNames=["my-lb"], Tags=[{"Key": "a", "Value": "b"}])

    tags = dict(
        [
            (d["Key"], d["Value"])
            for d in client.describe_tags(LoadBalancerNames=["my-lb"])[
                "TagDescriptions"
            ][0]["Tags"]
        ]
    )
    tags.should.have.key("a").which.should.equal("b")

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

    client.add_tags.when.called_with(
        LoadBalancerNames=["my-lb"], Tags=[{"Key": "k", "Value": "b"}]
    ).should.throw(botocore.exceptions.ClientError)

    client.add_tags(LoadBalancerNames=["my-lb"], Tags=[{"Key": "j", "Value": "c"}])

    tags = dict(
        [
            (d["Key"], d["Value"])
            for d in client.describe_tags(LoadBalancerNames=["my-lb"])[
                "TagDescriptions"
            ][0]["Tags"]
        ]
    )

    tags.should.have.key("a").which.should.equal("b")
    tags.should.have.key("b").which.should.equal("b")
    tags.should.have.key("c").which.should.equal("b")
    tags.should.have.key("d").which.should.equal("b")
    tags.should.have.key("e").which.should.equal("b")
    tags.should.have.key("f").which.should.equal("b")
    tags.should.have.key("g").which.should.equal("b")
    tags.should.have.key("h").which.should.equal("b")
    tags.should.have.key("i").which.should.equal("b")
    tags.should.have.key("j").which.should.equal("c")
    tags.shouldnt.have.key("k")

    client.remove_tags(LoadBalancerNames=["my-lb"], Tags=[{"Key": "a"}])

    tags = dict(
        [
            (d["Key"], d["Value"])
            for d in client.describe_tags(LoadBalancerNames=["my-lb"])[
                "TagDescriptions"
            ][0]["Tags"]
        ]
    )

    tags.shouldnt.have.key("a")
    tags.should.have.key("b").which.should.equal("b")
    tags.should.have.key("c").which.should.equal("b")
    tags.should.have.key("d").which.should.equal("b")
    tags.should.have.key("e").which.should.equal("b")
    tags.should.have.key("f").which.should.equal("b")
    tags.should.have.key("g").which.should.equal("b")
    tags.should.have.key("h").which.should.equal("b")
    tags.should.have.key("i").which.should.equal("b")
    tags.should.have.key("j").which.should.equal("c")

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
            (l["LoadBalancerName"], dict([(d["Key"], d["Value"]) for d in l["Tags"]]))
            for l in client.describe_tags(LoadBalancerNames=["my-lb", "other-lb"])[
                "TagDescriptions"
            ]
        ]
    )

    lb_tags.should.have.key("my-lb")
    lb_tags.should.have.key("other-lb")

    lb_tags["my-lb"].shouldnt.have.key("other")
    lb_tags["other-lb"].should.have.key("other").which.should.equal("something")


@mock_elb
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
    tags.should.have.key("k").which.should.equal("v")


@mock_elb
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
    lb_attrs["LoadBalancerAttributes"]["ConnectionDraining"]["Enabled"].should.equal(
        True
    )
    lb_attrs["LoadBalancerAttributes"]["ConnectionDraining"]["Timeout"].should.equal(
        300
    )

    # specify a custom ConnectionDraining timeout
    client.modify_load_balancer_attributes(
        LoadBalancerName="my-lb",
        LoadBalancerAttributes={"ConnectionDraining": {"Enabled": True, "Timeout": 45}},
    )
    lb_attrs = client.describe_load_balancer_attributes(LoadBalancerName="my-lb")
    lb_attrs["LoadBalancerAttributes"]["ConnectionDraining"]["Enabled"].should.equal(
        True
    )
    lb_attrs["LoadBalancerAttributes"]["ConnectionDraining"]["Timeout"].should.equal(45)


@mock_ec2
@mock_elb
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
    lb.should.have.key("Subnets").which.should.have.length_of(1)
    lb["Subnets"][0].should.equal(subnet.id)

    lb.should.have.key("VPCId").which.should.equal(vpc.id)


@mock_elb_deprecated
def test_create_load_balancer_duplicate():
    conn = boto.connect_elb()
    ports = [(80, 8080, "http"), (443, 8443, "tcp")]
    conn.create_load_balancer("my-lb", [], ports)
    conn.create_load_balancer.when.called_with("my-lb", [], ports).should.throw(
        BotoServerError
    )


@mock_elb
def test_create_load_balancer_duplicate_boto3():
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
    err["Code"].should.equal("DuplicateLoadBalancerName")
    err["Message"].should.equal(
        f"The specified load balancer name already exists for this account: {lb_name}"
    )
