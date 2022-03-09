import boto3
import botocore
from botocore.exceptions import ClientError
import pytest
import sure  # noqa # pylint: disable=unused-import

from moto import mock_acm, mock_elb, mock_ec2
from tests import EXAMPLE_AMI_ID
from uuid import uuid4


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
        LoadBalancerName=lb_name, LoadBalancerPort=81, SSLCertificateId=certificate_arn
    )

    elb = client.describe_load_balancers()["LoadBalancerDescriptions"][0]

    listener = elb["ListenerDescriptions"][0]["Listener"]
    listener.should.have.key("LoadBalancerPort").equals(80)
    listener.should.have.key("SSLCertificateId").equals("None")

    listener = elb["ListenerDescriptions"][1]["Listener"]
    listener.should.have.key("LoadBalancerPort").equals(81)
    listener.should.have.key("SSLCertificateId").equals(certificate_arn)


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
    attributes.should.have.key("CrossZoneLoadBalancing").equal({"Enabled": True})
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


@mock_elb
def test_access_log_attribute_boto3():
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
    access_log.should.equal({"Enabled": False})

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
    access_log.should.equal(
        {
            "Enabled": True,
            "S3BucketName": "mb",
            "EmitInterval": 42,
            "S3BucketPrefix": "s3bf",
        }
    )

    # Verify the attribute can be reset
    client.modify_load_balancer_attributes(
        LoadBalancerName=lb_name,
        LoadBalancerAttributes={"AccessLog": {"Enabled": False}},
    )
    lb_attrs = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    access_log = lb_attrs["AccessLog"]
    access_log.should.equal({"Enabled": False})


@mock_elb
def test_connection_settings_attribute_boto3():
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
    conn_settings.should.equal({"IdleTimeout": 60})

    # Specify our AccessLog attributes
    client.modify_load_balancer_attributes(
        LoadBalancerName=lb_name,
        LoadBalancerAttributes={"ConnectionSettings": {"IdleTimeout": 123}},
    )
    lb_attrs = client.describe_load_balancer_attributes(LoadBalancerName=lb_name)[
        "LoadBalancerAttributes"
    ]
    conn_settings = lb_attrs["ConnectionSettings"]
    conn_settings.should.equal({"IdleTimeout": 123})


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
        PolicyAttributes=[{"AttributeName": "ProxyProtocol", "AttributeValue": "true"}],
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    policies = balancer["Policies"]
    policies.should.have.key("OtherPolicies").equal(["ProxyPolicy"])


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
