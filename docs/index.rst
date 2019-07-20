.. _index:

=============================
Moto: Mock AWS Services
=============================

A library that allows you to easily mock out tests based on
`AWS infrastructure`_.

Getting Started
---------------

If you've never used ``moto`` before, you should read the
:doc:`Getting Started with Moto <docs/getting_started>` guide to get familiar
with ``moto`` and its usage.

Currently implemented Services:
-------------------------------

+---------------------------+-----------------------+------------------------------------+
| Service Name              | Decorator             | Development Status                 |
+===========================+=======================+====================================+
| ACM                       | @mock_acm             | all endpoints done                 |
+---------------------------+-----------------------+------------------------------------+
| API Gateway               | @mock_apigateway      | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| Autoscaling               | @mock_autoscaling     | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| Cloudformation            | @mock_cloudformation  | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| Cloudwatch                | @mock_cloudwatch      | basic endpoints done               |
+---------------------------+-----------------------+------------------------------------+
| CloudwatchEvents          | @mock_events          | all endpoints done                 |
+---------------------------+-----------------------+------------------------------------+
| Cognito Identity          | @mock_cognitoidentity | all endpoints done                 |
+---------------------------+-----------------------+------------------------------------+
| Cognito Identity Provider | @mock_cognitoidp      | all endpoints done                 |
+---------------------------+-----------------------+------------------------------------+
| Config                    | @mock_config          | basic endpoints done               |
+---------------------------+-----------------------+------------------------------------+
| Data Pipeline             | @mock_datapipeline    | basic endpoints done               |
+---------------------------+-----------------------+------------------------------------+
| DynamoDB                  | - @mock_dynamodb      | - core endpoints done              |
| DynamoDB2                 | - @mock_dynamodb2     | - core endpoints + partial indexes |
+---------------------------+-----------------------+------------------------------------+
| EC2                       | @mock_ec2             | core endpoints done                |
|     - AMI                 |                       |     - core endpoints done          |
|     - EBS                 |                       |     - core endpoints done          |
|     - Instances           |                       |     - all  endpoints done          |
|     - Security Groups     |                       |     - core endpoints done          |
|     - Tags                |                       |     - all  endpoints done          |
+---------------------------+-----------------------+------------------------------------+
| ECR                       | @mock_ecr             | basic endpoints done               |
+---------------------------+-----------------------+------------------------------------+
| ECS                       | @mock_ecs             | basic endpoints done               |
+---------------------------+-----------------------+------------------------------------+
| ELB                       | @mock_elb             | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| ELBv2                     | @mock_elbv2           | all endpoints done                 |
+---------------------------+-----------------------+------------------------------------+
| EMR                       | @mock_emr             | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| Glacier                   | @mock_glacier         | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| IAM                       | @mock_iam             | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| IoT                       | @mock_iot             | core endpoints done                |
|                           | @mock_iotdata         | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| Kinesis                   | @mock_kinesis         | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| KMS                       | @mock_kms             | basic endpoints done               |
+---------------------------+-----------------------+------------------------------------+
| Lambda                    | @mock_lambda          | basic endpoints done,              |
|                           |                       | requires docker                    |
+---------------------------+-----------------------+------------------------------------+
| Logs                      | @mock_logs            | basic endpoints done               |
+---------------------------+-----------------------+------------------------------------+
| Organizations             | @mock_organizations   | some core edpoints done            |
+---------------------------+-----------------------+------------------------------------+
| Polly                     | @mock_polly           | all endpoints done                 |
+---------------------------+-----------------------+------------------------------------+
| RDS                       | @mock_rds             | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| RDS2                      | @mock_rds2            | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| Redshift                  | @mock_redshift        | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| Route53                   | @mock_route53         | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| S3                        | @mock_s3              | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| SecretsManager            | @mock_secretsmanager  | basic endpoints done               |
+---------------------------+-----------------------+------------------------------------+
| SES                       | @mock_ses             | all endpoints done                 |
+---------------------------+-----------------------+------------------------------------+
| SNS                       | @mock_sns             | all endpoints done                 |
+---------------------------+-----------------------+------------------------------------+
| SQS                       | @mock_sqs             | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| SSM                       | @mock_ssm             | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| STS                       | @mock_sts             | core endpoints done                |
+---------------------------+-----------------------+------------------------------------+
| SWF                       | @mock_swf             | basic endpoints done               |
+---------------------------+-----------------------+------------------------------------+
| X-Ray                     | @mock_xray            | all endpoints done                 |
+---------------------------+-----------------------+------------------------------------+



Additional Resources
--------------------

* `Moto Source Repository`_
* `Moto Issue Tracker`_

.. _AWS infrastructure: http://aws.amazon.com/
.. _Moto Issue Tracker: https://github.com/spulec/moto/issues
.. _Moto Source Repository: https://github.com/spulec/moto

.. toctree::
   :maxdepth: 2
   :hidden:
   :glob:

   docs/getting_started
   docs/server_mode
   docs/moto_apis
   docs/ec2_tut
