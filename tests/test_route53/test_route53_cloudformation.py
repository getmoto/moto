import json
from copy import deepcopy

import boto3

from moto import mock_aws
from tests.test_cloudformation.fixtures import (
    route53_ec2_instance_with_public_ip,
    route53_health_check,
    route53_roundrobin,
)

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


@mock_aws
def test_create_stack_hosted_zone_by_id():
    cf_conn = boto3.client("cloudformation", region_name="us-east-1")
    conn = boto3.client("route53", region_name="us-east-1")

    # when creating a hosted zone via CF
    cf_conn.create_stack(
        StackName="test_stack1", TemplateBody=json.dumps(template_hosted_zone)
    )

    # then a hosted zone should exist
    zone = conn.list_hosted_zones()["HostedZones"][0]
    assert zone["Name"] == "foo.bar.baz"
    assert zone["ResourceRecordSetCount"] == 2

    # when adding a record set to this zone
    cf_conn.create_stack(
        StackName="test_stack2",
        TemplateBody=json.dumps(template_record_set),
        Parameters=[{"ParameterKey": "ZoneId", "ParameterValue": zone["Id"]}],
    )

    # then the hosted zone should have a record
    updated_zone = conn.list_hosted_zones()["HostedZones"][0]
    assert updated_zone["Id"] == zone["Id"]
    assert updated_zone["Name"] == "foo.bar.baz"
    assert updated_zone["ResourceRecordSetCount"] == 3


@mock_aws
def test_route53_roundrobin():
    cf = boto3.client("cloudformation", region_name="us-west-1")
    route53 = boto3.client("route53", region_name="us-west-1")

    template_json = json.dumps(route53_roundrobin.template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    zones = route53.list_hosted_zones()["HostedZones"]
    assert len(zones) == 1
    zone_id = zones[0]["Id"].split("/")[2]

    rrsets = route53.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]
    assert len(rrsets) == 4
    record_set1 = rrsets[2]
    assert record_set1["Name"] == "test_stack.us-west-1.my_zone."
    assert record_set1["SetIdentifier"] == "test_stack AWS"
    assert record_set1["Type"] == "CNAME"
    assert record_set1["TTL"] == 900
    assert record_set1["Weight"] == 3
    assert record_set1["ResourceRecords"][0]["Value"] == "aws.amazon.com"

    record_set2 = rrsets[3]
    assert record_set2["Name"] == "test_stack.us-west-1.my_zone."
    assert record_set2["SetIdentifier"] == "test_stack Amazon"
    assert record_set2["Type"] == "CNAME"
    assert record_set2["TTL"] == 900
    assert record_set2["Weight"] == 1
    assert record_set2["ResourceRecords"][0]["Value"] == "www.amazon.com"

    stack = cf.describe_stacks(StackName="test_stack")["Stacks"][0]
    output = stack["Outputs"][0]
    assert output["OutputKey"] == "DomainName"
    assert output["OutputValue"] == f"arn:aws:route53:::hostedzone/{zone_id}"


@mock_aws
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
    assert len(zones) == 1
    zone_id = zones[0]["Id"].split("/")[2]

    rrsets = route53.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]
    assert len(rrsets) == 3

    record_set = rrsets[2]
    assert record_set["Name"] == f"{instance_id}.us-west-1.my_zone."
    assert record_set["Type"] == "A"
    assert record_set["TTL"] == 900
    assert record_set["ResourceRecords"][0]["Value"] == "10.0.0.25"
    assert "SetIdentifier" not in record_set
    assert "Weight" not in record_set


@mock_aws
def test_route53_associate_health_check():
    route53 = boto3.client("route53", region_name="us-west-1")

    template_json = json.dumps(route53_health_check.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    checks = route53.list_health_checks()["HealthChecks"]
    assert len(checks) == 1
    check = checks[0]
    health_check_id = check["Id"]
    config = check["HealthCheckConfig"]
    assert config["FailureThreshold"] == 3
    assert config["IPAddress"] == "10.0.0.4"
    assert config["Port"] == 80
    assert config["RequestInterval"] == 10
    assert config["ResourcePath"] == "/"
    assert config["Type"] == "HTTP"

    zones = route53.list_hosted_zones()["HostedZones"]
    assert len(zones) == 1
    zone_id = zones[0]["Id"].split("/")[2]

    rrsets = route53.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]
    assert len(rrsets) == 3
    record_set = rrsets[0]
    assert record_set["HealthCheckId"] == health_check_id


@mock_aws
def test_route53_with_update():
    route53 = boto3.client("route53", region_name="us-west-1")

    template_json = json.dumps(route53_health_check.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    zones = route53.list_hosted_zones()["HostedZones"]
    assert len(zones) == 1
    zone_id = zones[0]["Id"]
    zone_id = zone_id.split("/")
    zone_id = zone_id[2]

    rrsets = route53.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]
    assert len(rrsets) == 3

    record_set = rrsets[0]
    assert record_set["ResourceRecords"][0]["Value"] == "my.example.com"

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
    assert len(zones) == 1
    zone_id = zones[0]["Id"].split("/")[2]

    rrsets = route53.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]
    assert len(rrsets) == 3

    record_set = rrsets[0]
    assert record_set["ResourceRecords"][0]["Value"] == "my_other.example.com"


@mock_aws
def test_delete_route53_recordset():
    cf = boto3.client("cloudformation", region_name="us-west-1")

    # given a stack with a record set
    stack_name = "test_stack_recordset_delete"
    template_json = json.dumps(route53_health_check.template)

    cf.create_stack(StackName=stack_name, TemplateBody=template_json)

    # when the stack is deleted
    cf.delete_stack(StackName=stack_name)

    # then it should not error
