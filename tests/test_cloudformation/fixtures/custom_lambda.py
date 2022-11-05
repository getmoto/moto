# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/walkthrough-custom-resources-lambda-lookup-amiids.html


def get_template(lambda_code):
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Sample template using Custom Resource",
        "Resources": {
            "CustomInfo": {
                "Type": "Custom::Info",
                "Properties": {
                    "ServiceToken": {"Fn::GetAtt": ["InfoFunction", "Arn"]},
                    "Region": {"Ref": "AWS::Region"},
                    "MyProperty": "stuff",
                },
            },
            "InfoFunction": {
                "Type": "AWS::Lambda::Function",
                "Properties": {
                    "Code": {
                        "ZipFile": {"Fn::Join": ["\n", lambda_code.splitlines()]},
                    },
                    "Handler": "index.lambda_handler",
                    "Role": {"Fn::GetAtt": ["LambdaExecutionRole", "Arn"]},
                    "Runtime": "python3.8",
                    "Timeout": "30",
                },
            },
            "LambdaExecutionRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": ["lambda.amazonaws.com"]},
                                "Action": ["sts:AssumeRole"],
                            }
                        ],
                    },
                    "Path": "/",
                    "Policies": [
                        {
                            "PolicyName": "root",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": [
                                            "logs:CreateLogGroup",
                                            "logs:CreateLogStream",
                                            "logs:PutLogEvents",
                                        ],
                                        "Resource": "arn:aws:logs:*:*:*",
                                    }
                                ],
                            },
                        }
                    ],
                },
            },
        },
        "Outputs": {
            "infokey": {
                "Description": "A very important value",
                "Value": {"Fn::GetAtt": ["CustomInfo", "info_value"]},
            }
        },
    }
