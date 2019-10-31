from __future__ import unicode_literals

template = {
    "Resources": {
        "HostedZone": {
            "Type": "AWS::Route53::HostedZone",
            "Properties": {"Name": "my_zone"},
        },
        "my_health_check": {
            "Type": "AWS::Route53::HealthCheck",
            "Properties": {
                "HealthCheckConfig": {
                    "FailureThreshold": 3,
                    "IPAddress": "10.0.0.4",
                    "Port": 80,
                    "RequestInterval": 10,
                    "ResourcePath": "/",
                    "Type": "HTTP",
                }
            },
        },
        "myDNSRecord": {
            "Type": "AWS::Route53::RecordSet",
            "Properties": {
                "HostedZoneId": {"Ref": "HostedZone"},
                "Comment": "DNS name for my instance.",
                "Name": "my_record_set",
                "Type": "A",
                "TTL": "900",
                "ResourceRecords": ["my.example.com"],
                "HealthCheckId": {"Ref": "my_health_check"},
            },
        },
    }
}
