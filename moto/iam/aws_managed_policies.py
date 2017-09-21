# Imported via `make aws_managed_policies`
aws_managed_policies_data = """
{
    "AWSAccountActivityAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSAccountActivityAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:18+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "aws-portal:ViewBilling"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJQRYCWMFX5J3E333K",
        "PolicyName": "AWSAccountActivityAccess",
        "UpdateDate": "2015-02-06T18:41:18+00:00",
        "VersionId": "v1"
    },
    "AWSAccountUsageReportAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSAccountUsageReportAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:19+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "aws-portal:ViewUsage"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJLIB4VSBVO47ZSBB6",
        "PolicyName": "AWSAccountUsageReportAccess",
        "UpdateDate": "2015-02-06T18:41:19+00:00",
        "VersionId": "v1"
    },
    "AWSAgentlessDiscoveryService": {
        "Arn": "arn:aws:iam::aws:policy/AWSAgentlessDiscoveryService",
        "AttachmentCount": 0,
        "CreateDate": "2016-08-02T01:35:11+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "awsconnector:RegisterConnector",
                        "awsconnector:GetConnectorHealth"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "iam:GetUser",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "s3:GetObject",
                        "s3:ListBucket"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::connector-platform-upgrade-info/*",
                        "arn:aws:s3:::connector-platform-upgrade-info",
                        "arn:aws:s3:::connector-platform-upgrade-bundles/*",
                        "arn:aws:s3:::connector-platform-upgrade-bundles",
                        "arn:aws:s3:::connector-platform-release-notes/*",
                        "arn:aws:s3:::connector-platform-release-notes",
                        "arn:aws:s3:::prod.agentless.discovery.connector.upgrade/*",
                        "arn:aws:s3:::prod.agentless.discovery.connector.upgrade"
                    ]
                },
                {
                    "Action": [
                        "s3:PutObject",
                        "s3:PutObjectAcl"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::import-to-ec2-connector-debug-logs/*"
                    ]
                },
                {
                    "Action": [
                        "SNS:Publish"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:sns:*:*:metrics-sns-topic-for-*"
                },
                {
                    "Action": [
                        "Discovery:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "Discovery"
                },
                {
                    "Action": [
                        "arsenal:RegisterOnPremisesAgent"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "arsenal"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIA3DIL7BYQ35ISM4K",
        "PolicyName": "AWSAgentlessDiscoveryService",
        "UpdateDate": "2016-08-02T01:35:11+00:00",
        "VersionId": "v1"
    },
    "AWSApplicationDiscoveryAgentAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSApplicationDiscoveryAgentAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-05-11T21:38:47+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "arsenal:RegisterOnPremisesAgent"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAICZIOVAGC6JPF3WHC",
        "PolicyName": "AWSApplicationDiscoveryAgentAccess",
        "UpdateDate": "2016-05-11T21:38:47+00:00",
        "VersionId": "v1"
    },
    "AWSApplicationDiscoveryServiceFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSApplicationDiscoveryServiceFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-05-11T21:30:50+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "discovery:*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJBNJEA6ZXM2SBOPDU",
        "PolicyName": "AWSApplicationDiscoveryServiceFullAccess",
        "UpdateDate": "2016-05-11T21:30:50+00:00",
        "VersionId": "v1"
    },
    "AWSBatchFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSBatchFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-13T00:38:59+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "batch:*",
                        "cloudwatch:GetMetricStatistics",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeKeyPairs",
                        "ecs:DescribeClusters",
                        "ecs:Describe*",
                        "ecs:List*",
                        "logs:Describe*",
                        "logs:Get*",
                        "logs:TestMetricFilter",
                        "logs:FilterLogEvents",
                        "iam:ListInstanceProfiles",
                        "iam:ListRoles"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "iam:PassRole"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/AWSBatchServiceRole",
                        "arn:aws:iam::*:role/ecsInstanceRole",
                        "arn:aws:iam::*:role/iaws-ec2-spot-fleet-role",
                        "arn:aws:iam::*:role/aws-ec2-spot-fleet-role",
                        "arn:aws:iam::*:role/AWSBatchJobRole*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ7K2KIWB3HZVK3CUO",
        "PolicyName": "AWSBatchFullAccess",
        "UpdateDate": "2016-12-13T00:38:59+00:00",
        "VersionId": "v2"
    },
    "AWSBatchServiceRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-05-11T20:44:52+00:00",
        "DefaultVersionId": "v4",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeInstances",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeImages",
                        "ec2:DescribeImageAttribute",
                        "ec2:DescribeSpotFleetInstances",
                        "ec2:DescribeSpotFleetRequests",
                        "ec2:DescribeSpotPriceHistory",
                        "ec2:RequestSpotFleet",
                        "ec2:CancelSpotFleetRequests",
                        "ec2:ModifySpotFleetRequest",
                        "ec2:TerminateInstances",
                        "autoscaling:DescribeAccountLimits",
                        "autoscaling:DescribeAutoScalingGroups",
                        "autoscaling:DescribeLaunchConfigurations",
                        "autoscaling:DescribeAutoScalingInstances",
                        "autoscaling:CreateLaunchConfiguration",
                        "autoscaling:CreateAutoScalingGroup",
                        "autoscaling:UpdateAutoScalingGroup",
                        "autoscaling:SetDesiredCapacity",
                        "autoscaling:DeleteLaunchConfiguration",
                        "autoscaling:DeleteAutoScalingGroup",
                        "autoscaling:CreateOrUpdateTags",
                        "autoscaling:SuspendProcesses",
                        "autoscaling:PutNotificationConfiguration",
                        "autoscaling:TerminateInstanceInAutoScalingGroup",
                        "ecs:DescribeClusters",
                        "ecs:DescribeContainerInstances",
                        "ecs:DescribeTaskDefinition",
                        "ecs:DescribeTasks",
                        "ecs:ListClusters",
                        "ecs:ListContainerInstances",
                        "ecs:ListTaskDefinitionFamilies",
                        "ecs:ListTaskDefinitions",
                        "ecs:ListTasks",
                        "ecs:CreateCluster",
                        "ecs:DeleteCluster",
                        "ecs:RegisterTaskDefinition",
                        "ecs:DeregisterTaskDefinition",
                        "ecs:RunTask",
                        "ecs:StartTask",
                        "ecs:StopTask",
                        "ecs:UpdateContainerAgent",
                        "ecs:DeregisterContainerInstance",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogGroups",
                        "iam:GetInstanceProfile",
                        "iam:PassRole"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIUETIXPCKASQJURFE",
        "PolicyName": "AWSBatchServiceRole",
        "UpdateDate": "2017-05-11T20:44:52+00:00",
        "VersionId": "v4"
    },
    "AWSCertificateManagerFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCertificateManagerFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-01-21T17:02:36+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "acm:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJYCHABBP6VQIVBCBQ",
        "PolicyName": "AWSCertificateManagerFullAccess",
        "UpdateDate": "2016-01-21T17:02:36+00:00",
        "VersionId": "v1"
    },
    "AWSCertificateManagerReadOnly": {
        "Arn": "arn:aws:iam::aws:policy/AWSCertificateManagerReadOnly",
        "AttachmentCount": 0,
        "CreateDate": "2016-04-21T15:08:16+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": {
                "Action": [
                    "acm:DescribeCertificate",
                    "acm:ListCertificates",
                    "acm:GetCertificate",
                    "acm:ListTagsForCertificate"
                ],
                "Effect": "Allow",
                "Resource": "*"
            },
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI4GSWX6S4MESJ3EWC",
        "PolicyName": "AWSCertificateManagerReadOnly",
        "UpdateDate": "2016-04-21T15:08:16+00:00",
        "VersionId": "v2"
    },
    "AWSCloudFormationReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCloudFormationReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:39:49+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudformation:DescribeStacks",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:DescribeStackResource",
                        "cloudformation:DescribeStackResources",
                        "cloudformation:GetTemplate",
                        "cloudformation:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJWVBEE4I2POWLODLW",
        "PolicyName": "AWSCloudFormationReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:39:49+00:00",
        "VersionId": "v1"
    },
    "AWSCloudHSMFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCloudHSMFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:39:51+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "cloudhsm:*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIMBQYQZM7F63DA2UU",
        "PolicyName": "AWSCloudHSMFullAccess",
        "UpdateDate": "2015-02-06T18:39:51+00:00",
        "VersionId": "v1"
    },
    "AWSCloudHSMReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCloudHSMReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:39:52+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudhsm:Get*",
                        "cloudhsm:List*",
                        "cloudhsm:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAISVCBSY7YDBOT67KE",
        "PolicyName": "AWSCloudHSMReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:39:52+00:00",
        "VersionId": "v1"
    },
    "AWSCloudHSMRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSCloudHSMRole",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:23+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:CreateNetworkInterface",
                        "ec2:CreateTags",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DescribeNetworkInterfaceAttribute",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:DetachNetworkInterface"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAI7QIUU4GC66SF26WE",
        "PolicyName": "AWSCloudHSMRole",
        "UpdateDate": "2015-02-06T18:41:23+00:00",
        "VersionId": "v1"
    },
    "AWSCloudTrailFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCloudTrailFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-02-16T18:31:28+00:00",
        "DefaultVersionId": "v4",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "sns:AddPermission",
                        "sns:CreateTopic",
                        "sns:DeleteTopic",
                        "sns:ListTopics",
                        "sns:SetTopicAttributes",
                        "sns:GetTopicAttributes"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "s3:CreateBucket",
                        "s3:DeleteBucket",
                        "s3:ListAllMyBuckets",
                        "s3:PutBucketPolicy",
                        "s3:ListBucket",
                        "s3:GetObject",
                        "s3:GetBucketLocation",
                        "s3:GetBucketPolicy"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "cloudtrail:*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "logs:CreateLogGroup"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "iam:PassRole",
                        "iam:ListRoles",
                        "iam:GetRolePolicy",
                        "iam:GetUser"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "kms:ListKeys",
                        "kms:ListAliases"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIQNUJTQYDRJPC3BNK",
        "PolicyName": "AWSCloudTrailFullAccess",
        "UpdateDate": "2016-02-16T18:31:28+00:00",
        "VersionId": "v4"
    },
    "AWSCloudTrailReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCloudTrailReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-14T20:41:52+00:00",
        "DefaultVersionId": "v6",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:GetObject",
                        "s3:GetBucketLocation"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "cloudtrail:GetTrailStatus",
                        "cloudtrail:DescribeTrails",
                        "cloudtrail:LookupEvents",
                        "cloudtrail:ListTags",
                        "cloudtrail:ListPublicKeys",
                        "cloudtrail:GetEventSelectors",
                        "s3:ListAllMyBuckets",
                        "kms:ListAliases"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJDU7KJADWBSEQ3E7S",
        "PolicyName": "AWSCloudTrailReadOnlyAccess",
        "UpdateDate": "2016-12-14T20:41:52+00:00",
        "VersionId": "v6"
    },
    "AWSCodeBuildAdminAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodeBuildAdminAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-01T19:04:44+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codebuild:*",
                        "codecommit:GetBranch",
                        "codecommit:GetCommit",
                        "codecommit:GetRepository",
                        "codecommit:ListBranches",
                        "codecommit:ListRepositories",
                        "ecr:DescribeRepositories",
                        "ecr:ListImages",
                        "s3:GetBucketLocation",
                        "s3:ListAllMyBuckets"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "logs:GetLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:logs:*:*:log-group:/aws/codebuild/*:log-stream:*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJQJGIOIE3CD2TQXDS",
        "PolicyName": "AWSCodeBuildAdminAccess",
        "UpdateDate": "2016-12-01T19:04:44+00:00",
        "VersionId": "v1"
    },
    "AWSCodeBuildDeveloperAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodeBuildDeveloperAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-01T19:02:32+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codebuild:StartBuild",
                        "codebuild:StopBuild",
                        "codebuild:BatchGet*",
                        "codebuild:Get*",
                        "codebuild:List*",
                        "codecommit:GetBranch",
                        "codecommit:GetCommit",
                        "codecommit:GetRepository",
                        "codecommit:ListBranches",
                        "s3:GetBucketLocation",
                        "s3:ListAllMyBuckets"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "logs:GetLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:logs:*:*:log-group:/aws/codebuild/*:log-stream:*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIMKTMR34XSBQW45HS",
        "PolicyName": "AWSCodeBuildDeveloperAccess",
        "UpdateDate": "2016-12-01T19:02:32+00:00",
        "VersionId": "v1"
    },
    "AWSCodeBuildReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodeBuildReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-01T19:03:41+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codebuild:BatchGet*",
                        "codebuild:Get*",
                        "codebuild:List*",
                        "codecommit:GetBranch",
                        "codecommit:GetCommit",
                        "codecommit:GetRepository"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "logs:GetLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:logs:*:*:log-group:/aws/codebuild/*:log-stream:*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJIZZWN6557F5HVP2K",
        "PolicyName": "AWSCodeBuildReadOnlyAccess",
        "UpdateDate": "2016-12-01T19:03:41+00:00",
        "VersionId": "v1"
    },
    "AWSCodeCommitFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodeCommitFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-07-09T17:02:19+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codecommit:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI4VCZ3XPIZLQ5NZV2",
        "PolicyName": "AWSCodeCommitFullAccess",
        "UpdateDate": "2015-07-09T17:02:19+00:00",
        "VersionId": "v1"
    },
    "AWSCodeCommitPowerUser": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodeCommitPowerUser",
        "AttachmentCount": 0,
        "CreateDate": "2017-05-22T21:12:48+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codecommit:BatchGetRepositories",
                        "codecommit:CreateBranch",
                        "codecommit:CreateRepository",
                        "codecommit:DeleteBranch",
                        "codecommit:Get*",
                        "codecommit:GitPull",
                        "codecommit:GitPush",
                        "codecommit:List*",
                        "codecommit:Put*",
                        "codecommit:Test*",
                        "codecommit:Update*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI4UIINUVGB5SEC57G",
        "PolicyName": "AWSCodeCommitPowerUser",
        "UpdateDate": "2017-05-22T21:12:48+00:00",
        "VersionId": "v3"
    },
    "AWSCodeCommitReadOnly": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodeCommitReadOnly",
        "AttachmentCount": 0,
        "CreateDate": "2015-07-09T17:05:06+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codecommit:BatchGetRepositories",
                        "codecommit:Get*",
                        "codecommit:GitPull",
                        "codecommit:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJACNSXR7Z2VLJW3D6",
        "PolicyName": "AWSCodeCommitReadOnly",
        "UpdateDate": "2015-07-09T17:05:06+00:00",
        "VersionId": "v1"
    },
    "AWSCodeDeployDeployerAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodeDeployDeployerAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-05-19T18:18:43+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codedeploy:Batch*",
                        "codedeploy:CreateDeployment",
                        "codedeploy:Get*",
                        "codedeploy:List*",
                        "codedeploy:RegisterApplicationRevision"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJUWEPOMGLMVXJAPUI",
        "PolicyName": "AWSCodeDeployDeployerAccess",
        "UpdateDate": "2015-05-19T18:18:43+00:00",
        "VersionId": "v1"
    },
    "AWSCodeDeployFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodeDeployFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-05-19T18:13:23+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "codedeploy:*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIONKN3TJZUKXCHXWC",
        "PolicyName": "AWSCodeDeployFullAccess",
        "UpdateDate": "2015-05-19T18:13:23+00:00",
        "VersionId": "v1"
    },
    "AWSCodeDeployReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodeDeployReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-05-19T18:21:32+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codedeploy:Batch*",
                        "codedeploy:Get*",
                        "codedeploy:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAILZHHKCKB4NE7XOIQ",
        "PolicyName": "AWSCodeDeployReadOnlyAccess",
        "UpdateDate": "2015-05-19T18:21:32+00:00",
        "VersionId": "v1"
    },
    "AWSCodeDeployRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-11T19:09:51+00:00",
        "DefaultVersionId": "v6",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "autoscaling:CompleteLifecycleAction",
                        "autoscaling:DeleteLifecycleHook",
                        "autoscaling:DescribeAutoScalingGroups",
                        "autoscaling:DescribeLifecycleHooks",
                        "autoscaling:PutLifecycleHook",
                        "autoscaling:RecordLifecycleActionHeartbeat",
                        "autoscaling:CreateAutoScalingGroup",
                        "autoscaling:UpdateAutoScalingGroup",
                        "autoscaling:EnableMetricsCollection",
                        "autoscaling:DescribeAutoScalingGroups",
                        "autoscaling:DescribePolicies",
                        "autoscaling:DescribeScheduledActions",
                        "autoscaling:DescribeNotificationConfigurations",
                        "autoscaling:DescribeLifecycleHooks",
                        "autoscaling:SuspendProcesses",
                        "autoscaling:ResumeProcesses",
                        "autoscaling:AttachLoadBalancers",
                        "autoscaling:PutScalingPolicy",
                        "autoscaling:PutScheduledUpdateGroupAction",
                        "autoscaling:PutNotificationConfiguration",
                        "autoscaling:PutLifecycleHook",
                        "autoscaling:DescribeScalingActivities",
                        "autoscaling:DeleteAutoScalingGroup",
                        "ec2:DescribeInstances",
                        "ec2:DescribeInstanceStatus",
                        "ec2:TerminateInstances",
                        "tag:GetTags",
                        "tag:GetResources",
                        "sns:Publish",
                        "cloudwatch:DescribeAlarms",
                        "cloudwatch:PutMetricAlarm",
                        "elasticloadbalancing:DescribeLoadBalancers",
                        "elasticloadbalancing:DescribeInstanceHealth",
                        "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
                        "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
                        "elasticloadbalancing:DescribeTargetGroups",
                        "elasticloadbalancing:DescribeTargetHealth",
                        "elasticloadbalancing:RegisterTargets",
                        "elasticloadbalancing:DeregisterTargets"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJ2NKMKD73QS5NBFLA",
        "PolicyName": "AWSCodeDeployRole",
        "UpdateDate": "2017-09-11T19:09:51+00:00",
        "VersionId": "v6"
    },
    "AWSCodePipelineApproverAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodePipelineApproverAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-02T17:24:58+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codepipeline:GetPipeline",
                        "codepipeline:GetPipelineState",
                        "codepipeline:GetPipelineExecution",
                        "codepipeline:ListPipelineExecutions",
                        "codepipeline:ListPipelines",
                        "codepipeline:PutApprovalResult"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAICXNWK42SQ6LMDXM2",
        "PolicyName": "AWSCodePipelineApproverAccess",
        "UpdateDate": "2017-08-02T17:24:58+00:00",
        "VersionId": "v3"
    },
    "AWSCodePipelineCustomActionAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodePipelineCustomActionAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-07-09T17:02:54+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codepipeline:AcknowledgeJob",
                        "codepipeline:GetJobDetails",
                        "codepipeline:PollForJobs",
                        "codepipeline:PutJobFailureResult",
                        "codepipeline:PutJobSuccessResult"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJFW5Z32BTVF76VCYC",
        "PolicyName": "AWSCodePipelineCustomActionAccess",
        "UpdateDate": "2015-07-09T17:02:54+00:00",
        "VersionId": "v1"
    },
    "AWSCodePipelineFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodePipelineFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-01T19:59:46+00:00",
        "DefaultVersionId": "v5",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codepipeline:*",
                        "iam:ListRoles",
                        "iam:PassRole",
                        "s3:CreateBucket",
                        "s3:GetBucketPolicy",
                        "s3:GetObject",
                        "s3:ListAllMyBuckets",
                        "s3:ListBucket",
                        "s3:PutBucketPolicy",
                        "codecommit:ListBranches",
                        "codecommit:ListRepositories",
                        "codedeploy:GetApplication",
                        "codedeploy:GetDeploymentGroup",
                        "codedeploy:ListApplications",
                        "codedeploy:ListDeploymentGroups",
                        "elasticbeanstalk:DescribeApplications",
                        "elasticbeanstalk:DescribeEnvironments",
                        "lambda:GetFunctionConfiguration",
                        "lambda:ListFunctions",
                        "opsworks:DescribeApps",
                        "opsworks:DescribeLayers",
                        "opsworks:DescribeStacks",
                        "cloudformation:DescribeStacks",
                        "cloudformation:ListChangeSets"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJP5LH77KSAT2KHQGG",
        "PolicyName": "AWSCodePipelineFullAccess",
        "UpdateDate": "2016-11-01T19:59:46+00:00",
        "VersionId": "v5"
    },
    "AWSCodePipelineReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodePipelineReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-02T17:25:18+00:00",
        "DefaultVersionId": "v6",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codepipeline:GetPipeline",
                        "codepipeline:GetPipelineState",
                        "codepipeline:GetPipelineExecution",
                        "codepipeline:ListPipelineExecutions",
                        "codepipeline:ListActionTypes",
                        "codepipeline:ListPipelines",
                        "iam:ListRoles",
                        "s3:GetBucketPolicy",
                        "s3:GetObject",
                        "s3:ListAllMyBuckets",
                        "s3:ListBucket",
                        "codecommit:ListBranches",
                        "codecommit:ListRepositories",
                        "codedeploy:GetApplication",
                        "codedeploy:GetDeploymentGroup",
                        "codedeploy:ListApplications",
                        "codedeploy:ListDeploymentGroups",
                        "elasticbeanstalk:DescribeApplications",
                        "elasticbeanstalk:DescribeEnvironments",
                        "lambda:GetFunctionConfiguration",
                        "lambda:ListFunctions",
                        "opsworks:DescribeApps",
                        "opsworks:DescribeLayers",
                        "opsworks:DescribeStacks"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAILFKZXIBOTNC5TO2Q",
        "PolicyName": "AWSCodePipelineReadOnlyAccess",
        "UpdateDate": "2017-08-02T17:25:18+00:00",
        "VersionId": "v6"
    },
    "AWSCodeStarFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSCodeStarFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-04-19T16:23:19+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "codestar:*",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeSubnets"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "CodeStarEC2"
                },
                {
                    "Action": [
                        "cloudformation:DescribeStack*",
                        "cloudformation:GetTemplateSummary"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:cloudformation:*:*:stack/awscodestar-*"
                    ],
                    "Sid": "CodeStarCF"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIXI233TFUGLZOJBEC",
        "PolicyName": "AWSCodeStarFullAccess",
        "UpdateDate": "2017-04-19T16:23:19+00:00",
        "VersionId": "v1"
    },
    "AWSCodeStarServiceRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSCodeStarServiceRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-07-13T19:53:22+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudformation:*Stack*",
                        "cloudformation:GetTemplate"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:cloudformation:*:*:stack/awscodestar-*",
                        "arn:aws:cloudformation:*:*:stack/awseb-*"
                    ],
                    "Sid": "ProjectStack"
                },
                {
                    "Action": [
                        "cloudformation:GetTemplateSummary",
                        "cloudformation:DescribeChangeSet"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "ProjectStackTemplate"
                },
                {
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::awscodestar-*/*"
                    ],
                    "Sid": "ProjectQuickstarts"
                },
                {
                    "Action": [
                        "s3:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::aws-codestar-*",
                        "arn:aws:s3:::aws-codestar-*/*",
                        "arn:aws:s3:::elasticbeanstalk-*",
                        "arn:aws:s3:::elasticbeanstalk-*/*"
                    ],
                    "Sid": "ProjectS3Buckets"
                },
                {
                    "Action": [
                        "codestar:*Project",
                        "codestar:*Resource*",
                        "codestar:List*",
                        "codestar:Describe*",
                        "codestar:Get*",
                        "codestar:AssociateTeamMember",
                        "codecommit:*",
                        "codepipeline:*",
                        "codedeploy:*",
                        "codebuild:*",
                        "ec2:RunInstances",
                        "autoscaling:*",
                        "cloudwatch:Put*",
                        "ec2:*",
                        "elasticbeanstalk:*",
                        "elasticloadbalancing:*",
                        "iam:ListRoles",
                        "logs:*",
                        "sns:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "ProjectServices"
                },
                {
                    "Action": [
                        "iam:AttachRolePolicy",
                        "iam:CreateRole",
                        "iam:DeleteRole",
                        "iam:DeleteRolePolicy",
                        "iam:DetachRolePolicy",
                        "iam:GetRole",
                        "iam:PassRole",
                        "iam:PutRolePolicy",
                        "iam:SetDefaultPolicyVersion",
                        "iam:CreatePolicy",
                        "iam:DeletePolicy",
                        "iam:AddRoleToInstanceProfile",
                        "iam:CreateInstanceProfile",
                        "iam:DeleteInstanceProfile",
                        "iam:RemoveRoleFromInstanceProfile"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/CodeStarWorker*",
                        "arn:aws:iam::*:policy/CodeStarWorker*",
                        "arn:aws:iam::*:instance-profile/awscodestar-*"
                    ],
                    "Sid": "ProjectWorkerRoles"
                },
                {
                    "Action": [
                        "iam:AttachUserPolicy",
                        "iam:DetachUserPolicy"
                    ],
                    "Condition": {
                        "ArnEquals": {
                            "iam:PolicyArn": [
                                "arn:aws:iam::*:policy/CodeStar_*"
                            ]
                        }
                    },
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "ProjectTeamMembers"
                },
                {
                    "Action": [
                        "iam:CreatePolicy",
                        "iam:DeletePolicy",
                        "iam:CreatePolicyVersion",
                        "iam:DeletePolicyVersion",
                        "iam:ListEntitiesForPolicy",
                        "iam:ListPolicyVersions"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:policy/CodeStar_*"
                    ],
                    "Sid": "ProjectRoles"
                },
                {
                    "Action": [
                        "iam:ListAttachedRolePolicies"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/aws-codestar-service-role",
                        "arn:aws:iam::*:role/service-role/aws-codestar-service-role"
                    ],
                    "Sid": "InspectServiceRole"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIN6D4M2KD3NBOC4M4",
        "PolicyName": "AWSCodeStarServiceRole",
        "UpdateDate": "2017-07-13T19:53:22+00:00",
        "VersionId": "v2"
    },
    "AWSConfigRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSConfigRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-14T19:04:46+00:00",
        "DefaultVersionId": "v10",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudtrail:DescribeTrails",
                        "ec2:Describe*",
                        "config:Put*",
                        "config:Get*",
                        "config:List*",
                        "config:Describe*",
                        "cloudtrail:GetTrailStatus",
                        "s3:GetObject",
                        "iam:GetAccountAuthorizationDetails",
                        "iam:GetAccountPasswordPolicy",
                        "iam:GetAccountSummary",
                        "iam:GetGroup",
                        "iam:GetGroupPolicy",
                        "iam:GetPolicy",
                        "iam:GetPolicyVersion",
                        "iam:GetRole",
                        "iam:GetRolePolicy",
                        "iam:GetUser",
                        "iam:GetUserPolicy",
                        "iam:ListAttachedGroupPolicies",
                        "iam:ListAttachedRolePolicies",
                        "iam:ListAttachedUserPolicies",
                        "iam:ListEntitiesForPolicy",
                        "iam:ListGroupPolicies",
                        "iam:ListGroupsForUser",
                        "iam:ListInstanceProfilesForRole",
                        "iam:ListPolicyVersions",
                        "iam:ListRolePolicies",
                        "iam:ListUserPolicies",
                        "elasticloadbalancing:DescribeLoadBalancers",
                        "elasticloadbalancing:DescribeLoadBalancerAttributes",
                        "elasticloadbalancing:DescribeLoadBalancerPolicies",
                        "elasticloadbalancing:DescribeTags",
                        "acm:DescribeCertificate",
                        "acm:ListCertificates",
                        "acm:ListTagsForCertificate",
                        "rds:DescribeDBInstances",
                        "rds:DescribeDBSecurityGroups",
                        "rds:DescribeDBSnapshotAttributes",
                        "rds:DescribeDBSnapshots",
                        "rds:DescribeDBSubnetGroups",
                        "rds:DescribeEventSubscriptions",
                        "rds:ListTagsForResource",
                        "rds:DescribeDBClusters",
                        "s3:GetAccelerateConfiguration",
                        "s3:GetBucketAcl",
                        "s3:GetBucketCORS",
                        "s3:GetBucketLocation",
                        "s3:GetBucketLogging",
                        "s3:GetBucketNotification",
                        "s3:GetBucketPolicy",
                        "s3:GetBucketRequestPayment",
                        "s3:GetBucketTagging",
                        "s3:GetBucketVersioning",
                        "s3:GetBucketWebsite",
                        "s3:GetLifecycleConfiguration",
                        "s3:GetReplicationConfiguration",
                        "s3:ListAllMyBuckets",
                        "redshift:DescribeClusterParameterGroups",
                        "redshift:DescribeClusterParameters",
                        "redshift:DescribeClusterSecurityGroups",
                        "redshift:DescribeClusterSnapshots",
                        "redshift:DescribeClusterSubnetGroups",
                        "redshift:DescribeClusters",
                        "redshift:DescribeEventSubscriptions",
                        "redshift:DescribeLoggingStatus",
                        "dynamodb:DescribeLimits",
                        "dynamodb:DescribeTable",
                        "dynamodb:ListTables",
                        "dynamodb:ListTagsOfResource",
                        "cloudwatch:DescribeAlarms",
                        "application-autoscaling:DescribeScalableTargets",
                        "application-autoscaling:DescribeScalingPolicies",
                        "autoscaling:DescribeAutoScalingGroups",
                        "autoscaling:DescribeLaunchConfigurations",
                        "autoscaling:DescribeLifecycleHooks",
                        "autoscaling:DescribePolicies",
                        "autoscaling:DescribeScheduledActions",
                        "autoscaling:DescribeTags"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIQRXRDRGJUA33ELIO",
        "PolicyName": "AWSConfigRole",
        "UpdateDate": "2017-08-14T19:04:46+00:00",
        "VersionId": "v10"
    },
    "AWSConfigRulesExecutionRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSConfigRulesExecutionRole",
        "AttachmentCount": 0,
        "CreateDate": "2016-03-25T17:59:36+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::*/AWSLogs/*/Config/*"
                },
                {
                    "Action": [
                        "config:Put*",
                        "config:Get*",
                        "config:List*",
                        "config:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJUB3KIKTA4PU4OYAA",
        "PolicyName": "AWSConfigRulesExecutionRole",
        "UpdateDate": "2016-03-25T17:59:36+00:00",
        "VersionId": "v1"
    },
    "AWSConfigUserAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSConfigUserAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-08-30T19:15:19+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "config:Get*",
                        "config:Describe*",
                        "config:Deliver*",
                        "config:List*",
                        "tag:GetResources",
                        "tag:GetTagKeys",
                        "cloudtrail:DescribeTrails",
                        "cloudtrail:GetTrailStatus",
                        "cloudtrail:LookupEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIWTTSFJ7KKJE3MWGA",
        "PolicyName": "AWSConfigUserAccess",
        "UpdateDate": "2016-08-30T19:15:19+00:00",
        "VersionId": "v3"
    },
    "AWSConnector": {
        "Arn": "arn:aws:iam::aws:policy/AWSConnector",
        "AttachmentCount": 0,
        "CreateDate": "2015-09-28T19:50:38+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": "iam:GetUser",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "s3:ListAllMyBuckets"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "s3:CreateBucket",
                        "s3:DeleteBucket",
                        "s3:DeleteObject",
                        "s3:GetBucketLocation",
                        "s3:GetObject",
                        "s3:ListBucket",
                        "s3:PutObject",
                        "s3:PutObjectAcl",
                        "s3:AbortMultipartUpload",
                        "s3:ListBucketMultipartUploads",
                        "s3:ListMultipartUploadParts"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::import-to-ec2-*"
                },
                {
                    "Action": [
                        "ec2:CancelConversionTask",
                        "ec2:CancelExportTask",
                        "ec2:CreateImage",
                        "ec2:CreateInstanceExportTask",
                        "ec2:CreateTags",
                        "ec2:CreateVolume",
                        "ec2:DeleteTags",
                        "ec2:DeleteVolume",
                        "ec2:DescribeConversionTasks",
                        "ec2:DescribeExportTasks",
                        "ec2:DescribeImages",
                        "ec2:DescribeInstanceAttribute",
                        "ec2:DescribeInstanceStatus",
                        "ec2:DescribeInstances",
                        "ec2:DescribeRegions",
                        "ec2:DescribeTags",
                        "ec2:DetachVolume",
                        "ec2:ImportInstance",
                        "ec2:ImportVolume",
                        "ec2:ModifyInstanceAttribute",
                        "ec2:RunInstances",
                        "ec2:StartInstances",
                        "ec2:StopInstances",
                        "ec2:TerminateInstances",
                        "ec2:ImportImage",
                        "ec2:DescribeImportImageTasks",
                        "ec2:DeregisterImage",
                        "ec2:DescribeSnapshots",
                        "ec2:DeleteSnapshot",
                        "ec2:CancelImportTask",
                        "ec2:ImportSnapshot",
                        "ec2:DescribeImportSnapshotTasks"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "SNS:Publish"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:sns:*:*:metrics-sns-topic-for-*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ6YATONJHICG3DJ3U",
        "PolicyName": "AWSConnector",
        "UpdateDate": "2015-09-28T19:50:38+00:00",
        "VersionId": "v3"
    },
    "AWSDataPipelineRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSDataPipelineRole",
        "AttachmentCount": 0,
        "CreateDate": "2016-02-22T17:17:38+00:00",
        "DefaultVersionId": "v5",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:*",
                        "datapipeline:DescribeObjects",
                        "datapipeline:EvaluateExpression",
                        "dynamodb:BatchGetItem",
                        "dynamodb:DescribeTable",
                        "dynamodb:GetItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:UpdateTable",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CancelSpotInstanceRequests",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateTags",
                        "ec2:DeleteTags",
                        "ec2:Describe*",
                        "ec2:ModifyImageAttribute",
                        "ec2:ModifyInstanceAttribute",
                        "ec2:RequestSpotInstances",
                        "ec2:RunInstances",
                        "ec2:StartInstances",
                        "ec2:StopInstances",
                        "ec2:TerminateInstances",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:DeleteSecurityGroup",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:CreateNetworkInterface",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DetachNetworkInterface",
                        "elasticmapreduce:*",
                        "iam:GetInstanceProfile",
                        "iam:GetRole",
                        "iam:GetRolePolicy",
                        "iam:ListAttachedRolePolicies",
                        "iam:ListRolePolicies",
                        "iam:ListInstanceProfiles",
                        "iam:PassRole",
                        "rds:DescribeDBInstances",
                        "rds:DescribeDBSecurityGroups",
                        "redshift:DescribeClusters",
                        "redshift:DescribeClusterSecurityGroups",
                        "s3:CreateBucket",
                        "s3:DeleteObject",
                        "s3:Get*",
                        "s3:List*",
                        "s3:Put*",
                        "sdb:BatchPutAttributes",
                        "sdb:Select*",
                        "sns:GetTopicAttributes",
                        "sns:ListTopics",
                        "sns:Publish",
                        "sns:Subscribe",
                        "sns:Unsubscribe",
                        "sqs:CreateQueue",
                        "sqs:Delete*",
                        "sqs:GetQueue*",
                        "sqs:PurgeQueue",
                        "sqs:ReceiveMessage"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIKCP6XS3ESGF4GLO2",
        "PolicyName": "AWSDataPipelineRole",
        "UpdateDate": "2016-02-22T17:17:38+00:00",
        "VersionId": "v5"
    },
    "AWSDataPipeline_FullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSDataPipeline_FullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-17T18:48:39+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:List*",
                        "dynamodb:DescribeTable",
                        "rds:DescribeDBInstances",
                        "rds:DescribeDBSecurityGroups",
                        "redshift:DescribeClusters",
                        "redshift:DescribeClusterSecurityGroups",
                        "sns:ListTopics",
                        "sns:Subscribe",
                        "iam:ListRoles",
                        "iam:GetRolePolicy",
                        "iam:GetInstanceProfile",
                        "iam:ListInstanceProfiles",
                        "datapipeline:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": "iam:PassRole",
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/DataPipelineDefaultResourceRole",
                        "arn:aws:iam::*:role/DataPipelineDefaultRole"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIXOFIG7RSBMRPHXJ4",
        "PolicyName": "AWSDataPipeline_FullAccess",
        "UpdateDate": "2017-08-17T18:48:39+00:00",
        "VersionId": "v2"
    },
    "AWSDataPipeline_PowerUser": {
        "Arn": "arn:aws:iam::aws:policy/AWSDataPipeline_PowerUser",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-17T18:49:42+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:List*",
                        "dynamodb:DescribeTable",
                        "rds:DescribeDBInstances",
                        "rds:DescribeDBSecurityGroups",
                        "redshift:DescribeClusters",
                        "redshift:DescribeClusterSecurityGroups",
                        "sns:ListTopics",
                        "iam:ListRoles",
                        "iam:GetRolePolicy",
                        "iam:GetInstanceProfile",
                        "iam:ListInstanceProfiles",
                        "datapipeline:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": "iam:PassRole",
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/DataPipelineDefaultResourceRole",
                        "arn:aws:iam::*:role/DataPipelineDefaultRole"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIMXGLVY6DVR24VTYS",
        "PolicyName": "AWSDataPipeline_PowerUser",
        "UpdateDate": "2017-08-17T18:49:42+00:00",
        "VersionId": "v2"
    },
    "AWSDeviceFarmFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSDeviceFarmFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-07-13T16:37:38+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "devicefarm:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJO7KEDP4VYJPNT5UW",
        "PolicyName": "AWSDeviceFarmFullAccess",
        "UpdateDate": "2015-07-13T16:37:38+00:00",
        "VersionId": "v1"
    },
    "AWSDirectConnectFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSDirectConnectFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:07+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "directconnect:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJQF2QKZSK74KTIHOW",
        "PolicyName": "AWSDirectConnectFullAccess",
        "UpdateDate": "2015-02-06T18:40:07+00:00",
        "VersionId": "v1"
    },
    "AWSDirectConnectReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSDirectConnectReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:08+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "directconnect:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI23HZ27SI6FQMGNQ2",
        "PolicyName": "AWSDirectConnectReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:08+00:00",
        "VersionId": "v1"
    },
    "AWSDirectoryServiceFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSDirectoryServiceFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-02-24T23:10:36+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ds:*",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateNetworkInterface",
                        "ec2:CreateSecurityGroup",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:RevokeSecurityGroupIngress",
                        "sns:GetTopicAttributes",
                        "sns:ListSubscriptions",
                        "sns:ListSubscriptionsByTopic",
                        "sns:ListTopics"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "sns:CreateTopic",
                        "sns:DeleteTopic",
                        "sns:SetTopicAttributes",
                        "sns:Subscribe",
                        "sns:Unsubscribe"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:sns:*:*:DirectoryMonitoring*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAINAW5ANUWTH3R4ANI",
        "PolicyName": "AWSDirectoryServiceFullAccess",
        "UpdateDate": "2016-02-24T23:10:36+00:00",
        "VersionId": "v2"
    },
    "AWSDirectoryServiceReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSDirectoryServiceReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-02-24T23:11:18+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ds:Check*",
                        "ds:Describe*",
                        "ds:Get*",
                        "ds:List*",
                        "ds:Verify*",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "sns:ListTopics",
                        "sns:GetTopicAttributes",
                        "sns:ListSubscriptions",
                        "sns:ListSubscriptionsByTopic"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIHWYO6WSDNCG64M2W",
        "PolicyName": "AWSDirectoryServiceReadOnlyAccess",
        "UpdateDate": "2016-02-24T23:11:18+00:00",
        "VersionId": "v3"
    },
    "AWSEC2SpotServiceRolePolicy": {
        "Arn": "arn:aws:iam::aws:policy/aws-service-role/AWSEC2SpotServiceRolePolicy",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-18T18:51:54+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeInstances",
                        "ec2:StartInstances",
                        "ec2:StopInstances"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "iam:PassRole"
                    ],
                    "Condition": {
                        "StringLike": {
                            "iam:PassedToService": "ec2.amazonaws.com"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/aws-service-role/",
        "PolicyId": "ANPAIZJJBQNXQYVKTEXGM",
        "PolicyName": "AWSEC2SpotServiceRolePolicy",
        "UpdateDate": "2017-09-18T18:51:54+00:00",
        "VersionId": "v1"
    },
    "AWSElasticBeanstalkCustomPlatformforEC2Role": {
        "Arn": "arn:aws:iam::aws:policy/AWSElasticBeanstalkCustomPlatformforEC2Role",
        "AttachmentCount": 0,
        "CreateDate": "2017-02-21T22:50:30+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:AttachVolume",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CopyImage",
                        "ec2:CreateImage",
                        "ec2:CreateKeypair",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateSnapshot",
                        "ec2:CreateTags",
                        "ec2:CreateVolume",
                        "ec2:DeleteKeypair",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DeleteSnapshot",
                        "ec2:DeleteVolume",
                        "ec2:DeregisterImage",
                        "ec2:DescribeImageAttribute",
                        "ec2:DescribeImages",
                        "ec2:DescribeInstances",
                        "ec2:DescribeRegions",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSnapshots",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeTags",
                        "ec2:DescribeVolumes",
                        "ec2:DetachVolume",
                        "ec2:GetPasswordData",
                        "ec2:ModifyImageAttribute",
                        "ec2:ModifyInstanceAttribute",
                        "ec2:ModifySnapshotAttribute",
                        "ec2:RegisterImage",
                        "ec2:RunInstances",
                        "ec2:StopInstances",
                        "ec2:TerminateInstances"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "EC2Access"
                },
                {
                    "Action": [
                        "s3:Get*",
                        "s3:List*",
                        "s3:PutObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::elasticbeanstalk-*",
                        "arn:aws:s3:::elasticbeanstalk-*/*"
                    ],
                    "Sid": "BucketAccess"
                },
                {
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:logs:*:*:log-group:/aws/elasticbeanstalk/platform/*",
                    "Sid": "CloudWatchLogsAccess"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJRVFXSS6LEIQGBKDY",
        "PolicyName": "AWSElasticBeanstalkCustomPlatformforEC2Role",
        "UpdateDate": "2017-02-21T22:50:30+00:00",
        "VersionId": "v1"
    },
    "AWSElasticBeanstalkEnhancedHealth": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkEnhancedHealth",
        "AttachmentCount": 0,
        "CreateDate": "2016-08-22T20:28:36+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "elasticloadbalancing:DescribeInstanceHealth",
                        "elasticloadbalancing:DescribeLoadBalancers",
                        "elasticloadbalancing:DescribeTargetHealth",
                        "ec2:DescribeInstances",
                        "ec2:DescribeInstanceStatus",
                        "ec2:GetConsoleOutput",
                        "ec2:AssociateAddress",
                        "ec2:DescribeAddresses",
                        "ec2:DescribeSecurityGroups",
                        "sqs:GetQueueAttributes",
                        "sqs:GetQueueUrl",
                        "autoscaling:DescribeAutoScalingGroups",
                        "autoscaling:DescribeAutoScalingInstances",
                        "autoscaling:DescribeScalingActivities",
                        "autoscaling:DescribeNotificationConfigurations"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIH5EFJNMOGUUTKLFE",
        "PolicyName": "AWSElasticBeanstalkEnhancedHealth",
        "UpdateDate": "2016-08-22T20:28:36+00:00",
        "VersionId": "v2"
    },
    "AWSElasticBeanstalkFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSElasticBeanstalkFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-21T01:00:13+00:00",
        "DefaultVersionId": "v5",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "elasticbeanstalk:*",
                        "ec2:*",
                        "ecs:*",
                        "ecr:*",
                        "elasticloadbalancing:*",
                        "autoscaling:*",
                        "cloudwatch:*",
                        "s3:*",
                        "sns:*",
                        "cloudformation:*",
                        "dynamodb:*",
                        "rds:*",
                        "sqs:*",
                        "logs:*",
                        "iam:GetPolicyVersion",
                        "iam:GetRole",
                        "iam:PassRole",
                        "iam:ListRolePolicies",
                        "iam:ListAttachedRolePolicies",
                        "iam:ListInstanceProfiles",
                        "iam:ListRoles",
                        "iam:ListServerCertificates",
                        "acm:DescribeCertificate",
                        "acm:ListCertificates",
                        "codebuild:CreateProject",
                        "codebuild:DeleteProject",
                        "codebuild:BatchGetBuilds",
                        "codebuild:StartBuild"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "iam:AddRoleToInstanceProfile",
                        "iam:CreateInstanceProfile",
                        "iam:CreateRole"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/aws-elasticbeanstalk*",
                        "arn:aws:iam::*:instance-profile/aws-elasticbeanstalk*"
                    ]
                },
                {
                    "Action": [
                        "iam:AttachRolePolicy"
                    ],
                    "Condition": {
                        "StringLike": {
                            "iam:PolicyArn": [
                                "arn:aws:iam::aws:policy/AWSElasticBeanstalk*",
                                "arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalk*"
                            ]
                        }
                    },
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIZYX2YLLBW2LJVUFW",
        "PolicyName": "AWSElasticBeanstalkFullAccess",
        "UpdateDate": "2016-12-21T01:00:13+00:00",
        "VersionId": "v5"
    },
    "AWSElasticBeanstalkMulticontainerDocker": {
        "Arn": "arn:aws:iam::aws:policy/AWSElasticBeanstalkMulticontainerDocker",
        "AttachmentCount": 0,
        "CreateDate": "2016-06-06T23:45:37+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ecs:Poll",
                        "ecs:StartTask",
                        "ecs:StopTask",
                        "ecs:DiscoverPollEndpoint",
                        "ecs:StartTelemetrySession",
                        "ecs:RegisterContainerInstance",
                        "ecs:DeregisterContainerInstance",
                        "ecs:DescribeContainerInstances",
                        "ecs:Submit*",
                        "ecs:DescribeTasks"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "ECSAccess"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ45SBYG72SD6SHJEY",
        "PolicyName": "AWSElasticBeanstalkMulticontainerDocker",
        "UpdateDate": "2016-06-06T23:45:37+00:00",
        "VersionId": "v2"
    },
    "AWSElasticBeanstalkReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSElasticBeanstalkReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:19+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "elasticbeanstalk:Check*",
                        "elasticbeanstalk:Describe*",
                        "elasticbeanstalk:List*",
                        "elasticbeanstalk:RequestEnvironmentInfo",
                        "elasticbeanstalk:RetrieveEnvironmentInfo",
                        "ec2:Describe*",
                        "elasticloadbalancing:Describe*",
                        "autoscaling:Describe*",
                        "cloudwatch:Describe*",
                        "cloudwatch:List*",
                        "cloudwatch:Get*",
                        "s3:Get*",
                        "s3:List*",
                        "sns:Get*",
                        "sns:List*",
                        "cloudformation:Describe*",
                        "cloudformation:Get*",
                        "cloudformation:List*",
                        "cloudformation:Validate*",
                        "cloudformation:Estimate*",
                        "rds:Describe*",
                        "sqs:Get*",
                        "sqs:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI47KNGXDAXFD4SDHG",
        "PolicyName": "AWSElasticBeanstalkReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:19+00:00",
        "VersionId": "v1"
    },
    "AWSElasticBeanstalkService": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkService",
        "AttachmentCount": 0,
        "CreateDate": "2017-06-21T16:49:23+00:00",
        "DefaultVersionId": "v11",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudformation:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:cloudformation:*:*:stack/awseb-*",
                        "arn:aws:cloudformation:*:*:stack/eb-*"
                    ],
                    "Sid": "AllowCloudformationOperationsOnElasticBeanstalkStacks"
                },
                {
                    "Action": [
                        "logs:DeleteLogGroup"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:log-group:/aws/elasticbeanstalk*"
                    ],
                    "Sid": "AllowDeleteCloudwatchLogGroups"
                },
                {
                    "Action": [
                        "s3:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::elasticbeanstalk-*",
                        "arn:aws:s3:::elasticbeanstalk-*/*"
                    ],
                    "Sid": "AllowS3OperationsOnElasticBeanstalkBuckets"
                },
                {
                    "Action": [
                        "autoscaling:AttachInstances",
                        "autoscaling:CreateAutoScalingGroup",
                        "autoscaling:CreateLaunchConfiguration",
                        "autoscaling:DeleteLaunchConfiguration",
                        "autoscaling:DeleteAutoScalingGroup",
                        "autoscaling:DeleteScheduledAction",
                        "autoscaling:DescribeAccountLimits",
                        "autoscaling:DescribeAutoScalingGroups",
                        "autoscaling:DescribeAutoScalingInstances",
                        "autoscaling:DescribeLaunchConfigurations",
                        "autoscaling:DescribeLoadBalancers",
                        "autoscaling:DescribeNotificationConfigurations",
                        "autoscaling:DescribeScalingActivities",
                        "autoscaling:DescribeScheduledActions",
                        "autoscaling:DetachInstances",
                        "autoscaling:PutScheduledUpdateGroupAction",
                        "autoscaling:ResumeProcesses",
                        "autoscaling:SetDesiredCapacity",
                        "autoscaling:SuspendProcesses",
                        "autoscaling:TerminateInstanceInAutoScalingGroup",
                        "autoscaling:UpdateAutoScalingGroup",
                        "cloudwatch:PutMetricAlarm",
                        "ec2:AssociateAddress",
                        "ec2:AllocateAddress",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateSecurityGroup",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAddresses",
                        "ec2:DescribeImages",
                        "ec2:DescribeInstances",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSnapshots",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:DisassociateAddress",
                        "ec2:ReleaseAddress",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:RevokeSecurityGroupIngress",
                        "ec2:TerminateInstances",
                        "ecs:CreateCluster",
                        "ecs:DeleteCluster",
                        "ecs:DescribeClusters",
                        "ecs:RegisterTaskDefinition",
                        "elasticbeanstalk:*",
                        "elasticloadbalancing:ApplySecurityGroupsToLoadBalancer",
                        "elasticloadbalancing:ConfigureHealthCheck",
                        "elasticloadbalancing:CreateLoadBalancer",
                        "elasticloadbalancing:DeleteLoadBalancer",
                        "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
                        "elasticloadbalancing:DescribeInstanceHealth",
                        "elasticloadbalancing:DescribeLoadBalancers",
                        "elasticloadbalancing:DescribeTargetHealth",
                        "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
                        "elasticloadbalancing:DescribeTargetGroups",
                        "elasticloadbalancing:RegisterTargets",
                        "elasticloadbalancing:DeregisterTargets",
                        "iam:ListRoles",
                        "iam:PassRole",
                        "logs:CreateLogGroup",
                        "logs:PutRetentionPolicy",
                        "rds:DescribeDBEngineVersions",
                        "rds:DescribeDBInstances",
                        "rds:DescribeOrderableDBInstanceOptions",
                        "s3:CopyObject",
                        "s3:GetObject",
                        "s3:GetObjectAcl",
                        "s3:GetObjectMetadata",
                        "s3:ListBucket",
                        "s3:listBuckets",
                        "s3:ListObjects",
                        "sns:CreateTopic",
                        "sns:GetTopicAttributes",
                        "sns:ListSubscriptionsByTopic",
                        "sns:Subscribe",
                        "sns:SetTopicAttributes",
                        "sqs:GetQueueAttributes",
                        "sqs:GetQueueUrl",
                        "codebuild:CreateProject",
                        "codebuild:DeleteProject",
                        "codebuild:BatchGetBuilds",
                        "codebuild:StartBuild"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ],
                    "Sid": "AllowOperations"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJKQ5SN74ZQ4WASXBM",
        "PolicyName": "AWSElasticBeanstalkService",
        "UpdateDate": "2017-06-21T16:49:23+00:00",
        "VersionId": "v11"
    },
    "AWSElasticBeanstalkServiceRolePolicy": {
        "Arn": "arn:aws:iam::aws:policy/aws-service-role/AWSElasticBeanstalkServiceRolePolicy",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-13T23:46:37+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "iam:PassRole"
                    ],
                    "Condition": {
                        "StringLikeIfExists": {
                            "iam:PassedToService": "elasticbeanstalk.amazonaws.com"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "AllowPassRoleToElasticBeanstalk"
                },
                {
                    "Action": [
                        "cloudformation:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:cloudformation:*:*:stack/awseb-*",
                        "arn:aws:cloudformation:*:*:stack/eb-*"
                    ],
                    "Sid": "AllowCloudformationOperationsOnElasticBeanstalkStacks"
                },
                {
                    "Action": [
                        "logs:DeleteLogGroup"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:log-group:/aws/elasticbeanstalk*"
                    ],
                    "Sid": "AllowDeleteCloudwatchLogGroups"
                },
                {
                    "Action": [
                        "s3:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::elasticbeanstalk-*",
                        "arn:aws:s3:::elasticbeanstalk-*/*"
                    ],
                    "Sid": "AllowS3OperationsOnElasticBeanstalkBuckets"
                },
                {
                    "Action": [
                        "autoscaling:AttachInstances",
                        "autoscaling:CreateAutoScalingGroup",
                        "autoscaling:CreateLaunchConfiguration",
                        "autoscaling:DeleteLaunchConfiguration",
                        "autoscaling:DeleteAutoScalingGroup",
                        "autoscaling:DeleteScheduledAction",
                        "autoscaling:DescribeAccountLimits",
                        "autoscaling:DescribeAutoScalingGroups",
                        "autoscaling:DescribeAutoScalingInstances",
                        "autoscaling:DescribeLaunchConfigurations",
                        "autoscaling:DescribeLoadBalancers",
                        "autoscaling:DescribeNotificationConfigurations",
                        "autoscaling:DescribeScalingActivities",
                        "autoscaling:DescribeScheduledActions",
                        "autoscaling:DetachInstances",
                        "autoscaling:PutScheduledUpdateGroupAction",
                        "autoscaling:ResumeProcesses",
                        "autoscaling:SetDesiredCapacity",
                        "autoscaling:SuspendProcesses",
                        "autoscaling:TerminateInstanceInAutoScalingGroup",
                        "autoscaling:UpdateAutoScalingGroup",
                        "cloudwatch:PutMetricAlarm",
                        "ec2:AssociateAddress",
                        "ec2:AllocateAddress",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateSecurityGroup",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAddresses",
                        "ec2:DescribeImages",
                        "ec2:DescribeInstances",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:DisassociateAddress",
                        "ec2:ReleaseAddress",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:RevokeSecurityGroupIngress",
                        "ec2:TerminateInstances",
                        "ecs:CreateCluster",
                        "ecs:DeleteCluster",
                        "ecs:DescribeClusters",
                        "ecs:RegisterTaskDefinition",
                        "elasticbeanstalk:*",
                        "elasticloadbalancing:ApplySecurityGroupsToLoadBalancer",
                        "elasticloadbalancing:ConfigureHealthCheck",
                        "elasticloadbalancing:CreateLoadBalancer",
                        "elasticloadbalancing:DeleteLoadBalancer",
                        "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
                        "elasticloadbalancing:DescribeInstanceHealth",
                        "elasticloadbalancing:DescribeLoadBalancers",
                        "elasticloadbalancing:DescribeTargetHealth",
                        "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
                        "elasticloadbalancing:DescribeTargetGroups",
                        "elasticloadbalancing:RegisterTargets",
                        "elasticloadbalancing:DeregisterTargets",
                        "iam:ListRoles",
                        "logs:CreateLogGroup",
                        "logs:PutRetentionPolicy",
                        "rds:DescribeDBInstances",
                        "rds:DescribeOrderableDBInstanceOptions",
                        "rds:DescribeDBEngineVersions",
                        "sns:ListTopics",
                        "sns:GetTopicAttributes",
                        "sns:ListSubscriptionsByTopic",
                        "sqs:GetQueueAttributes",
                        "sqs:GetQueueUrl",
                        "codebuild:CreateProject",
                        "codebuild:DeleteProject",
                        "codebuild:BatchGetBuilds",
                        "codebuild:StartBuild"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ],
                    "Sid": "AllowOperations"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/aws-service-role/",
        "PolicyId": "ANPAIID62QSI3OSIPQXTM",
        "PolicyName": "AWSElasticBeanstalkServiceRolePolicy",
        "UpdateDate": "2017-09-13T23:46:37+00:00",
        "VersionId": "v1"
    },
    "AWSElasticBeanstalkWebTier": {
        "Arn": "arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-21T02:06:25+00:00",
        "DefaultVersionId": "v4",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:Get*",
                        "s3:List*",
                        "s3:PutObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::elasticbeanstalk-*",
                        "arn:aws:s3:::elasticbeanstalk-*/*"
                    ],
                    "Sid": "BucketAccess"
                },
                {
                    "Action": [
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "XRayAccess"
                },
                {
                    "Action": [
                        "logs:PutLogEvents",
                        "logs:CreateLogStream"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:log-group:/aws/elasticbeanstalk*"
                    ],
                    "Sid": "CloudWatchLogsAccess"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIUF4325SJYOREKW3A",
        "PolicyName": "AWSElasticBeanstalkWebTier",
        "UpdateDate": "2016-12-21T02:06:25+00:00",
        "VersionId": "v4"
    },
    "AWSElasticBeanstalkWorkerTier": {
        "Arn": "arn:aws:iam::aws:policy/AWSElasticBeanstalkWorkerTier",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-21T02:01:55+00:00",
        "DefaultVersionId": "v4",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:PutMetricData"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "MetricsAccess"
                },
                {
                    "Action": [
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "XRayAccess"
                },
                {
                    "Action": [
                        "sqs:ChangeMessageVisibility",
                        "sqs:DeleteMessage",
                        "sqs:ReceiveMessage",
                        "sqs:SendMessage"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "QueueAccess"
                },
                {
                    "Action": [
                        "s3:Get*",
                        "s3:List*",
                        "s3:PutObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::elasticbeanstalk-*",
                        "arn:aws:s3:::elasticbeanstalk-*/*"
                    ],
                    "Sid": "BucketAccess"
                },
                {
                    "Action": [
                        "dynamodb:BatchGetItem",
                        "dynamodb:BatchWriteItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:UpdateItem"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:dynamodb:*:*:table/*-stack-AWSEBWorkerCronLeaderRegistry*"
                    ],
                    "Sid": "DynamoPeriodicTasks"
                },
                {
                    "Action": [
                        "logs:PutLogEvents",
                        "logs:CreateLogStream"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:log-group:/aws/elasticbeanstalk*"
                    ],
                    "Sid": "CloudWatchLogsAccess"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJQDLBRSJVKVF4JMSK",
        "PolicyName": "AWSElasticBeanstalkWorkerTier",
        "UpdateDate": "2016-12-21T02:01:55+00:00",
        "VersionId": "v4"
    },
    "AWSElasticLoadBalancingClassicServiceRolePolicy": {
        "Arn": "arn:aws:iam::aws:policy/aws-service-role/AWSElasticLoadBalancingClassicServiceRolePolicy",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-19T22:36:18+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeAddresses",
                        "ec2:DescribeInstances",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeClassicLinkInstances",
                        "ec2:DescribeVpcClassicLink",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateNetworkInterface",
                        "ec2:DeleteNetworkInterface",
                        "ec2:ModifyNetworkInterface",
                        "ec2:ModifyNetworkInterfaceAttribute",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:AssociateAddress",
                        "ec2:DisassociateAddress",
                        "ec2:AttachNetworkInterface",
                        "ec2:DetachNetworkInterface",
                        "ec2:AssignPrivateIpAddresses",
                        "ec2:AssignIpv6Addresses",
                        "ec2:UnassignIpv6Addresses"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/aws-service-role/",
        "PolicyId": "ANPAIUMWW3QP7DPZPNVU4",
        "PolicyName": "AWSElasticLoadBalancingClassicServiceRolePolicy",
        "UpdateDate": "2017-09-19T22:36:18+00:00",
        "VersionId": "v1"
    },
    "AWSElasticLoadBalancingServiceRolePolicy": {
        "Arn": "arn:aws:iam::aws:policy/aws-service-role/AWSElasticLoadBalancingServiceRolePolicy",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-19T22:19:04+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeAddresses",
                        "ec2:DescribeInstances",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeClassicLinkInstances",
                        "ec2:DescribeVpcClassicLink",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateNetworkInterface",
                        "ec2:DeleteNetworkInterface",
                        "ec2:ModifyNetworkInterface",
                        "ec2:ModifyNetworkInterfaceAttribute",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:AssociateAddress",
                        "ec2:DisassociateAddress",
                        "ec2:AttachNetworkInterface",
                        "ec2:DetachNetworkInterface",
                        "ec2:AssignPrivateIpAddresses",
                        "ec2:AssignIpv6Addresses",
                        "ec2:UnassignIpv6Addresses"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/aws-service-role/",
        "PolicyId": "ANPAIMHWGGSRHLOQUICJQ",
        "PolicyName": "AWSElasticLoadBalancingServiceRolePolicy",
        "UpdateDate": "2017-09-19T22:19:04+00:00",
        "VersionId": "v1"
    },
    "AWSEnhancedClassicNetworkingMangementPolicy": {
        "Arn": "arn:aws:iam::aws:policy/aws-service-role/AWSEnhancedClassicNetworkingMangementPolicy",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-20T17:29:09+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeInstances",
                        "ec2:DescribeSecurityGroups"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/aws-service-role/",
        "PolicyId": "ANPAI7T4V2HZTS72QVO52",
        "PolicyName": "AWSEnhancedClassicNetworkingMangementPolicy",
        "UpdateDate": "2017-09-20T17:29:09+00:00",
        "VersionId": "v1"
    },
    "AWSGlueConsoleFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-13T00:12:54+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "glue:*",
                        "redshift:DescribeClusters",
                        "redshift:DescribeClusterSubnetGroups",
                        "iam:ListRoles",
                        "iam:ListRolePolicies",
                        "iam:GetRole",
                        "iam:GetRolePolicy",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeVpcEndpoints",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeVpcAttribute",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeInstances",
                        "rds:DescribeDBInstances",
                        "s3:ListAllMyBuckets",
                        "s3:ListBucket",
                        "s3:GetBucketAcl",
                        "s3:GetBucketLocation",
                        "cloudformation:DescribeStacks",
                        "cloudformation:GetTemplateSummary"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::aws-glue-*/*",
                        "arn:aws:s3:::*/*aws-glue-*/*",
                        "arn:aws:s3:::aws-glue-*"
                    ]
                },
                {
                    "Action": [
                        "s3:CreateBucket"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::aws-glue-*"
                    ]
                },
                {
                    "Action": [
                        "logs:GetLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:/aws-glue/*"
                    ]
                },
                {
                    "Action": [
                        "cloudformation:CreateStack",
                        "cloudformation:DeleteStack"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:cloudformation:*:*:stack/aws-glue*/*"
                },
                {
                    "Action": [
                        "ec2:TerminateInstances",
                        "ec2:RunInstances",
                        "ec2:CreateTags",
                        "ec2:DeleteTags"
                    ],
                    "Condition": {
                        "ForAllValues:StringEquals": {
                            "aws:TagKeys": [
                                "aws-glue-dev-endpoint"
                            ]
                        }
                    },
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "iam:PassRole"
                    ],
                    "Condition": {
                        "StringLike": {
                            "iam:PassedToService": [
                                "glue.amazonaws.com"
                            ]
                        }
                    },
                    "Effect": "Allow",
                    "Resource": "arn:aws:iam::*:role/AWSGlueServiceRole*"
                },
                {
                    "Action": [
                        "iam:PassRole"
                    ],
                    "Condition": {
                        "StringLike": {
                            "iam:PassedToService": [
                                "ec2.amazonaws.com"
                            ]
                        }
                    },
                    "Effect": "Allow",
                    "Resource": "arn:aws:iam::*:role/AWSGlueServiceNotebookRole*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJNZGDEOD7MISOVSVI",
        "PolicyName": "AWSGlueConsoleFullAccess",
        "UpdateDate": "2017-09-13T00:12:54+00:00",
        "VersionId": "v2"
    },
    "AWSGlueServiceNotebookRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSGlueServiceNotebookRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-17T18:08:29+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "glue:CreateDatabase",
                        "glue:CreatePartition",
                        "glue:CreateTable",
                        "glue:DeleteDatabase",
                        "glue:DeletePartition",
                        "glue:DeleteTable",
                        "glue:GetDatabase",
                        "glue:GetDatabases",
                        "glue:GetPartition",
                        "glue:GetPartitions",
                        "glue:GetTable",
                        "glue:GetTableVersions",
                        "glue:GetTables",
                        "glue:UpdateDatabase",
                        "glue:UpdatePartition",
                        "glue:UpdateTable",
                        "glue:CreateBookmark",
                        "glue:GetBookmark",
                        "glue:UpdateBookmark",
                        "glue:GetMetric",
                        "glue:PutMetric",
                        "glue:CreateConnection",
                        "glue:CreateJob",
                        "glue:DeleteConnection",
                        "glue:DeleteJob",
                        "glue:GetConnection",
                        "glue:GetConnections",
                        "glue:GetDevEndpoint",
                        "glue:GetDevEndpoints",
                        "glue:GetJob",
                        "glue:GetJobs",
                        "glue:UpdateJob",
                        "glue:BatchDeleteConnection",
                        "glue:UpdateConnection",
                        "glue:GetUserDefinedFunction",
                        "glue:UpdateUserDefinedFunction",
                        "glue:GetUserDefinedFunctions",
                        "glue:DeleteUserDefinedFunction",
                        "glue:CreateUserDefinedFunction",
                        "glue:BatchGetPartition",
                        "glue:BatchDeletePartition",
                        "glue:BatchCreatePartition",
                        "glue:BatchDeleteTable",
                        "glue:UpdateDevEndpoint",
                        "s3:GetBucketLocation",
                        "s3:ListBucket",
                        "s3:ListAllMyBuckets",
                        "s3:GetBucketAcl"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::crawler-public*",
                        "arn:aws:s3:::aws-glue*"
                    ]
                },
                {
                    "Action": [
                        "s3:PutObject",
                        "s3:DeleteObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::aws-glue*"
                    ]
                },
                {
                    "Action": [
                        "ec2:CreateTags",
                        "ec2:DeleteTags"
                    ],
                    "Condition": {
                        "ForAllValues:StringEquals": {
                            "aws:TagKeys": [
                                "aws-glue-service-resource"
                            ]
                        }
                    },
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:ec2:*:*:network-interface/*",
                        "arn:aws:ec2:*:*:security-group/*",
                        "arn:aws:ec2:*:*:instance/*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIMRC6VZUHJYCTKWFI",
        "PolicyName": "AWSGlueServiceNotebookRole",
        "UpdateDate": "2017-08-17T18:08:29+00:00",
        "VersionId": "v2"
    },
    "AWSGlueServiceRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-23T21:35:25+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "glue:*",
                        "s3:GetBucketLocation",
                        "s3:ListBucket",
                        "s3:ListAllMyBuckets",
                        "s3:GetBucketAcl",
                        "ec2:DescribeVpcEndpoints",
                        "ec2:DescribeRouteTables",
                        "ec2:CreateNetworkInterface",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcAttribute",
                        "iam:ListRolePolicies",
                        "iam:GetRole",
                        "iam:GetRolePolicy"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "s3:CreateBucket"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::aws-glue-*"
                    ]
                },
                {
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::aws-glue-*/*",
                        "arn:aws:s3:::*/*aws-glue-*/*"
                    ]
                },
                {
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::crawler-public*",
                        "arn:aws:s3:::aws-glue-*"
                    ]
                },
                {
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:/aws-glue/*"
                    ]
                },
                {
                    "Action": [
                        "ec2:CreateTags",
                        "ec2:DeleteTags"
                    ],
                    "Condition": {
                        "ForAllValues:StringEquals": {
                            "aws:TagKeys": [
                                "aws-glue-service-resource"
                            ]
                        }
                    },
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:ec2:*:*:network-interface/*",
                        "arn:aws:ec2:*:*:security-group/*",
                        "arn:aws:ec2:*:*:instance/*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIRUJCPEBPMEZFAS32",
        "PolicyName": "AWSGlueServiceRole",
        "UpdateDate": "2017-08-23T21:35:25+00:00",
        "VersionId": "v3"
    },
    "AWSGreengrassFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSGreengrassFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-05-03T00:47:37+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "greengrass:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJWPV6OBK4QONH4J3O",
        "PolicyName": "AWSGreengrassFullAccess",
        "UpdateDate": "2017-05-03T00:47:37+00:00",
        "VersionId": "v1"
    },
    "AWSGreengrassResourceAccessRolePolicy": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSGreengrassResourceAccessRolePolicy",
        "AttachmentCount": 0,
        "CreateDate": "2017-05-26T23:10:54+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "iot:DeleteThingShadow",
                        "iot:GetThingShadow",
                        "iot:UpdateThingShadow"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iot:*:*:thing/GG_*",
                        "arn:aws:iot:*:*:thing/*-gcm",
                        "arn:aws:iot:*:*:thing/*-gda",
                        "arn:aws:iot:*:*:thing/*-gci"
                    ],
                    "Sid": "AllowGreengrassAccessToShadows"
                },
                {
                    "Action": [
                        "iot:DescribeThing"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:iot:*:*:thing/*",
                    "Sid": "AllowGreengrassToDescribeThings"
                },
                {
                    "Action": [
                        "iot:DescribeCertificate"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:iot:*:*:cert/*",
                    "Sid": "AllowGreengrassToDescribeCertificates"
                },
                {
                    "Action": [
                        "greengrass:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "AllowGreengrassToCallGreengrassServices"
                },
                {
                    "Action": [
                        "lambda:GetFunction",
                        "lambda:GetFunctionConfiguration"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "AllowGreengrassToGetLambdaFunctions"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJPKEIMB6YMXDEVRTM",
        "PolicyName": "AWSGreengrassResourceAccessRolePolicy",
        "UpdateDate": "2017-05-26T23:10:54+00:00",
        "VersionId": "v3"
    },
    "AWSHealthFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSHealthFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-06T12:30:31+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "health:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI3CUMPCPEUPCSXC4Y",
        "PolicyName": "AWSHealthFullAccess",
        "UpdateDate": "2016-12-06T12:30:31+00:00",
        "VersionId": "v1"
    },
    "AWSImportExportFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSImportExportFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:43+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "importexport:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJCQCT4JGTLC6722MQ",
        "PolicyName": "AWSImportExportFullAccess",
        "UpdateDate": "2015-02-06T18:40:43+00:00",
        "VersionId": "v1"
    },
    "AWSImportExportReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSImportExportReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:42+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "importexport:ListJobs",
                        "importexport:GetStatus"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJNTV4OG52ESYZHCNK",
        "PolicyName": "AWSImportExportReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:42+00:00",
        "VersionId": "v1"
    },
    "AWSIoTConfigAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSIoTConfigAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-07-27T20:41:18+00:00",
        "DefaultVersionId": "v4",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "iot:AcceptCertificateTransfer",
                        "iot:AttachPrincipalPolicy",
                        "iot:AttachThingPrincipal",
                        "iot:CancelCertificateTransfer",
                        "iot:CreateCertificateFromCsr",
                        "iot:CreateKeysAndCertificate",
                        "iot:CreatePolicy",
                        "iot:CreatePolicyVersion",
                        "iot:CreateThing",
                        "iot:CreateThingType",
                        "iot:CreateTopicRule",
                        "iot:DeleteCertificate",
                        "iot:DeleteCACertificate",
                        "iot:DeletePolicy",
                        "iot:DeletePolicyVersion",
                        "iot:DeleteRegistrationCode",
                        "iot:DeleteThing",
                        "iot:DeleteThingType",
                        "iot:DeleteTopicRule",
                        "iot:DeprecateThingType",
                        "iot:DescribeCertificate",
                        "iot:DescribeCACertificate",
                        "iot:DescribeEndpoint",
                        "iot:DescribeThing",
                        "iot:DescribeThingType",
                        "iot:DetachPrincipalPolicy",
                        "iot:DetachThingPrincipal",
                        "iot:GetLoggingOptions",
                        "iot:GetPolicy",
                        "iot:GetPolicyVersion",
                        "iot:GetRegistrationCode",
                        "iot:GetTopicRule",
                        "iot:ListCertificates",
                        "iot:ListCACertificates",
                        "iot:ListCertificatesByCA",
                        "iot:ListPolicies",
                        "iot:ListPolicyPrincipals",
                        "iot:ListPolicyVersions",
                        "iot:ListPrincipalPolicies",
                        "iot:ListPrincipalThings",
                        "iot:ListThingPrincipals",
                        "iot:ListThings",
                        "iot:ListThingTypes",
                        "iot:ListTopicRules",
                        "iot:RegisterCertificate",
                        "iot:RegisterCACertificate",
                        "iot:RejectCertificateTransfer",
                        "iot:ReplaceTopicRule",
                        "iot:SetDefaultPolicyVersion",
                        "iot:SetLoggingOptions",
                        "iot:TransferCertificate",
                        "iot:UpdateCertificate",
                        "iot:UpdateCACertificate",
                        "iot:UpdateThing"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIWWGD4LM4EMXNRL7I",
        "PolicyName": "AWSIoTConfigAccess",
        "UpdateDate": "2016-07-27T20:41:18+00:00",
        "VersionId": "v4"
    },
    "AWSIoTConfigReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSIoTConfigReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-07-27T20:41:36+00:00",
        "DefaultVersionId": "v4",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "iot:DescribeCertificate",
                        "iot:DescribeCACertificate",
                        "iot:DescribeEndpoint",
                        "iot:DescribeThing",
                        "iot:DescribeThingType",
                        "iot:GetLoggingOptions",
                        "iot:GetPolicy",
                        "iot:GetPolicyVersion",
                        "iot:GetRegistrationCode",
                        "iot:GetTopicRule",
                        "iot:ListCertificates",
                        "iot:ListCertificatesByCA",
                        "iot:ListCACertificates",
                        "iot:ListPolicies",
                        "iot:ListPolicyPrincipals",
                        "iot:ListPolicyVersions",
                        "iot:ListPrincipalPolicies",
                        "iot:ListPrincipalThings",
                        "iot:ListThingPrincipals",
                        "iot:ListThings",
                        "iot:ListThingTypes",
                        "iot:ListTopicRules"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJHENEMXGX4XMFOIOI",
        "PolicyName": "AWSIoTConfigReadOnlyAccess",
        "UpdateDate": "2016-07-27T20:41:36+00:00",
        "VersionId": "v4"
    },
    "AWSIoTDataAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSIoTDataAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-10-27T21:51:18+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "iot:Connect",
                        "iot:Publish",
                        "iot:Subscribe",
                        "iot:Receive",
                        "iot:GetThingShadow",
                        "iot:UpdateThingShadow"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJM2KI2UJDR24XPS2K",
        "PolicyName": "AWSIoTDataAccess",
        "UpdateDate": "2015-10-27T21:51:18+00:00",
        "VersionId": "v1"
    },
    "AWSIoTFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSIoTFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-10-08T15:19:49+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "iot:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJU2FPGG6PQWN72V2G",
        "PolicyName": "AWSIoTFullAccess",
        "UpdateDate": "2015-10-08T15:19:49+00:00",
        "VersionId": "v1"
    },
    "AWSIoTLogging": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSIoTLogging",
        "AttachmentCount": 0,
        "CreateDate": "2015-10-08T15:17:25+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:PutMetricFilter",
                        "logs:PutRetentionPolicy",
                        "logs:GetLogEvents",
                        "logs:DeleteLogStream"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAI6R6Z2FHHGS454W7W",
        "PolicyName": "AWSIoTLogging",
        "UpdateDate": "2015-10-08T15:17:25+00:00",
        "VersionId": "v1"
    },
    "AWSIoTRuleActions": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSIoTRuleActions",
        "AttachmentCount": 0,
        "CreateDate": "2015-10-08T15:14:51+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": {
                "Action": [
                    "dynamodb:PutItem",
                    "kinesis:PutRecord",
                    "iot:Publish",
                    "s3:PutObject",
                    "sns:Publish",
                    "sqs:SendMessage*"
                ],
                "Effect": "Allow",
                "Resource": "*"
            },
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJEZ6FS7BUZVUHMOKY",
        "PolicyName": "AWSIoTRuleActions",
        "UpdateDate": "2015-10-08T15:14:51+00:00",
        "VersionId": "v1"
    },
    "AWSKeyManagementServicePowerUser": {
        "Arn": "arn:aws:iam::aws:policy/AWSKeyManagementServicePowerUser",
        "AttachmentCount": 1,
        "CreateDate": "2017-03-07T00:55:11+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "kms:CreateAlias",
                        "kms:CreateKey",
                        "kms:DeleteAlias",
                        "kms:Describe*",
                        "kms:GenerateRandom",
                        "kms:Get*",
                        "kms:List*",
                        "kms:TagResource",
                        "kms:UntagResource",
                        "iam:ListGroups",
                        "iam:ListRoles",
                        "iam:ListUsers"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJNPP7PPPPMJRV2SA4",
        "PolicyName": "AWSKeyManagementServicePowerUser",
        "UpdateDate": "2017-03-07T00:55:11+00:00",
        "VersionId": "v2"
    },
    "AWSLambdaBasicExecutionRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        "AttachmentCount": 0,
        "CreateDate": "2015-04-09T15:03:43+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJNCQGXC42545SKXIK",
        "PolicyName": "AWSLambdaBasicExecutionRole",
        "UpdateDate": "2015-04-09T15:03:43+00:00",
        "VersionId": "v1"
    },
    "AWSLambdaDynamoDBExecutionRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSLambdaDynamoDBExecutionRole",
        "AttachmentCount": 0,
        "CreateDate": "2015-04-09T15:09:29+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "dynamodb:DescribeStream",
                        "dynamodb:GetRecords",
                        "dynamodb:GetShardIterator",
                        "dynamodb:ListStreams",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIP7WNAGMIPYNW4WQG",
        "PolicyName": "AWSLambdaDynamoDBExecutionRole",
        "UpdateDate": "2015-04-09T15:09:29+00:00",
        "VersionId": "v1"
    },
    "AWSLambdaENIManagementAccess": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSLambdaENIManagementAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-06T00:37:27+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:CreateNetworkInterface",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DeleteNetworkInterface"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJXAW2Q3KPTURUT2QC",
        "PolicyName": "AWSLambdaENIManagementAccess",
        "UpdateDate": "2016-12-06T00:37:27+00:00",
        "VersionId": "v1"
    },
    "AWSLambdaExecute": {
        "Arn": "arn:aws:iam::aws:policy/AWSLambdaExecute",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:46+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "logs:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:logs:*:*:*"
                },
                {
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJE5FX7FQZSU5XAKGO",
        "PolicyName": "AWSLambdaExecute",
        "UpdateDate": "2015-02-06T18:40:46+00:00",
        "VersionId": "v1"
    },
    "AWSLambdaFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSLambdaFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-05-25T19:08:45+00:00",
        "DefaultVersionId": "v7",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:*",
                        "cognito-identity:ListIdentityPools",
                        "cognito-sync:GetCognitoEvents",
                        "cognito-sync:SetCognitoEvents",
                        "dynamodb:*",
                        "events:*",
                        "iam:ListAttachedRolePolicies",
                        "iam:ListRolePolicies",
                        "iam:ListRoles",
                        "iam:PassRole",
                        "kinesis:DescribeStream",
                        "kinesis:ListStreams",
                        "kinesis:PutRecord",
                        "lambda:*",
                        "logs:*",
                        "s3:*",
                        "sns:ListSubscriptions",
                        "sns:ListSubscriptionsByTopic",
                        "sns:ListTopics",
                        "sns:Subscribe",
                        "sns:Unsubscribe",
                        "sns:Publish",
                        "sqs:ListQueues",
                        "sqs:SendMessage",
                        "tag:GetResources",
                        "kms:ListAliases",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeSecurityGroups",
                        "iot:GetTopicRule",
                        "iot:ListTopicRules",
                        "iot:CreateTopicRule",
                        "iot:ReplaceTopicRule",
                        "iot:AttachPrincipalPolicy",
                        "iot:AttachThingPrincipal",
                        "iot:CreateKeysAndCertificate",
                        "iot:CreatePolicy",
                        "iot:CreateThing",
                        "iot:ListPolicies",
                        "iot:ListThings",
                        "iot:DescribeEndpoint",
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI6E2CYYMI4XI7AA5K",
        "PolicyName": "AWSLambdaFullAccess",
        "UpdateDate": "2017-05-25T19:08:45+00:00",
        "VersionId": "v7"
    },
    "AWSLambdaInvocation-DynamoDB": {
        "Arn": "arn:aws:iam::aws:policy/AWSLambdaInvocation-DynamoDB",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:47+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "dynamodb:DescribeStream",
                        "dynamodb:GetRecords",
                        "dynamodb:GetShardIterator",
                        "dynamodb:ListStreams"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJTHQ3EKCQALQDYG5G",
        "PolicyName": "AWSLambdaInvocation-DynamoDB",
        "UpdateDate": "2015-02-06T18:40:47+00:00",
        "VersionId": "v1"
    },
    "AWSLambdaKinesisExecutionRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole",
        "AttachmentCount": 0,
        "CreateDate": "2015-04-09T15:14:16+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "kinesis:DescribeStream",
                        "kinesis:GetRecords",
                        "kinesis:GetShardIterator",
                        "kinesis:ListStreams",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJHOLKJPXV4GBRMJUQ",
        "PolicyName": "AWSLambdaKinesisExecutionRole",
        "UpdateDate": "2015-04-09T15:14:16+00:00",
        "VersionId": "v1"
    },
    "AWSLambdaReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSLambdaReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-05-04T18:22:29+00:00",
        "DefaultVersionId": "v6",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:Describe*",
                        "cloudwatch:Get*",
                        "cloudwatch:List*",
                        "cognito-identity:ListIdentityPools",
                        "cognito-sync:GetCognitoEvents",
                        "dynamodb:BatchGetItem",
                        "dynamodb:DescribeStream",
                        "dynamodb:DescribeTable",
                        "dynamodb:GetItem",
                        "dynamodb:ListStreams",
                        "dynamodb:ListTables",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "events:List*",
                        "events:Describe*",
                        "iam:ListRoles",
                        "kinesis:DescribeStream",
                        "kinesis:ListStreams",
                        "lambda:List*",
                        "lambda:Get*",
                        "logs:DescribeMetricFilters",
                        "logs:GetLogEvents",
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams",
                        "s3:Get*",
                        "s3:List*",
                        "sns:ListTopics",
                        "sns:ListSubscriptions",
                        "sns:ListSubscriptionsByTopic",
                        "sqs:ListQueues",
                        "tag:GetResources",
                        "kms:ListAliases",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeSecurityGroups",
                        "iot:GetTopicRules",
                        "iot:ListTopicRules",
                        "iot:ListPolicies",
                        "iot:ListThings",
                        "iot:DescribeEndpoint"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJLDG7J3CGUHFN4YN6",
        "PolicyName": "AWSLambdaReadOnlyAccess",
        "UpdateDate": "2017-05-04T18:22:29+00:00",
        "VersionId": "v6"
    },
    "AWSLambdaRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSLambdaRole",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:28+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJX4DPCRGTC4NFDUXI",
        "PolicyName": "AWSLambdaRole",
        "UpdateDate": "2015-02-06T18:41:28+00:00",
        "VersionId": "v1"
    },
    "AWSLambdaVPCAccessExecutionRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
        "AttachmentCount": 0,
        "CreateDate": "2016-02-11T23:15:26+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "ec2:CreateNetworkInterface",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DeleteNetworkInterface"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJVTME3YLVNL72YR2K",
        "PolicyName": "AWSLambdaVPCAccessExecutionRole",
        "UpdateDate": "2016-02-11T23:15:26+00:00",
        "VersionId": "v1"
    },
    "AWSMarketplaceFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSMarketplaceFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-11T17:21:45+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "aws-marketplace:*",
                        "cloudformation:CreateStack",
                        "cloudformation:DescribeStackResource",
                        "cloudformation:DescribeStackResources",
                        "cloudformation:DescribeStacks",
                        "cloudformation:List*",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateTags",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAddresses",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeImages",
                        "ec2:DescribeInstances",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeTags",
                        "ec2:DescribeVpcs",
                        "ec2:RunInstances",
                        "ec2:StartInstances",
                        "ec2:StopInstances",
                        "ec2:TerminateInstances"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI2DV5ULJSO2FYVPYG",
        "PolicyName": "AWSMarketplaceFullAccess",
        "UpdateDate": "2015-02-11T17:21:45+00:00",
        "VersionId": "v1"
    },
    "AWSMarketplaceGetEntitlements": {
        "Arn": "arn:aws:iam::aws:policy/AWSMarketplaceGetEntitlements",
        "AttachmentCount": 0,
        "CreateDate": "2017-03-27T19:37:24+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "aws-marketplace:GetEntitlements"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJLPIMQE4WMHDC2K7C",
        "PolicyName": "AWSMarketplaceGetEntitlements",
        "UpdateDate": "2017-03-27T19:37:24+00:00",
        "VersionId": "v1"
    },
    "AWSMarketplaceManageSubscriptions": {
        "Arn": "arn:aws:iam::aws:policy/AWSMarketplaceManageSubscriptions",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:32+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "aws-marketplace:ViewSubscriptions",
                        "aws-marketplace:Subscribe",
                        "aws-marketplace:Unsubscribe"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJRDW2WIFN7QLUAKBQ",
        "PolicyName": "AWSMarketplaceManageSubscriptions",
        "UpdateDate": "2015-02-06T18:40:32+00:00",
        "VersionId": "v1"
    },
    "AWSMarketplaceMeteringFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSMarketplaceMeteringFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-03-17T22:39:22+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "aws-marketplace:MeterUsage"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ65YJPG7CC7LDXNA6",
        "PolicyName": "AWSMarketplaceMeteringFullAccess",
        "UpdateDate": "2016-03-17T22:39:22+00:00",
        "VersionId": "v1"
    },
    "AWSMarketplaceRead-only": {
        "Arn": "arn:aws:iam::aws:policy/AWSMarketplaceRead-only",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:31+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "aws-marketplace:ViewSubscriptions",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAddresses",
                        "ec2:DescribeImages",
                        "ec2:DescribeInstances",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJOOM6LETKURTJ3XZ2",
        "PolicyName": "AWSMarketplaceRead-only",
        "UpdateDate": "2015-02-06T18:40:31+00:00",
        "VersionId": "v1"
    },
    "AWSMigrationHubDMSAccess": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSMigrationHubDMSAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-14T14:00:06+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "mgh:CreateProgressUpdateStream"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:mgh:*:*:progressUpdateStream/DMS"
                },
                {
                    "Action": [
                        "mgh:AssociateCreatedArtifact",
                        "mgh:DescribeMigrationTask",
                        "mgh:DisassociateCreatedArtifact",
                        "mgh:ImportMigrationTask",
                        "mgh:ListCreatedArtifacts",
                        "mgh:NotifyMigrationTaskState",
                        "mgh:PutResourceAttributes",
                        "mgh:NotifyApplicationState",
                        "mgh:DescribeApplicationState",
                        "mgh:AssociateDiscoveredResource",
                        "mgh:DisassociateDiscoveredResource",
                        "mgh:ListDiscoveredResources"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:mgh:*:*:progressUpdateStream/DMS/*"
                },
                {
                    "Action": [
                        "mgh:ListMigrationTasks"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIUQB56VA4JHLN7G2W",
        "PolicyName": "AWSMigrationHubDMSAccess",
        "UpdateDate": "2017-08-14T14:00:06+00:00",
        "VersionId": "v1"
    },
    "AWSMigrationHubDiscoveryAccess": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSMigrationHubDiscoveryAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-14T13:30:51+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "discovery:ListConfigurations",
                        "discovery:DescribeConfigurations"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAITRMRLSV7JAL6YIGG",
        "PolicyName": "AWSMigrationHubDiscoveryAccess",
        "UpdateDate": "2017-08-14T13:30:51+00:00",
        "VersionId": "v1"
    },
    "AWSMigrationHubFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSMigrationHubFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-14T14:09:27+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "mgh:*",
                        "discovery:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "iam:GetRole"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ4A2SZKHUYHDYIGOK",
        "PolicyName": "AWSMigrationHubFullAccess",
        "UpdateDate": "2017-08-14T14:09:27+00:00",
        "VersionId": "v2"
    },
    "AWSMigrationHubSMSAccess": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSMigrationHubSMSAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-14T13:57:54+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "mgh:CreateProgressUpdateStream"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:mgh:*:*:progressUpdateStream/SMS"
                },
                {
                    "Action": [
                        "mgh:AssociateCreatedArtifact",
                        "mgh:DescribeMigrationTask",
                        "mgh:DisassociateCreatedArtifact",
                        "mgh:ImportMigrationTask",
                        "mgh:ListCreatedArtifacts",
                        "mgh:NotifyMigrationTaskState",
                        "mgh:PutResourceAttributes",
                        "mgh:NotifyApplicationState",
                        "mgh:DescribeApplicationState",
                        "mgh:AssociateDiscoveredResource",
                        "mgh:DisassociateDiscoveredResource",
                        "mgh:ListDiscoveredResources"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:mgh:*:*:progressUpdateStream/SMS/*"
                },
                {
                    "Action": [
                        "mgh:ListMigrationTasks"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIWQYYT6TSVIRJO4TY",
        "PolicyName": "AWSMigrationHubSMSAccess",
        "UpdateDate": "2017-08-14T13:57:54+00:00",
        "VersionId": "v1"
    },
    "AWSMobileHub_FullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSMobileHub_FullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-10T22:23:47+00:00",
        "DefaultVersionId": "v10",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "apigateway:GET",
                        "apigateway:GetRestApis",
                        "apigateway:GetResources",
                        "apigateway:POST",
                        "apigateway:TestInvokeMethod",
                        "dynamodb:DescribeTable",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "iam:ListSAMLProviders",
                        "lambda:ListFunctions",
                        "sns:ListTopics",
                        "lex:GetIntent",
                        "lex:GetIntents",
                        "lex:GetSlotType",
                        "lex:GetSlotTypes",
                        "lex:GetBot",
                        "lex:GetBots",
                        "lex:GetBotAlias",
                        "lex:GetBotAliases",
                        "mobilehub:CreateProject",
                        "mobilehub:DeleteProject",
                        "mobilehub:UpdateProject",
                        "mobilehub:ExportProject",
                        "mobilehub:ImportProject",
                        "mobilehub:SynchronizeProject",
                        "mobilehub:GenerateProjectParameters",
                        "mobilehub:GetProject",
                        "mobilehub:GetProjectSnapshot",
                        "mobilehub:ListAvailableConnectors",
                        "mobilehub:ListAvailableFeatures",
                        "mobilehub:ListAvailableRegions",
                        "mobilehub:ListProjects",
                        "mobilehub:ValidateProject",
                        "mobilehub:VerifyServiceRole",
                        "mobilehub:DescribeBundle",
                        "mobilehub:ExportBundle",
                        "mobilehub:ListBundles"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::*/aws-my-sample-app*.zip"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIJLU43R6AGRBK76DM",
        "PolicyName": "AWSMobileHub_FullAccess",
        "UpdateDate": "2017-08-10T22:23:47+00:00",
        "VersionId": "v10"
    },
    "AWSMobileHub_ReadOnly": {
        "Arn": "arn:aws:iam::aws:policy/AWSMobileHub_ReadOnly",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-10T22:08:23+00:00",
        "DefaultVersionId": "v8",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "dynamodb:DescribeTable",
                        "iam:ListSAMLProviders",
                        "lambda:ListFunctions",
                        "sns:ListTopics",
                        "lex:GetIntent",
                        "lex:GetIntents",
                        "lex:GetSlotType",
                        "lex:GetSlotTypes",
                        "lex:GetBot",
                        "lex:GetBots",
                        "lex:GetBotAlias",
                        "lex:GetBotAliases",
                        "mobilehub:ExportProject",
                        "mobilehub:GenerateProjectParameters",
                        "mobilehub:GetProject",
                        "mobilehub:GetProjectSnapshot",
                        "mobilehub:ListAvailableConnectors",
                        "mobilehub:ListAvailableFeatures",
                        "mobilehub:ListAvailableRegions",
                        "mobilehub:ListProjects",
                        "mobilehub:ValidateProject",
                        "mobilehub:VerifyServiceRole",
                        "mobilehub:DescribeBundle",
                        "mobilehub:ExportBundle",
                        "mobilehub:ListBundles"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::*/aws-my-sample-app*.zip"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIBXVYVL3PWQFBZFGW",
        "PolicyName": "AWSMobileHub_ReadOnly",
        "UpdateDate": "2017-08-10T22:08:23+00:00",
        "VersionId": "v8"
    },
    "AWSMobileHub_ServiceUseOnly": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSMobileHub_ServiceUseOnly",
        "AttachmentCount": 0,
        "CreateDate": "2017-06-02T23:35:49+00:00",
        "DefaultVersionId": "v23",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudformation:CreateUploadBucket",
                        "cloudformation:ValidateTemplate",
                        "cloudfront:CreateDistribution",
                        "cloudfront:DeleteDistribution",
                        "cloudfront:GetDistribution",
                        "cloudfront:GetDistributionConfig",
                        "cloudfront:UpdateDistribution",
                        "cognito-identity:CreateIdentityPool",
                        "cognito-identity:UpdateIdentityPool",
                        "cognito-identity:DeleteIdentityPool",
                        "cognito-identity:SetIdentityPoolRoles",
                        "cognito-idp:CreateUserPool",
                        "dynamodb:CreateTable",
                        "dynamodb:DeleteTable",
                        "dynamodb:DescribeTable",
                        "dynamodb:UpdateTable",
                        "iam:AddClientIDToOpenIDConnectProvider",
                        "iam:CreateOpenIDConnectProvider",
                        "iam:GetOpenIDConnectProvider",
                        "iam:ListOpenIDConnectProviders",
                        "iam:CreateSAMLProvider",
                        "iam:GetSAMLProvider",
                        "iam:ListSAMLProvider",
                        "iam:UpdateSAMLProvider",
                        "lambda:CreateFunction",
                        "lambda:DeleteFunction",
                        "lambda:GetFunction",
                        "mobileanalytics:CreateApp",
                        "mobileanalytics:DeleteApp",
                        "sns:CreateTopic",
                        "sns:DeleteTopic",
                        "sns:ListPlatformApplications",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "lex:PutIntent",
                        "lex:GetIntent",
                        "lex:GetIntents",
                        "lex:PutSlotType",
                        "lex:GetSlotType",
                        "lex:GetSlotTypes",
                        "lex:PutBot",
                        "lex:GetBot",
                        "lex:GetBots",
                        "lex:GetBotAlias",
                        "lex:GetBotAliases"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "sns:CreatePlatformApplication",
                        "sns:DeletePlatformApplication",
                        "sns:GetPlatformApplicationAttributes",
                        "sns:SetPlatformApplicationAttributes"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:sns:*:*:app/*_MOBILEHUB_*"
                    ]
                },
                {
                    "Action": [
                        "s3:CreateBucket",
                        "s3:DeleteBucket",
                        "s3:DeleteBucketPolicy",
                        "s3:DeleteBucketWebsite",
                        "s3:ListBucket",
                        "s3:ListBucketVersions",
                        "s3:GetBucketLocation",
                        "s3:GetBucketVersioning",
                        "s3:PutBucketVersioning",
                        "s3:PutBucketWebsite",
                        "s3:PutBucketPolicy",
                        "s3:SetBucketCrossOriginConfiguration"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::*-userfiles-mobilehub-*",
                        "arn:aws:s3:::*-contentdelivery-mobilehub-*",
                        "arn:aws:s3:::*-hosting-mobilehub-*",
                        "arn:aws:s3:::*-deployments-mobilehub-*"
                    ]
                },
                {
                    "Action": [
                        "s3:DeleteObject",
                        "s3:DeleteVersion",
                        "s3:DeleteObjectVersion",
                        "s3:GetObject",
                        "s3:GetObjectVersion",
                        "s3:PutObject",
                        "s3:PutObjectAcl"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::*-userfiles-mobilehub-*/*",
                        "arn:aws:s3:::*-contentdelivery-mobilehub-*/*",
                        "arn:aws:s3:::*-hosting-mobilehub-*/*",
                        "arn:aws:s3:::*-deployments-mobilehub-*/*"
                    ]
                },
                {
                    "Action": [
                        "lambda:AddPermission",
                        "lambda:CreateAlias",
                        "lambda:DeleteAlias",
                        "lambda:UpdateAlias",
                        "lambda:GetFunctionConfiguration",
                        "lambda:GetPolicy",
                        "lambda:RemovePermission",
                        "lambda:UpdateFunctionCode",
                        "lambda:UpdateFunctionConfiguration"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:lambda:*:*:function:*-mobilehub-*"
                    ]
                },
                {
                    "Action": [
                        "iam:CreateRole",
                        "iam:DeleteRole",
                        "iam:DeleteRolePolicy",
                        "iam:GetRole",
                        "iam:GetRolePolicy",
                        "iam:ListRolePolicies",
                        "iam:PassRole",
                        "iam:PutRolePolicy",
                        "iam:UpdateAssumeRolePolicy",
                        "iam:AttachRolePolicy",
                        "iam:DetachRolePolicy"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/*_unauth_MOBILEHUB_*",
                        "arn:aws:iam::*:role/*_auth_MOBILEHUB_*",
                        "arn:aws:iam::*:role/*_consolepush_MOBILEHUB_*",
                        "arn:aws:iam::*:role/*_lambdaexecutionrole_MOBILEHUB_*",
                        "arn:aws:iam::*:role/*_smsverification_MOBILEHUB_*",
                        "arn:aws:iam::*:role/*_botexecutionrole_MOBILEHUB_*",
                        "arn:aws:iam::*:role/pinpoint-events",
                        "arn:aws:iam::*:role/MOBILEHUB-*-lambdaexecution*",
                        "arn:aws:iam::*:role/MobileHub_Service_Role"
                    ]
                },
                {
                    "Action": [
                        "iam:CreateServiceLinkedRole",
                        "iam:GetRole"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/aws-service-role/lex.amazonaws.com/AWSServiceRoleForLexBots"
                    ]
                },
                {
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:log-group:/aws/mobilehub/*:log-stream:*"
                    ]
                },
                {
                    "Action": [
                        "iam:ListAttachedRolePolicies"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/MobileHub_Service_Role"
                    ]
                },
                {
                    "Action": [
                        "cloudformation:CreateStack",
                        "cloudformation:DeleteStack",
                        "cloudformation:DescribeStacks",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:DescribeStackResource",
                        "cloudformation:GetTemplate",
                        "cloudformation:ListStackResources",
                        "cloudformation:ListStacks",
                        "cloudformation:UpdateStack"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:cloudformation:*:*:stack/MOBILEHUB-*"
                    ]
                },
                {
                    "Action": [
                        "apigateway:DELETE",
                        "apigateway:GET",
                        "apigateway:HEAD",
                        "apigateway:OPTIONS",
                        "apigateway:PATCH",
                        "apigateway:POST",
                        "apigateway:PUT"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:apigateway:*::/restapis*"
                    ]
                },
                {
                    "Action": [
                        "cognito-idp:DeleteUserPool",
                        "cognito-idp:DescribeUserPool",
                        "cognito-idp:CreateUserPoolClient",
                        "cognito-idp:DescribeUserPoolClient",
                        "cognito-idp:DeleteUserPoolClient"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:cognito-idp:*:*:userpool/*"
                    ]
                },
                {
                    "Action": [
                        "mobiletargeting:UpdateApnsChannel",
                        "mobiletargeting:UpdateApnsSandboxChannel",
                        "mobiletargeting:UpdateEmailChannel",
                        "mobiletargeting:UpdateGcmChannel",
                        "mobiletargeting:UpdateSmsChannel",
                        "mobiletargeting:DeleteApnsChannel",
                        "mobiletargeting:DeleteApnsSandboxChannel",
                        "mobiletargeting:DeleteEmailChannel",
                        "mobiletargeting:DeleteGcmChannel",
                        "mobiletargeting:DeleteSmsChannel"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:mobiletargeting:*:*:apps/*/channels/*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIUHPQXBDZUWOP3PSK",
        "PolicyName": "AWSMobileHub_ServiceUseOnly",
        "UpdateDate": "2017-06-02T23:35:49+00:00",
        "VersionId": "v23"
    },
    "AWSOpsWorksCMInstanceProfileRole": {
        "Arn": "arn:aws:iam::aws:policy/AWSOpsWorksCMInstanceProfileRole",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-24T09:48:22+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:AbortMultipartUpload",
                        "s3:DeleteObject",
                        "s3:GetObject",
                        "s3:ListAllMyBuckets",
                        "s3:ListBucket",
                        "s3:ListMultipartUploadParts",
                        "s3:PutObject"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::aws-opsworks-cm-*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAICSU3OSHCURP2WIZW",
        "PolicyName": "AWSOpsWorksCMInstanceProfileRole",
        "UpdateDate": "2016-11-24T09:48:22+00:00",
        "VersionId": "v1"
    },
    "AWSOpsWorksCMServiceRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSOpsWorksCMServiceRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-04-03T12:00:07+00:00",
        "DefaultVersionId": "v6",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:CreateBucket",
                        "s3:DeleteObject",
                        "s3:DeleteBucket",
                        "s3:GetObject",
                        "s3:HeadBucket",
                        "s3:ListBucket",
                        "s3:ListObjects",
                        "s3:PutBucketPolicy"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::aws-opsworks-cm-*"
                    ]
                },
                {
                    "Action": [
                        "ssm:DescribeInstanceInformation",
                        "ssm:GetCommandInvocation",
                        "ssm:ListCommandInvocations",
                        "ssm:ListCommands"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "ssm:SendCommand"
                    ],
                    "Condition": {
                        "StringLike": {
                            "ssm:resourceTag/aws:cloudformation:stack-name": "aws-opsworks-cm-*"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "ssm:SendCommand"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:ssm:*::document/*",
                        "arn:aws:s3:::aws-opsworks-cm-*"
                    ]
                },
                {
                    "Action": [
                        "ec2:AllocateAddress",
                        "ec2:AssociateAddress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateImage",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateSnapshot",
                        "ec2:CreateTags",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DeleteSnapshot",
                        "ec2:DeregisterImage",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAddresses",
                        "ec2:DescribeImages",
                        "ec2:DescribeInstanceStatus",
                        "ec2:DescribeInstances",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSnapshots",
                        "ec2:DescribeSubnets",
                        "ec2:DisassociateAddress",
                        "ec2:ReleaseAddress",
                        "ec2:RunInstances",
                        "ec2:StopInstances"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "ec2:TerminateInstances"
                    ],
                    "Condition": {
                        "StringLike": {
                            "ec2:ResourceTag/aws:cloudformation:stack-name": "aws-opsworks-cm-*"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "cloudformation:CreateStack",
                        "cloudformation:DeleteStack",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:DescribeStackResources",
                        "cloudformation:DescribeStacks",
                        "cloudformation:UpdateStack"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:cloudformation:*:*:stack/aws-opsworks-cm-*"
                    ]
                },
                {
                    "Action": [
                        "iam:PassRole"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/aws-opsworks-cm-*",
                        "arn:aws:iam::*:role/service-role/aws-opsworks-cm-*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJ6I6MPGJE62URSHCO",
        "PolicyName": "AWSOpsWorksCMServiceRole",
        "UpdateDate": "2017-04-03T12:00:07+00:00",
        "VersionId": "v6"
    },
    "AWSOpsWorksCloudWatchLogs": {
        "Arn": "arn:aws:iam::aws:policy/AWSOpsWorksCloudWatchLogs",
        "AttachmentCount": 0,
        "CreateDate": "2017-03-30T17:47:19+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJXFIK7WABAY5CPXM4",
        "PolicyName": "AWSOpsWorksCloudWatchLogs",
        "UpdateDate": "2017-03-30T17:47:19+00:00",
        "VersionId": "v1"
    },
    "AWSOpsWorksFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSOpsWorksFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:48+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "opsworks:*",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "elasticloadbalancing:DescribeInstanceHealth",
                        "elasticloadbalancing:DescribeLoadBalancers",
                        "iam:GetRolePolicy",
                        "iam:ListInstanceProfiles",
                        "iam:ListRoles",
                        "iam:ListUsers",
                        "iam:PassRole"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAICN26VXMXASXKOQCG",
        "PolicyName": "AWSOpsWorksFullAccess",
        "UpdateDate": "2015-02-06T18:40:48+00:00",
        "VersionId": "v1"
    },
    "AWSOpsWorksInstanceRegistration": {
        "Arn": "arn:aws:iam::aws:policy/AWSOpsWorksInstanceRegistration",
        "AttachmentCount": 0,
        "CreateDate": "2016-06-03T14:23:15+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "opsworks:DescribeStackProvisioningParameters",
                        "opsworks:DescribeStacks",
                        "opsworks:RegisterInstance"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJG3LCPVNI4WDZCIMU",
        "PolicyName": "AWSOpsWorksInstanceRegistration",
        "UpdateDate": "2016-06-03T14:23:15+00:00",
        "VersionId": "v1"
    },
    "AWSOpsWorksRegisterCLI": {
        "Arn": "arn:aws:iam::aws:policy/AWSOpsWorksRegisterCLI",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:49+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "opsworks:AssignInstance",
                        "opsworks:CreateStack",
                        "opsworks:CreateLayer",
                        "opsworks:DeregisterInstance",
                        "opsworks:DescribeInstances",
                        "opsworks:DescribeStackProvisioningParameters",
                        "opsworks:DescribeStacks",
                        "opsworks:UnassignInstance"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "ec2:DescribeInstances"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "iam:AddUserToGroup",
                        "iam:CreateAccessKey",
                        "iam:CreateGroup",
                        "iam:CreateUser",
                        "iam:ListInstanceProfiles",
                        "iam:PassRole",
                        "iam:PutUserPolicy"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ3AB5ZBFPCQGTVDU4",
        "PolicyName": "AWSOpsWorksRegisterCLI",
        "UpdateDate": "2015-02-06T18:40:49+00:00",
        "VersionId": "v1"
    },
    "AWSOpsWorksRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSOpsWorksRole",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:27+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:GetMetricStatistics",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeInstances",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "elasticloadbalancing:DescribeInstanceHealth",
                        "elasticloadbalancing:DescribeLoadBalancers",
                        "iam:GetRolePolicy",
                        "iam:ListInstanceProfiles",
                        "iam:ListRoles",
                        "iam:ListUsers",
                        "iam:PassRole",
                        "opsworks:*",
                        "rds:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIDUTMOKHJFAPJV45W",
        "PolicyName": "AWSOpsWorksRole",
        "UpdateDate": "2015-02-06T18:41:27+00:00",
        "VersionId": "v1"
    },
    "AWSQuickSightDescribeRDS": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSQuickSightDescribeRDS",
        "AttachmentCount": 0,
        "CreateDate": "2015-11-10T23:24:50+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "rds:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJU5J6OAMCJD3OO76O",
        "PolicyName": "AWSQuickSightDescribeRDS",
        "UpdateDate": "2015-11-10T23:24:50+00:00",
        "VersionId": "v1"
    },
    "AWSQuickSightDescribeRedshift": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSQuickSightDescribeRedshift",
        "AttachmentCount": 0,
        "CreateDate": "2015-11-10T23:25:01+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "redshift:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJFEM6MLSLTW4ZNBW2",
        "PolicyName": "AWSQuickSightDescribeRedshift",
        "UpdateDate": "2015-11-10T23:25:01+00:00",
        "VersionId": "v1"
    },
    "AWSQuickSightListIAM": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSQuickSightListIAM",
        "AttachmentCount": 0,
        "CreateDate": "2015-11-10T23:25:07+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "iam:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAI3CH5UUWZN4EKGILO",
        "PolicyName": "AWSQuickSightListIAM",
        "UpdateDate": "2015-11-10T23:25:07+00:00",
        "VersionId": "v1"
    },
    "AWSQuicksightAthenaAccess": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AWSQuicksightAthenaAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-11T23:37:32+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "athena:BatchGetQueryExecution",
                        "athena:CancelQueryExecution",
                        "athena:GetCatalogs",
                        "athena:GetExecutionEngine",
                        "athena:GetExecutionEngines",
                        "athena:GetNamespace",
                        "athena:GetNamespaces",
                        "athena:GetQueryExecution",
                        "athena:GetQueryExecutions",
                        "athena:GetQueryResults",
                        "athena:GetTable",
                        "athena:GetTables",
                        "athena:ListQueryExecutions",
                        "athena:RunQuery",
                        "athena:StartQueryExecution",
                        "athena:StopQueryExecution"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "glue:CreateDatabase",
                        "glue:DeleteDatabase",
                        "glue:GetDatabase",
                        "glue:GetDatabases",
                        "glue:UpdateDatabase",
                        "glue:CreateTable",
                        "glue:DeleteTable",
                        "glue:BatchDeleteTable",
                        "glue:UpdateTable",
                        "glue:GetTable",
                        "glue:GetTables",
                        "glue:BatchCreatePartition",
                        "glue:CreatePartition",
                        "glue:DeletePartition",
                        "glue:BatchDeletePartition",
                        "glue:UpdatePartition",
                        "glue:GetPartition",
                        "glue:GetPartitions",
                        "glue:BatchGetPartition"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "s3:GetBucketLocation",
                        "s3:GetObject",
                        "s3:ListBucket",
                        "s3:ListBucketMultipartUploads",
                        "s3:ListMultipartUploadParts",
                        "s3:AbortMultipartUpload",
                        "s3:CreateBucket",
                        "s3:PutObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::aws-athena-query-results-*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAI4JB77JXFQXDWNRPM",
        "PolicyName": "AWSQuicksightAthenaAccess",
        "UpdateDate": "2017-08-11T23:37:32+00:00",
        "VersionId": "v3"
    },
    "AWSStepFunctionsConsoleFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSStepFunctionsConsoleFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-01-12T00:19:34+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": "states:*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "iam:ListRoles",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "iam:PassRole",
                    "Effect": "Allow",
                    "Resource": "arn:aws:iam::*:role/service-role/StatesExecutionRole*"
                },
                {
                    "Action": "lambda:ListFunctions",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJIYC52YWRX6OSMJWK",
        "PolicyName": "AWSStepFunctionsConsoleFullAccess",
        "UpdateDate": "2017-01-12T00:19:34+00:00",
        "VersionId": "v2"
    },
    "AWSStepFunctionsFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSStepFunctionsFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-01-11T21:51:32+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "states:*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJXKA6VP3UFBVHDPPA",
        "PolicyName": "AWSStepFunctionsFullAccess",
        "UpdateDate": "2017-01-11T21:51:32+00:00",
        "VersionId": "v1"
    },
    "AWSStepFunctionsReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSStepFunctionsReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-01-11T21:46:19+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "states:ListStateMachines",
                        "states:ListActivities",
                        "states:DescribeStateMachine",
                        "states:ListExecutions",
                        "states:DescribeExecution",
                        "states:GetExecutionHistory",
                        "states:DescribeActivity"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJONHB2TJQDJPFW5TM",
        "PolicyName": "AWSStepFunctionsReadOnlyAccess",
        "UpdateDate": "2017-01-11T21:46:19+00:00",
        "VersionId": "v1"
    },
    "AWSStorageGatewayFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSStorageGatewayFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:09+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "storagegateway:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "ec2:DescribeSnapshots",
                        "ec2:DeleteSnapshot"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJG5SSPAVOGK3SIDGU",
        "PolicyName": "AWSStorageGatewayFullAccess",
        "UpdateDate": "2015-02-06T18:41:09+00:00",
        "VersionId": "v1"
    },
    "AWSStorageGatewayReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSStorageGatewayReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:10+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "storagegateway:List*",
                        "storagegateway:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "ec2:DescribeSnapshots"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIFKCTUVOPD5NICXJK",
        "PolicyName": "AWSStorageGatewayReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:41:10+00:00",
        "VersionId": "v1"
    },
    "AWSSupportAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSSupportAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:11+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "support:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJSNKQX2OW67GF4S7E",
        "PolicyName": "AWSSupportAccess",
        "UpdateDate": "2015-02-06T18:41:11+00:00",
        "VersionId": "v1"
    },
    "AWSWAFFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSWAFFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-07T21:33:25+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "waf:*",
                        "waf-regional:*",
                        "elasticloadbalancing:SetWebACL"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJMIKIAFXZEGOLRH7C",
        "PolicyName": "AWSWAFFullAccess",
        "UpdateDate": "2016-12-07T21:33:25+00:00",
        "VersionId": "v2"
    },
    "AWSWAFReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSWAFReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-07T21:30:54+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "waf:Get*",
                        "waf:List*",
                        "waf-regional:Get*",
                        "waf-regional:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAINZVDMX2SBF7EU2OC",
        "PolicyName": "AWSWAFReadOnlyAccess",
        "UpdateDate": "2016-12-07T21:30:54+00:00",
        "VersionId": "v2"
    },
    "AWSXrayFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSXrayFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-01T18:30:55+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "xray:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJQBYG45NSJMVQDB2K",
        "PolicyName": "AWSXrayFullAccess",
        "UpdateDate": "2016-12-01T18:30:55+00:00",
        "VersionId": "v1"
    },
    "AWSXrayReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSXrayReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-01T18:27:02+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "xray:BatchGetTraces",
                        "xray:GetServiceGraph",
                        "xray:GetTraceGraph",
                        "xray:GetTraceSummaries"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIH4OFXWPS6ZX6OPGQ",
        "PolicyName": "AWSXrayReadOnlyAccess",
        "UpdateDate": "2016-12-01T18:27:02+00:00",
        "VersionId": "v1"
    },
    "AWSXrayWriteOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-01T18:19:53+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIAACM4LMYSRGBCTM6",
        "PolicyName": "AWSXrayWriteOnlyAccess",
        "UpdateDate": "2016-12-01T18:19:53+00:00",
        "VersionId": "v1"
    },
    "AdministratorAccess": {
        "Arn": "arn:aws:iam::aws:policy/AdministratorAccess",
        "AttachmentCount": 3,
        "CreateDate": "2015-02-06T18:39:46+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIWMBCKSKIEE64ZLYK",
        "PolicyName": "AdministratorAccess",
        "UpdateDate": "2015-02-06T18:39:46+00:00",
        "VersionId": "v1"
    },
    "AmazonAPIGatewayAdministrator": {
        "Arn": "arn:aws:iam::aws:policy/AmazonAPIGatewayAdministrator",
        "AttachmentCount": 0,
        "CreateDate": "2015-07-09T17:34:45+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "apigateway:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:apigateway:*::/*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ4PT6VY5NLKTNUYSI",
        "PolicyName": "AmazonAPIGatewayAdministrator",
        "UpdateDate": "2015-07-09T17:34:45+00:00",
        "VersionId": "v1"
    },
    "AmazonAPIGatewayInvokeFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonAPIGatewayInvokeFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-07-09T17:36:12+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "execute-api:Invoke"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:execute-api:*:*:*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIIWAX2NOOQJ4AIEQ6",
        "PolicyName": "AmazonAPIGatewayInvokeFullAccess",
        "UpdateDate": "2015-07-09T17:36:12+00:00",
        "VersionId": "v1"
    },
    "AmazonAPIGatewayPushToCloudWatchLogs": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs",
        "AttachmentCount": 0,
        "CreateDate": "2015-11-11T23:41:46+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams",
                        "logs:PutLogEvents",
                        "logs:GetLogEvents",
                        "logs:FilterLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIK4GFO7HLKYN64ASK",
        "PolicyName": "AmazonAPIGatewayPushToCloudWatchLogs",
        "UpdateDate": "2015-11-11T23:41:46+00:00",
        "VersionId": "v1"
    },
    "AmazonAppStreamFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonAppStreamFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-07T23:56:23+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "appstream:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "application-autoscaling:DeleteScalingPolicy",
                        "application-autoscaling:DescribeScalableTargets",
                        "application-autoscaling:DescribeScalingPolicies",
                        "application-autoscaling:PutScalingPolicy",
                        "application-autoscaling:RegisterScalableTarget"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "cloudwatch:DeleteAlarms",
                        "cloudwatch:DescribeAlarms",
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:PutMetricAlarm"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "iam:ListRoles",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "iam:PassRole",
                    "Condition": {
                        "StringLike": {
                            "iam:PassedToService": "application-autoscaling.amazonaws.com"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": "arn:aws:iam::*:role/service-role/ApplicationAutoScalingForAmazonAppStreamAccess"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJLZZXU2YQVGL4QDNC",
        "PolicyName": "AmazonAppStreamFullAccess",
        "UpdateDate": "2017-09-07T23:56:23+00:00",
        "VersionId": "v2"
    },
    "AmazonAppStreamReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonAppStreamReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-07T21:00:06+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "appstream:Get*",
                        "appstream:List*",
                        "appstream:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJXIFDGB4VBX23DX7K",
        "PolicyName": "AmazonAppStreamReadOnlyAccess",
        "UpdateDate": "2016-12-07T21:00:06+00:00",
        "VersionId": "v2"
    },
    "AmazonAppStreamServiceAccess": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonAppStreamServiceAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-05-23T23:00:47+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeVpcs",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:CreateNetworkInterface",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DescribeSubnets",
                        "ec2:AssociateAddress",
                        "ec2:DisassociateAddress",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSecurityGroups"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "s3:CreateBucket",
                        "s3:ListBucket",
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:GetObjectVersion",
                        "s3:DeleteObjectVersion",
                        "s3:PutBucketPolicy"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::appstream2-36fb080bb8-*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAISBRZ7LMMCBYEF3SE",
        "PolicyName": "AmazonAppStreamServiceAccess",
        "UpdateDate": "2017-05-23T23:00:47+00:00",
        "VersionId": "v3"
    },
    "AmazonAthenaFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonAthenaFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-13T00:13:48+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "athena:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "glue:CreateDatabase",
                        "glue:DeleteDatabase",
                        "glue:GetDatabase",
                        "glue:GetDatabases",
                        "glue:UpdateDatabase",
                        "glue:CreateTable",
                        "glue:DeleteTable",
                        "glue:BatchDeleteTable",
                        "glue:UpdateTable",
                        "glue:GetTable",
                        "glue:GetTables",
                        "glue:BatchCreatePartition",
                        "glue:CreatePartition",
                        "glue:DeletePartition",
                        "glue:BatchDeletePartition",
                        "glue:UpdatePartition",
                        "glue:GetPartition",
                        "glue:GetPartitions",
                        "glue:BatchGetPartition"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "s3:GetBucketLocation",
                        "s3:GetObject",
                        "s3:ListBucket",
                        "s3:ListBucketMultipartUploads",
                        "s3:ListMultipartUploadParts",
                        "s3:AbortMultipartUpload",
                        "s3:CreateBucket",
                        "s3:PutObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::aws-athena-query-results-*"
                    ]
                },
                {
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::athena-examples*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIPJMLMD4C7RYZ6XCK",
        "PolicyName": "AmazonAthenaFullAccess",
        "UpdateDate": "2017-09-13T00:13:48+00:00",
        "VersionId": "v3"
    },
    "AmazonCloudDirectoryFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonCloudDirectoryFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-02-25T00:41:39+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "clouddirectory:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJG3XQK77ATFLCF2CK",
        "PolicyName": "AmazonCloudDirectoryFullAccess",
        "UpdateDate": "2017-02-25T00:41:39+00:00",
        "VersionId": "v1"
    },
    "AmazonCloudDirectoryReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonCloudDirectoryReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-02-28T23:42:06+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "clouddirectory:List*",
                        "clouddirectory:Get*",
                        "clouddirectory:LookupPolicy",
                        "clouddirectory:BatchRead"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAICMSZQGR3O62KMD6M",
        "PolicyName": "AmazonCloudDirectoryReadOnlyAccess",
        "UpdateDate": "2017-02-28T23:42:06+00:00",
        "VersionId": "v1"
    },
    "AmazonCognitoDeveloperAuthenticatedIdentities": {
        "Arn": "arn:aws:iam::aws:policy/AmazonCognitoDeveloperAuthenticatedIdentities",
        "AttachmentCount": 0,
        "CreateDate": "2015-03-24T17:22:23+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cognito-identity:GetOpenIdTokenForDeveloperIdentity",
                        "cognito-identity:LookupDeveloperIdentity",
                        "cognito-identity:MergeDeveloperIdentities",
                        "cognito-identity:UnlinkDeveloperIdentity"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIQOKZ5BGKLCMTXH4W",
        "PolicyName": "AmazonCognitoDeveloperAuthenticatedIdentities",
        "UpdateDate": "2015-03-24T17:22:23+00:00",
        "VersionId": "v1"
    },
    "AmazonCognitoPowerUser": {
        "Arn": "arn:aws:iam::aws:policy/AmazonCognitoPowerUser",
        "AttachmentCount": 0,
        "CreateDate": "2016-06-02T16:57:56+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cognito-identity:*",
                        "cognito-idp:*",
                        "cognito-sync:*",
                        "iam:ListRoles",
                        "iam:ListOpenIdConnectProviders",
                        "sns:ListPlatformApplications"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJKW5H2HNCPGCYGR6Y",
        "PolicyName": "AmazonCognitoPowerUser",
        "UpdateDate": "2016-06-02T16:57:56+00:00",
        "VersionId": "v2"
    },
    "AmazonCognitoReadOnly": {
        "Arn": "arn:aws:iam::aws:policy/AmazonCognitoReadOnly",
        "AttachmentCount": 0,
        "CreateDate": "2016-06-02T17:30:24+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cognito-identity:Describe*",
                        "cognito-identity:Get*",
                        "cognito-identity:List*",
                        "cognito-idp:Describe*",
                        "cognito-idp:AdminGetUser",
                        "cognito-idp:List*",
                        "cognito-sync:Describe*",
                        "cognito-sync:Get*",
                        "cognito-sync:List*",
                        "iam:ListOpenIdConnectProviders",
                        "iam:ListRoles",
                        "sns:ListPlatformApplications"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJBFTRZD2GQGJHSVQK",
        "PolicyName": "AmazonCognitoReadOnly",
        "UpdateDate": "2016-06-02T17:30:24+00:00",
        "VersionId": "v2"
    },
    "AmazonDMSCloudWatchLogsRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonDMSCloudWatchLogsRole",
        "AttachmentCount": 0,
        "CreateDate": "2016-01-07T23:44:53+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "logs:DescribeLogGroups"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ],
                    "Sid": "AllowDescribeOnAllLogGroups"
                },
                {
                    "Action": [
                        "logs:DescribeLogStreams"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:log-group:dms-tasks-*"
                    ],
                    "Sid": "AllowDescribeOfAllLogStreamsOnDmsTasksLogGroup"
                },
                {
                    "Action": [
                        "logs:CreateLogGroup"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:log-group:dms-tasks-*"
                    ],
                    "Sid": "AllowCreationOfDmsTasksLogGroups"
                },
                {
                    "Action": [
                        "logs:CreateLogStream"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:log-group:dms-tasks-*:log-stream:dms-task-*"
                    ],
                    "Sid": "AllowCreationOfDmsTaskLogStream"
                },
                {
                    "Action": [
                        "logs:PutLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:log-group:dms-tasks-*:log-stream:dms-task-*"
                    ],
                    "Sid": "AllowUploadOfLogEventsToDmsTaskLogStream"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJBG7UXZZXUJD3TDJE",
        "PolicyName": "AmazonDMSCloudWatchLogsRole",
        "UpdateDate": "2016-01-07T23:44:53+00:00",
        "VersionId": "v1"
    },
    "AmazonDMSRedshiftS3Role": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonDMSRedshiftS3Role",
        "AttachmentCount": 0,
        "CreateDate": "2016-04-20T17:05:56+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:CreateBucket",
                        "s3:ListBucket",
                        "s3:DeleteBucket",
                        "s3:GetBucketLocation",
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:GetObjectVersion",
                        "s3:GetBucketPolicy",
                        "s3:PutBucketPolicy",
                        "s3:DeleteBucketPolicy"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::dms-*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAI3CCUQ4U5WNC5F6B6",
        "PolicyName": "AmazonDMSRedshiftS3Role",
        "UpdateDate": "2016-04-20T17:05:56+00:00",
        "VersionId": "v1"
    },
    "AmazonDMSVPCManagementRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonDMSVPCManagementRole",
        "AttachmentCount": 0,
        "CreateDate": "2016-05-23T16:29:57+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:CreateNetworkInterface",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:DeleteNetworkInterface",
                        "ec2:ModifyNetworkInterfaceAttribute"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJHKIGMBQI4AEFFSYO",
        "PolicyName": "AmazonDMSVPCManagementRole",
        "UpdateDate": "2016-05-23T16:29:57+00:00",
        "VersionId": "v3"
    },
    "AmazonDRSVPCManagement": {
        "Arn": "arn:aws:iam::aws:policy/AmazonDRSVPCManagement",
        "AttachmentCount": 0,
        "CreateDate": "2015-09-02T00:09:20+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateNetworkInterface",
                        "ec2:CreateSecurityGroup",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcAttribute",
                        "ec2:DescribeVpcs",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DeleteSecurityGroup",
                        "ec2:ModifyNetworkInterfaceAttribute",
                        "ec2:RevokeSecurityGroupIngress"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJPXIBTTZMBEFEX6UA",
        "PolicyName": "AmazonDRSVPCManagement",
        "UpdateDate": "2015-09-02T00:09:20+00:00",
        "VersionId": "v1"
    },
    "AmazonDynamoDBFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-06-28T23:23:34+00:00",
        "DefaultVersionId": "v5",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "dynamodb:*",
                        "dax:*",
                        "application-autoscaling:DeleteScalingPolicy",
                        "application-autoscaling:DeregisterScalableTarget",
                        "application-autoscaling:DescribeScalableTargets",
                        "application-autoscaling:DescribeScalingActivities",
                        "application-autoscaling:DescribeScalingPolicies",
                        "application-autoscaling:PutScalingPolicy",
                        "application-autoscaling:RegisterScalableTarget",
                        "cloudwatch:DeleteAlarms",
                        "cloudwatch:DescribeAlarmHistory",
                        "cloudwatch:DescribeAlarms",
                        "cloudwatch:DescribeAlarmsForMetric",
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:ListMetrics",
                        "cloudwatch:PutMetricAlarm",
                        "datapipeline:ActivatePipeline",
                        "datapipeline:CreatePipeline",
                        "datapipeline:DeletePipeline",
                        "datapipeline:DescribeObjects",
                        "datapipeline:DescribePipelines",
                        "datapipeline:GetPipelineDefinition",
                        "datapipeline:ListPipelines",
                        "datapipeline:PutPipelineDefinition",
                        "datapipeline:QueryObjects",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeSecurityGroups",
                        "iam:GetRole",
                        "iam:ListRoles",
                        "sns:CreateTopic",
                        "sns:DeleteTopic",
                        "sns:ListSubscriptions",
                        "sns:ListSubscriptionsByTopic",
                        "sns:ListTopics",
                        "sns:Subscribe",
                        "sns:Unsubscribe",
                        "sns:SetTopicAttributes",
                        "lambda:CreateFunction",
                        "lambda:ListFunctions",
                        "lambda:ListEventSourceMappings",
                        "lambda:CreateEventSourceMapping",
                        "lambda:DeleteEventSourceMapping",
                        "lambda:GetFunctionConfiguration",
                        "lambda:DeleteFunction"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "iam:PassRole"
                    ],
                    "Condition": {
                        "StringLike": {
                            "iam:PassedToService": [
                                "application-autoscaling.amazonaws.com",
                                "dax.amazonaws.com"
                            ]
                        }
                    },
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAINUGF2JSOSUY76KYA",
        "PolicyName": "AmazonDynamoDBFullAccess",
        "UpdateDate": "2017-06-28T23:23:34+00:00",
        "VersionId": "v5"
    },
    "AmazonDynamoDBFullAccesswithDataPipeline": {
        "Arn": "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccesswithDataPipeline",
        "AttachmentCount": 0,
        "CreateDate": "2015-11-12T02:17:42+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:DeleteAlarms",
                        "cloudwatch:DescribeAlarmHistory",
                        "cloudwatch:DescribeAlarms",
                        "cloudwatch:DescribeAlarmsForMetric",
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:ListMetrics",
                        "cloudwatch:PutMetricAlarm",
                        "dynamodb:*",
                        "sns:CreateTopic",
                        "sns:DeleteTopic",
                        "sns:ListSubscriptions",
                        "sns:ListSubscriptionsByTopic",
                        "sns:ListTopics",
                        "sns:Subscribe",
                        "sns:Unsubscribe",
                        "sns:SetTopicAttributes"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "DDBConsole"
                },
                {
                    "Action": [
                        "lambda:*",
                        "iam:ListRoles"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "DDBConsoleTriggers"
                },
                {
                    "Action": [
                        "datapipeline:*",
                        "iam:ListRoles"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "DDBConsoleImportExport"
                },
                {
                    "Action": [
                        "iam:GetRolePolicy",
                        "iam:PassRole"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ],
                    "Sid": "IAMEDPRoles"
                },
                {
                    "Action": [
                        "ec2:CreateTags",
                        "ec2:DescribeInstances",
                        "ec2:RunInstances",
                        "ec2:StartInstances",
                        "ec2:StopInstances",
                        "ec2:TerminateInstances",
                        "elasticmapreduce:*",
                        "datapipeline:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "EMR"
                },
                {
                    "Action": [
                        "s3:DeleteObject",
                        "s3:Get*",
                        "s3:List*",
                        "s3:Put*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ],
                    "Sid": "S3"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ3ORT7KDISSXGHJXA",
        "PolicyName": "AmazonDynamoDBFullAccesswithDataPipeline",
        "UpdateDate": "2015-11-12T02:17:42+00:00",
        "VersionId": "v2"
    },
    "AmazonDynamoDBReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonDynamoDBReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-06-12T21:11:40+00:00",
        "DefaultVersionId": "v5",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "application-autoscaling:DescribeScalableTargets",
                        "application-autoscaling:DescribeScalingActivities",
                        "application-autoscaling:DescribeScalingPolicies",
                        "cloudwatch:DescribeAlarmHistory",
                        "cloudwatch:DescribeAlarms",
                        "cloudwatch:DescribeAlarmsForMetric",
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:ListMetrics",
                        "datapipeline:DescribeObjects",
                        "datapipeline:DescribePipelines",
                        "datapipeline:GetPipelineDefinition",
                        "datapipeline:ListPipelines",
                        "datapipeline:QueryObjects",
                        "dynamodb:BatchGetItem",
                        "dynamodb:DescribeTable",
                        "dynamodb:GetItem",
                        "dynamodb:ListTables",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:DescribeReservedCapacity",
                        "dynamodb:DescribeReservedCapacityOfferings",
                        "dynamodb:ListTagsOfResource",
                        "dynamodb:DescribeTimeToLive",
                        "dynamodb:DescribeLimits",
                        "iam:GetRole",
                        "iam:ListRoles",
                        "sns:ListSubscriptionsByTopic",
                        "sns:ListTopics",
                        "lambda:ListFunctions",
                        "lambda:ListEventSourceMappings",
                        "lambda:GetFunctionConfiguration"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIY2XFNA232XJ6J7X2",
        "PolicyName": "AmazonDynamoDBReadOnlyAccess",
        "UpdateDate": "2017-06-12T21:11:40+00:00",
        "VersionId": "v5"
    },
    "AmazonEC2ContainerRegistryFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-12-21T17:06:48+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ecr:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIESRL7KD7IIVF6V4W",
        "PolicyName": "AmazonEC2ContainerRegistryFullAccess",
        "UpdateDate": "2015-12-21T17:06:48+00:00",
        "VersionId": "v1"
    },
    "AmazonEC2ContainerRegistryPowerUser": {
        "Arn": "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser",
        "AttachmentCount": 0,
        "CreateDate": "2016-10-11T22:28:07+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:GetRepositoryPolicy",
                        "ecr:DescribeRepositories",
                        "ecr:ListImages",
                        "ecr:DescribeImages",
                        "ecr:BatchGetImage",
                        "ecr:InitiateLayerUpload",
                        "ecr:UploadLayerPart",
                        "ecr:CompleteLayerUpload",
                        "ecr:PutImage"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJDNE5PIHROIBGGDDW",
        "PolicyName": "AmazonEC2ContainerRegistryPowerUser",
        "UpdateDate": "2016-10-11T22:28:07+00:00",
        "VersionId": "v2"
    },
    "AmazonEC2ContainerRegistryReadOnly": {
        "Arn": "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
        "AttachmentCount": 0,
        "CreateDate": "2016-10-11T22:08:43+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:GetRepositoryPolicy",
                        "ecr:DescribeRepositories",
                        "ecr:ListImages",
                        "ecr:DescribeImages",
                        "ecr:BatchGetImage"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIFYZPA37OOHVIH7KQ",
        "PolicyName": "AmazonEC2ContainerRegistryReadOnly",
        "UpdateDate": "2016-10-11T22:08:43+00:00",
        "VersionId": "v2"
    },
    "AmazonEC2ContainerServiceAutoscaleRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceAutoscaleRole",
        "AttachmentCount": 1,
        "CreateDate": "2016-05-12T23:25:44+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ecs:DescribeServices",
                        "ecs:UpdateService"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "cloudwatch:DescribeAlarms"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIUAP3EGGGXXCPDQKK",
        "PolicyName": "AmazonEC2ContainerServiceAutoscaleRole",
        "UpdateDate": "2016-05-12T23:25:44+00:00",
        "VersionId": "v1"
    },
    "AmazonEC2ContainerServiceEventsRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceEventsRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-05-30T16:51:35+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ecs:RunTask"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAITKFNIUAG27VSYNZ4",
        "PolicyName": "AmazonEC2ContainerServiceEventsRole",
        "UpdateDate": "2017-05-30T16:51:35+00:00",
        "VersionId": "v1"
    },
    "AmazonEC2ContainerServiceFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonEC2ContainerServiceFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-06-08T00:18:56+00:00",
        "DefaultVersionId": "v4",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "autoscaling:Describe*",
                        "autoscaling:UpdateAutoScalingGroup",
                        "cloudformation:CreateStack",
                        "cloudformation:DeleteStack",
                        "cloudformation:DescribeStack*",
                        "cloudformation:UpdateStack",
                        "cloudwatch:GetMetricStatistics",
                        "ec2:Describe*",
                        "elasticloadbalancing:*",
                        "ecs:*",
                        "events:DescribeRule",
                        "events:DeleteRule",
                        "events:ListRuleNamesByTarget",
                        "events:ListTargetsByRule",
                        "events:PutRule",
                        "events:PutTargets",
                        "events:RemoveTargets",
                        "iam:ListInstanceProfiles",
                        "iam:ListRoles",
                        "iam:PassRole"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJALOYVTPDZEMIACSM",
        "PolicyName": "AmazonEC2ContainerServiceFullAccess",
        "UpdateDate": "2017-06-08T00:18:56+00:00",
        "VersionId": "v4"
    },
    "AmazonEC2ContainerServiceRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceRole",
        "AttachmentCount": 1,
        "CreateDate": "2016-08-11T13:08:01+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:Describe*",
                        "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
                        "elasticloadbalancing:DeregisterTargets",
                        "elasticloadbalancing:Describe*",
                        "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
                        "elasticloadbalancing:RegisterTargets"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJO53W2XHNACG7V77Q",
        "PolicyName": "AmazonEC2ContainerServiceRole",
        "UpdateDate": "2016-08-11T13:08:01+00:00",
        "VersionId": "v2"
    },
    "AmazonEC2ContainerServiceforEC2Role": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role",
        "AttachmentCount": 1,
        "CreateDate": "2017-05-17T23:09:13+00:00",
        "DefaultVersionId": "v5",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ecs:CreateCluster",
                        "ecs:DeregisterContainerInstance",
                        "ecs:DiscoverPollEndpoint",
                        "ecs:Poll",
                        "ecs:RegisterContainerInstance",
                        "ecs:StartTelemetrySession",
                        "ecs:UpdateContainerInstancesState",
                        "ecs:Submit*",
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJLYJCVHC7TQHCSQDS",
        "PolicyName": "AmazonEC2ContainerServiceforEC2Role",
        "UpdateDate": "2017-05-17T23:09:13+00:00",
        "VersionId": "v5"
    },
    "AmazonEC2FullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonEC2FullAccess",
        "AttachmentCount": 1,
        "CreateDate": "2015-02-06T18:40:15+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "ec2:*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "elasticloadbalancing:*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "cloudwatch:*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "autoscaling:*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI3VAJF5ZCRZ7MCQE6",
        "PolicyName": "AmazonEC2FullAccess",
        "UpdateDate": "2015-02-06T18:40:15+00:00",
        "VersionId": "v1"
    },
    "AmazonEC2ReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:17+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "ec2:Describe*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "elasticloadbalancing:Describe*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "cloudwatch:ListMetrics",
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "autoscaling:Describe*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIGDT4SV4GSETWTBZK",
        "PolicyName": "AmazonEC2ReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:17+00:00",
        "VersionId": "v1"
    },
    "AmazonEC2ReportsAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonEC2ReportsAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:16+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "ec2-reports:*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIU6NBZVF2PCRW36ZW",
        "PolicyName": "AmazonEC2ReportsAccess",
        "UpdateDate": "2015-02-06T18:40:16+00:00",
        "VersionId": "v1"
    },
    "AmazonEC2RoleforAWSCodeDeploy": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforAWSCodeDeploy",
        "AttachmentCount": 0,
        "CreateDate": "2017-03-20T17:14:10+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:GetObject",
                        "s3:GetObjectVersion",
                        "s3:ListBucket"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIAZKXZ27TAJ4PVWGK",
        "PolicyName": "AmazonEC2RoleforAWSCodeDeploy",
        "UpdateDate": "2017-03-20T17:14:10+00:00",
        "VersionId": "v2"
    },
    "AmazonEC2RoleforDataPipelineRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforDataPipelineRole",
        "AttachmentCount": 0,
        "CreateDate": "2016-02-22T17:24:05+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:*",
                        "datapipeline:*",
                        "dynamodb:*",
                        "ec2:Describe*",
                        "elasticmapreduce:AddJobFlowSteps",
                        "elasticmapreduce:Describe*",
                        "elasticmapreduce:ListInstance*",
                        "elasticmapreduce:ModifyInstanceGroups",
                        "rds:Describe*",
                        "redshift:DescribeClusters",
                        "redshift:DescribeClusterSecurityGroups",
                        "s3:*",
                        "sdb:*",
                        "sns:*",
                        "sqs:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJ3Z5I2WAJE5DN2J36",
        "PolicyName": "AmazonEC2RoleforDataPipelineRole",
        "UpdateDate": "2016-02-22T17:24:05+00:00",
        "VersionId": "v3"
    },
    "AmazonEC2RoleforSSM": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-10T20:49:08+00:00",
        "DefaultVersionId": "v4",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ssm:DescribeAssociation",
                        "ssm:GetDeployablePatchSnapshotForInstance",
                        "ssm:GetDocument",
                        "ssm:GetParameters",
                        "ssm:ListAssociations",
                        "ssm:ListInstanceAssociations",
                        "ssm:PutInventory",
                        "ssm:PutComplianceItems",
                        "ssm:UpdateAssociationStatus",
                        "ssm:UpdateInstanceAssociationStatus",
                        "ssm:UpdateInstanceInformation"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "ec2messages:AcknowledgeMessage",
                        "ec2messages:DeleteMessage",
                        "ec2messages:FailMessage",
                        "ec2messages:GetEndpoint",
                        "ec2messages:GetMessages",
                        "ec2messages:SendReply"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "cloudwatch:PutMetricData"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "ec2:DescribeInstanceStatus"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "ds:CreateComputer",
                        "ds:DescribeDirectories"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams",
                        "logs:PutLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "s3:PutObject",
                        "s3:GetObject",
                        "s3:AbortMultipartUpload",
                        "s3:ListMultipartUploadParts",
                        "s3:ListBucketMultipartUploads"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "s3:ListBucket"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::amazon-ssm-packages-*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAI6TL3SMY22S4KMMX6",
        "PolicyName": "AmazonEC2RoleforSSM",
        "UpdateDate": "2017-08-10T20:49:08+00:00",
        "VersionId": "v4"
    },
    "AmazonEC2SpotFleetAutoscaleRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetAutoscaleRole",
        "AttachmentCount": 0,
        "CreateDate": "2016-08-19T18:27:22+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeSpotFleetRequests",
                        "ec2:ModifySpotFleetRequest"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "cloudwatch:DescribeAlarms"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIMFFRMIOBGDP2TAVE",
        "PolicyName": "AmazonEC2SpotFleetAutoscaleRole",
        "UpdateDate": "2016-08-19T18:27:22+00:00",
        "VersionId": "v1"
    },
    "AmazonEC2SpotFleetRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetRole",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-10T21:19:35+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeImages",
                        "ec2:DescribeSubnets",
                        "ec2:RequestSpotInstances",
                        "ec2:TerminateInstances",
                        "ec2:DescribeInstanceStatus",
                        "iam:PassRole"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIMRTKHWK7ESSNETSW",
        "PolicyName": "AmazonEC2SpotFleetRole",
        "UpdateDate": "2016-11-10T21:19:35+00:00",
        "VersionId": "v3"
    },
    "AmazonEC2SpotFleetTaggingRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-07-26T19:10:35+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeImages",
                        "ec2:DescribeSubnets",
                        "ec2:RequestSpotInstances",
                        "ec2:TerminateInstances",
                        "ec2:DescribeInstanceStatus",
                        "ec2:CreateTags"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": "iam:PassRole",
                    "Condition": {
                        "StringEquals": {
                            "iam:PassedToService": "ec2.amazonaws.com"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJ5U6UMLCEYLX5OLC4",
        "PolicyName": "AmazonEC2SpotFleetTaggingRole",
        "UpdateDate": "2017-07-26T19:10:35+00:00",
        "VersionId": "v2"
    },
    "AmazonESFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonESFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-10-01T19:14:00+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "es:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJM6ZTCU24QL5PZCGC",
        "PolicyName": "AmazonESFullAccess",
        "UpdateDate": "2015-10-01T19:14:00+00:00",
        "VersionId": "v1"
    },
    "AmazonESReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonESReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-10-01T19:18:24+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "es:Describe*",
                        "es:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJUDMRLOQ7FPAR46FQ",
        "PolicyName": "AmazonESReadOnlyAccess",
        "UpdateDate": "2015-10-01T19:18:24+00:00",
        "VersionId": "v1"
    },
    "AmazonElastiCacheFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonElastiCacheFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:20+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "elasticache:*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIA2V44CPHAUAAECKG",
        "PolicyName": "AmazonElastiCacheFullAccess",
        "UpdateDate": "2015-02-06T18:40:20+00:00",
        "VersionId": "v1"
    },
    "AmazonElastiCacheReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonElastiCacheReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:21+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "elasticache:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIPDACSNQHSENWAKM2",
        "PolicyName": "AmazonElastiCacheReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:21+00:00",
        "VersionId": "v1"
    },
    "AmazonElasticFileSystemFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonElasticFileSystemFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-14T10:18:34+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:CreateNetworkInterface",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeNetworkInterfaceAttribute",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcAttribute",
                        "ec2:DescribeVpcs",
                        "ec2:ModifyNetworkInterfaceAttribute",
                        "elasticfilesystem:*",
                        "kms:DescribeKey",
                        "kms:ListAliases"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJKXTMNVQGIDNCKPBC",
        "PolicyName": "AmazonElasticFileSystemFullAccess",
        "UpdateDate": "2017-08-14T10:18:34+00:00",
        "VersionId": "v3"
    },
    "AmazonElasticFileSystemReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonElasticFileSystemReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-14T10:09:49+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeNetworkInterfaceAttribute",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcAttribute",
                        "ec2:DescribeVpcs",
                        "elasticfilesystem:Describe*",
                        "kms:ListAliases"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIPN5S4NE5JJOKVC4Y",
        "PolicyName": "AmazonElasticFileSystemReadOnlyAccess",
        "UpdateDate": "2017-08-14T10:09:49+00:00",
        "VersionId": "v3"
    },
    "AmazonElasticMapReduceFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonElasticMapReduceFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-20T19:27:37+00:00",
        "DefaultVersionId": "v5",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:*",
                        "cloudformation:CreateStack",
                        "cloudformation:DescribeStackEvents",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:CancelSpotInstanceRequests",
                        "ec2:CreateRoute",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateTags",
                        "ec2:DeleteRoute",
                        "ec2:DeleteTags",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeInstances",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSpotInstanceRequests",
                        "ec2:DescribeSpotPriceHistory",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcAttribute",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeNetworkAcls",
                        "ec2:CreateVpcEndpoint",
                        "ec2:ModifyImageAttribute",
                        "ec2:ModifyInstanceAttribute",
                        "ec2:RequestSpotInstances",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:RunInstances",
                        "ec2:TerminateInstances",
                        "elasticmapreduce:*",
                        "iam:GetPolicy",
                        "iam:GetPolicyVersion",
                        "iam:ListRoles",
                        "iam:PassRole",
                        "kms:List*",
                        "s3:*",
                        "sdb:*",
                        "support:CreateCase",
                        "support:DescribeServices",
                        "support:DescribeSeverityLevels"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "iam:CreateServiceLinkedRole",
                    "Condition": {
                        "StringLike": {
                            "iam:AWSServiceName": "elasticmapreduce.amazonaws.com"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": "arn:aws:iam::*:role/aws-service-role/elasticmapreduce.amazonaws.com/AWSServiceRoleForEMRCleanup"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIZP5JFP3AMSGINBB2",
        "PolicyName": "AmazonElasticMapReduceFullAccess",
        "UpdateDate": "2017-09-20T19:27:37+00:00",
        "VersionId": "v5"
    },
    "AmazonElasticMapReduceReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonElasticMapReduceReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-05-22T23:00:19+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "elasticmapreduce:Describe*",
                        "elasticmapreduce:List*",
                        "elasticmapreduce:ViewEventsFromAllClustersInConsole",
                        "s3:GetObject",
                        "s3:ListAllMyBuckets",
                        "s3:ListBucket",
                        "sdb:Select",
                        "cloudwatch:GetMetricStatistics"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIHP6NH2S6GYFCOINC",
        "PolicyName": "AmazonElasticMapReduceReadOnlyAccess",
        "UpdateDate": "2017-05-22T23:00:19+00:00",
        "VersionId": "v2"
    },
    "AmazonElasticMapReduceRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-07-17T21:29:50+00:00",
        "DefaultVersionId": "v8",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CancelSpotInstanceRequests",
                        "ec2:CreateNetworkInterface",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateTags",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DeleteTags",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeDhcpOptions",
                        "ec2:DescribeImages",
                        "ec2:DescribeInstanceStatus",
                        "ec2:DescribeInstances",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeNetworkAcls",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribePrefixLists",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSpotInstanceRequests",
                        "ec2:DescribeSpotPriceHistory",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeTags",
                        "ec2:DescribeVpcAttribute",
                        "ec2:DescribeVpcEndpoints",
                        "ec2:DescribeVpcEndpointServices",
                        "ec2:DescribeVpcs",
                        "ec2:DetachNetworkInterface",
                        "ec2:ModifyImageAttribute",
                        "ec2:ModifyInstanceAttribute",
                        "ec2:RequestSpotInstances",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:RunInstances",
                        "ec2:TerminateInstances",
                        "ec2:DeleteVolume",
                        "ec2:DescribeVolumeStatus",
                        "ec2:DescribeVolumes",
                        "ec2:DetachVolume",
                        "iam:GetRole",
                        "iam:GetRolePolicy",
                        "iam:ListInstanceProfiles",
                        "iam:ListRolePolicies",
                        "iam:PassRole",
                        "s3:CreateBucket",
                        "s3:Get*",
                        "s3:List*",
                        "sdb:BatchPutAttributes",
                        "sdb:Select",
                        "sqs:CreateQueue",
                        "sqs:Delete*",
                        "sqs:GetQueue*",
                        "sqs:PurgeQueue",
                        "sqs:ReceiveMessage",
                        "cloudwatch:PutMetricAlarm",
                        "cloudwatch:DescribeAlarms",
                        "cloudwatch:DeleteAlarms",
                        "application-autoscaling:RegisterScalableTarget",
                        "application-autoscaling:DeregisterScalableTarget",
                        "application-autoscaling:PutScalingPolicy",
                        "application-autoscaling:DeleteScalingPolicy",
                        "application-autoscaling:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIDI2BQT2LKXZG36TW",
        "PolicyName": "AmazonElasticMapReduceRole",
        "UpdateDate": "2017-07-17T21:29:50+00:00",
        "VersionId": "v8"
    },
    "AmazonElasticMapReduceforAutoScalingRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforAutoScalingRole",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-18T01:09:10+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:DescribeAlarms",
                        "elasticmapreduce:ListInstanceGroups",
                        "elasticmapreduce:ModifyInstanceGroups"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJSVXG6QHPE6VHDZ4Q",
        "PolicyName": "AmazonElasticMapReduceforAutoScalingRole",
        "UpdateDate": "2016-11-18T01:09:10+00:00",
        "VersionId": "v1"
    },
    "AmazonElasticMapReduceforEC2Role": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-11T23:57:30+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:*",
                        "dynamodb:*",
                        "ec2:Describe*",
                        "elasticmapreduce:Describe*",
                        "elasticmapreduce:ListBootstrapActions",
                        "elasticmapreduce:ListClusters",
                        "elasticmapreduce:ListInstanceGroups",
                        "elasticmapreduce:ListInstances",
                        "elasticmapreduce:ListSteps",
                        "kinesis:CreateStream",
                        "kinesis:DeleteStream",
                        "kinesis:DescribeStream",
                        "kinesis:GetRecords",
                        "kinesis:GetShardIterator",
                        "kinesis:MergeShards",
                        "kinesis:PutRecord",
                        "kinesis:SplitShard",
                        "rds:Describe*",
                        "s3:*",
                        "sdb:*",
                        "sns:*",
                        "sqs:*",
                        "glue:CreateDatabase",
                        "glue:UpdateDatabase",
                        "glue:DeleteDatabase",
                        "glue:GetDatabase",
                        "glue:GetDatabases",
                        "glue:CreateTable",
                        "glue:UpdateTable",
                        "glue:DeleteTable",
                        "glue:GetTable",
                        "glue:GetTables",
                        "glue:GetTableVersions",
                        "glue:CreatePartition",
                        "glue:BatchCreatePartition",
                        "glue:UpdatePartition",
                        "glue:DeletePartition",
                        "glue:BatchDeletePartition",
                        "glue:GetPartition",
                        "glue:GetPartitions",
                        "glue:BatchGetPartition",
                        "glue:CreateUserDefinedFunction",
                        "glue:UpdateUserDefinedFunction",
                        "glue:DeleteUserDefinedFunction",
                        "glue:GetUserDefinedFunction",
                        "glue:GetUserDefinedFunctions"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIGALS5RCDLZLB3PGS",
        "PolicyName": "AmazonElasticMapReduceforEC2Role",
        "UpdateDate": "2017-08-11T23:57:30+00:00",
        "VersionId": "v3"
    },
    "AmazonElasticTranscoderFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonElasticTranscoderFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:24+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "elastictranscoder:*",
                        "cloudfront:*",
                        "s3:List*",
                        "s3:Put*",
                        "s3:Get*",
                        "s3:*MultipartUpload*",
                        "iam:CreateRole",
                        "iam:GetRolePolicy",
                        "iam:PassRole",
                        "iam:PutRolePolicy",
                        "iam:List*",
                        "sns:CreateTopic",
                        "sns:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ4D5OJU75P5ZJZVNY",
        "PolicyName": "AmazonElasticTranscoderFullAccess",
        "UpdateDate": "2015-02-06T18:40:24+00:00",
        "VersionId": "v1"
    },
    "AmazonElasticTranscoderJobsSubmitter": {
        "Arn": "arn:aws:iam::aws:policy/AmazonElasticTranscoderJobsSubmitter",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:25+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "elastictranscoder:Read*",
                        "elastictranscoder:List*",
                        "elastictranscoder:*Job",
                        "elastictranscoder:*Preset",
                        "s3:List*",
                        "iam:List*",
                        "sns:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIN5WGARIKZ3E2UQOU",
        "PolicyName": "AmazonElasticTranscoderJobsSubmitter",
        "UpdateDate": "2015-02-06T18:40:25+00:00",
        "VersionId": "v1"
    },
    "AmazonElasticTranscoderReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonElasticTranscoderReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:26+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "elastictranscoder:Read*",
                        "elastictranscoder:List*",
                        "s3:List*",
                        "iam:List*",
                        "sns:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJGPP7GPMJRRJMEP3Q",
        "PolicyName": "AmazonElasticTranscoderReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:26+00:00",
        "VersionId": "v1"
    },
    "AmazonElasticTranscoderRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonElasticTranscoderRole",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:26+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:ListBucket",
                        "s3:Put*",
                        "s3:Get*",
                        "s3:*MultipartUpload*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ],
                    "Sid": "1"
                },
                {
                    "Action": [
                        "sns:Publish"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ],
                    "Sid": "2"
                },
                {
                    "Action": [
                        "s3:*Policy*",
                        "sns:*Permission*",
                        "sns:*Delete*",
                        "s3:*Delete*",
                        "sns:*Remove*"
                    ],
                    "Effect": "Deny",
                    "Resource": [
                        "*"
                    ],
                    "Sid": "3"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJNW3WMKVXFJ2KPIQ2",
        "PolicyName": "AmazonElasticTranscoderRole",
        "UpdateDate": "2015-02-06T18:41:26+00:00",
        "VersionId": "v1"
    },
    "AmazonElasticsearchServiceRolePolicy": {
        "Arn": "arn:aws:iam::aws:policy/aws-service-role/AmazonElasticsearchServiceRolePolicy",
        "AttachmentCount": 0,
        "CreateDate": "2017-07-07T00:15:31+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:CreateNetworkInterface",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:ModifyNetworkInterfaceAttribute",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "Stmt1480452973134"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/aws-service-role/",
        "PolicyId": "ANPAJFEWZPHXKLCVHEUIC",
        "PolicyName": "AmazonElasticsearchServiceRolePolicy",
        "UpdateDate": "2017-07-07T00:15:31+00:00",
        "VersionId": "v1"
    },
    "AmazonGlacierFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonGlacierFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:28+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "glacier:*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJQSTZJWB2AXXAKHVQ",
        "PolicyName": "AmazonGlacierFullAccess",
        "UpdateDate": "2015-02-06T18:40:28+00:00",
        "VersionId": "v1"
    },
    "AmazonGlacierReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonGlacierReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-05-05T18:46:10+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "glacier:DescribeJob",
                        "glacier:DescribeVault",
                        "glacier:GetDataRetrievalPolicy",
                        "glacier:GetJobOutput",
                        "glacier:GetVaultAccessPolicy",
                        "glacier:GetVaultLock",
                        "glacier:GetVaultNotifications",
                        "glacier:ListJobs",
                        "glacier:ListMultipartUploads",
                        "glacier:ListParts",
                        "glacier:ListTagsForVault",
                        "glacier:ListVaults"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI2D5NJKMU274MET4E",
        "PolicyName": "AmazonGlacierReadOnlyAccess",
        "UpdateDate": "2016-05-05T18:46:10+00:00",
        "VersionId": "v2"
    },
    "AmazonInspectorFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonInspectorFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-12T17:42:57+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "inspector:*",
                        "ec2:DescribeInstances",
                        "ec2:DescribeTags",
                        "sns:ListTopics",
                        "events:DescribeRule",
                        "events:ListRuleNamesByTarget"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI7Y6NTA27NWNA5U5E",
        "PolicyName": "AmazonInspectorFullAccess",
        "UpdateDate": "2017-09-12T17:42:57+00:00",
        "VersionId": "v3"
    },
    "AmazonInspectorReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonInspectorReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-12T16:53:06+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "inspector:Describe*",
                        "inspector:Get*",
                        "inspector:List*",
                        "inspector:LocalizeText",
                        "inspector:Preview*",
                        "ec2:DescribeInstances",
                        "ec2:DescribeTags",
                        "sns:ListTopics",
                        "events:DescribeRule",
                        "events:ListRuleNamesByTarget"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJXQNTHTEJ2JFRN2SE",
        "PolicyName": "AmazonInspectorReadOnlyAccess",
        "UpdateDate": "2017-09-12T16:53:06+00:00",
        "VersionId": "v3"
    },
    "AmazonKinesisAnalyticsFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonKinesisAnalyticsFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-09-21T19:01:14+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "kinesisanalytics:*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "kinesis:CreateStream",
                        "kinesis:DeleteStream",
                        "kinesis:DescribeStream",
                        "kinesis:ListStreams",
                        "kinesis:PutRecord",
                        "kinesis:PutRecords"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "firehose:DescribeDeliveryStream",
                        "firehose:ListDeliveryStreams"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:ListMetrics"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "logs:GetLogEvents",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "iam:ListPolicyVersions",
                        "iam:ListRoles"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "iam:PassRole",
                    "Effect": "Allow",
                    "Resource": "arn:aws:iam::*:role/service-role/kinesis-analytics*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJQOSKHTXP43R7P5AC",
        "PolicyName": "AmazonKinesisAnalyticsFullAccess",
        "UpdateDate": "2016-09-21T19:01:14+00:00",
        "VersionId": "v1"
    },
    "AmazonKinesisAnalyticsReadOnly": {
        "Arn": "arn:aws:iam::aws:policy/AmazonKinesisAnalyticsReadOnly",
        "AttachmentCount": 0,
        "CreateDate": "2016-09-21T18:16:43+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "kinesisanalytics:Describe*",
                        "kinesisanalytics:Get*",
                        "kinesisanalytics:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "kinesis:DescribeStream",
                        "kinesis:ListStreams"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "firehose:DescribeDeliveryStream",
                        "firehose:ListDeliveryStreams"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:ListMetrics"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "logs:GetLogEvents",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "iam:ListPolicyVersions",
                        "iam:ListRoles"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIJIEXZAFUK43U7ARK",
        "PolicyName": "AmazonKinesisAnalyticsReadOnly",
        "UpdateDate": "2016-09-21T18:16:43+00:00",
        "VersionId": "v1"
    },
    "AmazonKinesisFirehoseFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonKinesisFirehoseFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-10-07T18:45:26+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "firehose:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJMZQMTZ7FRBFHHAHI",
        "PolicyName": "AmazonKinesisFirehoseFullAccess",
        "UpdateDate": "2015-10-07T18:45:26+00:00",
        "VersionId": "v1"
    },
    "AmazonKinesisFirehoseReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonKinesisFirehoseReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-10-07T18:43:39+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "firehose:Describe*",
                        "firehose:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ36NT645INW4K24W6",
        "PolicyName": "AmazonKinesisFirehoseReadOnlyAccess",
        "UpdateDate": "2015-10-07T18:43:39+00:00",
        "VersionId": "v1"
    },
    "AmazonKinesisFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonKinesisFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:29+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "kinesis:*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIVF32HAMOXCUYRAYE",
        "PolicyName": "AmazonKinesisFullAccess",
        "UpdateDate": "2015-02-06T18:40:29+00:00",
        "VersionId": "v1"
    },
    "AmazonKinesisReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonKinesisReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:30+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "kinesis:Get*",
                        "kinesis:List*",
                        "kinesis:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIOCMTDT5RLKZ2CAJO",
        "PolicyName": "AmazonKinesisReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:30+00:00",
        "VersionId": "v1"
    },
    "AmazonLexFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonLexFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-04-14T19:45:37+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:DescribeAlarms",
                        "cloudwatch:DescribeAlarmsForMetric",
                        "kms:DescribeKey",
                        "kms:ListAliases",
                        "lambda:GetPolicy",
                        "lambda:ListFunctions",
                        "lex:*",
                        "polly:DescribeVoices",
                        "polly:SynthesizeSpeech"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "lambda:AddPermission",
                        "lambda:RemovePermission"
                    ],
                    "Condition": {
                        "StringLike": {
                            "lambda:Principal": "lex.amazonaws.com"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": "arn:aws:lambda:*:*:function:AmazonLex*"
                },
                {
                    "Action": [
                        "iam:GetRole",
                        "iam:DeleteRole"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/aws-service-role/lex.amazonaws.com/AWSServiceRoleForLexBots",
                        "arn:aws:iam::*:role/aws-service-role/channels.lex.amazonaws.com/AWSServiceRoleForLexChannels"
                    ]
                },
                {
                    "Action": [
                        "iam:CreateServiceLinkedRole"
                    ],
                    "Condition": {
                        "StringLike": {
                            "iam:AWSServiceName": "lex.amazonaws.com"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/aws-service-role/lex.amazonaws.com/AWSServiceRoleForLexBots"
                    ]
                },
                {
                    "Action": [
                        "iam:DetachRolePolicy"
                    ],
                    "Condition": {
                        "StringLike": {
                            "iam:PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/AmazonLexBotPolicy"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/aws-service-role/lex.amazonaws.com/AWSServiceRoleForLexBots"
                    ]
                },
                {
                    "Action": [
                        "iam:CreateServiceLinkedRole"
                    ],
                    "Condition": {
                        "StringLike": {
                            "iam:AWSServiceName": "channels.lex.amazonaws.com"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/aws-service-role/channels.lex.amazonaws.com/AWSServiceRoleForLexChannels"
                    ]
                },
                {
                    "Action": [
                        "iam:DetachRolePolicy"
                    ],
                    "Condition": {
                        "StringLike": {
                            "iam:PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/LexChannelPolicy"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/aws-service-role/channels.lex.amazonaws.com/AWSServiceRoleForLexChannels"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJVLXDHKVC23HRTKSI",
        "PolicyName": "AmazonLexFullAccess",
        "UpdateDate": "2017-04-14T19:45:37+00:00",
        "VersionId": "v3"
    },
    "AmazonLexReadOnly": {
        "Arn": "arn:aws:iam::aws:policy/AmazonLexReadOnly",
        "AttachmentCount": 0,
        "CreateDate": "2017-04-11T23:13:33+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "lex:GetBot",
                        "lex:GetBotAlias",
                        "lex:GetBotAliases",
                        "lex:GetBots",
                        "lex:GetBotChannelAssociation",
                        "lex:GetBotChannelAssociations",
                        "lex:GetBotVersions",
                        "lex:GetBuiltinIntent",
                        "lex:GetBuiltinIntents",
                        "lex:GetBuiltinSlotTypes",
                        "lex:GetIntent",
                        "lex:GetIntents",
                        "lex:GetIntentVersions",
                        "lex:GetSlotType",
                        "lex:GetSlotTypes",
                        "lex:GetSlotTypeVersions",
                        "lex:GetUtterancesView"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJGBI5LSMAJNDGBNAM",
        "PolicyName": "AmazonLexReadOnly",
        "UpdateDate": "2017-04-11T23:13:33+00:00",
        "VersionId": "v1"
    },
    "AmazonLexRunBotsOnly": {
        "Arn": "arn:aws:iam::aws:policy/AmazonLexRunBotsOnly",
        "AttachmentCount": 0,
        "CreateDate": "2017-04-11T23:06:24+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "lex:PostContent",
                        "lex:PostText"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJVZGB5CM3N6YWJHBE",
        "PolicyName": "AmazonLexRunBotsOnly",
        "UpdateDate": "2017-04-11T23:06:24+00:00",
        "VersionId": "v1"
    },
    "AmazonMachineLearningBatchPredictionsAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMachineLearningBatchPredictionsAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-04-09T17:12:19+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "machinelearning:CreateBatchPrediction",
                        "machinelearning:DeleteBatchPrediction",
                        "machinelearning:DescribeBatchPredictions",
                        "machinelearning:GetBatchPrediction",
                        "machinelearning:UpdateBatchPrediction"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAILOI4HTQSFTF3GQSC",
        "PolicyName": "AmazonMachineLearningBatchPredictionsAccess",
        "UpdateDate": "2015-04-09T17:12:19+00:00",
        "VersionId": "v1"
    },
    "AmazonMachineLearningCreateOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMachineLearningCreateOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-06-29T20:55:03+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "machinelearning:Add*",
                        "machinelearning:Create*",
                        "machinelearning:Delete*",
                        "machinelearning:Describe*",
                        "machinelearning:Get*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJDRUNIC2RYAMAT3CK",
        "PolicyName": "AmazonMachineLearningCreateOnlyAccess",
        "UpdateDate": "2016-06-29T20:55:03+00:00",
        "VersionId": "v2"
    },
    "AmazonMachineLearningFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMachineLearningFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-04-09T17:25:41+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "machinelearning:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIWKW6AGSGYOQ5ERHC",
        "PolicyName": "AmazonMachineLearningFullAccess",
        "UpdateDate": "2015-04-09T17:25:41+00:00",
        "VersionId": "v1"
    },
    "AmazonMachineLearningManageRealTimeEndpointOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMachineLearningManageRealTimeEndpointOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-04-09T17:32:41+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "machinelearning:CreateRealtimeEndpoint",
                        "machinelearning:DeleteRealtimeEndpoint"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJJL3PC3VCSVZP6OCI",
        "PolicyName": "AmazonMachineLearningManageRealTimeEndpointOnlyAccess",
        "UpdateDate": "2015-04-09T17:32:41+00:00",
        "VersionId": "v1"
    },
    "AmazonMachineLearningReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMachineLearningReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-04-09T17:40:02+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "machinelearning:Describe*",
                        "machinelearning:Get*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIW5VYBCGEX56JCINC",
        "PolicyName": "AmazonMachineLearningReadOnlyAccess",
        "UpdateDate": "2015-04-09T17:40:02+00:00",
        "VersionId": "v1"
    },
    "AmazonMachineLearningRealTimePredictionOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMachineLearningRealTimePredictionOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-04-09T17:44:06+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "machinelearning:Predict"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIWMCNQPRWMWT36GVQ",
        "PolicyName": "AmazonMachineLearningRealTimePredictionOnlyAccess",
        "UpdateDate": "2015-04-09T17:44:06+00:00",
        "VersionId": "v1"
    },
    "AmazonMachineLearningRoleforRedshiftDataSource": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonMachineLearningRoleforRedshiftDataSource",
        "AttachmentCount": 0,
        "CreateDate": "2015-04-09T17:05:26+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateSecurityGroup",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeSecurityGroups",
                        "ec2:RevokeSecurityGroupIngress",
                        "redshift:AuthorizeClusterSecurityGroupIngress",
                        "redshift:CreateClusterSecurityGroup",
                        "redshift:DescribeClusters",
                        "redshift:DescribeClusterSecurityGroups",
                        "redshift:ModifyCluster",
                        "redshift:RevokeClusterSecurityGroupIngress",
                        "s3:GetBucketLocation",
                        "s3:GetBucketPolicy",
                        "s3:GetObject",
                        "s3:PutBucketPolicy",
                        "s3:PutObject"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIQ5UDYYMNN42BM4AK",
        "PolicyName": "AmazonMachineLearningRoleforRedshiftDataSource",
        "UpdateDate": "2015-04-09T17:05:26+00:00",
        "VersionId": "v1"
    },
    "AmazonMacieFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMacieFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-14T14:54:30+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "macie:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJJF2N5FR6S5TZN5OA",
        "PolicyName": "AmazonMacieFullAccess",
        "UpdateDate": "2017-08-14T14:54:30+00:00",
        "VersionId": "v1"
    },
    "AmazonMacieServiceRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonMacieServiceRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-14T14:53:26+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:Get*",
                        "s3:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJVV7PON3FPBL2PSGC",
        "PolicyName": "AmazonMacieServiceRole",
        "UpdateDate": "2017-08-14T14:53:26+00:00",
        "VersionId": "v1"
    },
    "AmazonMacieSetupRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonMacieSetupRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-14T14:53:34+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudtrail:DescribeTrails",
                        "cloudtrail:GetEventSelectors",
                        "cloudtrail:GetTrailStatus",
                        "cloudtrail:ListTags",
                        "cloudtrail:LookupEvents",
                        "iam:ListAccountAliases",
                        "s3:GetBucket*",
                        "s3:ListBucket",
                        "s3:ListAllMyBuckets"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "cloudtrail:CreateTrail",
                        "cloudtrail:StartLogging",
                        "cloudtrail:StopLogging",
                        "cloudtrail:UpdateTrail",
                        "cloudtrail:DeleteTrail",
                        "cloudtrail:PutEventSelectors"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:cloudtrail:*:*:trail/AWSMacieTrail-DO-NOT-EDIT"
                },
                {
                    "Action": [
                        "s3:CreateBucket",
                        "s3:DeleteBucket",
                        "s3:DeleteBucketPolicy",
                        "s3:DeleteBucketWebsite",
                        "s3:DeleteObject",
                        "s3:DeleteObjectTagging",
                        "s3:DeleteObjectVersion",
                        "s3:DeleteObjectVersionTagging",
                        "s3:DeleteReplicationConfiguration",
                        "s3:PutBucketPolicy"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::awsmacie-*",
                        "arn:aws:s3:::awsmacietrail-*",
                        "arn:aws:s3:::*-awsmacietrail-*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJ5DC6UBVKND7ADSKA",
        "PolicyName": "AmazonMacieSetupRole",
        "UpdateDate": "2017-08-14T14:53:34+00:00",
        "VersionId": "v1"
    },
    "AmazonMechanicalTurkFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMechanicalTurkFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-12-11T19:08:19+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "mechanicalturk:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJDGCL5BET73H5QIQC",
        "PolicyName": "AmazonMechanicalTurkFullAccess",
        "UpdateDate": "2015-12-11T19:08:19+00:00",
        "VersionId": "v1"
    },
    "AmazonMechanicalTurkReadOnly": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMechanicalTurkReadOnly",
        "AttachmentCount": 0,
        "CreateDate": "2017-02-27T21:45:50+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "mechanicalturk:Get*",
                        "mechanicalturk:Search*",
                        "mechanicalturk:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIO5IY3G3WXSX5PPRM",
        "PolicyName": "AmazonMechanicalTurkReadOnly",
        "UpdateDate": "2017-02-27T21:45:50+00:00",
        "VersionId": "v2"
    },
    "AmazonMobileAnalyticsFinancialReportAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMobileAnalyticsFinancialReportAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:35+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "mobileanalytics:GetReports",
                        "mobileanalytics:GetFinancialReports"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJKJHO2R27TXKCWBU4",
        "PolicyName": "AmazonMobileAnalyticsFinancialReportAccess",
        "UpdateDate": "2015-02-06T18:40:35+00:00",
        "VersionId": "v1"
    },
    "AmazonMobileAnalyticsFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMobileAnalyticsFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:34+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "mobileanalytics:*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIJIKLU2IJ7WJ6DZFG",
        "PolicyName": "AmazonMobileAnalyticsFullAccess",
        "UpdateDate": "2015-02-06T18:40:34+00:00",
        "VersionId": "v1"
    },
    "AmazonMobileAnalyticsNon-financialReportAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMobileAnalyticsNon-financialReportAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:36+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "mobileanalytics:GetReports",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIQLKQ4RXPUBBVVRDE",
        "PolicyName": "AmazonMobileAnalyticsNon-financialReportAccess",
        "UpdateDate": "2015-02-06T18:40:36+00:00",
        "VersionId": "v1"
    },
    "AmazonMobileAnalyticsWriteOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonMobileAnalyticsWriteOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:37+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "mobileanalytics:PutEvents",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ5TAWBBQC2FAL3G6G",
        "PolicyName": "AmazonMobileAnalyticsWriteOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:37+00:00",
        "VersionId": "v1"
    },
    "AmazonPollyFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonPollyFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-30T18:59:06+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "polly:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJUZOYQU6XQYPR7EWS",
        "PolicyName": "AmazonPollyFullAccess",
        "UpdateDate": "2016-11-30T18:59:06+00:00",
        "VersionId": "v1"
    },
    "AmazonPollyReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonPollyReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-30T18:59:24+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "polly:DescribeVoices",
                        "polly:GetLexicon",
                        "polly:ListLexicons",
                        "polly:SynthesizeSpeech"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ5FENL3CVPL2FPDLA",
        "PolicyName": "AmazonPollyReadOnlyAccess",
        "UpdateDate": "2016-11-30T18:59:24+00:00",
        "VersionId": "v1"
    },
    "AmazonRDSDirectoryServiceAccess": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonRDSDirectoryServiceAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-02-26T02:02:05+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ds:DescribeDirectories",
                        "ds:AuthorizeApplication",
                        "ds:UnauthorizeApplication"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIL4KBY57XWMYUHKUU",
        "PolicyName": "AmazonRDSDirectoryServiceAccess",
        "UpdateDate": "2016-02-26T02:02:05+00:00",
        "VersionId": "v1"
    },
    "AmazonRDSEnhancedMonitoringRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole",
        "AttachmentCount": 1,
        "CreateDate": "2015-11-11T19:58:29+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:PutRetentionPolicy"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:log-group:RDS*"
                    ],
                    "Sid": "EnableCreationAndManagementOfRDSCloudwatchLogGroups"
                },
                {
                    "Action": [
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams",
                        "logs:GetLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:logs:*:*:log-group:RDS*:log-stream:*"
                    ],
                    "Sid": "EnableCreationAndManagementOfRDSCloudwatchLogStreams"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJV7BS425S4PTSSVGK",
        "PolicyName": "AmazonRDSEnhancedMonitoringRole",
        "UpdateDate": "2015-11-11T19:58:29+00:00",
        "VersionId": "v1"
    },
    "AmazonRDSFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonRDSFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-14T23:40:45+00:00",
        "DefaultVersionId": "v4",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "rds:*",
                        "cloudwatch:DescribeAlarms",
                        "cloudwatch:GetMetricStatistics",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcAttribute",
                        "ec2:DescribeVpcs",
                        "sns:ListSubscriptions",
                        "sns:ListTopics",
                        "logs:DescribeLogStreams",
                        "logs:GetLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "pi:*",
                    "Effect": "Allow",
                    "Resource": "arn:aws:pi:*:*:metrics/rds/*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI3R4QMOG6Q5A4VWVG",
        "PolicyName": "AmazonRDSFullAccess",
        "UpdateDate": "2017-09-14T23:40:45+00:00",
        "VersionId": "v4"
    },
    "AmazonRDSReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonRDSReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-28T21:36:32+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "rds:Describe*",
                        "rds:ListTagsForResource",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcAttribute",
                        "ec2:DescribeVpcs"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "cloudwatch:GetMetricStatistics",
                        "logs:DescribeLogStreams",
                        "logs:GetLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJKTTTYV2IIHKLZ346",
        "PolicyName": "AmazonRDSReadOnlyAccess",
        "UpdateDate": "2017-08-28T21:36:32+00:00",
        "VersionId": "v3"
    },
    "AmazonRedshiftFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonRedshiftFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-19T18:27:44+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "redshift:*",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAddresses",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeInternetGateways",
                        "sns:CreateTopic",
                        "sns:Get*",
                        "sns:List*",
                        "cloudwatch:Describe*",
                        "cloudwatch:Get*",
                        "cloudwatch:List*",
                        "cloudwatch:PutMetricAlarm",
                        "cloudwatch:EnableAlarmActions",
                        "cloudwatch:DisableAlarmActions"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "iam:CreateServiceLinkedRole",
                    "Condition": {
                        "StringLike": {
                            "iam:AWSServiceName": "redshift.amazonaws.com"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": "arn:aws:iam::*:role/aws-service-role/redshift.amazonaws.com/AWSServiceRoleForRedshift"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAISEKCHH4YDB46B5ZO",
        "PolicyName": "AmazonRedshiftFullAccess",
        "UpdateDate": "2017-09-19T18:27:44+00:00",
        "VersionId": "v2"
    },
    "AmazonRedshiftReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonRedshiftReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:51+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "redshift:Describe*",
                        "redshift:ViewQueriesInConsole",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAddresses",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeInternetGateways",
                        "sns:Get*",
                        "sns:List*",
                        "cloudwatch:Describe*",
                        "cloudwatch:List*",
                        "cloudwatch:Get*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIGD46KSON64QBSEZM",
        "PolicyName": "AmazonRedshiftReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:51+00:00",
        "VersionId": "v1"
    },
    "AmazonRedshiftServiceLinkedRolePolicy": {
        "Arn": "arn:aws:iam::aws:policy/aws-service-role/AmazonRedshiftServiceLinkedRolePolicy",
        "AttachmentCount": 0,
        "CreateDate": "2017-09-18T19:19:45+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeVpcs",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeAddress",
                        "ec2:AssociateAddress",
                        "ec2:DisassociateAddress",
                        "ec2:CreateNetworkInterface",
                        "ec2:DeleteNetworkInterface",
                        "ec2:ModifyNetworkInterfaceAttribute"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/aws-service-role/",
        "PolicyId": "ANPAJPY2VXNRUYOY3SRZS",
        "PolicyName": "AmazonRedshiftServiceLinkedRolePolicy",
        "UpdateDate": "2017-09-18T19:19:45+00:00",
        "VersionId": "v1"
    },
    "AmazonRekognitionFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonRekognitionFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-30T14:40:44+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "rekognition:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIWDAOK6AIFDVX6TT6",
        "PolicyName": "AmazonRekognitionFullAccess",
        "UpdateDate": "2016-11-30T14:40:44+00:00",
        "VersionId": "v1"
    },
    "AmazonRekognitionReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonRekognitionReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-30T14:58:06+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "rekognition:CompareFaces",
                        "rekognition:DetectFaces",
                        "rekognition:DetectLabels",
                        "rekognition:ListCollections",
                        "rekognition:ListFaces",
                        "rekognition:SearchFaces",
                        "rekognition:SearchFacesByImage"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAILWSUHXUY4ES43SA4",
        "PolicyName": "AmazonRekognitionReadOnlyAccess",
        "UpdateDate": "2016-11-30T14:58:06+00:00",
        "VersionId": "v1"
    },
    "AmazonRoute53DomainsFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonRoute53DomainsFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:56+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "route53:CreateHostedZone",
                        "route53domains:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIPAFBMIYUILMOKL6G",
        "PolicyName": "AmazonRoute53DomainsFullAccess",
        "UpdateDate": "2015-02-06T18:40:56+00:00",
        "VersionId": "v1"
    },
    "AmazonRoute53DomainsReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonRoute53DomainsReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:57+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "route53domains:Get*",
                        "route53domains:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIDRINP6PPTRXYVQCI",
        "PolicyName": "AmazonRoute53DomainsReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:57+00:00",
        "VersionId": "v1"
    },
    "AmazonRoute53FullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonRoute53FullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-02-14T21:25:53+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "route53:*",
                        "route53domains:*",
                        "cloudfront:ListDistributions",
                        "elasticloadbalancing:DescribeLoadBalancers",
                        "elasticbeanstalk:DescribeEnvironments",
                        "s3:ListBucket",
                        "s3:GetBucketLocation",
                        "s3:GetBucketWebsiteConfiguration",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeRegions",
                        "sns:ListTopics",
                        "sns:ListSubscriptionsByTopic",
                        "cloudwatch:DescribeAlarms",
                        "cloudwatch:GetMetricStatistics"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJWVDLG5RPST6PHQ3A",
        "PolicyName": "AmazonRoute53FullAccess",
        "UpdateDate": "2017-02-14T21:25:53+00:00",
        "VersionId": "v2"
    },
    "AmazonRoute53ReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonRoute53ReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-15T21:15:16+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "route53:Get*",
                        "route53:List*",
                        "route53:TestDNSAnswer"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAITOYK2ZAOQFXV2JNC",
        "PolicyName": "AmazonRoute53ReadOnlyAccess",
        "UpdateDate": "2016-11-15T21:15:16+00:00",
        "VersionId": "v2"
    },
    "AmazonS3FullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonS3FullAccess",
        "AttachmentCount": 1,
        "CreateDate": "2015-02-06T18:40:58+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "s3:*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIFIR6V6BVTRAHWINE",
        "PolicyName": "AmazonS3FullAccess",
        "UpdateDate": "2015-02-06T18:40:58+00:00",
        "VersionId": "v1"
    },
    "AmazonS3ReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:59+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:Get*",
                        "s3:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIZTJ4DXE7G6AGAE6M",
        "PolicyName": "AmazonS3ReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:59+00:00",
        "VersionId": "v1"
    },
    "AmazonSESFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonSESFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:02+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ses:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ2P4NXCHAT7NDPNR4",
        "PolicyName": "AmazonSESFullAccess",
        "UpdateDate": "2015-02-06T18:41:02+00:00",
        "VersionId": "v1"
    },
    "AmazonSESReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonSESReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:03+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ses:Get*",
                        "ses:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAINV2XPFRMWJJNSCGI",
        "PolicyName": "AmazonSESReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:41:03+00:00",
        "VersionId": "v1"
    },
    "AmazonSNSFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonSNSFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:05+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "sns:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJWEKLCXXUNT2SOLSG",
        "PolicyName": "AmazonSNSFullAccess",
        "UpdateDate": "2015-02-06T18:41:05+00:00",
        "VersionId": "v1"
    },
    "AmazonSNSReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonSNSReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:06+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "sns:GetTopicAttributes",
                        "sns:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIZGQCQTFOFPMHSB6W",
        "PolicyName": "AmazonSNSReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:41:06+00:00",
        "VersionId": "v1"
    },
    "AmazonSNSRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonSNSRole",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:30+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:PutMetricFilter",
                        "logs:PutRetentionPolicy"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJK5GQB7CIK7KHY2GA",
        "PolicyName": "AmazonSNSRole",
        "UpdateDate": "2015-02-06T18:41:30+00:00",
        "VersionId": "v1"
    },
    "AmazonSQSFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonSQSFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:07+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "sqs:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI65L554VRJ33ECQS6",
        "PolicyName": "AmazonSQSFullAccess",
        "UpdateDate": "2015-02-06T18:41:07+00:00",
        "VersionId": "v1"
    },
    "AmazonSQSReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonSQSReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:08+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "sqs:GetQueueAttributes",
                        "sqs:ListQueues"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIUGSSQY362XGCM6KW",
        "PolicyName": "AmazonSQSReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:41:08+00:00",
        "VersionId": "v1"
    },
    "AmazonSSMAutomationApproverAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonSSMAutomationApproverAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-07T23:07:28+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ssm:DescribeAutomationExecutions",
                        "ssm:GetAutomationExecution",
                        "ssm:SendAutomationSignal"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIDSSXIRWBSLWWIORC",
        "PolicyName": "AmazonSSMAutomationApproverAccess",
        "UpdateDate": "2017-08-07T23:07:28+00:00",
        "VersionId": "v1"
    },
    "AmazonSSMAutomationRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonSSMAutomationRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-07-24T23:29:12+00:00",
        "DefaultVersionId": "v5",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:lambda:*:*:function:Automation*"
                    ]
                },
                {
                    "Action": [
                        "ec2:CreateImage",
                        "ec2:CopyImage",
                        "ec2:DeregisterImage",
                        "ec2:DescribeImages",
                        "ec2:DeleteSnapshot",
                        "ec2:StartInstances",
                        "ec2:RunInstances",
                        "ec2:StopInstances",
                        "ec2:TerminateInstances",
                        "ec2:DescribeInstanceStatus",
                        "ec2:CreateTags",
                        "ec2:DeleteTags",
                        "ec2:DescribeTags",
                        "cloudformation:CreateStack",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:DescribeStacks",
                        "cloudformation:UpdateStack",
                        "cloudformation:DeleteStack"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "ssm:*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "sns:Publish"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:sns:*:*:Automation*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJIBQCTBCXD2XRNB6W",
        "PolicyName": "AmazonSSMAutomationRole",
        "UpdateDate": "2017-07-24T23:29:12+00:00",
        "VersionId": "v5"
    },
    "AmazonSSMFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonSSMFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-03-07T21:09:12+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:PutMetricData",
                        "ds:CreateComputer",
                        "ds:DescribeDirectories",
                        "ec2:DescribeInstanceStatus",
                        "logs:*",
                        "ssm:*",
                        "ec2messages:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJA7V6HI4ISQFMDYAG",
        "PolicyName": "AmazonSSMFullAccess",
        "UpdateDate": "2016-03-07T21:09:12+00:00",
        "VersionId": "v2"
    },
    "AmazonSSMMaintenanceWindowRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AmazonSSMMaintenanceWindowRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-09T20:49:14+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ssm:GetAutomationExecution",
                        "ssm:GetParameters",
                        "ssm:ListCommands",
                        "ssm:SendCommand",
                        "ssm:StartAutomationExecution"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ],
                    "Sid": "Stmt1477803259000"
                },
                {
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:lambda:*:*:function:SSM*",
                        "arn:aws:lambda:*:*:function:*:SSM*"
                    ],
                    "Sid": "Stmt1477803259001"
                },
                {
                    "Action": [
                        "states:DescribeExecution",
                        "states:StartExecution"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:states:*:*:stateMachine:SSM*",
                        "arn:aws:states:*:*:execution:SSM*"
                    ],
                    "Sid": "Stmt1477803259002"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJV3JNYSTZ47VOXYME",
        "PolicyName": "AmazonSSMMaintenanceWindowRole",
        "UpdateDate": "2017-08-09T20:49:14+00:00",
        "VersionId": "v2"
    },
    "AmazonSSMReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-05-29T17:44:19+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ssm:Describe*",
                        "ssm:Get*",
                        "ssm:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJODSKQGGJTHRYZ5FC",
        "PolicyName": "AmazonSSMReadOnlyAccess",
        "UpdateDate": "2015-05-29T17:44:19+00:00",
        "VersionId": "v1"
    },
    "AmazonVPCCrossAccountNetworkInterfaceOperations": {
        "Arn": "arn:aws:iam::aws:policy/AmazonVPCCrossAccountNetworkInterfaceOperations",
        "AttachmentCount": 0,
        "CreateDate": "2017-07-18T20:47:16+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeRouteTables",
                        "ec2:CreateRoute",
                        "ec2:DeleteRoute",
                        "ec2:ReplaceRoute"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:CreateNetworkInterface",
                        "ec2:DeleteNetworkInterface",
                        "ec2:CreateNetworkInterfacePermission",
                        "ec2:ModifyNetworkInterfaceAttribute",
                        "ec2:DescribeNetworkInterfaceAttribute",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeSubnets"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "ec2:AssignPrivateIpAddresses",
                        "ec2:UnassignPrivateIpAddresses"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ53Y4ZY5OHP4CNRJC",
        "PolicyName": "AmazonVPCCrossAccountNetworkInterfaceOperations",
        "UpdateDate": "2017-07-18T20:47:16+00:00",
        "VersionId": "v1"
    },
    "AmazonVPCFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonVPCFullAccess",
        "AttachmentCount": 1,
        "CreateDate": "2015-12-17T17:25:44+00:00",
        "DefaultVersionId": "v5",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:AcceptVpcPeeringConnection",
                        "ec2:AllocateAddress",
                        "ec2:AssignPrivateIpAddresses",
                        "ec2:AssociateAddress",
                        "ec2:AssociateDhcpOptions",
                        "ec2:AssociateRouteTable",
                        "ec2:AttachClassicLinkVpc",
                        "ec2:AttachInternetGateway",
                        "ec2:AttachNetworkInterface",
                        "ec2:AttachVpnGateway",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateCustomerGateway",
                        "ec2:CreateDhcpOptions",
                        "ec2:CreateFlowLogs",
                        "ec2:CreateInternetGateway",
                        "ec2:CreateNatGateway",
                        "ec2:CreateNetworkAcl",
                        "ec2:CreateNetworkAcl",
                        "ec2:CreateNetworkAclEntry",
                        "ec2:CreateNetworkInterface",
                        "ec2:CreateRoute",
                        "ec2:CreateRouteTable",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateSubnet",
                        "ec2:CreateTags",
                        "ec2:CreateVpc",
                        "ec2:CreateVpcEndpoint",
                        "ec2:CreateVpcPeeringConnection",
                        "ec2:CreateVpnConnection",
                        "ec2:CreateVpnConnectionRoute",
                        "ec2:CreateVpnGateway",
                        "ec2:DeleteCustomerGateway",
                        "ec2:DeleteDhcpOptions",
                        "ec2:DeleteFlowLogs",
                        "ec2:DeleteInternetGateway",
                        "ec2:DeleteNatGateway",
                        "ec2:DeleteNetworkAcl",
                        "ec2:DeleteNetworkAclEntry",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DeleteRoute",
                        "ec2:DeleteRouteTable",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DeleteSubnet",
                        "ec2:DeleteTags",
                        "ec2:DeleteVpc",
                        "ec2:DeleteVpcEndpoints",
                        "ec2:DeleteVpcPeeringConnection",
                        "ec2:DeleteVpnConnection",
                        "ec2:DeleteVpnConnectionRoute",
                        "ec2:DeleteVpnGateway",
                        "ec2:DescribeAddresses",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeClassicLinkInstances",
                        "ec2:DescribeCustomerGateways",
                        "ec2:DescribeDhcpOptions",
                        "ec2:DescribeFlowLogs",
                        "ec2:DescribeInstances",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeMovingAddresses",
                        "ec2:DescribeNatGateways",
                        "ec2:DescribeNetworkAcls",
                        "ec2:DescribeNetworkInterfaceAttribute",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribePrefixLists",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeTags",
                        "ec2:DescribeVpcAttribute",
                        "ec2:DescribeVpcClassicLink",
                        "ec2:DescribeVpcEndpoints",
                        "ec2:DescribeVpcEndpointServices",
                        "ec2:DescribeVpcPeeringConnections",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeVpnConnections",
                        "ec2:DescribeVpnGateways",
                        "ec2:DetachClassicLinkVpc",
                        "ec2:DetachInternetGateway",
                        "ec2:DetachNetworkInterface",
                        "ec2:DetachVpnGateway",
                        "ec2:DisableVgwRoutePropagation",
                        "ec2:DisableVpcClassicLink",
                        "ec2:DisassociateAddress",
                        "ec2:DisassociateRouteTable",
                        "ec2:EnableVgwRoutePropagation",
                        "ec2:EnableVpcClassicLink",
                        "ec2:ModifyNetworkInterfaceAttribute",
                        "ec2:ModifySubnetAttribute",
                        "ec2:ModifyVpcAttribute",
                        "ec2:ModifyVpcEndpoint",
                        "ec2:MoveAddressToVpc",
                        "ec2:RejectVpcPeeringConnection",
                        "ec2:ReleaseAddress",
                        "ec2:ReplaceNetworkAclAssociation",
                        "ec2:ReplaceNetworkAclEntry",
                        "ec2:ReplaceRoute",
                        "ec2:ReplaceRouteTableAssociation",
                        "ec2:ResetNetworkInterfaceAttribute",
                        "ec2:RestoreAddressToClassic",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:RevokeSecurityGroupIngress",
                        "ec2:UnassignPrivateIpAddresses"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJBWPGNOVKZD3JI2P2",
        "PolicyName": "AmazonVPCFullAccess",
        "UpdateDate": "2015-12-17T17:25:44+00:00",
        "VersionId": "v5"
    },
    "AmazonVPCReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonVPCReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-12-17T17:25:56+00:00",
        "DefaultVersionId": "v4",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeAddresses",
                        "ec2:DescribeClassicLinkInstances",
                        "ec2:DescribeCustomerGateways",
                        "ec2:DescribeDhcpOptions",
                        "ec2:DescribeFlowLogs",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeMovingAddresses",
                        "ec2:DescribeNatGateways",
                        "ec2:DescribeNetworkAcls",
                        "ec2:DescribeNetworkInterfaceAttribute",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribePrefixLists",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeTags",
                        "ec2:DescribeVpcAttribute",
                        "ec2:DescribeVpcClassicLink",
                        "ec2:DescribeVpcEndpoints",
                        "ec2:DescribeVpcEndpointServices",
                        "ec2:DescribeVpcPeeringConnections",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeVpnConnections",
                        "ec2:DescribeVpnGateways"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIICZJNOJN36GTG6CM",
        "PolicyName": "AmazonVPCReadOnlyAccess",
        "UpdateDate": "2015-12-17T17:25:56+00:00",
        "VersionId": "v4"
    },
    "AmazonWorkMailFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonWorkMailFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-04-20T08:35:49+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ds:AuthorizeApplication",
                        "ds:CheckAlias",
                        "ds:CreateAlias",
                        "ds:CreateDirectory",
                        "ds:CreateIdentityPoolDirectory",
                        "ds:CreateDomain",
                        "ds:DeleteAlias",
                        "ds:DeleteDirectory",
                        "ds:DescribeDirectories",
                        "ds:ExtendDirectory",
                        "ds:GetDirectoryLimits",
                        "ds:ListAuthorizedApplications",
                        "ds:UnauthorizeApplication",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateNetworkInterface",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateSubnet",
                        "ec2:CreateTags",
                        "ec2:CreateVpc",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DeleteSubnet",
                        "ec2:DeleteVpc",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeDomains",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:RevokeSecurityGroupIngress",
                        "kms:DescribeKey",
                        "kms:ListAliases",
                        "ses:*",
                        "workmail:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJQVKNMT7SVATQ4AUY",
        "PolicyName": "AmazonWorkMailFullAccess",
        "UpdateDate": "2017-04-20T08:35:49+00:00",
        "VersionId": "v3"
    },
    "AmazonWorkMailReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonWorkMailReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:42+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ses:Describe*",
                        "ses:Get*",
                        "workmail:Describe*",
                        "workmail:Get*",
                        "workmail:List*",
                        "workmail:Search*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJHF7J65E2QFKCWAJM",
        "PolicyName": "AmazonWorkMailReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:42+00:00",
        "VersionId": "v1"
    },
    "AmazonWorkSpacesAdmin": {
        "Arn": "arn:aws:iam::aws:policy/AmazonWorkSpacesAdmin",
        "AttachmentCount": 0,
        "CreateDate": "2016-08-18T23:08:42+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "workspaces:CreateWorkspaces",
                        "workspaces:DescribeWorkspaces",
                        "workspaces:RebootWorkspaces",
                        "workspaces:RebuildWorkspaces",
                        "workspaces:TerminateWorkspaces",
                        "workspaces:DescribeWorkspaceDirectories",
                        "workspaces:DescribeWorkspaceBundles",
                        "workspaces:ModifyWorkspaceProperties",
                        "workspaces:StopWorkspaces",
                        "workspaces:StartWorkspaces",
                        "workspaces:DescribeWorkspacesConnectionStatus",
                        "workspaces:CreateTags",
                        "workspaces:DeleteTags",
                        "workspaces:DescribeTags",
                        "kms:ListKeys",
                        "kms:ListAliases",
                        "kms:DescribeKey"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ26AU6ATUQCT5KVJU",
        "PolicyName": "AmazonWorkSpacesAdmin",
        "UpdateDate": "2016-08-18T23:08:42+00:00",
        "VersionId": "v2"
    },
    "AmazonWorkSpacesApplicationManagerAdminAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonWorkSpacesApplicationManagerAdminAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-04-09T14:03:18+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "wam:AuthenticatePackager",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJPRL4KYETIH7XGTSS",
        "PolicyName": "AmazonWorkSpacesApplicationManagerAdminAccess",
        "UpdateDate": "2015-04-09T14:03:18+00:00",
        "VersionId": "v1"
    },
    "AmazonZocaloFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonZocaloFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:13+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "zocalo:*",
                        "ds:*",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateNetworkInterface",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateSubnet",
                        "ec2:CreateTags",
                        "ec2:CreateVpc",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DeleteSecurityGroup",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:RevokeSecurityGroupIngress"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJLCDXYRINDMUXEVL6",
        "PolicyName": "AmazonZocaloFullAccess",
        "UpdateDate": "2015-02-06T18:41:13+00:00",
        "VersionId": "v1"
    },
    "AmazonZocaloReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AmazonZocaloReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:14+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "zocalo:Describe*",
                        "ds:DescribeDirectories",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeSubnets"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAISRCSSJNS3QPKZJPM",
        "PolicyName": "AmazonZocaloReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:41:14+00:00",
        "VersionId": "v1"
    },
    "ApplicationAutoScalingForAmazonAppStreamAccess": {
        "Arn": "arn:aws:iam::aws:policy/service-role/ApplicationAutoScalingForAmazonAppStreamAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-02-06T21:39:56+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "appstream:UpdateFleet",
                        "appstream:DescribeFleets"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "cloudwatch:DescribeAlarms"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIEL3HJCCWFVHA6KPG",
        "PolicyName": "ApplicationAutoScalingForAmazonAppStreamAccess",
        "UpdateDate": "2017-02-06T21:39:56+00:00",
        "VersionId": "v1"
    },
    "AutoScalingConsoleFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AutoScalingConsoleFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-01-12T19:43:16+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateKeyPair",
                        "ec2:CreateSecurityGroup",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeImages",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeVpcClassicLink",
                        "ec2:ImportKeyPair"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "elasticloadbalancing:Describe*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "cloudwatch:ListMetrics",
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:PutMetricAlarm",
                        "cloudwatch:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "autoscaling:*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "sns:ListSubscriptions",
                        "sns:ListTopics"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIYEN6FJGYYWJFFCZW",
        "PolicyName": "AutoScalingConsoleFullAccess",
        "UpdateDate": "2017-01-12T19:43:16+00:00",
        "VersionId": "v1"
    },
    "AutoScalingConsoleReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AutoScalingConsoleReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-01-12T19:48:53+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:DescribeVpcs",
                        "ec2:DescribeVpcClassicLink",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeSubnets"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "elasticloadbalancing:Describe*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "cloudwatch:ListMetrics",
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "autoscaling:Describe*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "sns:ListSubscriptions",
                        "sns:ListTopics"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI3A7GDXOYQV3VUQMK",
        "PolicyName": "AutoScalingConsoleReadOnlyAccess",
        "UpdateDate": "2017-01-12T19:48:53+00:00",
        "VersionId": "v1"
    },
    "AutoScalingFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/AutoScalingFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-01-12T19:31:58+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "autoscaling:*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": "cloudwatch:PutMetricAlarm",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIAWRCSJDDXDXGPCFU",
        "PolicyName": "AutoScalingFullAccess",
        "UpdateDate": "2017-01-12T19:31:58+00:00",
        "VersionId": "v1"
    },
    "AutoScalingNotificationAccessRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/AutoScalingNotificationAccessRole",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:22+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "sqs:SendMessage",
                        "sqs:GetQueueUrl",
                        "sns:Publish"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIO2VMUPGDC5PZVXVA",
        "PolicyName": "AutoScalingNotificationAccessRole",
        "UpdateDate": "2015-02-06T18:41:22+00:00",
        "VersionId": "v1"
    },
    "AutoScalingReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/AutoScalingReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-01-12T19:39:35+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "autoscaling:Describe*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIAFWUVLC2LPLSFTFG",
        "PolicyName": "AutoScalingReadOnlyAccess",
        "UpdateDate": "2017-01-12T19:39:35+00:00",
        "VersionId": "v1"
    },
    "Billing": {
        "Arn": "arn:aws:iam::aws:policy/job-function/Billing",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-10T17:33:18+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "aws-portal:*Billing",
                        "aws-portal:*Usage",
                        "aws-portal:*PaymentMethods",
                        "budgets:ViewBudget",
                        "budgets:ModifyBudget"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/job-function/",
        "PolicyId": "ANPAIFTHXT6FFMIRT7ZEA",
        "PolicyName": "Billing",
        "UpdateDate": "2016-11-10T17:33:18+00:00",
        "VersionId": "v1"
    },
    "CloudFrontFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/CloudFrontFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-01-21T17:03:57+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:ListAllMyBuckets"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::*"
                },
                {
                    "Action": [
                        "acm:ListCertificates",
                        "cloudfront:*",
                        "iam:ListServerCertificates",
                        "waf:ListWebACLs",
                        "waf:GetWebACL"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIPRV52SH6HDCCFY6U",
        "PolicyName": "CloudFrontFullAccess",
        "UpdateDate": "2016-01-21T17:03:57+00:00",
        "VersionId": "v3"
    },
    "CloudFrontReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/CloudFrontReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-01-21T17:03:28+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "acm:ListCertificates",
                        "cloudfront:Get*",
                        "cloudfront:List*",
                        "iam:ListServerCertificates",
                        "route53:List*",
                        "waf:ListWebACLs",
                        "waf:GetWebACL"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJJZMNYOTZCNQP36LG",
        "PolicyName": "CloudFrontReadOnlyAccess",
        "UpdateDate": "2016-01-21T17:03:28+00:00",
        "VersionId": "v3"
    },
    "CloudSearchFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/CloudSearchFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:39:56+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudsearch:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIM6OOWKQ7L7VBOZOC",
        "PolicyName": "CloudSearchFullAccess",
        "UpdateDate": "2015-02-06T18:39:56+00:00",
        "VersionId": "v1"
    },
    "CloudSearchReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/CloudSearchReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:39:57+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudsearch:Describe*",
                        "cloudsearch:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJWPLX7N7BCC3RZLHW",
        "PolicyName": "CloudSearchReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:39:57+00:00",
        "VersionId": "v1"
    },
    "CloudWatchActionsEC2Access": {
        "Arn": "arn:aws:iam::aws:policy/CloudWatchActionsEC2Access",
        "AttachmentCount": 0,
        "CreateDate": "2015-07-07T00:00:33+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:Describe*",
                        "ec2:Describe*",
                        "ec2:RebootInstances",
                        "ec2:StopInstances",
                        "ec2:TerminateInstances"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIOWD4E3FVSORSZTGU",
        "PolicyName": "CloudWatchActionsEC2Access",
        "UpdateDate": "2015-07-07T00:00:33+00:00",
        "VersionId": "v1"
    },
    "CloudWatchEventsBuiltInTargetExecutionAccess": {
        "Arn": "arn:aws:iam::aws:policy/service-role/CloudWatchEventsBuiltInTargetExecutionAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-01-14T18:35:49+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:Describe*",
                        "ec2:RebootInstances",
                        "ec2:StopInstances",
                        "ec2:TerminateInstances",
                        "ec2:CreateSnapshot"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "CloudWatchEventsBuiltInTargetExecutionAccess"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIC5AQ5DATYSNF4AUM",
        "PolicyName": "CloudWatchEventsBuiltInTargetExecutionAccess",
        "UpdateDate": "2016-01-14T18:35:49+00:00",
        "VersionId": "v1"
    },
    "CloudWatchEventsFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/CloudWatchEventsFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-01-14T18:37:08+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "events:*",
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "CloudWatchEventsFullAccess"
                },
                {
                    "Action": "iam:PassRole",
                    "Effect": "Allow",
                    "Resource": "arn:aws:iam::*:role/AWS_Events_Invoke_Targets",
                    "Sid": "IAMPassRoleForCloudWatchEvents"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJZLOYLNHESMYOJAFU",
        "PolicyName": "CloudWatchEventsFullAccess",
        "UpdateDate": "2016-01-14T18:37:08+00:00",
        "VersionId": "v1"
    },
    "CloudWatchEventsInvocationAccess": {
        "Arn": "arn:aws:iam::aws:policy/service-role/CloudWatchEventsInvocationAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-01-14T18:36:33+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "kinesis:PutRecord"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "CloudWatchEventsInvocationAccess"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJJXD6JKJLK2WDLZNO",
        "PolicyName": "CloudWatchEventsInvocationAccess",
        "UpdateDate": "2016-01-14T18:36:33+00:00",
        "VersionId": "v1"
    },
    "CloudWatchEventsReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/CloudWatchEventsReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-10T17:25:34+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "events:DescribeRule",
                        "events:ListRuleNamesByTarget",
                        "events:ListRules",
                        "events:ListTargetsByRule",
                        "events:TestEventPattern",
                        "events:DescribeEventBus"
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                    "Sid": "CloudWatchEventsReadOnlyAccess"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIILJPXXA6F7GYLYBS",
        "PolicyName": "CloudWatchEventsReadOnlyAccess",
        "UpdateDate": "2017-08-10T17:25:34+00:00",
        "VersionId": "v2"
    },
    "CloudWatchFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/CloudWatchFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:00+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "autoscaling:Describe*",
                        "cloudwatch:*",
                        "logs:*",
                        "sns:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIKEABORKUXN6DEAZU",
        "PolicyName": "CloudWatchFullAccess",
        "UpdateDate": "2015-02-06T18:40:00+00:00",
        "VersionId": "v1"
    },
    "CloudWatchLogsFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:02+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "logs:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ3ZGNWK2R5HW5BQFO",
        "PolicyName": "CloudWatchLogsFullAccess",
        "UpdateDate": "2015-02-06T18:40:02+00:00",
        "VersionId": "v1"
    },
    "CloudWatchLogsReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/CloudWatchLogsReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-14T22:22:16+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "logs:Describe*",
                        "logs:Get*",
                        "logs:List*",
                        "logs:TestMetricFilter",
                        "logs:FilterLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ2YIYDYSNNEHK3VKW",
        "PolicyName": "CloudWatchLogsReadOnlyAccess",
        "UpdateDate": "2017-08-14T22:22:16+00:00",
        "VersionId": "v3"
    },
    "CloudWatchReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:40:01+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "autoscaling:Describe*",
                        "cloudwatch:Describe*",
                        "cloudwatch:Get*",
                        "cloudwatch:List*",
                        "logs:Get*",
                        "logs:Describe*",
                        "logs:TestMetricFilter",
                        "sns:Get*",
                        "sns:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJN23PDQP7SZQAE3QE",
        "PolicyName": "CloudWatchReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:40:01+00:00",
        "VersionId": "v1"
    },
    "DataScientist": {
        "Arn": "arn:aws:iam::aws:policy/job-function/DataScientist",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-10T17:28:48+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "autoscaling:*",
                        "cloudwatch:*",
                        "cloudformation:CreateStack",
                        "cloudformation:DescribeStackEvents",
                        "datapipeline:Describe*",
                        "datapipeline:ListPipelines",
                        "datapipeline:GetPipelineDefinition",
                        "datapipeline:QueryObjects",
                        "dynamodb:*",
                        "ec2:CancelSpotInstanceRequests",
                        "ec2:CancelSpotFleetRequests",
                        "ec2:CreateTags",
                        "ec2:DeleteTags",
                        "ec2:Describe*",
                        "ec2:ModifyImageAttribute",
                        "ec2:ModifyInstanceAttribute",
                        "ec2:ModifySpotFleetRequest",
                        "ec2:RequestSpotInstances",
                        "ec2:RequestSpotFleet",
                        "elasticfilesystem:*",
                        "elasticmapreduce:*",
                        "es:*",
                        "firehose:*",
                        "iam:GetInstanceProfile",
                        "iam:GetRole",
                        "iam:GetPolicy",
                        "iam:GetPolicyVersion",
                        "iam:ListRoles",
                        "kinesis:*",
                        "kms:List*",
                        "lambda:Create*",
                        "lambda:Delete*",
                        "lambda:Get*",
                        "lambda:InvokeFunction",
                        "lambda:PublishVersion",
                        "lambda:Update*",
                        "lambda:List*",
                        "machinelearning:*",
                        "sdb:*",
                        "rds:*",
                        "sns:ListSubscriptions",
                        "sns:ListTopics",
                        "logs:DescribeLogStreams",
                        "logs:GetLogEvents",
                        "redshift:*",
                        "s3:CreateBucket",
                        "sns:CreateTopic",
                        "sns:Get*",
                        "sns:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "s3:Abort*",
                        "s3:DeleteObject",
                        "s3:Get*",
                        "s3:List*",
                        "s3:PutAccelerateConfiguration",
                        "s3:PutBucketLogging",
                        "s3:PutBucketNotification",
                        "s3:PutBucketTagging",
                        "s3:PutObject",
                        "s3:Replicate*",
                        "s3:RestoreObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "ec2:RunInstances",
                        "ec2:TerminateInstances"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "iam:GetRole",
                        "iam:PassRole"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/DataPipelineDefaultRole",
                        "arn:aws:iam::*:role/DataPipelineDefaultResourceRole",
                        "arn:aws:iam::*:role/EMR_EC2_DefaultRole",
                        "arn:aws:iam::*:role/EMR_DefaultRole",
                        "arn:aws:iam::*:role/kinesis-*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/job-function/",
        "PolicyId": "ANPAJ5YHI2BQW7EQFYDXS",
        "PolicyName": "DataScientist",
        "UpdateDate": "2016-11-10T17:28:48+00:00",
        "VersionId": "v1"
    },
    "DatabaseAdministrator": {
        "Arn": "arn:aws:iam::aws:policy/job-function/DatabaseAdministrator",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-10T17:25:43+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudwatch:DeleteAlarms",
                        "cloudwatch:Describe*",
                        "cloudwatch:DisableAlarmActions",
                        "cloudwatch:EnableAlarmActions",
                        "cloudwatch:Get*",
                        "cloudwatch:List*",
                        "cloudwatch:PutMetricAlarm",
                        "datapipeline:ActivatePipeline",
                        "datapipeline:CreatePipeline",
                        "datapipeline:DeletePipeline",
                        "datapipeline:DescribeObjects",
                        "datapipeline:DescribePipelines",
                        "datapipeline:GetPipelineDefinition",
                        "datapipeline:ListPipelines",
                        "datapipeline:PutPipelineDefinition",
                        "datapipeline:QueryObjects",
                        "dynamodb:*",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAddresses",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "elasticache:*",
                        "iam:ListRoles",
                        "iam:GetRole",
                        "kms:ListKeys",
                        "lambda:CreateEventSourceMapping",
                        "lambda:CreateFunction",
                        "lambda:DeleteEventSourceMapping",
                        "lambda:DeleteFunction",
                        "lambda:GetFunctionConfiguration",
                        "lambda:ListEventSourceMappings",
                        "lambda:ListFunctions",
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams",
                        "logs:FilterLogEvents",
                        "logs:GetLogEvents",
                        "logs:Create*",
                        "logs:PutLogEvents",
                        "logs:PutMetricFilter",
                        "rds:*",
                        "redshift:*",
                        "s3:CreateBucket",
                        "sns:CreateTopic",
                        "sns:DeleteTopic",
                        "sns:Get*",
                        "sns:List*",
                        "sns:SetTopicAttributes",
                        "sns:Subscribe",
                        "sns:Unsubscribe"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "s3:AbortMultipartUpload",
                        "s3:DeleteObject*",
                        "s3:Get*",
                        "s3:List*",
                        "s3:PutAccelerateConfiguration",
                        "s3:PutBucketTagging",
                        "s3:PutBucketVersioning",
                        "s3:PutBucketWebsite",
                        "s3:PutLifecycleConfiguration",
                        "s3:PutReplicationConfiguration",
                        "s3:PutObject*",
                        "s3:Replicate*",
                        "s3:RestoreObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "iam:GetRole",
                        "iam:PassRole"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/rds-monitoring-role",
                        "arn:aws:iam::*:role/rdbms-lambda-access",
                        "arn:aws:iam::*:role/lambda_exec_role",
                        "arn:aws:iam::*:role/lambda-dynamodb-*",
                        "arn:aws:iam::*:role/lambda-vpc-execution-role",
                        "arn:aws:iam::*:role/DataPipelineDefaultRole",
                        "arn:aws:iam::*:role/DataPipelineDefaultResourceRole"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/job-function/",
        "PolicyId": "ANPAIGBMAW4VUQKOQNVT6",
        "PolicyName": "DatabaseAdministrator",
        "UpdateDate": "2016-11-10T17:25:43+00:00",
        "VersionId": "v1"
    },
    "IAMFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/IAMFullAccess",
        "AttachmentCount": 2,
        "CreateDate": "2015-02-06T18:40:38+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "iam:*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI7XKCFMBPM3QQRRVQ",
        "PolicyName": "IAMFullAccess",
        "UpdateDate": "2015-02-06T18:40:38+00:00",
        "VersionId": "v1"
    },
    "IAMReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/IAMReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-09-06T17:06:37+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "iam:GenerateCredentialReport",
                        "iam:GenerateServiceLastAccessedDetails",
                        "iam:Get*",
                        "iam:List*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJKSO7NDY4T57MWDSQ",
        "PolicyName": "IAMReadOnlyAccess",
        "UpdateDate": "2016-09-06T17:06:37+00:00",
        "VersionId": "v3"
    },
    "IAMSelfManageServiceSpecificCredentials": {
        "Arn": "arn:aws:iam::aws:policy/IAMSelfManageServiceSpecificCredentials",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-22T17:25:18+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "iam:CreateServiceSpecificCredential",
                        "iam:ListServiceSpecificCredentials",
                        "iam:UpdateServiceSpecificCredential",
                        "iam:DeleteServiceSpecificCredential",
                        "iam:ResetServiceSpecificCredential"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:iam::*:user/${aws:username}"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAI4VT74EMXK2PMQJM2",
        "PolicyName": "IAMSelfManageServiceSpecificCredentials",
        "UpdateDate": "2016-12-22T17:25:18+00:00",
        "VersionId": "v1"
    },
    "IAMUserChangePassword": {
        "Arn": "arn:aws:iam::aws:policy/IAMUserChangePassword",
        "AttachmentCount": 1,
        "CreateDate": "2016-11-15T23:18:55+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "iam:ChangePassword"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:user/${aws:username}"
                    ]
                },
                {
                    "Action": [
                        "iam:GetAccountPasswordPolicy"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ4L4MM2A7QIEB56MS",
        "PolicyName": "IAMUserChangePassword",
        "UpdateDate": "2016-11-15T23:18:55+00:00",
        "VersionId": "v2"
    },
    "IAMUserSSHKeys": {
        "Arn": "arn:aws:iam::aws:policy/IAMUserSSHKeys",
        "AttachmentCount": 1,
        "CreateDate": "2015-07-09T17:08:54+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "iam:DeleteSSHPublicKey",
                        "iam:GetSSHPublicKey",
                        "iam:ListSSHPublicKeys",
                        "iam:UpdateSSHPublicKey",
                        "iam:UploadSSHPublicKey"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:iam::*:user/${aws:username}"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJTSHUA4UXGXU7ANUA",
        "PolicyName": "IAMUserSSHKeys",
        "UpdateDate": "2015-07-09T17:08:54+00:00",
        "VersionId": "v1"
    },
    "NetworkAdministrator": {
        "Arn": "arn:aws:iam::aws:policy/job-function/NetworkAdministrator",
        "AttachmentCount": 0,
        "CreateDate": "2017-03-20T18:44:58+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "autoscaling:Describe*",
                        "ec2:AllocateAddress",
                        "ec2:AssignPrivateIpAddresses",
                        "ec2:AssociateAddress",
                        "ec2:AssociateDhcpOptions",
                        "ec2:AssociateRouteTable",
                        "ec2:AttachInternetGateway",
                        "ec2:AttachNetworkInterface",
                        "ec2:AttachVpnGateway",
                        "ec2:CreateCustomerGateway",
                        "ec2:CreateDhcpOptions",
                        "ec2:CreateFlowLogs",
                        "ec2:CreateInternetGateway",
                        "ec2:CreateNatGateway",
                        "ec2:CreateNetworkAcl",
                        "ec2:CreateNetworkAcl",
                        "ec2:CreateNetworkAclEntry",
                        "ec2:CreateNetworkInterface",
                        "ec2:CreateRoute",
                        "ec2:CreateRouteTable",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateSubnet",
                        "ec2:CreateTags",
                        "ec2:CreateVpc",
                        "ec2:CreateVpcEndpoint",
                        "ec2:CreateVpnConnection",
                        "ec2:CreateVpnConnectionRoute",
                        "ec2:CreateVpnGateway",
                        "ec2:CreatePlacementGroup",
                        "ec2:DeletePlacementGroup",
                        "ec2:DescribePlacementGroups",
                        "ec2:DeleteFlowLogs",
                        "ec2:DeleteNatGateway",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DeleteSubnet",
                        "ec2:DeleteTags",
                        "ec2:DeleteVpc",
                        "ec2:DeleteVpcEndpoints",
                        "ec2:DeleteVpnConnection",
                        "ec2:DeleteVpnConnectionRoute",
                        "ec2:DeleteVpnGateway",
                        "ec2:DescribeAddresses",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeClassicLinkInstances",
                        "ec2:DescribeCustomerGateways",
                        "ec2:DescribeVpcClassicLinkDnsSupport",
                        "ec2:DescribeDhcpOptions",
                        "ec2:DescribeFlowLogs",
                        "ec2:DescribeInstances",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeMovingAddresses",
                        "ec2:DescribeNatGateways",
                        "ec2:DescribeNetworkAcls",
                        "ec2:DescribeNetworkInterfaceAttribute",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribePrefixLists",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeTags",
                        "ec2:DescribeVpcAttribute",
                        "ec2:DescribeVpcClassicLink",
                        "ec2:DescribeVpcEndpoints",
                        "ec2:DescribeVpcEndpointServices",
                        "ec2:DescribeVpcPeeringConnections",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeVpnConnections",
                        "ec2:DescribeVpnGateways",
                        "ec2:DetachInternetGateway",
                        "ec2:DetachNetworkInterface",
                        "ec2:DetachVpnGateway",
                        "ec2:DisableVgwRoutePropagation",
                        "ec2:DisassociateAddress",
                        "ec2:DisassociateRouteTable",
                        "ec2:EnableVgwRoutePropagation",
                        "ec2:ModifyNetworkInterfaceAttribute",
                        "ec2:ModifySubnetAttribute",
                        "ec2:ModifyVpcAttribute",
                        "ec2:ModifyVpcEndpoint",
                        "ec2:MoveAddressToVpc",
                        "ec2:ReleaseAddress",
                        "ec2:ReplaceNetworkAclAssociation",
                        "ec2:ReplaceNetworkAclEntry",
                        "ec2:ReplaceRoute",
                        "ec2:ReplaceRouteTableAssociation",
                        "ec2:ResetNetworkInterfaceAttribute",
                        "ec2:RestoreAddressToClassic",
                        "ec2:UnassignPrivateIpAddresses",
                        "directconnect:*",
                        "route53:*",
                        "route53domains:*",
                        "cloudfront:ListDistributions",
                        "elasticloadbalancing:*",
                        "elasticbeanstalk:Describe*",
                        "elasticbeanstalk:List*",
                        "elasticbeanstalk:RetrieveEnvironmentInfo",
                        "elasticbeanstalk:RequestEnvironmentInfo",
                        "sns:ListTopics",
                        "sns:ListSubscriptionsByTopic",
                        "sns:CreateTopic",
                        "cloudwatch:DescribeAlarms",
                        "cloudwatch:PutMetricAlarm",
                        "cloudwatch:DeleteAlarms",
                        "cloudwatch:GetMetricStatistics",
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams",
                        "logs:GetLogEvents"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "ec2:AcceptVpcPeeringConnection",
                        "ec2:AttachClassicLinkVpc",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateVpcPeeringConnection",
                        "ec2:DeleteCustomerGateway",
                        "ec2:DeleteDhcpOptions",
                        "ec2:DeleteInternetGateway",
                        "ec2:DeleteNetworkAcl",
                        "ec2:DeleteNetworkAclEntry",
                        "ec2:DeleteRoute",
                        "ec2:DeleteRouteTable",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DeleteVolume",
                        "ec2:DeleteVpcPeeringConnection",
                        "ec2:DetachClassicLinkVpc",
                        "ec2:DisableVpcClassicLink",
                        "ec2:EnableVpcClassicLink",
                        "ec2:GetConsoleScreenshot",
                        "ec2:RejectVpcPeeringConnection",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:RevokeSecurityGroupIngress"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "s3:ListBucket",
                        "s3:GetBucketLocation",
                        "s3:GetBucketWebsiteConfiguration"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "iam:GetRole",
                        "iam:ListRoles",
                        "iam:PassRole"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:iam::*:role/flow-logs-*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/job-function/",
        "PolicyId": "ANPAJPNMADZFJCVPJVZA2",
        "PolicyName": "NetworkAdministrator",
        "UpdateDate": "2017-03-20T18:44:58+00:00",
        "VersionId": "v2"
    },
    "PowerUserAccess": {
        "Arn": "arn:aws:iam::aws:policy/PowerUserAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-12-06T18:11:16+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Effect": "Allow",
                    "NotAction": [
                        "iam:*",
                        "organizations:*"
                    ],
                    "Resource": "*"
                },
                {
                    "Action": "organizations:DescribeOrganization",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJYRXTHIB4FOVS3ZXS",
        "PolicyName": "PowerUserAccess",
        "UpdateDate": "2016-12-06T18:11:16+00:00",
        "VersionId": "v2"
    },
    "QuickSightAccessForS3StorageManagementAnalyticsReadOnly": {
        "Arn": "arn:aws:iam::aws:policy/service-role/QuickSightAccessForS3StorageManagementAnalyticsReadOnly",
        "AttachmentCount": 0,
        "CreateDate": "2017-07-21T00:02:14+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:GetObject",
                        "s3:GetObjectMetadata"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::s3-analytics-export-shared-*"
                    ]
                },
                {
                    "Action": [
                        "s3:GetAnalyticsConfiguration",
                        "s3:ListAllMyBuckets",
                        "s3:GetBucketLocation"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIFWG3L3WDMR4I7ZJW",
        "PolicyName": "QuickSightAccessForS3StorageManagementAnalyticsReadOnly",
        "UpdateDate": "2017-07-21T00:02:14+00:00",
        "VersionId": "v3"
    },
    "RDSCloudHsmAuthorizationRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/RDSCloudHsmAuthorizationRole",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:29+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "cloudhsm:CreateLunaClient",
                        "cloudhsm:GetClientConfiguration",
                        "cloudhsm:DeleteLunaClient",
                        "cloudhsm:DescribeLunaClient",
                        "cloudhsm:ModifyLunaClient",
                        "cloudhsm:DescribeHapg",
                        "cloudhsm:ModifyHapg",
                        "cloudhsm:GetConfig"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAIWKFXRLQG2ROKKXLE",
        "PolicyName": "RDSCloudHsmAuthorizationRole",
        "UpdateDate": "2015-02-06T18:41:29+00:00",
        "VersionId": "v1"
    },
    "ReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/ReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-07-20T17:43:06+00:00",
        "DefaultVersionId": "v29",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "acm:Describe*",
                        "acm:Get*",
                        "acm:List*",
                        "apigateway:GET",
                        "application-autoscaling:Describe*",
                        "appstream:Describe*",
                        "appstream:Get*",
                        "appstream:List*",
                        "athena:List*",
                        "athena:Batch*",
                        "athena:Get*",
                        "autoscaling:Describe*",
                        "batch:List*",
                        "batch:Describe*",
                        "clouddirectory:List*",
                        "clouddirectory:BatchRead",
                        "clouddirectory:Get*",
                        "clouddirectory:LookupPolicy",
                        "cloudformation:Describe*",
                        "cloudformation:Get*",
                        "cloudformation:List*",
                        "cloudformation:Estimate*",
                        "cloudformation:Preview*",
                        "cloudfront:Get*",
                        "cloudfront:List*",
                        "cloudhsm:List*",
                        "cloudhsm:Describe*",
                        "cloudhsm:Get*",
                        "cloudsearch:Describe*",
                        "cloudsearch:List*",
                        "cloudtrail:Describe*",
                        "cloudtrail:Get*",
                        "cloudtrail:List*",
                        "cloudtrail:LookupEvents",
                        "cloudwatch:Describe*",
                        "cloudwatch:Get*",
                        "cloudwatch:List*",
                        "codebuild:BatchGet*",
                        "codebuild:List*",
                        "codecommit:BatchGet*",
                        "codecommit:Get*",
                        "codecommit:GitPull",
                        "codecommit:List*",
                        "codedeploy:BatchGet*",
                        "codedeploy:Get*",
                        "codedeploy:List*",
                        "codepipeline:List*",
                        "codepipeline:Get*",
                        "codestar:List*",
                        "codestar:Describe*",
                        "codestar:Get*",
                        "codestar:Verify*",
                        "cognito-identity:List*",
                        "cognito-identity:Describe*",
                        "cognito-identity:Lookup*",
                        "cognito-sync:List*",
                        "cognito-sync:Describe*",
                        "cognito-sync:Get*",
                        "cognito-sync:QueryRecords",
                        "cognito-idp:AdminList*",
                        "cognito-idp:List*",
                        "cognito-idp:Describe*",
                        "cognito-idp:Get*",
                        "config:Deliver*",
                        "config:Describe*",
                        "config:Get*",
                        "config:List*",
                        "connect:List*",
                        "connect:Describe*",
                        "connect:Get*",
                        "datapipeline:Describe*",
                        "datapipeline:EvaluateExpression",
                        "datapipeline:Get*",
                        "datapipeline:List*",
                        "datapipeline:QueryObjects",
                        "datapipeline:Validate*",
                        "directconnect:Describe*",
                        "directconnect:Confirm*",
                        "devicefarm:List*",
                        "devicefarm:Get*",
                        "discovery:Describe*",
                        "discovery:List*",
                        "discovery:Get*",
                        "dms:Describe*",
                        "dms:List*",
                        "dms:Test*",
                        "ds:Check*",
                        "ds:Describe*",
                        "ds:Get*",
                        "ds:List*",
                        "ds:Verify*",
                        "dynamodb:BatchGet*",
                        "dynamodb:Describe*",
                        "dynamodb:Get*",
                        "dynamodb:List*",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "ec2:Describe*",
                        "ec2:Get*",
                        "ec2messages:Get*",
                        "ecr:BatchCheck*",
                        "ecr:BatchGet*",
                        "ecr:Describe*",
                        "ecr:Get*",
                        "ecr:List*",
                        "ecs:Describe*",
                        "ecs:List*",
                        "elasticache:Describe*",
                        "elasticache:List*",
                        "elasticbeanstalk:Check*",
                        "elasticbeanstalk:Describe*",
                        "elasticbeanstalk:List*",
                        "elasticbeanstalk:Request*",
                        "elasticbeanstalk:Retrieve*",
                        "elasticbeanstalk:Validate*",
                        "elasticfilesystem:Describe*",
                        "elasticloadbalancing:Describe*",
                        "elasticmapreduce:Describe*",
                        "elasticmapreduce:List*",
                        "elasticmapreduce:View*",
                        "elastictranscoder:List*",
                        "elastictranscoder:Read*",
                        "es:Describe*",
                        "es:List*",
                        "es:ESHttpGet",
                        "es:ESHttpHead",
                        "events:Describe*",
                        "events:List*",
                        "events:Test*",
                        "firehose:Describe*",
                        "firehose:List*",
                        "gamelift:List*",
                        "gamelift:Get*",
                        "gamelift:Describe*",
                        "gamelift:RequestUploadCredentials",
                        "gamelift:ResolveAlias",
                        "gamelift:Search*",
                        "glacier:List*",
                        "glacier:Describe*",
                        "glacier:Get*",
                        "health:Describe*",
                        "health:Get*",
                        "health:List*",
                        "iam:Generate*",
                        "iam:Get*",
                        "iam:List*",
                        "iam:Simulate*",
                        "importexport:Get*",
                        "importexport:List*",
                        "inspector:Describe*",
                        "inspector:Get*",
                        "inspector:List*",
                        "inspector:Preview*",
                        "inspector:LocalizeText",
                        "iot:Describe*",
                        "iot:Get*",
                        "iot:List*",
                        "kinesisanalytics:Describe*",
                        "kinesisanalytics:Discover*",
                        "kinesisanalytics:Get*",
                        "kinesisanalytics:List*",
                        "kinesis:Describe*",
                        "kinesis:Get*",
                        "kinesis:List*",
                        "kms:Describe*",
                        "kms:Get*",
                        "kms:List*",
                        "lambda:List*",
                        "lambda:Get*",
                        "lex:Get*",
                        "lightsail:Get*",
                        "lightsail:Is*",
                        "lightsail:Download*",
                        "logs:Describe*",
                        "logs:Get*",
                        "logs:FilterLogEvents",
                        "logs:ListTagsLogGroup",
                        "logs:TestMetricFilter",
                        "machinelearning:Describe*",
                        "machinelearning:Get*",
                        "mobileanalytics:Get*",
                        "mobilehub:Get*",
                        "mobilehub:List*",
                        "mobilehub:Validate*",
                        "mobilehub:Verify*",
                        "mobiletargeting:Get*",
                        "opsworks:Describe*",
                        "opsworks:Get*",
                        "opsworks-cm:Describe*",
                        "organizations:Describe*",
                        "organizations:List*",
                        "polly:Describe*",
                        "polly:Get*",
                        "polly:List*",
                        "polly:SynthesizeSpeech",
                        "rekognition:CompareFaces",
                        "rekognition:Detect*",
                        "rekognition:List*",
                        "rekognition:Search*",
                        "rds:Describe*",
                        "rds:List*",
                        "rds:Download*",
                        "redshift:Describe*",
                        "redshift:View*",
                        "redshift:Get*",
                        "route53:Get*",
                        "route53:List*",
                        "route53:Test*",
                        "route53domains:Check*",
                        "route53domains:Get*",
                        "route53domains:List*",
                        "route53domains:View*",
                        "s3:Get*",
                        "s3:List*",
                        "s3:Head*",
                        "sdb:Get*",
                        "sdb:List*",
                        "sdb:Select*",
                        "servicecatalog:List*",
                        "servicecatalog:Scan*",
                        "servicecatalog:Search*",
                        "servicecatalog:Describe*",
                        "ses:Get*",
                        "ses:List*",
                        "ses:Describe*",
                        "ses:Verify*",
                        "shield:Describe*",
                        "shield:List*",
                        "sns:Get*",
                        "sns:List*",
                        "sns:Check*",
                        "sqs:Get*",
                        "sqs:List*",
                        "sqs:Receive*",
                        "ssm:Describe*",
                        "ssm:Get*",
                        "ssm:List*",
                        "states:List*",
                        "states:Describe*",
                        "states:GetExecutionHistory",
                        "storagegateway:Describe*",
                        "storagegateway:List*",
                        "sts:Get*",
                        "swf:Count*",
                        "swf:Describe*",
                        "swf:Get*",
                        "swf:List*",
                        "tag:Get*",
                        "trustedadvisor:Describe*",
                        "waf:Get*",
                        "waf:List*",
                        "waf-regional:List*",
                        "waf-regional:Get*",
                        "workdocs:Describe*",
                        "workdocs:Get*",
                        "workdocs:CheckAlias",
                        "workmail:Describe*",
                        "workmail:Get*",
                        "workmail:List*",
                        "workmail:Search*",
                        "workspaces:Describe*",
                        "xray:BatchGet*",
                        "xray:Get*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAILL3HVNFSB6DCOWYQ",
        "PolicyName": "ReadOnlyAccess",
        "UpdateDate": "2017-07-20T17:43:06+00:00",
        "VersionId": "v29"
    },
    "ResourceGroupsandTagEditorFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/ResourceGroupsandTagEditorFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:39:53+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "tag:getResources",
                        "tag:getTagKeys",
                        "tag:getTagValues",
                        "tag:addResourceTags",
                        "tag:removeResourceTags"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJNOS54ZFXN4T2Y34A",
        "PolicyName": "ResourceGroupsandTagEditorFullAccess",
        "UpdateDate": "2015-02-06T18:39:53+00:00",
        "VersionId": "v1"
    },
    "ResourceGroupsandTagEditorReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/ResourceGroupsandTagEditorReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:39:54+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "tag:getResources",
                        "tag:getTagKeys",
                        "tag:getTagValues"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJHXQTPI5I5JKAIU74",
        "PolicyName": "ResourceGroupsandTagEditorReadOnlyAccess",
        "UpdateDate": "2015-02-06T18:39:54+00:00",
        "VersionId": "v1"
    },
    "SecurityAudit": {
        "Arn": "arn:aws:iam::aws:policy/SecurityAudit",
        "AttachmentCount": 0,
        "CreateDate": "2017-07-12T20:16:44+00:00",
        "DefaultVersionId": "v12",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "acm:ListCertificates",
                        "acm:DescribeCertificate",
                        "cloudformation:getStackPolicy",
                        "logs:describeLogGroups",
                        "logs:describeMetricFilters",
                        "autoscaling:Describe*",
                        "cloudformation:DescribeStack*",
                        "cloudformation:GetTemplate",
                        "cloudformation:ListStack*",
                        "cloudfront:Get*",
                        "cloudfront:List*",
                        "cloudtrail:DescribeTrails",
                        "cloudtrail:GetTrailStatus",
                        "cloudtrail:ListTags",
                        "cloudwatch:Describe*",
                        "codecommit:BatchGetRepositories",
                        "codecommit:GetBranch",
                        "codecommit:GetObjectIdentifier",
                        "codecommit:GetRepository",
                        "codecommit:List*",
                        "codedeploy:Batch*",
                        "codedeploy:Get*",
                        "codedeploy:List*",
                        "config:Deliver*",
                        "config:Describe*",
                        "config:Get*",
                        "datapipeline:DescribeObjects",
                        "datapipeline:DescribePipelines",
                        "datapipeline:EvaluateExpression",
                        "datapipeline:GetPipelineDefinition",
                        "datapipeline:ListPipelines",
                        "datapipeline:QueryObjects",
                        "datapipeline:ValidatePipelineDefinition",
                        "directconnect:Describe*",
                        "dynamodb:ListTables",
                        "ec2:Describe*",
                        "ecs:Describe*",
                        "ecs:List*",
                        "elasticache:Describe*",
                        "elasticbeanstalk:Describe*",
                        "elasticloadbalancing:Describe*",
                        "elasticmapreduce:DescribeJobFlows",
                        "elasticmapreduce:ListClusters",
                        "elasticmapreduce:ListInstances",
                        "es:ListDomainNames",
                        "es:Describe*",
                        "firehose:Describe*",
                        "firehose:List*",
                        "glacier:DescribeVault",
                        "glacier:GetVaultAccessPolicy",
                        "glacier:ListVaults",
                        "iam:GenerateCredentialReport",
                        "iam:Get*",
                        "iam:List*",
                        "kms:Describe*",
                        "kms:Get*",
                        "kms:List*",
                        "lambda:GetPolicy",
                        "lambda:ListFunctions",
                        "rds:Describe*",
                        "rds:DownloadDBLogFilePortion",
                        "rds:ListTagsForResource",
                        "redshift:Describe*",
                        "route53:GetChange",
                        "route53:GetCheckerIpRanges",
                        "route53:GetGeoLocation",
                        "route53:GetHealthCheck",
                        "route53:GetHealthCheckCount",
                        "route53:GetHealthCheckLastFailureReason",
                        "route53:GetHostedZone",
                        "route53:GetHostedZoneCount",
                        "route53:GetReusableDelegationSet",
                        "route53:ListGeoLocations",
                        "route53:ListHealthChecks",
                        "route53:ListHostedZones",
                        "route53:ListHostedZonesByName",
                        "route53:ListResourceRecordSets",
                        "route53:ListReusableDelegationSets",
                        "route53:ListTagsForResource",
                        "route53:ListTagsForResources",
                        "route53domains:GetDomainDetail",
                        "route53domains:GetOperationDetail",
                        "route53domains:ListDomains",
                        "route53domains:ListOperations",
                        "route53domains:ListTagsForDomain",
                        "s3:GetBucket*",
                        "s3:GetAccelerateConfiguration",
                        "s3:GetAnalyticsConfiguration",
                        "s3:GetInventoryConfiguration",
                        "s3:GetMetricsConfiguration",
                        "s3:GetReplicationConfiguration",
                        "s3:GetLifecycleConfiguration",
                        "s3:GetObjectAcl",
                        "s3:GetObjectVersionAcl",
                        "s3:ListAllMyBuckets",
                        "sdb:DomainMetadata",
                        "sdb:ListDomains",
                        "ses:GetIdentityDkimAttributes",
                        "ses:GetIdentityVerificationAttributes",
                        "ses:ListIdentities",
                        "sns:GetTopicAttributes",
                        "sns:ListSubscriptionsByTopic",
                        "sns:ListTopics",
                        "sqs:GetQueueAttributes",
                        "sqs:ListQueues",
                        "tag:GetResources",
                        "tag:GetTagKeys"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIX2T3QCXHR2OGGCTO",
        "PolicyName": "SecurityAudit",
        "UpdateDate": "2017-07-12T20:16:44+00:00",
        "VersionId": "v12"
    },
    "ServerMigrationConnector": {
        "Arn": "arn:aws:iam::aws:policy/ServerMigrationConnector",
        "AttachmentCount": 0,
        "CreateDate": "2016-10-24T21:45:56+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": "iam:GetUser",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "sms:SendMessage",
                        "sms:GetMessages"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "s3:CreateBucket",
                        "s3:DeleteBucket",
                        "s3:DeleteObject",
                        "s3:GetBucketLocation",
                        "s3:GetObject",
                        "s3:ListBucket",
                        "s3:PutObject",
                        "s3:PutObjectAcl",
                        "s3:PutLifecycleConfiguration",
                        "s3:AbortMultipartUpload",
                        "s3:ListBucketMultipartUploads",
                        "s3:ListMultipartUploadParts"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::sms-b-*",
                        "arn:aws:s3:::import-to-ec2-*",
                        "arn:aws:s3:::server-migration-service-upgrade",
                        "arn:aws:s3:::server-migration-service-upgrade/*",
                        "arn:aws:s3:::connector-platform-upgrade-info/*",
                        "arn:aws:s3:::connector-platform-upgrade-info",
                        "arn:aws:s3:::connector-platform-upgrade-bundles/*",
                        "arn:aws:s3:::connector-platform-upgrade-bundles",
                        "arn:aws:s3:::connector-platform-release-notes/*",
                        "arn:aws:s3:::connector-platform-release-notes"
                    ]
                },
                {
                    "Action": "awsconnector:*",
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "SNS:Publish"
                    ],
                    "Effect": "Allow",
                    "Resource": "arn:aws:sns:*:*:metrics-sns-topic-for-*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJKZRWXIPK5HSG3QDQ",
        "PolicyName": "ServerMigrationConnector",
        "UpdateDate": "2016-10-24T21:45:56+00:00",
        "VersionId": "v1"
    },
    "ServerMigrationServiceRole": {
        "Arn": "arn:aws:iam::aws:policy/service-role/ServerMigrationServiceRole",
        "AttachmentCount": 0,
        "CreateDate": "2017-06-16T18:02:04+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "ec2:ModifySnapshotAttribute",
                        "ec2:CopySnapshot",
                        "ec2:CopyImage",
                        "ec2:Describe*",
                        "ec2:DeleteSnapshot",
                        "ec2:DeregisterImage",
                        "ec2:CreateTags",
                        "ec2:DeleteTags"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJMBH3M6BO63XFW2D4",
        "PolicyName": "ServerMigrationServiceRole",
        "UpdateDate": "2017-06-16T18:02:04+00:00",
        "VersionId": "v2"
    },
    "ServiceCatalogAdminFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/ServiceCatalogAdminFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2016-11-11T18:40:24+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "catalog-admin:*",
                        "catalog-user:*",
                        "cloudformation:CreateStack",
                        "cloudformation:CreateUploadBucket",
                        "cloudformation:DeleteStack",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:DescribeStacks",
                        "cloudformation:GetTemplateSummary",
                        "cloudformation:SetStackPolicy",
                        "cloudformation:ValidateTemplate",
                        "cloudformation:UpdateStack",
                        "iam:GetGroup",
                        "iam:GetRole",
                        "iam:GetUser",
                        "iam:ListGroups",
                        "iam:ListRoles",
                        "iam:ListUsers",
                        "iam:PassRole",
                        "s3:CreateBucket",
                        "s3:GetObject",
                        "s3:PutObject",
                        "servicecatalog:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIKTX42IAS75B7B7BY",
        "PolicyName": "ServiceCatalogAdminFullAccess",
        "UpdateDate": "2016-11-11T18:40:24+00:00",
        "VersionId": "v2"
    },
    "ServiceCatalogAdminReadOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/ServiceCatalogAdminReadOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-08T18:57:36+00:00",
        "DefaultVersionId": "v5",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "catalog-admin:DescribeConstraints",
                        "catalog-admin:DescribeListingForProduct",
                        "catalog-admin:DescribeListings",
                        "catalog-admin:DescribePortfolios",
                        "catalog-admin:DescribeProductVersions",
                        "catalog-admin:GetPortfolioCount",
                        "catalog-admin:GetPortfolios",
                        "catalog-admin:GetProductCounts",
                        "catalog-admin:ListAllPortfolioConstraints",
                        "catalog-admin:ListPortfolioConstraints",
                        "catalog-admin:ListPortfolios",
                        "catalog-admin:ListPrincipalConstraints",
                        "catalog-admin:ListProductConstraints",
                        "catalog-admin:ListResourceUsers",
                        "catalog-admin:ListTagsForResource",
                        "catalog-admin:SearchListings",
                        "catalog-user:*",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:DescribeStacks",
                        "cloudformation:GetTemplateSummary",
                        "iam:GetGroup",
                        "iam:GetRole",
                        "iam:GetUser",
                        "iam:ListGroups",
                        "iam:ListRoles",
                        "iam:ListUsers",
                        "s3:GetObject",
                        "servicecatalog:DescribeTagOption",
                        "servicecatalog:GetTagOptionMigrationStatus",
                        "servicecatalog:ListResourcesForTagOption",
                        "servicecatalog:ListTagOptions",
                        "servicecatalog:AccountLevelDescribeRecord",
                        "servicecatalog:AccountLevelListRecordHistory",
                        "servicecatalog:AccountLevelScanProvisionedProducts",
                        "servicecatalog:DescribeProduct",
                        "servicecatalog:DescribeProductView",
                        "servicecatalog:DescribeProvisioningParameters",
                        "servicecatalog:DescribeProvisionedProduct",
                        "servicecatalog:DescribeRecord",
                        "servicecatalog:ListLaunchPaths",
                        "servicecatalog:ListRecordHistory",
                        "servicecatalog:ScanProvisionedProducts",
                        "servicecatalog:SearchProducts",
                        "servicecatalog:DescribeConstraint",
                        "servicecatalog:DescribeProductAsAdmin",
                        "servicecatalog:DescribePortfolio",
                        "servicecatalog:DescribeProvisioningArtifact",
                        "servicecatalog:ListAcceptedPortfolioShares",
                        "servicecatalog:ListConstraintsForPortfolio",
                        "servicecatalog:ListPortfolioAccess",
                        "servicecatalog:ListPortfolios",
                        "servicecatalog:ListPortfoliosForProduct",
                        "servicecatalog:ListPrincipalsForPortfolio",
                        "servicecatalog:ListProvisioningArtifacts",
                        "servicecatalog:SearchProductsAsAdmin"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ7XOUSS75M4LIPKO4",
        "PolicyName": "ServiceCatalogAdminReadOnlyAccess",
        "UpdateDate": "2017-08-08T18:57:36+00:00",
        "VersionId": "v5"
    },
    "ServiceCatalogEndUserAccess": {
        "Arn": "arn:aws:iam::aws:policy/ServiceCatalogEndUserAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-08T18:58:57+00:00",
        "DefaultVersionId": "v4",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "catalog-user:*",
                        "s3:GetObject",
                        "servicecatalog:DescribeProduct",
                        "servicecatalog:DescribeProductView",
                        "servicecatalog:DescribeProvisioningParameters",
                        "servicecatalog:ListLaunchPaths",
                        "servicecatalog:SearchProducts"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "servicecatalog:ListRecordHistory",
                        "servicecatalog:DescribeProvisionedProduct",
                        "servicecatalog:DescribeRecord",
                        "servicecatalog:ScanProvisionedProducts"
                    ],
                    "Condition": {
                        "StringEquals": {
                            "servicecatalog:userLevel": "self"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJ56OMCO72RI4J5FSA",
        "PolicyName": "ServiceCatalogEndUserAccess",
        "UpdateDate": "2017-08-08T18:58:57+00:00",
        "VersionId": "v4"
    },
    "ServiceCatalogEndUserFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/ServiceCatalogEndUserFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-08-08T18:58:54+00:00",
        "DefaultVersionId": "v4",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "catalog-user:*",
                        "cloudformation:CreateStack",
                        "cloudformation:DeleteStack",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:DescribeStacks",
                        "cloudformation:GetTemplateSummary",
                        "cloudformation:SetStackPolicy",
                        "cloudformation:ValidateTemplate",
                        "cloudformation:UpdateStack",
                        "servicecatalog:DescribeProduct",
                        "servicecatalog:DescribeProductView",
                        "servicecatalog:DescribeProvisioningParameters",
                        "servicecatalog:ListLaunchPaths",
                        "servicecatalog:ProvisionProduct",
                        "servicecatalog:SearchProducts",
                        "s3:GetObject"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "servicecatalog:DescribeProvisionedProduct",
                        "servicecatalog:DescribeRecord",
                        "servicecatalog:ListRecordHistory",
                        "servicecatalog:ScanProvisionedProducts",
                        "servicecatalog:TerminateProvisionedProduct",
                        "servicecatalog:UpdateProvisionedProduct"
                    ],
                    "Condition": {
                        "StringEquals": {
                            "servicecatalog:userLevel": "self"
                        }
                    },
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAJIW7AFFOONVKW75KU",
        "PolicyName": "ServiceCatalogEndUserFullAccess",
        "UpdateDate": "2017-08-08T18:58:54+00:00",
        "VersionId": "v4"
    },
    "SimpleWorkflowFullAccess": {
        "Arn": "arn:aws:iam::aws:policy/SimpleWorkflowFullAccess",
        "AttachmentCount": 0,
        "CreateDate": "2015-02-06T18:41:04+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "swf:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/",
        "PolicyId": "ANPAIFE3AV6VE7EANYBVM",
        "PolicyName": "SimpleWorkflowFullAccess",
        "UpdateDate": "2015-02-06T18:41:04+00:00",
        "VersionId": "v1"
    },
    "SupportUser": {
        "Arn": "arn:aws:iam::aws:policy/job-function/SupportUser",
        "AttachmentCount": 0,
        "CreateDate": "2017-05-17T23:11:51+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "support:*",
                        "acm:DescribeCertificate",
                        "acm:GetCertificate",
                        "acm:List*",
                        "apigateway:GET",
                        "appstream:Get*",
                        "autoscaling:Describe*",
                        "aws-marketplace:ViewSubscriptions",
                        "cloudformation:Describe*",
                        "cloudformation:Get*",
                        "cloudformation:List*",
                        "cloudformation:EstimateTemplateCost",
                        "cloudfront:Get*",
                        "cloudfront:List*",
                        "cloudsearch:Describe*",
                        "cloudsearch:List*",
                        "cloudtrail:DescribeTrails",
                        "cloudtrail:GetTrailStatus",
                        "cloudtrail:LookupEvents",
                        "cloudtrail:ListTags",
                        "cloudtrail:ListPublicKeys",
                        "cloudwatch:Describe*",
                        "cloudwatch:Get*",
                        "cloudwatch:List*",
                        "codecommit:BatchGetRepositories",
                        "codecommit:Get*",
                        "codecommit:List*",
                        "codedeploy:Batch*",
                        "codedeploy:Get*",
                        "codedeploy:List*",
                        "codepipeline:AcknowledgeJob",
                        "codepipeline:AcknowledgeThirdPartyJob",
                        "codepipeline:ListActionTypes",
                        "codepipeline:ListPipelines",
                        "codepipeline:PollForJobs",
                        "codepipeline:PollForThirdPartyJobs",
                        "codepipeline:GetPipelineState",
                        "codepipeline:GetPipeline",
                        "cognito-identity:List*",
                        "cognito-identity:LookupDeveloperIdentity",
                        "cognito-identity:Describe*",
                        "cognito-idp:Describe*",
                        "cognito-sync:Describe*",
                        "cognito-sync:GetBulkPublishDetails",
                        "cognito-sync:GetCognitoEvents",
                        "cognito-sync:GetIdentityPoolConfiguration",
                        "cognito-sync:List*",
                        "config:DescribeConfigurationRecorders",
                        "config:DescribeConfigurationRecorderStatus",
                        "config:DescribeConfigRuleEvaluationStatus",
                        "config:DescribeConfigRules",
                        "config:DescribeDeliveryChannels",
                        "config:DescribeDeliveryChannelStatus",
                        "config:GetResourceConfigHistory",
                        "config:ListDiscoveredResources",
                        "datapipeline:DescribeObjects",
                        "datapipeline:DescribePipelines",
                        "datapipeline:GetPipelineDefinition",
                        "datapipeline:ListPipelines",
                        "datapipeline:QueryObjects",
                        "datapipeline:ReportTaskProgress",
                        "datapipeline:ReportTaskRunnerHeartbeat",
                        "devicefarm:List*",
                        "devicefarm:Get*",
                        "directconnect:Describe*",
                        "discovery:Describe*",
                        "discovery:ListConfigurations",
                        "dms:Describe*",
                        "dms:List*",
                        "ds:DescribeDirectories",
                        "ds:DescribeSnapshots",
                        "ds:GetDirectoryLimits",
                        "ds:GetSnapshotLimits",
                        "ds:ListAuthorizedApplications",
                        "dynamodb:DescribeLimits",
                        "dynamodb:DescribeTable",
                        "dynamodb:ListTables",
                        "ec2:Describe*",
                        "ec2:DescribeHosts",
                        "ec2:describeIdentityIdFormat",
                        "ec2:DescribeIdFormat",
                        "ec2:DescribeInstanceAttribute",
                        "ec2:DescribeNatGateways",
                        "ec2:DescribeReservedInstancesModifications",
                        "ec2:DescribeTags",
                        "ec2:GetFlowLogsCount",
                        "ecr:GetRepositoryPolicy",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:DescribeRepositories",
                        "ecr:ListImages",
                        "ecs:Describe*",
                        "ecs:List*",
                        "elasticache:Describe*",
                        "elasticache:List*",
                        "elasticbeanstalk:Check*",
                        "elasticbeanstalk:Describe*",
                        "elasticbeanstalk:List*",
                        "elasticbeanstalk:RequestEnvironmentInfo",
                        "elasticbeanstalk:RetrieveEnvironmentInfo",
                        "elasticbeanstalk:ValidateConfigurationSettings",
                        "elasticfilesystem:Describe*",
                        "elasticloadbalancing:Describe*",
                        "elasticmapreduce:Describe*",
                        "elasticmapreduce:List*",
                        "elastictranscoder:List*",
                        "elastictranscoder:ReadJob",
                        "elasticfilesystem:DescribeFileSystems",
                        "es:Describe*",
                        "es:List*",
                        "es:ESHttpGet",
                        "es:ESHttpHead",
                        "events:DescribeRule",
                        "events:List*",
                        "events:TestEventPattern",
                        "firehose:Describe*",
                        "firehose:List*",
                        "gamelift:List*",
                        "gamelift:Describe*",
                        "glacier:ListVaults",
                        "glacier:DescribeVault",
                        "glacier:DescribeJob",
                        "glacier:Get*",
                        "glacier:List*",
                        "iam:GenerateCredentialReport",
                        "iam:GenerateServiceLastAccessedDetails",
                        "iam:Get*",
                        "iam:List*",
                        "importexport:GetStatus",
                        "importexport:ListJobs",
                        "importexport:GetJobDetail",
                        "inspector:Describe*",
                        "inspector:List*",
                        "inspector:GetAssessmentTelemetry",
                        "inspector:LocalizeText",
                        "iot:Describe*",
                        "iot:Get*",
                        "iot:List*",
                        "kinesisanalytics:DescribeApplication",
                        "kinesisanalytics:DiscoverInputSchema",
                        "kinesisanalytics:GetApplicationState",
                        "kinesisanalytics:ListApplications",
                        "kinesis:Describe*",
                        "kinesis:Get*",
                        "kinesis:List*",
                        "kms:Describe*",
                        "kms:Get*",
                        "kms:List*",
                        "lambda:List*",
                        "lambda:Get*",
                        "logs:Describe*",
                        "logs:TestMetricFilter",
                        "machinelearning:Describe*",
                        "machinelearning:Get*",
                        "mobilehub:GetProject",
                        "mobilehub:List*",
                        "mobilehub:ValidateProject",
                        "mobilehub:VerifyServiceRole",
                        "opsworks:Describe*",
                        "rds:Describe*",
                        "rds:ListTagsForResource",
                        "redshift:Describe*",
                        "route53:Get*",
                        "route53:List*",
                        "route53domains:CheckDomainAvailability",
                        "route53domains:GetDomainDetail",
                        "route53domains:GetOperationDetail",
                        "route53domains:List*",
                        "s3:List*",
                        "sdb:GetAttributes",
                        "sdb:List*",
                        "sdb:Select*",
                        "servicecatalog:SearchProducts",
                        "servicecatalog:DescribeProduct",
                        "servicecatalog:DescribeProductView",
                        "servicecatalog:ListLaunchPaths",
                        "servicecatalog:DescribeProvisioningParameters",
                        "servicecatalog:ListRecordHistory",
                        "servicecatalog:DescribeRecord",
                        "servicecatalog:ScanProvisionedProducts",
                        "ses:Get*",
                        "ses:List*",
                        "sns:Get*",
                        "sns:List*",
                        "sqs:GetQueueAttributes",
                        "sqs:GetQueueUrl",
                        "sqs:ListQueues",
                        "sqs:ReceiveMessage",
                        "ssm:List*",
                        "ssm:Describe*",
                        "storagegateway:Describe*",
                        "storagegateway:List*",
                        "swf:Count*",
                        "swf:Describe*",
                        "swf:Get*",
                        "swf:List*",
                        "waf:Get*",
                        "waf:List*",
                        "workspaces:Describe*",
                        "workdocs:Describe*",
                        "workmail:Describe*",
                        "workmail:Get*",
                        "workspaces:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/job-function/",
        "PolicyId": "ANPAI3V4GSSN5SJY3P2RO",
        "PolicyName": "SupportUser",
        "UpdateDate": "2017-05-17T23:11:51+00:00",
        "VersionId": "v2"
    },
    "SystemAdministrator": {
        "Arn": "arn:aws:iam::aws:policy/job-function/SystemAdministrator",
        "AttachmentCount": 0,
        "CreateDate": "2017-03-24T17:45:43+00:00",
        "DefaultVersionId": "v2",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "acm:Describe*",
                        "acm:Get*",
                        "acm:List*",
                        "acm:Request*",
                        "acm:Resend*",
                        "autoscaling:*",
                        "cloudtrail:DescribeTrails",
                        "cloudtrail:GetTrailStatus",
                        "cloudtrail:ListPublicKeys",
                        "cloudtrail:ListTags",
                        "cloudtrail:LookupEvents",
                        "cloudtrail:StartLogging",
                        "cloudtrail:StopLogging",
                        "cloudwatch:*",
                        "codecommit:BatchGetRepositories",
                        "codecommit:CreateBranch",
                        "codecommit:CreateRepository",
                        "codecommit:Get*",
                        "codecommit:GitPull",
                        "codecommit:GitPush",
                        "codecommit:List*",
                        "codecommit:Put*",
                        "codecommit:Test*",
                        "codecommit:Update*",
                        "codedeploy:*",
                        "codepipeline:*",
                        "config:*",
                        "ds:*",
                        "ec2:Allocate*",
                        "ec2:AssignPrivateIpAddresses*",
                        "ec2:Associate*",
                        "ec2:Allocate*",
                        "ec2:AttachInternetGateway",
                        "ec2:AttachNetworkInterface",
                        "ec2:AttachVpnGateway",
                        "ec2:Bundle*",
                        "ec2:Cancel*",
                        "ec2:Copy*",
                        "ec2:CreateCustomerGateway",
                        "ec2:CreateDhcpOptions",
                        "ec2:CreateFlowLogs",
                        "ec2:CreateImage",
                        "ec2:CreateInstanceExportTask",
                        "ec2:CreateInternetGateway",
                        "ec2:CreateKeyPair",
                        "ec2:CreateNatGateway",
                        "ec2:CreateNetworkInterface",
                        "ec2:CreatePlacementGroup",
                        "ec2:CreateReservedInstancesListing",
                        "ec2:CreateRoute",
                        "ec2:CreateRouteTable",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateSnapshot",
                        "ec2:CreateSpotDatafeedSubscription",
                        "ec2:CreateSubnet",
                        "ec2:CreateTags",
                        "ec2:CreateVolume",
                        "ec2:CreateVpc",
                        "ec2:CreateVpcEndpoint",
                        "ec2:CreateVpnConnection",
                        "ec2:CreateVpnConnectionRoute",
                        "ec2:CreateVpnGateway",
                        "ec2:DeleteFlowLogs",
                        "ec2:DeleteKeyPair",
                        "ec2:DeleteNatGateway",
                        "ec2:DeleteNetworkInterface",
                        "ec2:DeletePlacementGroup",
                        "ec2:DeleteSnapshot",
                        "ec2:DeleteSpotDatafeedSubscription",
                        "ec2:DeleteSubnet",
                        "ec2:DeleteTags",
                        "ec2:DeleteVpc",
                        "ec2:DeleteVpcEndpoints",
                        "ec2:DeleteVpnConnection",
                        "ec2:DeleteVpnConnectionRoute",
                        "ec2:DeleteVpnGateway",
                        "ec2:DeregisterImage",
                        "ec2:Describe*",
                        "ec2:DetachInternetGateway",
                        "ec2:DetachNetworkInterface",
                        "ec2:DetachVpnGateway",
                        "ec2:DisableVgwRoutePropagation",
                        "ec2:DisableVpcClassicLinkDnsSupport",
                        "ec2:DisassociateAddress",
                        "ec2:DisassociateRouteTable",
                        "ec2:EnableVgwRoutePropagation",
                        "ec2:EnableVolumeIO",
                        "ec2:EnableVpcClassicLinkDnsSupport",
                        "ec2:GetConsoleOutput",
                        "ec2:GetHostReservationPurchasePreview",
                        "ec2:GetPasswordData",
                        "ec2:Import*",
                        "ec2:Modify*",
                        "ec2:MonitorInstances",
                        "ec2:MoveAddressToVpc",
                        "ec2:Purchase*",
                        "ec2:RegisterImage",
                        "ec2:Release*",
                        "ec2:Replace*",
                        "ec2:ReportInstanceStatus",
                        "ec2:Request*",
                        "ec2:Reset*",
                        "ec2:RestoreAddressToClassic",
                        "ec2:RunScheduledInstances",
                        "ec2:UnassignPrivateIpAddresses",
                        "ec2:UnmonitorInstances",
                        "elasticloadbalancing:*",
                        "events:*",
                        "iam:GetAccount*",
                        "iam:GetContextKeys*",
                        "iam:GetCredentialReport",
                        "iam:ListAccountAliases",
                        "iam:ListGroups",
                        "iam:ListOpenIDConnectProviders",
                        "iam:ListPolicies",
                        "iam:ListPoliciesGrantingServiceAccess",
                        "iam:ListRoles",
                        "iam:ListSAMLProviders",
                        "iam:ListServerCertificates",
                        "iam:Simulate*",
                        "iam:UpdateServerCertificate",
                        "iam:UpdateSigningCertificate",
                        "kinesis:ListStreams",
                        "kinesis:PutRecord",
                        "kms:CreateAlias",
                        "kms:CreateKey",
                        "kms:DeleteAlias",
                        "kms:Describe*",
                        "kms:GenerateRandom",
                        "kms:Get*",
                        "kms:List*",
                        "kms:Encrypt",
                        "kms:ReEncrypt*",
                        "lambda:Create*",
                        "lambda:Delete*",
                        "lambda:Get*",
                        "lambda:InvokeFunction",
                        "lambda:List*",
                        "lambda:PublishVersion",
                        "lambda:Update*",
                        "logs:*",
                        "rds:Describe*",
                        "rds:ListTagsForResource",
                        "route53:*",
                        "route53domains:*",
                        "ses:*",
                        "sns:*",
                        "sqs:*",
                        "trustedadvisor:*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "ec2:AcceptVpcPeeringConnection",
                        "ec2:AttachClassicLinkVpc",
                        "ec2:AttachVolume",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateVpcPeeringConnection",
                        "ec2:DeleteCustomerGateway",
                        "ec2:DeleteDhcpOptions",
                        "ec2:DeleteInternetGateway",
                        "ec2:DeleteNetworkAcl*",
                        "ec2:DeleteRoute",
                        "ec2:DeleteRouteTable",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DeleteVolume",
                        "ec2:DeleteVpcPeeringConnection",
                        "ec2:DetachClassicLinkVpc",
                        "ec2:DetachVolume",
                        "ec2:DisableVpcClassicLink",
                        "ec2:EnableVpcClassicLink",
                        "ec2:GetConsoleScreenshot",
                        "ec2:RebootInstances",
                        "ec2:RejectVpcPeeringConnection",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:RevokeSecurityGroupIngress",
                        "ec2:RunInstances",
                        "ec2:StartInstances",
                        "ec2:StopInstances",
                        "ec2:TerminateInstances"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": "s3:*",
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "iam:GetAccessKeyLastUsed",
                        "iam:GetGroup*",
                        "iam:GetInstanceProfile",
                        "iam:GetLoginProfile",
                        "iam:GetOpenIDConnectProvider",
                        "iam:GetPolicy*",
                        "iam:GetRole*",
                        "iam:GetSAMLProvider",
                        "iam:GetSSHPublicKey",
                        "iam:GetServerCertificate",
                        "iam:GetServiceLastAccessed*",
                        "iam:GetUser*",
                        "iam:ListAccessKeys",
                        "iam:ListAttached*",
                        "iam:ListEntitiesForPolicy",
                        "iam:ListGroupPolicies",
                        "iam:ListGroupsForUser",
                        "iam:ListInstanceProfiles*",
                        "iam:ListMFADevices",
                        "iam:ListPolicyVersions",
                        "iam:ListRolePolicies",
                        "iam:ListSSHPublicKeys",
                        "iam:ListSigningCertificates",
                        "iam:ListUserPolicies",
                        "iam:Upload*"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "*"
                    ]
                },
                {
                    "Action": [
                        "iam:GetRole",
                        "iam:ListRoles",
                        "iam:PassRole"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:iam::*:role/rds-monitoring-role",
                        "arn:aws:iam::*:role/ec2-sysadmin-*",
                        "arn:aws:iam::*:role/ecr-sysadmin-*",
                        "arn:aws:iam::*:role/lamdba-sysadmin-*"
                    ]
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/job-function/",
        "PolicyId": "ANPAITJPEZXCYCBXANDSW",
        "PolicyName": "SystemAdministrator",
        "UpdateDate": "2017-03-24T17:45:43+00:00",
        "VersionId": "v2"
    },
    "VMImportExportRoleForAWSConnector": {
        "Arn": "arn:aws:iam::aws:policy/service-role/VMImportExportRoleForAWSConnector",
        "AttachmentCount": 0,
        "CreateDate": "2015-09-03T20:48:59+00:00",
        "DefaultVersionId": "v1",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "s3:ListBucket",
                        "s3:GetBucketLocation",
                        "s3:GetObject"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::import-to-ec2-*"
                    ]
                },
                {
                    "Action": [
                        "ec2:ModifySnapshotAttribute",
                        "ec2:CopySnapshot",
                        "ec2:RegisterImage",
                        "ec2:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/service-role/",
        "PolicyId": "ANPAJFLQOOJ6F5XNX4LAW",
        "PolicyName": "VMImportExportRoleForAWSConnector",
        "UpdateDate": "2015-09-03T20:48:59+00:00",
        "VersionId": "v1"
    },
    "ViewOnlyAccess": {
        "Arn": "arn:aws:iam::aws:policy/job-function/ViewOnlyAccess",
        "AttachmentCount": 0,
        "CreateDate": "2017-06-26T22:35:31+00:00",
        "DefaultVersionId": "v3",
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "acm:ListCertificates",
                        "athena:List*",
                        "aws-marketplace:ViewSubscriptions",
                        "autoscaling:Describe*",
                        "batch:ListJobs",
                        "clouddirectory:ListAppliedSchemaArns",
                        "clouddirectory:ListDevelopmentSchemaArns",
                        "clouddirectory:ListDirectories",
                        "clouddirectory:ListPublishedSchemaArns",
                        "cloudformation:List*",
                        "cloudformation:DescribeStacks",
                        "cloudfront:List*",
                        "cloudhsm:ListAvailableZones",
                        "cloudhsm:ListLunaClients",
                        "cloudhsm:ListHapgs",
                        "cloudhsm:ListHsms",
                        "cloudsearch:List*",
                        "cloudsearch:DescribeDomains",
                        "cloudtrail:DescribeTrails",
                        "cloudtrail:LookupEvents",
                        "cloudwatch:List*",
                        "cloudwatch:GetMetricData",
                        "codebuild:ListBuilds*",
                        "codebuild:ListProjects",
                        "codecommit:List*",
                        "codedeploy:List*",
                        "codedeploy:Get*",
                        "codepipeline:ListPipelines",
                        "codestar:List*",
                        "codestar:Verify*",
                        "cognito-idp:List*",
                        "cognito-identity:ListIdentities",
                        "cognito-identity:ListIdentityPools",
                        "cognito-sync:ListDatasets",
                        "connect:List*",
                        "config:List*",
                        "config:Describe*",
                        "datapipeline:ListPipelines",
                        "datapipeline:DescribePipelines",
                        "datapipeline:GetAccountLimits",
                        "devicefarm:List*",
                        "directconnect:Describe*",
                        "discovery:List*",
                        "dms:List*",
                        "ds:DescribeDirectories",
                        "dynamodb:ListTables",
                        "ec2:DescribeAccountAttributes",
                        "ec2:DescribeAddresses",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DescribeBundleTasks",
                        "ec2:DescribeClassicLinkInstances",
                        "ec2:DescribeConversionTasks",
                        "ec2:DescribeCustomerGateways",
                        "ec2:DescribeDhcpOptions",
                        "ec2:DescribeExportTasks",
                        "ec2:DescribeFlowLogs",
                        "ec2:DescribeHost*",
                        "ec2:DescribeIdentityIdFormat",
                        "ec2:DescribeIdFormat",
                        "ec2:DescribeImage*",
                        "ec2:DescribeImport*",
                        "ec2:DescribeInstance*",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeKeyPairs",
                        "ec2:DescribeMovingAddresses",
                        "ec2:DescribeNatGateways",
                        "ec2:DescribeNetwork*",
                        "ec2:DescribePlacementGroups",
                        "ec2:DescribePrefixLists",
                        "ec2:DescribeRegions",
                        "ec2:DescribeReserved*",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSnapshot*",
                        "ec2:DescribeSpot*",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVolume*",
                        "ec2:DescribeVpc*",
                        "ec2:DescribeVpnGateways",
                        "ecr:DescribeRepositories",
                        "ecr:ListImages",
                        "ecs:List*",
                        "elasticache:Describe*",
                        "elasticbeanstalk:DescribeApplicationVersions",
                        "elasticbeanstalk:DescribeApplications",
                        "elasticbeanstalk:DescribeEnvironments",
                        "elasticbeanstalk:ListAvailableSolutionStacks",
                        "elasticloadbalancing:DescribeListeners",
                        "elasticloadbalancing:DescribeLoadBalancers",
                        "elasticloadbalancing:DescribeTargetGroups",
                        "elasticloadbalancing:DescribeTargetHealth",
                        "elasticfilesystem:DescribeFileSystems",
                        "elasticmapreduce:List*",
                        "elastictranscoder:List*",
                        "es:DescribeElasticsearchDomain",
                        "es:DescribeElasticsearchDomains",
                        "es:ListDomainNames",
                        "events:ListRuleNamesByTarget",
                        "events:ListRules",
                        "events:ListTargetsByRule",
                        "firehose:List*",
                        "firehose:DescribeDeliveryStream",
                        "gamelift:List*",
                        "glacier:List*",
                        "iam:List*",
                        "iam:GetAccountSummary",
                        "iam:GetLoginProfile",
                        "importexport:ListJobs",
                        "inspector:List*",
                        "iot:List*",
                        "kinesis:ListStreams",
                        "kinesisanalytics:ListApplications",
                        "kms:ListKeys",
                        "lambda:List*",
                        "lex:GetBotAliases",
                        "lex:GetBotChannelAssociations",
                        "lex:GetBots",
                        "lex:GetBotVersions",
                        "lex:GetIntents",
                        "lex:GetIntentVersions",
                        "lex:GetSlotTypes",
                        "lex:GetSlotTypeVersions",
                        "lex:GetUtterancesView",
                        "lightsail:GetBlueprints",
                        "lightsail:GetBundles",
                        "lightsail:GetInstances",
                        "lightsail:GetInstanceSnapshots",
                        "lightsail:GetKeyPair",
                        "lightsail:GetRegions",
                        "lightsail:GetStaticIps",
                        "lightsail:IsVpcPeered",
                        "logs:Describe*",
                        "machinelearning:Describe*",
                        "mobilehub:ListAvailableFeatures",
                        "mobilehub:ListAvailableRegions",
                        "mobilehub:ListProjects",
                        "opsworks:Describe*",
                        "opsworks-cm:Describe*",
                        "organizations:List*",
                        "mobiletargeting:GetApplicationSettings",
                        "mobiletargeting:GetCampaigns",
                        "mobiletargeting:GetImportJobs",
                        "mobiletargeting:GetSegments",
                        "polly:Describe*",
                        "polly:List*",
                        "rds:Describe*",
                        "redshift:DescribeClusters",
                        "redshift:DescribeEvents",
                        "redshift:ViewQueriesInConsole",
                        "route53:List*",
                        "route53:Get*",
                        "route53domains:List*",
                        "s3:ListAllMyBuckets",
                        "s3:ListBucket",
                        "sdb:List*",
                        "servicecatalog:List*",
                        "ses:List*",
                        "shield:List*",
                        "states:ListActivities",
                        "states:ListStateMachines",
                        "sns:List*",
                        "sqs:ListQueues",
                        "ssm:ListAssociations",
                        "ssm:ListDocuments",
                        "storagegateway:ListGateways",
                        "storagegateway:ListLocalDisks",
                        "storagegateway:ListVolumeRecoveryPoints",
                        "storagegateway:ListVolumes",
                        "swf:List*",
                        "trustedadvisor:Describe*",
                        "waf:List*",
                        "waf-regional:List*",
                        "workdocs:DescribeAvailableDirectories",
                        "workdocs:DescribeInstances",
                        "workmail:Describe*",
                        "workspaces:Describe*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "IsAttachable": true,
        "IsDefaultVersion": true,
        "Path": "/job-function/",
        "PolicyId": "ANPAID22R6XPJATWOFDK6",
        "PolicyName": "ViewOnlyAccess",
        "UpdateDate": "2017-06-26T22:35:31+00:00",
        "VersionId": "v3"
    }
}"""
