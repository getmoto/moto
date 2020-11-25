import json

import boto3
from botocore.exceptions import ClientError
import pytest
import sure  # noqa

from moto import mock_iam

invalid_policy_document_test_cases = [
    {
        "document": "This is not a json document",
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            }
        },
        "error_message": "Policy document must be version 2012-10-17 or greater.",
    },
    {
        "document": {
            "Version": "2008-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Policy document must be version 2012-10-17 or greater.",
    },
    {
        "document": {
            "Version": "2013-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {"Version": "2012-10-17"},
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {"Version": "2012-10-17", "Statement": ["afd"]},
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
            "Extra field": "value",
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Extra field": "value",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Id": ["cd3a324d2343d942772346-34234234423404-4c2242343242349d1642ee"],
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Id": {},
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "invalid",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "invalid",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Actions/Conditions must be prefaced by a vendor, e.g., iam, sdb, ec2, etc.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "NotAction": "",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Actions/Conditions must be prefaced by a vendor, e.g., iam, sdb, ec2, etc.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "a a:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Vendor a a is not valid",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:List:Bucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Actions/Condition can contain only one colon.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "s3s:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                },
                {
                    "Effect": "Allow",
                    "Action": "s:3s:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                },
            ],
        },
        "error_message": "Actions/Condition can contain only one colon.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "invalid resource",
            },
        },
        "error_message": 'Resource invalid resource must be in ARN format or "*".',
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "EnableDisableHongKong",
                    "Effect": "Allow",
                    "Action": ["account:EnableRegion", "account:DisableRegion"],
                    "Resource": "",
                    "Condition": {
                        "StringEquals": {"account:TargetRegion": "ap-east-1"}
                    },
                },
                {
                    "Sid": "ViewConsole",
                    "Effect": "Allow",
                    "Action": ["aws-portal:ViewAccount", "account:ListRegions"],
                    "Resource": "",
                },
            ],
        },
        "error_message": 'Resource  must be in ARN format or "*".',
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s:3:ListBucket",
                "Resource": "sdfsadf",
            },
        },
        "error_message": 'Resource sdfsadf must be in ARN format or "*".',
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": ["adf"],
            },
        },
        "error_message": 'Resource adf must be in ARN format or "*".',
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {"Effect": "Allow", "Action": "s3:ListBucket", "Resource": ""},
        },
        "error_message": 'Resource  must be in ARN format or "*".',
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "NotAction": "s3s:ListBucket",
                "Resource": "a:bsdfdsafsad",
            },
        },
        "error_message": 'Partition "bsdfdsafsad" is not valid for resource "arn:bsdfdsafsad:*:*:*:*".',
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "NotAction": "s3s:ListBucket",
                "Resource": "a:b:cadfsdf",
            },
        },
        "error_message": 'Partition "b" is not valid for resource "arn:b:cadfsdf:*:*:*".',
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "NotAction": "s3s:ListBucket",
                "Resource": "a:b:c:d:e:f:g:h",
            },
        },
        "error_message": 'Partition "b" is not valid for resource "arn:b:c:d:e:f:g:h".',
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "aws:s3:::example_bucket",
            },
        },
        "error_message": 'Partition "s3" is not valid for resource "arn:s3:::example_bucket:*".',
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": [
                    "arn:error:s3:::example_bucket",
                    "arn:error:s3::example_bucket",
                ],
            },
        },
        "error_message": 'Partition "error" is not valid for resource "arn:error:s3:::example_bucket".',
    },
    {
        "document": {"Version": "2012-10-17", "Statement": []},
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {"Effect": "Allow", "Action": "s3:ListBucket"},
        },
        "error_message": "Policy statement must contain resources.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {"Effect": "Allow", "Action": "s3:ListBucket", "Resource": []},
        },
        "error_message": "Policy statement must contain resources.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {"Effect": "Allow", "Action": "invalid"},
        },
        "error_message": "Policy statement must contain resources.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {"Effect": "Allow", "Resource": "arn:aws:s3:::example_bucket"},
        },
        "error_message": "Policy statement must contain actions.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {"Version": "2012-10-17", "Statement": {"Effect": "Allow"}},
        "error_message": "Policy statement must contain actions.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": [],
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Policy statement must contain actions.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Deny"},
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                },
            ],
        },
        "error_message": "Policy statement must contain actions.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:iam:::example_bucket",
            },
        },
        "error_message": 'IAM resource path must either be "*" or start with user/, federated-user/, role/, group/, instance-profile/, mfa/, server-certificate/, policy/, sms-mfa/, saml-provider/, oidc-provider/, report/, access-report/.',
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3::example_bucket",
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {"Effect": "Allow", "Resource": "arn:aws:s3::example_bucket"},
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws",
            },
        },
        "error_message": "Resource vendor must be fully qualified and cannot contain regexes.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": {"a": "arn:aws:s3:::example_bucket"},
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Deny",
                "Action": "s3:ListBucket",
                "Resource": ["adfdf", {}],
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "NotAction": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "NotResource": [],
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Deny",
                "Action": [[]],
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "NotAction": "s3s:ListBucket",
                "Action": [],
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": {},
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": [],
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": "a",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {"a": "b"},
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {"DateGreaterThan": "b"},
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {"DateGreaterThan": []},
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {"DateGreaterThan": {"a": {}}},
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {"DateGreaterThan": {"a": {}}},
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {"x": {"a": "1"}},
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {"ForAnyValue::StringEqualsIfExists": {"a": "asf"}},
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": [
                    {"ForAllValues:StringEquals": {"aws:TagKeys": "Department"}}
                ],
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:iam:us-east-1::example_bucket",
            },
        },
        "error_message": "IAM resource arn:aws:iam:us-east-1::example_bucket cannot contain region information.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:us-east-1::example_bucket",
            },
        },
        "error_message": "Resource arn:aws:s3:us-east-1::example_bucket can not contain region information.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Sid": {},
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Sid": [],
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "sdf",
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                },
                {"Sid": "sdf", "Effect": "Allow"},
            ],
        },
        "error_message": "Statement IDs (SID) in a single policy must be unique.",
    },
    {
        "document": {
            "Statement": [
                {
                    "Sid": "sdf",
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                },
                {"Sid": "sdf", "Effect": "Allow"},
            ]
        },
        "error_message": "Policy document must be version 2012-10-17 or greater.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "NotAction": "s3:ListBucket",
                "Action": "iam:dsf",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "NotResource": "*",
            },
        },
        "error_message": "Syntax errors in policy.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "denY",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {"DateGreaterThan": {"a": "sdfdsf"}},
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {"DateGreaterThan": {"a": "sdfdsf"}},
            }
        },
        "error_message": "Policy document must be version 2012-10-17 or greater.",
    },
    {
        "document": {
            "Statement": {
                "Effect": "denY",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            }
        },
        "error_message": "Policy document must be version 2012-10-17 or greater.",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Condition": {"DateGreaterThan": {"a": "sdfdsf"}},
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "NotAction": "s3:ListBucket",
                "Resource": "arn:aws::::example_bucket",
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "allow",
                "Resource": "arn:aws:s3:us-east-1::example_bucket",
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "sdf",
                    "Effect": "aLLow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                },
                {"Sid": "sdf", "Effect": "Allow"},
            ],
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "NotResource": "arn:aws:s3::example_bucket",
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {"DateLessThanEquals": {"a": "234-13"}},
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {
                    "DateLessThanEquals": {"a": "2016-12-13t2:00:00.593194+1"}
                },
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {
                    "DateLessThanEquals": {"a": "2016-12-13t2:00:00.1999999999+10:59"}
                },
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Condition": {"DateLessThan": {"a": "9223372036854775808"}},
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:error:s3:::example_bucket",
                "Condition": {"DateGreaterThan": {"a": "sdfdsf"}},
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws::fdsasf",
            },
        },
        "error_message": "The policy failed legacy parsing",
    },
]

