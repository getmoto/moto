Moto Changelog
===================

1.3.14
-----

    General Changes:
        * Support for Python 3.8
        * Linting: Black is now enforced.

    New Services:
        * Athena
        * Config
        * DataSync
        * Step Functions

    New methods:
        * Athena:
            * create_work_group()
            * list_work_groups()
        * API Gateway:
            * delete_stage()
            * update_api_key()
        * CloudWatch Logs
            * list_tags_log_group()
            * tag_log_group()
            * untag_log_group()
        * Config
            * batch_get_resource_config()
            * delete_aggregation_authorization()
            * delete_configuration_aggregator()
            * describe_aggregation_authorizations()
            * describe_configuration_aggregators()
            * get_resource_config_history()
            * list_aggregate_discovered_resources() (For S3)
            * list_discovered_resources() (For S3)
            * put_aggregation_authorization()
            * put_configuration_aggregator()
        * Cognito
            * assume_role_with_web_identity()
            * describe_identity_pool()
            * get_open_id_token()
            * update_user_pool_domain()
        * DataSync:
            * cancel_task_execution()
            * create_location()
            * create_task()
            * start_task_execution()
        * EC2:
            * create_launch_template()
            * create_launch_template_version()
            * describe_launch_template_versions()
            * describe_launch_templates()
        * ECS
            * decrypt()
            * encrypt()
            * generate_data_key_without_plaintext()
            * generate_random()
            * re_encrypt()
        * Glue
            * batch_get_partition()
        * IAM
            * create_open_id_connect_provider()
            * create_virtual_mfa_device()
            * delete_account_password_policy()
            * delete_open_id_connect_provider()
            * delete_policy()
            * delete_virtual_mfa_device()
            * get_account_password_policy()
            * get_open_id_connect_provider()
            * list_open_id_connect_providers()
            * list_virtual_mfa_devices()
            * update_account_password_policy()
        * Lambda
            * create_event_source_mapping()
            * delete_event_source_mapping()
            * get_event_source_mapping()
            * list_event_source_mappings()
            * update_configuration()
            * update_event_source_mapping()
            * update_function_code()
        * KMS
            * decrypt()
            * encrypt()
            * generate_data_key_without_plaintext()
            * generate_random()
            * re_encrypt()
        * SES
            * send_templated_email()
        * SNS
            * add_permission()
            * list_tags_for_resource()
            * remove_permission()
            * tag_resource()
            * untag_resource()
        * SSM
            * describe_parameters()
            * get_parameter_history()
        * Step Functions
            * create_state_machine()
            * delete_state_machine()
            * describe_execution()
            * describe_state_machine()
            * describe_state_machine_for_execution()
            * list_executions()
            * list_state_machines()
            * list_tags_for_resource()
            * start_execution()
            * stop_execution()
        SQS
            * list_queue_tags()
            * send_message_batch()

    General updates:
        * API Gateway:
            * Now generates valid IDs
            * API Keys, Usage Plans now support tags
        * ACM:
            * list_certificates() accepts the status parameter
        * Batch:
            * submit_job() can now be called with job name
        * CloudWatch Events
            * Multi-region support
        * CloudWatch Logs
            * get_log_events() now supports pagination
        * Cognito:
            * Now throws UsernameExistsException for known users
        * DynamoDB
            * update_item() now supports lists, the list_append-operator and removing nested items
            * delete_item() now supports condition expressions
            * get_item() now supports projection expression
            * Enforces 400KB item size
            * Validation on duplicate keys in batch_get_item()
            * Validation on AttributeDefinitions on create_table()
            * Validation on Query Key Expression
            * Projection Expressions now support nested attributes
        * EC2:
            * Change DesiredCapacity behaviour for AutoScaling groups
            * Extend list of supported EC2 ENI properties
            * Create ASG from Instance now supported
            * ASG attached to a terminated instance now recreate the instance of required
            * Unify OwnerIDs
        * ECS
            * Task definition revision deregistration: remaining revisions now remain unchanged
            * Fix created_at/updated_at format for deployments
            * Support multiple regions
        * ELB
            * Return correct response then describing target health of stopped instances
            * Target groups now longer show terminated instances
            * 'fixed-response' now a supported action-type
            * Now supports redirect: authenticate-cognito
        * Kinesis FireHose
            * Now supports ExtendedS3DestinationConfiguration
        * KMS
            * Now supports tags
        * Organizations
            * create_organization() now creates Master account
        * Redshift
            * Fix timezone problems when creating a cluster
            * Support for enhanced_vpc_routing-parameter
        * Route53
            * Implemented UPSERT for change_resource_records
        * S3:
            * Support partNumber for head_object
            * Support for INTELLIGENT_TIERING, GLACIER and DEEP_ARCHIVE
            * Fix KeyCount attribute
            * list_objects now supports pagination (next_marker)
            * Support tagging for versioned objects
        * STS
            * Implement validation on policy length
        * Lambda
            * Support EventSourceMappings for SQS, DynamoDB
            * get_function(), delete_function() now both support ARNs as parameters
        * IAM
            * Roles now support tags
            * Policy Validation: SID can be empty
            * Validate roles have no attachments when deleting
        * SecretsManager
            * Now supports binary secrets
        * IOT
            * update_thing_shadow validation
            * delete_thing now also removed principals
        * SQS
            * Tags supported for create_queue()


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
