Moto Changelog
===================

1.3.7
-----

    * Switch from mocking requests to using before-send for AWS calls

1.3.6
-----

    * Fix boto3 pinning.

1.3.5
-----

    * Pin down botocore issue as temporary fix for #1793.
    * More features on secrets manager

1.3.4
------

    * IAM get account authorization details
    * adding account id to ManagedPolicy ARN
    * APIGateway usage plans and usage plan keys
    * ECR list images

1.3.3
------
    
    * Fix a regression in S3 url regexes
    * APIGateway region fixes
    * ECS improvements
    * Add @mock_cognitoidentity, thanks to @brcoding


1.3.2
------
The huge change in this version is that the responses library is no longer vendored. Many developers are now unblocked. Kudos to @spulec for the fix.

    * Fix route53 TTL bug
    * Added filtering support for S3 lifecycle
    * unvendoring responses

1.3.0
------

Dozens of major endpoint additions in this release. Highlights include:

    * Fixed AMI tests and the Travis build setup
    * SNS improvements
    * Dynamodb improvements
    * EBS improvements
    * Redshift improvements
    * RDS snapshot improvements
    * S3 improvements
    * Cloudwatch improvements
    * SSM improvements
    * IAM improvements
    * ELBV1 and ELBV2 improvements
    * Lambda improvements
    * EC2 spot pricing improvements
    * ApiGateway improvements
    * VPC improvements

1.2.0
------

    * Supports filtering AMIs by self
    * Implemented signal_workflow_execution for SWF
    * Wired SWF backend to the moto server
    * Added url decoding to x-amz-copy-source header for copying S3 files
    * Revamped lambda function storage to do versioning
    * IOT improvements
    * RDS improvements
    * Implemented CloudWatch get_metric_statistics
    * Improved Cloudformation EC2 support
    * Implemented Cloudformation change_set endpoints
    
1.1.25
-----

    * Implemented Iot and Iot-data
    * Implemented resource tagging API
    * EC2 AMIs now have owners
    * Improve codegen scaffolding
    * Many small fixes to EC2 support
    * CloudFormation ELBv2 support
    * UTF fixes for S3
    * Implemented SSM get_parameters_by_path
    * More advanced Dynamodb querying

1.1.24
-----

    * Implemented Batch
    * Fixed regression with moto_server dashboard
    * Fixed and closed many outstanding bugs
    * Fixed serious performance problem with EC2 reservation listing
    * Fixed Route53 list_resource_record_sets

1.1.23
-----

    * Implemented X-Ray
    * Implemented Autoscaling EC2 attachment
    * Implemented Autoscaling Load Balancer methods
    * Improved DynamoDB filter expressions

1.1.22
-----

    * Lambda policies
    * Dynamodb filter expressions
    * EC2 Spot fleet improvements

1.1.21
-----

    * ELBv2 bugfixes
    * Removing GPL'd dependency

1.1.20
-----

    * Improved `make scaffold`
    * Implemented IAM attached group policies
    * Implemented skeleton of Cloudwatch Logs
    * Redshift: fixed multi-params
    * Redshift: implement taggable resources
    * Lambda + SNS: Major enhancements

1.1.19
-----

    * Fixing regression from 1.1.15

1.1.15
-----

    * Polly implementation
    * Added EC2 instance info
    * SNS publish by phone number

1.1.14
-----

    * ACM implementation
    * Added `make scaffold`
    * X-Ray implementation

1.1.13
-----

    * Created alpine-based Dockerfile (dockerhub: motoserver/moto)
    * SNS.SetSMSAttributes & SNS.GetSMSAttributes + Filtering
    * S3 ACL implementation
    * pushing to Dockerhub on `make publish`

1.1.12
-----

    * implemented all AWS managed policies in source
    * fixing Dynamodb CapacityUnits format
    * S3 ACL implementation

1.1.11
-----

    * S3 authentication
    * SSM get_parameter
    * ELBv2 target group tagging
    * EC2 Security group filters

1.1.10
-----

    * EC2 vpc address filtering
    * EC2 elastic ip dissociation
    * ELBv2 target group tagging
    * fixed complexity of accepting new filter implementations

1.1.9
-----

    * EC2 root device mapping

1.1.8
-----

    * Lambda get_function for function created with zipfile
    * scripts/implementation_coverage.py

1.1.7
-----

    * Lambda invoke_async
    * EC2 keypair filtering

1.1.6
-----

    * Dynamo ADD and DELETE operations in update expressions
    * Lambda tag support

1.1.5
-----

    * Dynamo allow ADD update_item of a string set
    * Handle max-keys in list-objects
    * bugfixes in pagination

1.1.3
-----

    * EC2 vpc_id in responses

1.1.2
-----

    * IAM account aliases
    * SNS subscription attributes
    * bugfixes in Dynamo, CFN, and EC2

1.1.1
-----

    * EC2 group-id filter
    * EC2 list support for filters

1.1.0
-----

    * Add ELBv2
    * IAM user policies
    * RDS snapshots
    * IAM policy versions

1.0.1
-----

    * Add Cloudformation exports
    * Add ECR
    * IAM policy versions

1.0.0
-----

    BACKWARDS INCOMPATIBLE
    * The normal @mock_<service> decorators will no longer work with boto. It is suggested that you upgrade to boto3 or use the standalone-server mode. If you would still like to use boto, you must use the @mock_<service>_deprecated decorators which will be removed in a future release.
    * The @mock_s3bucket_path decorator is now deprecated. Use the @mock_s3 decorator instead.
    * Drop support for Python 2.6
    * Redshift server defaults to returning XML instead of JSON

    Added features
    * Reset API: a reset API has been added to flush all of the current data ex: `requests.post("http://motoapi.amazonaws.com/moto-api/reset")`
    * A dashboard is now available with moto_server at http://localhost:5000/moto-api/

0.4.31
------

    * ECS Cloudformation support
    * Cleaned up RDS XML/JSON issues
    * Boto==2.45
    * Add STS get_caller_identity
    * Turn on variable escaping in templates for S3 XML documents

0.4.30
------

    * Change spot requests to launch instances

0.4.29
------

    * Nest flask import so that it is not required globally

0.4.28
------

    * Add basic spot fleet support
    * IAM Managed Policies
    * Better EMR coverage
    * Basic KMS support for encrypt/decrypt

0.4.27
------

    *

0.4.25
------

    * ASG tags
    * ContainerInstance handling in ECS
    *

0.4.22
------

    * Add basic lambda endpoints
    * Support placement for EC2
    * Cleanup API versions


0.4.21
------

    * Fix bug with wrong response matches for S3

0.4.20
------

    * mock_s3 and mocks3bucket_path are now the same thing. The server decides
    which interface to is being used based on the request Host header. We will
    evetually deprecate mocks3bucket_path.
    * Basic ECS support
    * More Dynamo querying and indexes
    * Add Kinesis and ELB tags
    * Add JSON responses for EMR
    * Fix root instance volume to show up in other EBS volume calls
