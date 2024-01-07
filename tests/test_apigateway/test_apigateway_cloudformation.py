import json

import boto3

from moto import mock_aws

template = """{
  "AWSTemplateFormatVersion": "2010-09-09",
  "Description": "The AWS CloudFormation template for this Serverless application",
  "Resources": {
    "ServerlessDeploymentBucket": {
      "Type": "AWS::S3::Bucket"
    },
    "HelloLogGroup": {
      "Type": "AWS::Logs::LogGroup",
      "Properties": {
        "LogGroupName": "/aws/lambda/timeseries-service-dev-hello"
      }
    },
    "IamRoleLambdaExecution": {
      "Type": "AWS::IAM::Role",
      "Properties": {
        "AssumeRolePolicyDocument": {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Principal": {
                "Service": [
                  "lambda.amazonaws.com"
                ]
              },
              "Action": [
                "sts:AssumeRole"
              ]
            }
          ]
        },
        "Policies": [
          {
            "PolicyName": {
              "Fn::Join": [
                "-",
                [
                  "dev",
                  "timeseries-service",
                  "lambda"
                ]
              ]
            },
            "PolicyDocument": {
              "Version": "2012-10-17",
              "Statement": [
                {
                  "Effect": "Allow",
                  "Action": [
                    "logs:CreateLogStream"
                  ],
                  "Resource": [
                    {
                      "Fn::Sub": "arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/timeseries-service-dev-hello:*"
                    }
                  ]
                },
                {
                  "Effect": "Allow",
                  "Action": [
                    "logs:PutLogEvents"
                  ],
                  "Resource": [
                    {
                      "Fn::Sub": "arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/timeseries-service-dev-hello:*:*"
                    }
                  ]
                }
              ]
            }
          }
        ],
        "Path": "/",
        "RoleName": {
          "Fn::Join": [
            "-",
            [
              "timeseries-service",
              "dev",
              "us-east-1",
              "lambdaRole"
            ]
          ]
        }
      }
    },
    "HelloLambdaFunction": {
      "Type": "AWS::Lambda::Function",
      "Properties": {
        "Code": {
          "S3Bucket": {
            "Ref": "ServerlessDeploymentBucket"
          },
          "S3Key": "serverless/timeseries-service/dev/1542744572309-2018-11-20T20:09:32.309Z/timeseries-service.zip"
        },
        "FunctionName": "timeseries-service-dev-hello",
        "Handler": "handler.hello",
        "MemorySize": 1024,
        "Role": {
          "Fn::GetAtt": [
            "IamRoleLambdaExecution",
            "Arn"
          ]
        },
        "Runtime": "python3.11",
        "Timeout": 6
      },
      "DependsOn": [
        "HelloLogGroup",
        "IamRoleLambdaExecution"
      ]
    },
    "HelloLambdaVersionU88Ag36tX5K6Yuze3R8jedH2g7q2TTGuafWQxEnUmo": {
      "Type": "AWS::Lambda::Version",
      "DeletionPolicy": "Retain",
      "Properties": {
        "FunctionName": {
          "Ref": "HelloLambdaFunction"
        },
        "CodeSha256": "+pq+8RveA979z1DNF8UKnFGZfgE07blNyJGust5VJnU="
      }
    },
    "ApiGatewayRestApi": {
      "Type": "AWS::ApiGateway::RestApi",
      "Properties": {
        "Name": "dev-timeseries-service",
        "EndpointConfiguration": {
          "Types": [
            "EDGE"
          ]
        }
      }
    },
    "ApiGatewayResourceHello": {
      "Type": "AWS::ApiGateway::Resource",
      "Properties": {
        "ParentId": {
          "Fn::GetAtt": [
            "ApiGatewayRestApi",
            "RootResourceId"
          ]
        },
        "PathPart": "hello",
        "RestApiId": {
          "Ref": "ApiGatewayRestApi"
        }
      }
    },
    "ApiGatewayMethodHelloGet": {
      "Type": "AWS::ApiGateway::Method",
      "Properties": {
        "HttpMethod": "GET",
        "RequestParameters": {},
        "ResourceId": {
          "Ref": "ApiGatewayResourceHello"
        },
        "RestApiId": {
          "Ref": "ApiGatewayRestApi"
        },
        "ApiKeyRequired": false,
        "AuthorizationType": "NONE",
        "Integration": {
          "IntegrationHttpMethod": "POST",
          "Type": "AWS_PROXY",
          "Uri": {
            "Fn::Join": [
              "",
              [
                "arn:",
                {
                  "Ref": "AWS::Partition"
                },
                ":apigateway:",
                {
                  "Ref": "AWS::Region"
                },
                ":lambda:path/2015-03-31/functions/",
                {
                  "Fn::GetAtt": [
                    "HelloLambdaFunction",
                    "Arn"
                  ]
                },
                "/invocations"
              ]
            ]
          }
        },
        "MethodResponses": []
      }
    },
    "ApiGatewayDeployment1542744572805": {
      "Type": "AWS::ApiGateway::Deployment",
      "Properties": {
        "RestApiId": {
          "Ref": "ApiGatewayRestApi"
        },
        "StageName": "dev"
      },
      "DependsOn": [
        "ApiGatewayMethodHelloGet"
      ]
    },
    "HelloLambdaPermissionApiGateway": {
      "Type": "AWS::Lambda::Permission",
      "Properties": {
        "FunctionName": {
          "Fn::GetAtt": [
            "HelloLambdaFunction",
            "Arn"
          ]
        },
        "Action": "lambda:InvokeFunction",
        "Principal": {
          "Fn::Join": [
            "",
            [
              "apigateway.",
              {
                "Ref": "AWS::URLSuffix"
              }
            ]
          ]
        },
        "SourceArn": {
          "Fn::Join": [
            "",
            [
              "arn:",
              {
                "Ref": "AWS::Partition"
              },
              ":execute-api:",
              {
                "Ref": "AWS::Region"
              },
              ":",
              {
                "Ref": "AWS::AccountId"
              },
              ":",
              {
                "Ref": "ApiGatewayRestApi"
              },
              "/*/*"
            ]
          ]
        }
      }
    }
  },
  "Outputs": {
    "ServerlessDeploymentBucketName": {
      "Value": {
        "Ref": "ServerlessDeploymentBucket"
      }
    },
    "HelloLambdaFunctionQualifiedArn": {
      "Description": "Current Lambda function version",
      "Value": {
        "Ref": "HelloLambdaVersionU88Ag36tX5K6Yuze3R8jedH2g7q2TTGuafWQxEnUmo"
      }
    },
    "ServiceEndpoint": {
      "Description": "URL of the service endpoint",
      "Value": {
        "Fn::Join": [
          "",
          [
            "https://",
            {
              "Ref": "ApiGatewayRestApi"
            },
            ".execute-api.us-east-1.",
            {
              "Ref": "AWS::URLSuffix"
            },
            "/dev"
          ]
        ]
      }
    }
  }
}"""

