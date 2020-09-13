Moto Changelog
===================

Unreleased
-----
    * Reduced dependency overhead.
      It is now possible to install dependencies for only specific services using:
      pip install moto[service1,service1].
      See the README for more information.



1.3.16
-----
Full list of PRs merged in this release:
https://github.com/spulec/moto/pulls?q=is%3Apr+is%3Aclosed+merged%3A2019-11-14..2020-09-07


    General Changes:
        * The scaffold.py-script has been fixed to make it easier to scaffold new services.
          See the README for an introduction.

    New Services:
        * Application Autoscaling
        * Code Commit
        * Code Pipeline
        * Elastic Beanstalk
        * Kinesis Video
        * Kinesis Video Archived Media
        * Managed BlockChain
        * Resource Access Manager (ram)
        * Sagemaker

    New Methods:
        * Athena:
            * create_named_query
            * get_named_query
            * get_work_group
            * start_query_execution
            * stop_query_execution
        * API Gateway:
            * create_authorizer
            * create_domain_name
            * create_model
            * delete_authorizer
            * get_authorizer
            * get_authorizers
            * get_domain_name
            * get_domain_names
            * get_model
            * get_models
            * update_authorizer
        * Autoscaling:
            * enter_standby
            * exit_standby
            * terminate_instance_in_auto_scaling_group
        * CloudFormation:
            * get_template_summary
        * CloudWatch:
            * describe_alarms_for_metric
            * get_metric_data
        * CloudWatch Logs:
            * delete_subscription_filter
            * describe_subscription_filters
            * put_subscription_filter
        * Cognito IDP:
            * associate_software_token
            * create_resource_server
            * confirm_sign_up
            * initiate_auth
            * set_user_mfa_preference
            * sign_up
            * verify_software_token
        * DynamoDB:
            * describe_continuous_backups
            * transact_get_items
            * transact_write_items
            * update_continuous_backups
        * EC2:
            * create_vpc_endpoint
            * describe_vpc_classic_link
            * describe_vpc_classic_link_dns_support
            * describe_vpc_endpoint_services
            * disable_vpc_classic_link
            * disable_vpc_classic_link_dns_support
            * enable_vpc_classic_link
            * enable_vpc_classic_link_dns_support
            * register_image
        * ECS:
            * create_task_set
            * delete_task_set
            * describe_task_set
            * update_service_primary_task_set
            * update_task_set
        * Events:
            * delete_event_bus
            * create_event_bus
            * list_event_buses
            * list_tags_for_resource
            * tag_resource
            * untag_resource
        * Glue:
            * get_databases
        * IAM:
            * delete_group
            * delete_instance_profile
            * delete_ssh_public_key
            * get_account_summary
            * get_ssh_public_key
            * list_user_tags
            * list_ssh_public_keys
            * update_ssh_public_key
            * upload_ssh_public_key
        * IOT:
            * cancel_job
            * cancel_job_execution
            * create_policy_version
            * delete_job
            * delete_job_execution
            * describe_endpoint
            * describe_job_execution
            * delete_policy_version
            * get_policy_version
            * get_job_document
            * list_attached_policies
            * list_job_executions_for_job
            * list_job_executions_for_thing
            * list_jobs
            * list_policy_versions
            * set_default_policy_version
            * register_certificate_without_ca
        * KMS:
            * untag_resource
        * Lambda:
            * delete_function_concurrency
            * get_function_concurrency
            * put_function_concurrency
        * Organisations:
            * describe_create_account_status
            * deregister_delegated_administrator
            * disable_policy_type
            * enable_policy_type
            * list_delegated_administrators
            * list_delegated_services_for_account
            * list_tags_for_resource
            * register_delegated_administrator
            * tag_resource
            * untag_resource
            * update_organizational_unit
        * S3:
            * delete_bucket_encryption
            * delete_public_access_block
            * get_bucket_encryption
            * get_public_access_block
            * put_bucket_encryption
            * put_public_access_block
        * S3 Control:
            * delete_public_access_block
            * get_public_access_block
            * put_public_access_block
        * SecretsManager:
            * get_resource_policy
            * update_secret
        * SES:
            * create_configuration_set
            * create_configuration_set_event_destination
            * create_receipt_rule_set
            * create_receipt_rule
            * create_template
            * get_template
            * get_send_statistics
            * list_templates
        * STS:
            * assume_role_with_saml
        * SSM:
            * create_documen
            * delete_document
            * describe_document
            * get_document
            * list_documents
            * update_document
            * update_document_default_version
        * SWF:
            * undeprecate_activity_type
            * undeprecate_domain
            * undeprecate_workflow_type

    General Updates:
        * API Gateway - create_rest_api now supports policy-parameter
        * Autoscaling - describe_auto_scaling_instances now supports InstanceIds-parameter
        * AutoScalingGroups - now support launch templates
        * CF - Now supports DependsOn-configuration
        * CF - Now supports FN::Transform AWS::Include mapping
        * CF - Now supports update and deletion of Lambdas
        * CF - Now supports creation, update and deletion of EventBus (Events)
        * CF - Now supports update of Rules (Events)
        * CF - Now supports creation, update and deletion of EventSourceMappings (AWS Lambda)
        * CF - Now supports update and deletion of Kinesis Streams
        * CF - Now supports creation of DynamoDB streams
        * CF - Now supports deletion of  DynamoDB tables
        * CF - list_stacks now supports the status_filter-parameter
        * Cognito IDP - list_users now supports filter-parameter
        * DynamoDB - GSI/LSI's now support ProjectionType=KEYS_ONLY
        * EC2 - create_route now supports the NetworkInterfaceId-parameter
        * EC2 - describe_instances now supports additional filters (owner-id)
        * EC2 - describe_instance_status now supports additional filters (instance-state-name, instance-state-code)
        * EC2 - describe_nat_gateways now supports additional filters (nat-gateway-id, vpc-id, subnet-id, state)
        * EC2 - describe_vpn_gateways now supports additional filters (attachment.vpc_id, attachment.state, vpn-gateway-id, type)
        * IAM - list_users now supports path_prefix-parameter
        * IOT - list_thing_groups now supports parent_group, name_prefix_filter, recursive-parameters
        * S3 - delete_objects now supports deletion of specific VersionIds
        * SecretsManager - list_secrets now supports filters-parameter
        * SFN - start_execution now receives and validates input
        * SNS - Now supports sending a message directly to a phone number
        * SQS - MessageAttributes now support labeled DataTypes

1.3.15
-----

This release broke dependency management for a lot of services - please upgrade to 1.3.16.

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
