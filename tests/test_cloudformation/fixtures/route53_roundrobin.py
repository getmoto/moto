from __future__ import unicode_literals

template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "AWS CloudFormation Sample Template Route53_RoundRobin: Sample template showing how to use weighted round robin (WRR) DNS entried via Amazon Route 53. This contrived sample uses weighted CNAME records to illustrate that the weighting influences the return records. It assumes that you already have a Hosted Zone registered with Amazon Route 53. **WARNING** This template creates one or more AWS resources. You will be billed for the AWS resources used if you create a stack from this template.",
    "Parameters": {"R53ZoneName": {"Type": "String", "Default": "my_zone"}},
    "Resources": {
        "MyZone": {
            "Type": "AWS::Route53::HostedZone",
            "Properties": {"Name": {"Ref": "R53ZoneName"}},
        },
        "MyDNSRecord": {
            "Type": "AWS::Route53::RecordSetGroup",
            "Properties": {
                "HostedZoneId": {"Ref": "MyZone"},
                "Comment": "Contrived example to redirect to aws.amazon.com 75% of the time and www.amazon.com 25% of the time.",
                "RecordSets": [
                    {
                        "SetIdentifier": {
                            "Fn::Join": [" ", [{"Ref": "AWS::StackName"}, "AWS"]]
                        },
                        "Name": {
                            "Fn::Join": [
                                "",
                                [
                                    {"Ref": "AWS::StackName"},
                                    ".",
                                    {"Ref": "AWS::Region"},
                                    ".",
                                    {"Ref": "R53ZoneName"},
                                    ".",
                                ],
                            ]
                        },
                        "Type": "CNAME",
                        "TTL": "900",
                        "ResourceRecords": ["aws.amazon.com"],
                        "Weight": "3",
                    },
                    {
                        "SetIdentifier": {
                            "Fn::Join": [" ", [{"Ref": "AWS::StackName"}, "Amazon"]]
                        },
                        "Name": {
                            "Fn::Join": [
                                "",
                                [
                                    {"Ref": "AWS::StackName"},
                                    ".",
                                    {"Ref": "AWS::Region"},
                                    ".",
                                    {"Ref": "R53ZoneName"},
                                    ".",
                                ],
                            ]
                        },
                        "Type": "CNAME",
                        "TTL": "900",
                        "ResourceRecords": ["www.amazon.com"],
                        "Weight": "1",
                    },
                ],
            },
        },
    },
    "Outputs": {
        "DomainName": {
            "Description": "Fully qualified domain name",
            "Value": {"Ref": "MyDNSRecord"},
        }
    },
}
