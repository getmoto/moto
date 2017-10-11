Moto Changelog
===================

Latest
------
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