valid_policy_documents = [
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": ["arn:aws:s3:::example_bucket"],
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "iam: asdf safdsf af ",
            "Resource": "arn:aws:s3:::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": ["arn:aws:s3:::example_bucket", "*"],
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "*",
            "Resource": "arn:aws:s3:::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            }
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "service-prefix:action-name",
            "Resource": "*",
            "Condition": {
                "DateGreaterThan": {"aws:CurrentTime": "2017-07-01T00:00:00Z"},
                "DateLessThan": {"aws:CurrentTime": "2017-12-31T23:59:59Z"},
            },
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "fsx:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:iam:::user/example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s33:::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:fdsasf",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {},
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {"ForAllValues:StringEquals": {"aws:TagKeys": "Department"}},
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:cloudwatch:us-east-1::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:ec2:us-east-1::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:invalid-service:::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:invalid-service:us-east-1::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {
                "DateGreaterThan": {"aws:CurrentTime": "2017-07-01T00:00:00Z"},
                "DateLessThan": {"aws:CurrentTime": "2017-12-31T23:59:59Z"},
            },
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {"DateGreaterThan": {}},
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {"DateGreaterThan": {"a": []}},
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {"a": {}},
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Sid": "dsfsdfsdfsdfsdfsadfsd",
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ConsoleDisplay",
                "Effect": "Allow",
                "Action": [
                    "iam:GetRole",
                    "iam:GetUser",
                    "iam:ListRoles",
                    "iam:ListRoleTags",
                    "iam:ListUsers",
                    "iam:ListUserTags",
                ],
                "Resource": "*",
            },
            {
                "Sid": "AddTag",
                "Effect": "Allow",
                "Action": ["iam:TagUser", "iam:TagRole"],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {"aws:RequestTag/CostCenter": ["A-123", "B-456"]},
                    "ForAllValues:StringEquals": {"aws:TagKeys": "CostCenter"},
                },
            },
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "NotAction": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Deny",
            "Action": "s3:*",
            "NotResource": [
                "arn:aws:s3:::HRBucket/Payroll",
                "arn:aws:s3:::HRBucket/Payroll/*",
            ],
        },
    },
    {
        "Version": "2012-10-17",
        "Id": "sdfsdfsdf",
        "Statement": {
            "Effect": "Allow",
            "NotAction": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "aaaaaadsfdsafsadfsadfaaaaa:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3-s:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3.s:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "NotAction": "s3:ListBucket",
            "NotResource": "*",
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "sdf",
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
            {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
            },
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {"DateGreaterThan": {"a": "01T"}},
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {"x": {}, "y": {}},
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {"StringEqualsIfExists": {"a": "asf"}},
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {"ForAnyValue:StringEqualsIfExists": {"a": "asf"}},
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {"DateLessThanEquals": {"a": "2019-07-01T13:20:15Z"}},
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {
                "DateLessThanEquals": {"a": "2016-12-13T21:20:37.593194+00:00"}
            },
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {"DateLessThanEquals": {"a": "2016-12-13t2:00:00.593194+23"}},
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::example_bucket",
            "Condition": {"DateLessThan": {"a": "-292275054"}},
        },
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowViewAccountInfo",
                "Effect": "Allow",
                "Action": [
                    "iam:GetAccountPasswordPolicy",
                    "iam:GetAccountSummary",
                    "iam:ListVirtualMFADevices",
                ],
                "Resource": "*",
            },
            {
                "Sid": "AllowManageOwnPasswords",
                "Effect": "Allow",
                "Action": ["iam:ChangePassword", "iam:GetUser"],
                "Resource": "arn:aws:iam::*:user/${aws:username}",
            },
            {
                "Sid": "AllowManageOwnAccessKeys",
                "Effect": "Allow",
                "Action": [
                    "iam:CreateAccessKey",
                    "iam:DeleteAccessKey",
                    "iam:ListAccessKeys",
                    "iam:UpdateAccessKey",
                ],
                "Resource": "arn:aws:iam::*:user/${aws:username}",
            },
            {
                "Sid": "AllowManageOwnSigningCertificates",
                "Effect": "Allow",
                "Action": [
                    "iam:DeleteSigningCertificate",
                    "iam:ListSigningCertificates",
                    "iam:UpdateSigningCertificate",
                    "iam:UploadSigningCertificate",
                ],
                "Resource": "arn:aws:iam::*:user/${aws:username}",
            },
            {
                "Sid": "AllowManageOwnSSHPublicKeys",
                "Effect": "Allow",
                "Action": [
                    "iam:DeleteSSHPublicKey",
                    "iam:GetSSHPublicKey",
                    "iam:ListSSHPublicKeys",
                    "iam:UpdateSSHPublicKey",
                    "iam:UploadSSHPublicKey",
                ],
                "Resource": "arn:aws:iam::*:user/${aws:username}",
            },
            {
                "Sid": "AllowManageOwnGitCredentials",
                "Effect": "Allow",
                "Action": [
                    "iam:CreateServiceSpecificCredential",
                    "iam:DeleteServiceSpecificCredential",
                    "iam:ListServiceSpecificCredentials",
                    "iam:ResetServiceSpecificCredential",
                    "iam:UpdateServiceSpecificCredential",
                ],
                "Resource": "arn:aws:iam::*:user/${aws:username}",
            },
            {
                "Sid": "AllowManageOwnVirtualMFADevice",
                "Effect": "Allow",
                "Action": ["iam:CreateVirtualMFADevice", "iam:DeleteVirtualMFADevice"],
                "Resource": "arn:aws:iam::*:mfa/${aws:username}",
            },
            {
                "Sid": "AllowManageOwnUserMFA",
                "Effect": "Allow",
                "Action": [
                    "iam:DeactivateMFADevice",
                    "iam:EnableMFADevice",
                    "iam:ListMFADevices",
                    "iam:ResyncMFADevice",
                ],
                "Resource": "arn:aws:iam::*:user/${aws:username}",
            },
            {
                "Sid": "DenyAllExceptListedIfNoMFA",
                "Effect": "Deny",
                "NotAction": [
                    "iam:CreateVirtualMFADevice",
                    "iam:EnableMFADevice",
                    "iam:GetUser",
                    "iam:ListMFADevices",
                    "iam:ListVirtualMFADevices",
                    "iam:ResyncMFADevice",
                    "sts:GetSessionToken",
                ],
                "Resource": "*",
                "Condition": {"BoolIfExists": {"aws:MultiFactorAuthPresent": "false"}},
            },
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ListAndDescribe",
                "Effect": "Allow",
                "Action": [
                    "dynamodb:List*",
                    "dynamodb:DescribeReservedCapacity*",
                    "dynamodb:DescribeLimits",
                    "dynamodb:DescribeTimeToLive",
                ],
                "Resource": "*",
            },
            {
                "Sid": "SpecificTable",
                "Effect": "Allow",
                "Action": [
                    "dynamodb:BatchGet*",
                    "dynamodb:DescribeStream",
                    "dynamodb:DescribeTable",
                    "dynamodb:Get*",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWrite*",
                    "dynamodb:CreateTable",
                    "dynamodb:Delete*",
                    "dynamodb:Update*",
                    "dynamodb:PutItem",
                ],
                "Resource": "arn:aws:dynamodb:*:*:table/MyTable",
            },
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["ec2:AttachVolume", "ec2:DetachVolume"],
                "Resource": ["arn:aws:ec2:*:*:volume/*", "arn:aws:ec2:*:*:instance/*"],
                "Condition": {
                    "ArnEquals": {
                        "ec2:SourceInstanceARN": "arn:aws:ec2:*:*:instance/instance-id"
                    }
                },
            }
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["ec2:AttachVolume", "ec2:DetachVolume"],
                "Resource": "arn:aws:ec2:*:*:instance/*",
                "Condition": {
                    "StringEquals": {"ec2:ResourceTag/Department": "Development"}
                },
            },
            {
                "Effect": "Allow",
                "Action": ["ec2:AttachVolume", "ec2:DetachVolume"],
                "Resource": "arn:aws:ec2:*:*:volume/*",
                "Condition": {
                    "StringEquals": {"ec2:ResourceTag/VolumeUser": "${aws:username}"}
                },
            },
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "StartStopIfTags",
                "Effect": "Allow",
                "Action": [
                    "ec2:StartInstances",
                    "ec2:StopInstances",
                    "ec2:DescribeTags",
                ],
                "Resource": "arn:aws:ec2:region:account-id:instance/*",
                "Condition": {
                    "StringEquals": {
                        "ec2:ResourceTag/Project": "DataAnalytics",
                        "aws:PrincipalTag/Department": "Data",
                    }
                },
            }
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ListYourObjects",
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": ["arn:aws:s3:::bucket-name"],
                "Condition": {
                    "StringLike": {
                        "s3:prefix": [
                            "cognito/application-name/${cognito-identity.amazonaws.com:sub}"
                        ]
                    }
                },
            },
            {
                "Sid": "ReadWriteDeleteYourObjects",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                "Resource": [
                    "arn:aws:s3:::bucket-name/cognito/application-name/${cognito-identity.amazonaws.com:sub}",
                    "arn:aws:s3:::bucket-name/cognito/application-name/${cognito-identity.amazonaws.com:sub}/*",
                ],
            },
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:ListAllMyBuckets", "s3:GetBucketLocation"],
                "Resource": "*",
            },
            {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::bucket-name",
                "Condition": {
                    "StringLike": {"s3:prefix": ["", "home/", "home/${aws:userid}/*"]}
                },
            },
            {
                "Effect": "Allow",
                "Action": "s3:*",
                "Resource": [
                    "arn:aws:s3:::bucket-name/home/${aws:userid}",
                    "arn:aws:s3:::bucket-name/home/${aws:userid}/*",
                ],
            },
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ConsoleAccess",
                "Effect": "Allow",
                "Action": [
                    "s3:GetAccountPublicAccessBlock",
                    "s3:GetBucketAcl",
                    "s3:GetBucketLocation",
                    "s3:GetBucketPolicyStatus",
                    "s3:GetBucketPublicAccessBlock",
                    "s3:ListAllMyBuckets",
                ],
                "Resource": "*",
            },
            {
                "Sid": "ListObjectsInBucket",
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": ["arn:aws:s3:::bucket-name"],
            },
            {
                "Sid": "AllObjectActions",
                "Effect": "Allow",
                "Action": "s3:*Object",
                "Resource": ["arn:aws:s3:::bucket-name/*"],
            },
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowViewAccountInfo",
                "Effect": "Allow",
                "Action": ["iam:GetAccountPasswordPolicy", "iam:GetAccountSummary"],
                "Resource": "*",
            },
            {
                "Sid": "AllowManageOwnPasswords",
                "Effect": "Allow",
                "Action": ["iam:ChangePassword", "iam:GetUser"],
                "Resource": "arn:aws:iam::*:user/${aws:username}",
            },
            {
                "Sid": "AllowManageOwnAccessKeys",
                "Effect": "Allow",
                "Action": [
                    "iam:CreateAccessKey",
                    "iam:DeleteAccessKey",
                    "iam:ListAccessKeys",
                    "iam:UpdateAccessKey",
                ],
                "Resource": "arn:aws:iam::*:user/${aws:username}",
            },
            {
                "Sid": "AllowManageOwnSigningCertificates",
                "Effect": "Allow",
                "Action": [
                    "iam:DeleteSigningCertificate",
                    "iam:ListSigningCertificates",
                    "iam:UpdateSigningCertificate",
                    "iam:UploadSigningCertificate",
                ],
                "Resource": "arn:aws:iam::*:user/${aws:username}",
            },
            {
                "Sid": "AllowManageOwnSSHPublicKeys",
                "Effect": "Allow",
                "Action": [
                    "iam:DeleteSSHPublicKey",
                    "iam:GetSSHPublicKey",
                    "iam:ListSSHPublicKeys",
                    "iam:UpdateSSHPublicKey",
                    "iam:UploadSSHPublicKey",
                ],
                "Resource": "arn:aws:iam::*:user/${aws:username}",
            },
            {
                "Sid": "AllowManageOwnGitCredentials",
                "Effect": "Allow",
                "Action": [
                    "iam:CreateServiceSpecificCredential",
                    "iam:DeleteServiceSpecificCredential",
                    "iam:ListServiceSpecificCredentials",
                    "iam:ResetServiceSpecificCredential",
                    "iam:UpdateServiceSpecificCredential",
                ],
                "Resource": "arn:aws:iam::*:user/${aws:username}",
            },
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "ec2:*",
                "Resource": "*",
                "Effect": "Allow",
                "Condition": {"StringEquals": {"ec2:Region": "region"}},
            }
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "rds:*",
                "Resource": ["arn:aws:rds:region:*:*"],
            },
            {"Effect": "Allow", "Action": ["rds:Describe*"], "Resource": ["*"]},
        ],
    },
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Action": "rds:*",
                "Resource": ["arn:aws:rds:region:*:*"],
            },
            {
                "Sid": "",
                "Effect": "Allow",
                "Action": ["rds:Describe*"],
                "Resource": ["*"],
            },
        ],
    },
]


@pytest.mark.parametrize("invalid_policy_document", invalid_policy_document_test_cases)
@mock_iam
def test_create_policy_with_invalid_policy_document(invalid_policy_document):
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        conn.create_policy(
            PolicyName="TestCreatePolicy",
            PolicyDocument=json.dumps(invalid_policy_document["document"]),
        )
    ex.value.response["Error"]["Code"].should.equal("MalformedPolicyDocument")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        invalid_policy_document["error_message"]
    )


@pytest.mark.parametrize("valid_policy_document", valid_policy_documents)
@mock_iam
def test_create_policy_with_valid_policy_document(valid_policy_document):
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(
        PolicyName="TestCreatePolicy", PolicyDocument=json.dumps(valid_policy_document)
    )
