import json

import boto3
from botocore.exceptions import ClientError
from nose.tools import assert_raises

from moto import mock_iam


invalid_documents_test_cases = [
    {
        "document": "This is not a json document",
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket"
            }
        },
        "error_message": 'Policy document must be version 2012-10-17 or greater.'
    },
    {
        "document": {
            "Version": "2008-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket"
            }
        },
        "error_message": 'Policy document must be version 2012-10-17 or greater.'
    },
    {
        "document": {
            "Version": "2013-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket"
            }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17"
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": ["afd"]
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket"
            },
            "Extra field": "value"
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "Extra field": "value"
            }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Id": ["cd3a324d2343d942772346-34234234423404-4c2242343242349d1642ee"],
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket"
            }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Id": {},
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket"
            }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "invalid",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket"
            }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "invalid",
                "Resource": "arn:aws:s3:::example_bucket"
            }
        },
        "error_message": 'Actions/Conditions must be prefaced by a vendor, e.g., iam, sdb, ec2, etc.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "NotAction": "",
                    "Resource": "arn:aws:s3:::example_bucket"
                }
        },
        "error_message": 'Actions/Conditions must be prefaced by a vendor, e.g., iam, sdb, ec2, etc.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "a a:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket"
                }
        },
        "error_message": 'Vendor a a is not valid'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:List:Bucket",
                    "Resource": "arn:aws:s3:::example_bucket"
                }
        },
        "error_message": 'Actions/Condition can contain only one colon.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "s3s:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket"
                },
                {
                    "Effect": "Allow",
                    "Action": "s:3s:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket"
                }
            ]
        },
        "error_message": 'Actions/Condition can contain only one colon.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "invalid resource"
            }
        },
        "error_message": 'Resource invalid resource must be in ARN format or "*".'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s:3:ListBucket",
                    "Resource": "sdfsadf"
                }
        },
        "error_message": 'Resource sdfsadf must be in ARN format or "*".'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": ["adf"]
            }
        },
        "error_message": 'Resource adf must be in ARN format or "*".'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": ""
            }
        },
        "error_message": 'Resource  must be in ARN format or "*".'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "NotAction": "s3s:ListBucket",
                    "Resource": "a:bsdfdsafsad"
                }
        },
        "error_message": 'Partition "bsdfdsafsad" is not valid for resource "arn:bsdfdsafsad:*:*:*:*".'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "NotAction": "s3s:ListBucket",
                    "Resource": "a:b:cadfsdf"
                }
        },
        "error_message": 'Partition "b" is not valid for resource "arn:b:cadfsdf:*:*:*".'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "NotAction": "s3s:ListBucket",
                    "Resource": "a:b:c:d:e:f:g:h"
                }
        },
        "error_message": 'Partition "b" is not valid for resource "arn:b:c:d:e:f:g:h".'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": []
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket"
            }
        },
        "error_message": 'Policy statement must contain resources.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": []
            }
        },
        "error_message": 'Policy statement must contain resources.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "invalid"
            }
        },
        "error_message": 'Policy statement must contain resources.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Resource": "arn:aws:s3:::example_bucket"
            }
        },
        "error_message": 'Policy statement must contain actions.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket"
            }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow"
            }
        },
        "error_message": 'Policy statement must contain actions.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": [],
                    "Resource": "arn:aws:s3:::example_bucket"
                }
        },
        "error_message": 'Policy statement must contain actions.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Deny"
                },
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket"
                }
            ]
        },
        "error_message": 'Policy statement must contain actions.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:iam:::example_bucket"
                }
        },
        "error_message": 'IAM resource path must either be "*" or start with user/, federated-user/, role/, group/, instance-profile/, mfa/, server-certificate/, policy/, sms-mfa/, saml-provider/, oidc-provider/, report/, access-report/.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3::example_bucket"
                }
        },
        "error_message": 'The policy failed legacy parsing'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws"
                }
        },
        "error_message": 'Resource vendor must be fully qualified and cannot contain regexes.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": {
                        "a": "arn:aws:s3:::example_bucket"
                    }
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Deny",
                "Action": "s3:ListBucket",
                "Resource": ["adfdf", {}]
            }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "NotAction": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                    "NotResource": []
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Deny",
                "Action": [[]],
                "Resource": "arn:aws:s3:::example_bucket"
            }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "NotAction": "s3s:ListBucket",
                    "Action": [],
                    "Resource": "arn:aws:s3:::example_bucket"
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": {},
                    "Resource": "arn:aws:s3:::example_bucket"
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                    "Condition": []
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                    "Condition": "a"
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                    "Condition": {
                        "a": "b"
                    }
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                    "Condition": {
                        "DateGreaterThan": "b"
                    }
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                    "Condition": {
                        "DateGreaterThan": []
                    }
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                    "Condition": {
                        "DateGreaterThan": {"a": {}}
                    }
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::example_bucket",
                    "Condition": {
                        "DateGreaterThan": {"a": {}}
                    }
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                    "Condition": [
                        {"ForAllValues:StringEquals": {"aws:TagKeys": "Department"}}
                    ]
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:iam:us-east-1::example_bucket"
                }
        },
        "error_message": 'IAM resource arn:aws:iam:us-east-1::example_bucket cannot contain region information.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:us-east-1::example_bucket"
                }
        },
        "error_message": 'Resource arn:aws:s3:us-east-1::example_bucket can not contain region information.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Sid": {},
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket"
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Sid": [],
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket"
                }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "sdf",
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket"
                },
                {
                    "Sid": "sdf",
                    "Effect": "Allow"
                }
            ]
        },
        "error_message": 'Statement IDs (SID) in a single policy must be unique.'
    },
    {
        "document": {
            "Statement": [
                {
                    "Sid": "sdf",
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket"
                },
                {
                    "Sid": "sdf",
                    "Effect": "Allow"
                }
            ]
        },
        "error_message": 'Policy document must be version 2012-10-17 or greater.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "NotAction": "s3:ListBucket",
                "Action": "iam:dsf",
                "Resource": "arn:aws:s3:::example_bucket"
            }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket",
                "NotResource": "*"
            }
        },
        "error_message": 'Syntax errors in policy.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "denY",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example_bucket"
            }
        },
        "error_message": 'The policy failed legacy parsing'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                    "Condition": {
                        "DateGreaterThan": {"a": "sdfdsf"}
                    }
                }
        },
        "error_message": 'The policy failed legacy parsing'
    },
    {
        "document": {
            "Statement":
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket",
                    "Condition": {
                        "DateGreaterThan": {"a": "sdfdsf"}
                    }
                }
        },
        "error_message": 'Policy document must be version 2012-10-17 or greater.'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "Condition": {
                        "DateGreaterThan": {"a": "sdfdsf"}
                    }
                }
        },
        "error_message": 'The policy failed legacy parsing'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "Allow",
                    "NotAction": "s3:ListBucket",
                    "Resource": "arn:aws::::example_bucket"
                }
        },
        "error_message": 'The policy failed legacy parsing'
    },
    {
        "document": {
            "Version": "2012-10-17",
            "Statement":
                {
                    "Effect": "allow",
                    "Resource": "arn:aws:s3:us-east-1::example_bucket"
                }
        },
        "error_message": 'The policy failed legacy parsing'
    }
]  # TODO add more tests


def test_create_policy_with_invalid_policy_documents():
    for test_case in invalid_documents_test_cases:
        yield check_create_policy_with_invalid_policy_document, test_case


@mock_iam
def check_create_policy_with_invalid_policy_document(test_case):
    conn = boto3.client('iam', region_name='us-east-1')
    with assert_raises(ClientError) as ex:
        conn.create_policy(
            PolicyName="TestCreatePolicy",
            PolicyDocument=json.dumps(test_case["document"]))
    ex.exception.response['Error']['Code'].should.equal('MalformedPolicyDocument')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(400)
    ex.exception.response['Error']['Message'].should.equal(test_case["error_message"])
