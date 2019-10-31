from __future__ import unicode_literals

template = {
    "Parameters": {"R53ZoneName": {"Type": "String", "Default": "my_zone"}},
    "Resources": {
        "Ec2Instance": {
            "Type": "AWS::EC2::Instance",
            "Properties": {"ImageId": "ami-1234abcd", "PrivateIpAddress": "10.0.0.25"},
        },
        "HostedZone": {
            "Type": "AWS::Route53::HostedZone",
            "Properties": {"Name": {"Ref": "R53ZoneName"}},
        },
        "myDNSRecord": {
            "Type": "AWS::Route53::RecordSet",
            "Properties": {
                "HostedZoneId": {"Ref": "HostedZone"},
                "Comment": "DNS name for my instance.",
                "Name": {
                    "Fn::Join": [
                        "",
                        [
                            {"Ref": "Ec2Instance"},
                            ".",
                            {"Ref": "AWS::Region"},
                            ".",
                            {"Ref": "R53ZoneName"},
                            ".",
                        ],
                    ]
                },
                "Type": "A",
                "TTL": "900",
                "ResourceRecords": [{"Fn::GetAtt": ["Ec2Instance", "PrivateIp"]}],
            },
        },
    },
}