template_with_missing_sub = """{
  "AWSTemplateFormatVersion": "2010-09-09",
  "Description": "AWS CloudFormation template",
  "Resources": {
    "UnknownResource": {"Type": "AWS::Cloud9::EnvironmentEC2", "Properties": {}},
    "ApiGatewayRestApi": {
      "Type": "AWS::ApiGateway::RestApi",
      "Properties": {
        "Name": "test-api",
        "Description": {"Fn::Sub": "${UnknownResource}"},
        "EndpointConfiguration": {
          "Types": [
            "EDGE"
          ]
        }
      }
    }
  },
  "Outputs": {
  }
}"""


@mock_aws
def test_simple_apigateway_with_lambda_proxy():
    region = "us-east-1"
    apigw = boto3.client("apigateway", region_name=region)
    cf = boto3.client("cloudformation", region_name=region)
    awslambda = boto3.client("lambda", region_name=region)
    cf.create_stack(StackName="teststack", TemplateBody=template)
    #
    cf.describe_stacks(StackName="teststack")["Stacks"]
    resources = cf.describe_stack_resources(StackName="teststack")["StackResources"]
    api_id = [
        r["PhysicalResourceId"]
        for r in resources
        if r["ResourceType"] == "AWS::ApiGateway::RestApi"
    ][0]
    fn_name = [
        r["PhysicalResourceId"]
        for r in resources
        if r["LogicalResourceId"] == "HelloLambdaFunction"
    ][0]
    #
    # Verify Rest API was created
    api = apigw.get_rest_apis()["items"][0]
    assert api["id"] == api_id
    assert api["name"] == "dev-timeseries-service"
    #
    # Verify Gateway Resource was created
    paths = apigw.get_resources(restApiId=api_id)["items"]
    root_path = [p for p in paths if p["path"] == "/"][0]
    hello_path = [p for p in paths if p["path"] == "/hello"][0]
    assert hello_path["parentId"] == root_path["id"]
    #
    # Verify Gateway Method was created
    m = apigw.get_method(
        restApiId=api_id, resourceId=hello_path["id"], httpMethod="GET"
    )
    assert m["httpMethod"] == "GET"
    #
    # Verify a Gateway Deployment was created
    d = apigw.get_deployments(restApiId=api_id)["items"]
    assert len(d) == 1
    #
    # Verify Lambda function was created
    awslambda.get_function(FunctionName=fn_name)  # Will throw 404 if it doesn't exist
    #
    # Verify Lambda Permission was created
    policy = json.loads(awslambda.get_policy(FunctionName=fn_name)["Policy"])
    statement = policy["Statement"][0]
    assert (
        statement["FunctionName"]
        == f"arn:aws:lambda:us-east-1:123456789012:function:{fn_name}"
    )
    assert (
        statement["Condition"]["ArnLike"]["AWS:SourceArn"]
        == f"arn:aws:execute-api:us-east-1:123456789012:{api_id}/*/*"
    )


@mock_aws
def test_apigateway_with_unknown_description():
    region = "us-east-1"
    apigw = boto3.client("apigateway", region_name=region)
    cf = boto3.client("cloudformation", region_name=region)
    cf.create_stack(StackName="teststack", TemplateBody=template_with_missing_sub)

    api = apigw.get_rest_apis()["items"][0]
    assert api["description"] == "${UnknownResource}"
