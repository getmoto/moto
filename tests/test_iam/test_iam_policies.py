import json

import boto3
from botocore.exceptions import ClientError
from nose.tools import assert_raises

from moto import mock_iam


@mock_iam
def test_create_policy_with_invalid_policy_documents():
    conn = boto3.client('iam', region_name='us-east-1')

    invalid_documents_test_cases = [
        {
            "document": "This is not a json document",
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
        },
        {
            "document": {
                "Statement": {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket"
                }
            },
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Policy document must be version 2012-10-17 or greater.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Policy document must be version 2012-10-17 or greater.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
        },
        {
            "document": {
                "Version": "2012-10-17"
            },
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Actions/Conditions must be prefaced by a vendor, e.g., iam, sdb, ec2, etc.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Resource invalid resource must be in ARN format or "*".'
        },
        {
            "document": {
                "Version": "2012-10-17",
                "Statement": []
            },
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
        },
        {
            "document": {
                "Version": "2012-10-17",
                "Statement": {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket"
                }
            },
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Policy statement must contain resources.'
        },
        {
            "document": {
                "Version": "2012-10-17",
                "Statement": {
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::example_bucket"
                }
            },
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Policy statement must contain actions.'
        },
        {
            "document": {
                "Version": "2012-10-17",
                "Statement": {
                    "Action": "s3:ListBucket",
                    "Resource": "arn:aws:s3:::example_bucket"
                }
            },
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
        },
        {
            "document": {
                "Version": "2012-10-17",
                "Statement": {
                    "Effect": "Allow"
                }
            },
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Policy statement must contain actions.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Policy statement must contain actions.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: IAM resource path must either be "*" or start with user/, federated-user/, role/, group/, instance-profile/, mfa/, server-certificate/, policy/, sms-mfa/, saml-provider/, oidc-provider/, report/, access-report/.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: The policy failed legacy parsing'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Resource vendor must be fully qualified and cannot contain regexes.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: IAM resource arn:aws:iam:us-east-1::example_bucket cannot contain region information.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Resource arn:aws:s3:us-east-1::example_bucket can not contain region information.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Statement IDs (SID) in a single policy must be unique.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
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
            "error_message": 'An error occurred (MalformedPolicyDocument) when calling the CreatePolicy operation: Syntax errors in policy.'
        }
    ]  # TODO add more tests

    for test_case in invalid_documents_test_cases:
        with assert_raises(ClientError) as ex:
            conn.create_policy(
                PolicyName="TestCreatePolicy",
                PolicyDocument=json.dumps(test_case["document"]))
        ex.exception.response['Error']['Code'].should.equal('MalformedPolicyDocument')
        ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(400)
        ex.exception.response['Error']['Message'].should.equal(test_case["error_message"])