from __future__ import unicode_literals

template = {
    "Resources": {
        "Ec2Instance": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "ImageId": "ami-1234abcd",
                "PrivateIpAddress": "10.0.0.25",
            }
        },

        "HostedZone": {
            "Type": "AWS::Route53::HostedZone",
            "Properties": {
                "Name": "my_zone"
            }
        },

        "myDNSRecord": {
            "Type": "AWS::Route53::RecordSet",
            "Properties": {
                "HostedZoneName": {"Ref": "HostedZone"},
                "Comment": "DNS name for my instance.",
                "Name": {
                    "Fn::Join": ["", [
                        {"Ref": "Ec2Instance"}, ".",
                        {"Ref": "AWS::Region"}, ".",
                        {"Ref": "HostedZone"}, "."
                    ]]
                },
                "Type": "A",
                "TTL": "900",
                "ResourceRecords": [
                    {"Fn::GetAtt": ["Ec2Instance", "PrivateIp"]}
                ]
            }
        }
    },
}
