import boto3
import botocore
from botocore.exceptions import ClientError
import pytest
import sure  # noqa # pylint: disable=unused-import

from moto import mock_acm, mock_elb, mock_ec2, mock_iam
from moto.core import DEFAULT_ACCOUNT_ID
from tests import EXAMPLE_AMI_ID
from uuid import uuid4


@pytest.mark.parametrize("region_name", ["us-east-1", "ap-south-1"])
@pytest.mark.parametrize("zones", [["a"], ["a", "b"]])
@mock_elb
@mock_ec2
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
    describe.should.have.key("Subnets").length_of(zones)  # Default subnet for each zone
    describe.should.have.key("SecurityGroups").equal([security_group.id])
    describe.should.have.key("Scheme").equal("internal")

    describe.should.have.key("ListenerDescriptions")
    describe["ListenerDescriptions"].should.have.length_of(2)

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
def test_get_missing_elb():
    client = boto3.client("elb", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        client.describe_load_balancers(LoadBalancerNames=["unknown-lb"])
    err = ex.value.response["Error"]
    err["Code"].should.equal("LoadBalancerNotFound")
    err["Message"].should.equal(
        "The specified load balancer does not exist: unknown-lb"
    )


@mock_elb
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
            AvailabilityZones=["us-east-2a"],
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("CertificateNotFoundException")


@mock_elb
def test_create_and_delete_load_balancer():
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


@mock_ec2
@mock_elb
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
    describe.should.have.key("SecurityGroups").length_of(1)
    sec_group_id = describe["SecurityGroups"][0]
    sg = ec2.describe_security_groups(GroupIds=[sec_group_id])["SecurityGroups"][0]
    assert sg["GroupName"].startswith("default_elb_")


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
def test_create_and_delete_listener():
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

    client.delete_load_balancer_listeners(
        LoadBalancerName="my-lb", LoadBalancerPorts=[443]
    )

    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    list(balancer["ListenerDescriptions"]).should.have.length_of(1)


@mock_elb
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
    err["Code"].should.equal("DuplicateListener")
    err["Message"].should.equal(
        "A listener already exists for my-lb with LoadBalancerPort 80, but with a different InstancePort, Protocol, or SSLCertificateId"
    )


@mock_elb
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
    list(balancer["ListenerDescriptions"]).should.have.length_of(1)


@mock_acm
@mock_elb
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
    listeners.should.have.length_of(2)

    listeners[0]["Listener"]["Protocol"].should.equal("HTTP")
    listeners[0]["Listener"]["SSLCertificateId"].should.equal("None")

    listeners[1]["Listener"]["Protocol"].should.equal("TCP")
    listeners[1]["Listener"]["SSLCertificateId"].should.equal(certificate_arn)


@mock_iam
@mock_elb
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
    err["Code"].should.equal("CertificateNotFoundException")


@mock_acm
@mock_elb
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
    listener.should.have.key("LoadBalancerPort").equals(80)
    listener.should.have.key("SSLCertificateId").equals("None")

    listener = elb["ListenerDescriptions"][1]["Listener"]
    listener.should.have.key("LoadBalancerPort").equals(81)
    listener.should.have.key("SSLCertificateId").equals(certificate_arn)


@mock_elb
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
    lbs["LoadBalancerDescriptions"].should.have.length_of(1)

    lbs = client.describe_load_balancers(LoadBalancerNames=[lb_name2])
    lbs["LoadBalancerDescriptions"].should.have.length_of(1)

    lbs = client.describe_load_balancers(LoadBalancerNames=[lb_name1, lb_name2])
    lbs["LoadBalancerDescriptions"].should.have.length_of(2)

    with pytest.raises(ClientError) as ex:
        client.describe_load_balancers(LoadBalancerNames=["unknownlb"])
    err = ex.value.response["Error"]
    err["Code"].should.equal("LoadBalancerNotFound")
    err["Message"].should.equal("The specified load balancer does not exist: unknownlb")

    with pytest.raises(ClientError) as ex:
        client.describe_load_balancers(LoadBalancerNames=[lb_name1, "unknownlb"])
    err = ex.value.response["Error"]
    err["Code"].should.equal("LoadBalancerNotFound")
    # Bug - message sometimes shows the lb that does exist
    err["Message"].should.match("The specified load balancer does not exist:")


@mock_elb
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
    lb_names.should.contain(lb_name1)
    lb_names.should.contain(lb_name2)

    client.delete_load_balancer(LoadBalancerName=lb_name1)

    lbs = client.describe_load_balancers()["LoadBalancerDescriptions"]
    lb_names = [lb["LoadBalancerName"] for lb in lbs]
    lb_names.shouldnt.contain(lb_name1)
    lb_names.should.contain(lb_name2)


@mock_elb
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
    balancer["HealthCheck"]["Target"].should.equal("HTTP:8080/health")
    balancer["HealthCheck"]["Interval"].should.equal(20)
    balancer["HealthCheck"]["Timeout"].should.equal(23)
    balancer["HealthCheck"]["HealthyThreshold"].should.equal(3)
    balancer["HealthCheck"]["UnhealthyThreshold"].should.equal(5)


@mock_ec2
@mock_elb
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
    set(instance_ids).should.equal(set([instance_id1, instance_id2]))


@mock_ec2
@mock_elb
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
    balancer["Instances"].should.have.length_of(2)

    client.deregister_instances_from_load_balancer(
        LoadBalancerName="my-lb", Instances=[{"InstanceId": instance_id1}]
    )

    balancer = client.describe_load_balancers()["LoadBalancerDescriptions"][0]
    balancer["Instances"].should.have.length_of(1)
    balancer["Instances"][0]["InstanceId"].should.equal(instance_id2)


@mock_elb
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
    attributes.should.have.key("CrossZoneLoadBalancing").equal({"Enabled": False})
    attributes.should.have.key("AccessLog").equal({"Enabled": False})
    attributes.should.have.key("ConnectionDraining").equal({"Enabled": False})
    attributes.should.have.key("ConnectionSettings").equal({"IdleTimeout": 60})


@mock_elb
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
    attributes.should.have.key("ConnectionDraining").equal(
        {"Enabled": False, "Timeout": 300}
    )


@mock_elb
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


@mock_ec2
@mock_elb
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
    instances_health.should.have.length_of(2)


@mock_ec2
@mock_elb
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
    instances_health.should.have.length_of(3)

    # The first instance is healthy
    instances_health[0]["InstanceId"].should.equal(instance_ids[0])
    instances_health[0]["State"].should.equal("InService")

    # The second instance was never known to ELB
    instances_health[1]["InstanceId"].should.equal(instance_ids[1])
    instances_health[1]["State"].should.equal("Unknown")

    # The third instance was stopped
    instances_health[2]["InstanceId"].should.equal(instance_ids[2])
    instances_health[2]["State"].should.equal("OutOfService")


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
            (lb["LoadBalancerName"], dict([(d["Key"], d["Value"]) for d in lb["Tags"]]))
            for lb in client.describe_tags(LoadBalancerNames=["my-lb", "other-lb"])[
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
    lb.should.have.key("SourceSecurityGroup").equals(
        {"OwnerAlias": f"{DEFAULT_ACCOUNT_ID}", "GroupName": "default"}
    )


@mock_elb
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
    err["Code"].should.equal("DuplicateLoadBalancerName")
    err["Message"].should.equal(
        f"The specified load balancer name already exists for this account: {lb_name}"
    )
