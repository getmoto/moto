import boto3
import json
import sure  # noqa # pylint: disable=unused-import

from copy import deepcopy
from moto import mock_cloudformation, mock_ec2, mock_route53
from tests.test_cloudformation.fixtures import route53_ec2_instance_with_public_ip
from tests.test_cloudformation.fixtures import route53_health_check
from tests.test_cloudformation.fixtures import route53_roundrobin

template_hosted_zone = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 1",
    "Parameters": {},
    "Resources": {
        "Bar": {
            "Type": "AWS::Route53::HostedZone",
            "Properties": {"Name": "foo.bar.baz"},
        }
    },
}
template_record_set = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 2",
    "Parameters": {"ZoneId": {"Type": "String"}},
    "Resources": {
        "Foo": {
            "Properties": {
                "HostedZoneId": {"Ref": "ZoneId"},
                "RecordSets": [
                    {
                        "Name": "test.vpc.internal",
                        "Type": "A",
                        "SetIdentifier": "test1",
                        "Weight": 50,
                    }
                ],
            },
            "Type": "AWS::Route53::RecordSetGroup",
        }
    },
}


@mock_cloudformation
@mock_route53
def test_create_stack_hosted_zone_by_id():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    conn = boto3.client("route53", region_name="us-east-1")

    # when creating a hosted zone via CF
    cf_conn.create_stack(
        StackName="test_stack1", TemplateBody=json.dumps(template_hosted_zone)
    )

    # then a hosted zone should exist
    zone = conn.list_hosted_zones()["HostedZones"][0]
    zone.should.have.key("Name").equal("foo.bar.baz")
    zone.should.have.key("ResourceRecordSetCount").equal(2)

    # when adding a record set to this zone
    cf_conn.create_stack(
        StackName="test_stack2",
        TemplateBody=json.dumps(template_record_set),
        Parameters=[{"ParameterKey": "ZoneId", "ParameterValue": zone["Id"]}],
    )

    # then the hosted zone should have a record
    updated_zone = conn.list_hosted_zones()["HostedZones"][0]
    updated_zone.should.have.key("Id").equal(zone["Id"])
    updated_zone.should.have.key("Name").equal("foo.bar.baz")
    updated_zone.should.have.key("ResourceRecordSetCount").equal(3)


@mock_cloudformation
@mock_route53
def test_route53_roundrobin():
    cf = boto3.client("cloudformation", region_name="us-west-1")
    route53 = boto3.client("route53", region_name="us-west-1")

    template_json = json.dumps(route53_roundrobin.template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    zones = route53.list_hosted_zones()["HostedZones"]
    zones.should.have.length_of(1)
    zone_id = zones[0]["Id"].split("/")[2]

    rrsets = route53.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]
    rrsets.should.have.length_of(4)
    record_set1 = rrsets[2]
    record_set1["Name"].should.equal("test_stack.us-west-1.my_zone.")
    record_set1["SetIdentifier"].should.equal("test_stack AWS")
    record_set1["Type"].should.equal("CNAME")
    record_set1["TTL"].should.equal(900)
    record_set1["Weight"].should.equal(3)
    record_set1["ResourceRecords"][0]["Value"].should.equal("aws.amazon.com")

    record_set2 = rrsets[3]
    record_set2["Name"].should.equal("test_stack.us-west-1.my_zone.")
    record_set2["SetIdentifier"].should.equal("test_stack Amazon")
    record_set2["Type"].should.equal("CNAME")
    record_set2["TTL"].should.equal(900)
    record_set2["Weight"].should.equal(1)
    record_set2["ResourceRecords"][0]["Value"].should.equal("www.amazon.com")

    stack = cf.describe_stacks(StackName="test_stack")["Stacks"][0]
    output = stack["Outputs"][0]
    output["OutputKey"].should.equal("DomainName")
    output["OutputValue"].should.equal(f"arn:aws:route53:::hostedzone/{zone_id}")


@mock_cloudformation
@mock_ec2
@mock_route53
def test_route53_ec2_instance_with_public_ip():
    route53 = boto3.client("route53", region_name="us-west-1")
    ec2 = boto3.client("ec2", region_name="us-west-1")

    template_json = json.dumps(route53_ec2_instance_with_public_ip.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    instance_id = ec2.describe_instances()["Reservations"][0]["Instances"][0][
        "InstanceId"
    ]

    zones = route53.list_hosted_zones()["HostedZones"]
    zones.should.have.length_of(1)
    zone_id = zones[0]["Id"].split("/")[2]

    rrsets = route53.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]
    rrsets.should.have.length_of(3)

    record_set = rrsets[2]
    record_set["Name"].should.equal(f"{instance_id}.us-west-1.my_zone.")
    record_set.shouldnt.have.key("SetIdentifier")
    record_set["Type"].should.equal("A")
    record_set["TTL"].should.equal(900)
    record_set.shouldnt.have.key("Weight")
    record_set["ResourceRecords"][0]["Value"].should.equal("10.0.0.25")


@mock_cloudformation
@mock_route53
def test_route53_associate_health_check():
    route53 = boto3.client("route53", region_name="us-west-1")

    template_json = json.dumps(route53_health_check.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    checks = route53.list_health_checks()["HealthChecks"]
    checks.should.have.length_of(1)
    check = checks[0]
    health_check_id = check["Id"]
    config = check["HealthCheckConfig"]
    config["FailureThreshold"].should.equal(3)
    config["IPAddress"].should.equal("10.0.0.4")
    config["Port"].should.equal(80)
    config["RequestInterval"].should.equal(10)
    config["ResourcePath"].should.equal("/")
    config["Type"].should.equal("HTTP")

    zones = route53.list_hosted_zones()["HostedZones"]
    zones.should.have.length_of(1)
    zone_id = zones[0]["Id"].split("/")[2]

    rrsets = route53.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]
    rrsets.should.have.length_of(3)
    record_set = rrsets[0]
    record_set["HealthCheckId"].should.equal(health_check_id)


@mock_cloudformation
@mock_route53
def test_route53_with_update():
    route53 = boto3.client("route53", region_name="us-west-1")

    template_json = json.dumps(route53_health_check.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    zones = route53.list_hosted_zones()["HostedZones"]
    zones.should.have.length_of(1)
    zone_id = zones[0]["Id"]
    zone_id = zone_id.split("/")
    zone_id = zone_id[2]

    rrsets = route53.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]
    rrsets.should.have.length_of(3)

    record_set = rrsets[0]
    record_set["ResourceRecords"][0]["Value"].should.equal("my.example.com")

    # # given
    template = deepcopy(route53_health_check.template)
    template["Resources"]["myDNSRecord"]["Properties"]["ResourceRecords"] = [
        "my_other.example.com"
    ]
    template_json = json.dumps(template)

    # # when
    cf.update_stack(StackName="test_stack", TemplateBody=template_json)

    # # then
    zones = route53.list_hosted_zones()["HostedZones"]
    zones.should.have.length_of(1)
    zone_id = zones[0]["Id"].split("/")[2]

    rrsets = route53.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]
    rrsets.should.have.length_of(3)

    record_set = rrsets[0]
    record_set["ResourceRecords"][0]["Value"].should.equal("my_other.example.com")


@mock_cloudformation
@mock_route53
def test_delete_route53_recordset():

    cf = boto3.client("cloudformation", region_name="us-west-1")

    # given a stack with a record set
    stack_name = "test_stack_recordset_delete"
    template_json = json.dumps(route53_health_check.template)

    cf.create_stack(StackName=stack_name, TemplateBody=template_json)

    # when the stack is deleted
    cf.delete_stack(StackName=stack_name)

    # then it should not error
