from __future__ import unicode_literals

template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "AWS CloudFormation Sample Template to create a KMS Key.  The Fn::GetAtt is used to retrieve the ARN",
    "Resources": {
        "myKey": {
            "Type": "AWS::KMS::Key",
            "Properties": {
                "Description": "Sample KmsKey",
                "EnableKeyRotation": False,
                "Enabled": True,
                "KeyPolicy": {
                    "Version": "2012-10-17",
                    "Id": "key-default-1",
                    "Statement": [
                        {
                            "Sid": "Enable IAM User Permissions",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:aws:iam::",
                                            {"Ref": "AWS::AccountId"},
                                            ":root",
                                        ],
                                    ]
                                }
                            },
                            "Action": "kms:*",
                            "Resource": "*",
                        }
                    ],
                },
            },
        }
    },
    "Outputs": {
        "KeyArn": {
            "Description": "Generated Key Arn",
            "Value": {"Fn::GetAtt": ["myKey", "Arn"]},
        }
    },
}
