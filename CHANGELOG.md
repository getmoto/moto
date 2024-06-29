Moto Changelog
==============

5.0.10
-----
Docker Digest for 5.0.10: _sha256:bfb9cd2a437fc7c754b3a6a66b7fb528ec1a53e0c683e8b75514bff81543cf55_

    General:
        * CloudFormation now supports cfn-lint v1, as well as v0

    New Services:

        * FSX:
            * create_file_system()
            * delete_file_system()
            * describe_file_systems()
            * tag_resource()
            * untag_resource()

        * OpenSearch Serverless:
            * batch_get_collection()
            * create_collection()
            * create_security_policy()
            * create_vpc_endpoint()
            * delete_collection()
            * get_security_policy()
            * list_collections()
            * list_security_policies()
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()
            * update_security_policy()

        * Shield:
            * create_protection()
            * delete_protection()
            * describe_protection()
            * list_protections()
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()

    New Methods:
        * Sagemaker:
            * create_cluster()
            * delete_cluster()
            * describe_cluster()
            * list_clusters()
            * list_cluster_nodes()

    Miscellaneous:
        * CognitoIDP: admin_list_groups_by_user() now supports pagination
        * DynamoDB: transact_write_items() now validates the number of SET expressions
        * DynamoDB: update_item() now validates unused ExpressionAttributeValues
        * DynamoDB: query() now supports pagination when querying Global Indexes
        * EC2: describe_images() - feat: support filtering images by ExecutableUsers=['self']
        * EC2: describe_route_tables() now supports the filter `route.transit-gateway-id`
        * EC2: update_security_group_rule_descriptions_ingress() now supports updating multiple descriptions
        * EKS: create_nodegroup() now supports the `taints`-parameter
        * ELBv2: add_listener_certificates() now validates when adding too many certificates (> 25)
        * ELBv2: describe_target_health() now handles unknown/deregistered/terminated instances better
        * ResourceGroupsTaggingAPI: get_resources() now supports ResourceType=s3:bucket
        * RDS: Clusters now have the `creating`-status on create, and `available` immediately after - in line with AWS
        * SSM: get_parameter() now supports ARN's for the Name-parameter


5.0.9
-----
Docker Digest for 5.0.9: _sha256:df61e4e76344017f6c82924a3dd1cdd4dcbac4095cf234c6d6fb0a0f800fbeff_

    General:
        * Fixed an InfiniteRecursion-bug when accessing S3-buckets that was introduced in 5.0.8

    New Methods:
        * SSO-Admin:
            * list_accounts_for_provisioned_permission_set()
            * list_instances()
            * list_permission_sets_provisioned_to_account()
            * provision_permission_set()
            * update_instance()

    Miscellaneous:
        * DynamoDB: query() now handles pagination correctly on a GSI without a range key
        * IAM: create_policy() now returns tags correctly
        * S3: list_objects(): The default value for MaxKeys can now be configured, using an environment variable:
          MOTO_S3_DEFAULT_MAX_KEYS=1

5.0.8
-----
Docker Digest for 5.0.8: _sha256:cfcd97074011bd563cdbeebac35ed710581a23cb2be07ab9b67aa00298fc3369_

    General:
        * Improved support for non-generic partitions (China, GovCloud, ISO-regions). 
          All ARN's now contain the correct partition for resources created in those regions.

    New Services:
        * NetworkManager:
            * create_global_network()
            * describe_global_networks()
            * create_core_network()
            * create_global_network()
            * delete_core_network()
            * list_core_networks()
            * get_core_network()
            * tag_resource()
            * untag_resource()

    Miscellaneous:
        * ResilienceHub: list_app_assessments() can now return pre-configured results
        * ResourceGroupTagging: get_resources() now returns results when filtering on "lambda:function"
        * S3: delete_object_tagging()/put_object_tagging() now send an EventBridge notification


5.0.7
-----
Docker Digest for 5.0.7: _sha256:81ac52ff74b0bf0f4957ee4260e6a7e75d66c9e5d040ed4f721a5500b873c88a_

    New Services:
        * Sagemaker Metrics:
            * batch_put_metrics()

    New Methods:
        * DynamoDB:
            * describe_import()
            * import_table()

        * EMR Serverless:
            * cancel_job_run()
            * get_job_run()
            * list_job_runs()
            * start_job_run()

        * IAM:
            * tag_instance_profile()
            * untag_instance_profile()

        * Panorama:
            * create_node_from_template_job()
            * describe_node_from_template_job()
            * list_nodes()

        * SSO-Admin:
            * describe_account_assignment_creation_status()
            * describe_account_assignment_deletion_status()

        * WAFv2:
            * create_ip_set()
            * delete_ip_set()
            * list_ip_sets()
            * get_ip_set()
            * update_ip_set()
            * put_logging_configuration()
            * get_logging_configuration()
            * list_logging_configurations()
            * delete_logging_configuration()

    Miscellaneous:
        * Athena: start_query_execution() now supports the ExecutionParameters-parameter
        * DynamoDB: Tables now support DeleteProtection
        * DynamoDB: update_item() no longer throws an error when deleting an item from an empty set
        * DynamoDB: update_item() no throws an error when adding an empty set
        * EC2: delete_network_acl() now throws an error when the ACL still has associations attached to it
        * EC2: describe_route_tables() now supports the `route.nat-gateway-id` filter
        * EC2: revoke_security_group_ingress/_egress() now throw an error when an unknown Security Group is passed

5.0.6
-----
Docker Digest for 5.0.6: _sha256:da919d3c1db07b378c413ed00a6c1c3e32ce1943a13671658c4db0f55dd49e42_

    New Services:
        * Bedrock:
            * create_model_customization_job()
            * delete_custom_model()
            * delete_model_invocation_logging_configuration()
            * get_custom_model()
            * get_model_customization_job()
            * get_model_invocation_logging_configuration()
            * list_custom_models()
            * list_model_customization_jobs()
            * list_tags_for_resource()
            * put_model_invocation_logging_configuration()
            * stop_model_customization_job()
            * tag_resource()
            * untag_resource()

        * BedrockAgent:
            * create_agent()
            * create_knowledge_base()
            * delete_agent()
            * delete_knowledge_base()
            * get_agent()
            * get_knowledge_base()
            * list_agents()
            * list_knowledge_bases()
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()

    New Methods:
        * EC2:
            * describe_addresses_attributes()

        * Rekognition:
            * detect_custom_labels()

        * Sagemaker:
            * update_trial_component()

    Miscellaneous:
        * CloudFront: update_distribution() now supports the CacheBehaviours-parameter
        * DynamoDB: query() now acts correctly when paginating GSI tables without range keys
        * EC2: RouteTables can now have multiple propagations
        * EC2: describe_instances() now now filter by product-code and product-code.type
        * EC2: describe_security_group_rules() now validates the format of the incoming security group id's
        * ECS: update_service() now supports the loadBalancers-parameter
        * Logs: describe_metric_filter() now has the correct validation for metricNamespaces
        * IOT: search_index() now supports thingTypeName
        * SFN: send_task_failure()/send_task_success() now work correctly when using the Parser
        * SNS: subscribe() now throws an exception if the endpoint doesn't exist
        * SQS: Improved queue name validation


5.0.5
-----
Docker Digest for 5.0.5: _sha256:b95cf0d65557475f29e7256938028eef352e23acafe8e07c071cd58b67c44708_

    General:
        * DynamoDB: scan() now returns items in a alphabetical order
    
    New Methods:
        * SecretsManager:
            * batch_get_secret_value()

    Miscellaneous:
        * ApplicationAutoscaling: put_scaling_policy() now generates CW alarms for DynamoDB and ECS
        * DynamoDB: Fix pagination for scan()/query()
        * DynamoDB: batch_write_item() now validates for duplicate DELETE or PUT requests
        * Events: put_events() now validates that input-values cannot be empty
        * IOT: create_topic_rule() now validates name-format
        * ResourceGroupsTaggingAPI: tag_resources() now supports RDS snapshots
        * SFN: Fixed a bug where the executionInput was double encoded


5.0.4
-----
Docker Digest for 5.0.4: _sha256:e13e917e563bd1e3bb745b0ce914bdcc3bd4577542e13e1468eac5078774b2aa_

    General:
        * Lambda: The results of a Dockerless invocation can now be configured.
          See http://docs.getmoto.org/en/latest/docs/services/lambda.html

        * StepFunctions can now execute the provided StepFunctionMachine (opt-in), instead of returning static data (still the default).
          See http://docs.getmoto.org/en/latest/docs/services/stepfunctions.html

    New Service:
        * ElastiCache:
            * list_tags_for_resource()

        * ResilienceHub:
            * create_app()
            * create_app_version_app_component()
            * create_app_version_resource()
            * create_resiliency_policy()
            * describe_app()
            * describe_resiliency_policy()
            * import_resources_to_draft_app_version()
            * list_app_assessments()
            * list_app_version_app_components()
            * list_app_version_resources()
            * list_app_versions()
            * list_apps()
            * list_resiliency_policies()
            * list_tags_for_resource()
            * publish_app_version()
            * tag_resource()
            * untag_resource()

        * Workspaces:
            * create_tags()
            * create_workspace_image()
            * create_workspaces()
            * deregister_workspace_directory()
            * describe_client_properties()
            * describe_tags()
            * describe_workspace_directories()
            * describe_workspace_image_permissions()
            * describe_workspace_images()
            * describe_workspaces()
            * modify_client_properties()
            * modify_selfservice_permissions()
            * modify_workspace_creation_properties()
            * register_workspace_directory()
            * update_workspace_image_permission()

    Miscellaneous:
        * APIGateway: update_usage_plan() now supports some remove-operations
        * Autoscaling: describe_auto_scaling_groups() now returns a dynamic CreatedTime
        * CloudFormation: Outputs now support Conditions
        * CloudFormation: Outputs now return Descriptions
        * CognitoIDP: admin_update_user_attributes() and admin_delete_user_attributes now correctly update the UserLastModifiedDate
        * DynamoDB: query() no longer requires the LastEvaluatedKey to exist
        * EC2: describe_vpc_endpoint_services() now supports all services
        * Kinesis: list_streams() now returns StreamSummaries
        * Lambda: get_policy() now throws an error when no statements exist
        * ResourceGroupsTaggingAPI now supports DynamoDB tables
        * ResourceGroupsTaggingAPI now supports SSM documents
        * S3: EventBridge notifications are now supported for ObjectRestore:Post
        * S3: restore_object() now contains limited validation when supplying both Days- and Type-argument
        * S3: select_object_content() now supports Compressed requests and CSV responses
        * SecretsManager: list_secrets() now handles negative matches correctly
        * SNS: delete_endpoint() is now an idempotent operation, just like AWS


5.0.3
-----
Docker Digest for 5.0.3: _sha256:032d8ead42f289d9700e9bc844c6d264575ad11b3f6c22cc76d65ff638c8c7bd_

    General:
        * New configuration options for:
          - Passing URL's through the proxy
          - Configuring DOcker-less services in ServerMode
          See http://docs.getmoto.org/en/latest/docs/configuration/index.html

    New Services:
        * Route53Domains:
            * delete_domain()
            * list_domains()
            * list_operations()
            * register_domain()
            * update_domain_nameservers()

    New Methods:
        * CostExplorer:
            * get_cost_and_usage()

        * ECR:
            * get_registry_scanning_configuration()

    Miscellaneous:
        * ApiGateway: update_usage_plan() now supports adding apiStages
        * Athena: get_query_execution() now returns exact OutputLocation file
        * Autoscaling: describe_auto_scaling_groups() now supports the filters-argument
        * CloudFront: create_distribution() now supports CustomHeaders
        * CloudFront: update_distribution() now handles updates to DistributionConfig correctly
        * CloudFormation - Now supports creation and deletion of AWS::EMR::Cluster
        * CloudFormation - Now supports creation and deletion of AWS::EMR::SecurityConfiguration
        * CloudFormation - Now supports creation and deletion of AWS::EFS::AccessPoint
        * CloudFormation - Now supports creation and deletion of AWS::EFS::FileSystem
        * CloudFormation - Now supports creation and deletion of AWS::EMR::InstanceGroupConfig
        * CloudFormation - Now supports deletion of AWS::Logs::LogGroup
        * CloudFormation: delete_stack() now handles resource dependencies better
        * CloudWatch: put_metric_data() now supports large (compressed) requests
        * CognitoIDP: admin_initiate_auth() and respond_to_auth_challenge() now support SMS_MFA
        * DynamoDB: transact_write_items() now raises ValidationException when putting and deleting the same item
        * EC2: authorize_security_group_egress/_ingress now support the TagSpecifications-argument
        * EC2: describe_security_group_rules() now supports Tag-filters
        * S3: EventBridge notifications are now supported for ObjectCreated:POST/COPY/MULTIPART_UPLOAD and ObjectDeleted
        * SNS: subscribe() now adds support the `$or`, `equals-ignore-case` and `suffix` features in a FilterPolicy 
        * SQS: send_message() should respect DelaySeconds of 0


5.0.2
-----
Docker Digest for 5.0.2: _sha256:89cc6c764d714bf76e592a61f0c06fd142f672085e1dd3a53eb734aaeb4e14e2_

    General:
        * Removed the `python-jose` and `sshpubkeys` dependencies in favor of `joserfc`. This removes a transitive dependency on `ecdsa`, which contains a open security vulnerability

    New Methods:
        * Autoscaling:
            * batch_put_scheduled_update_group_action()
            * batch_delete_scheduled_action()

        * RDS:
            * create_db_proxy()
            * describe_db_proxies()

    Miscellaneous:
        * AWSLambda: The ImageConfig.EntryPoint of a function is now used when invoking it in a Docker container
        * CognitoIDP now allows public actions even if IAM auth is enabled
        * DynamoDB: create_table() now validates the number of KeySchema-items
        * EC2: modify_image_attributes() now supports all LaunchPermissions
        * ECS: register_task_definition() now has improved validation around `memory`-parameters
        * Glue: create_database() now supports the `tags`-parameter
        * IAM: assume_user()/create_user()/get_caller_identity() now return the correct partition for China (aws-cn) when called from a Chinese region
        * ResourceGroupsTagging: get_resources() now supports ELB resources
        * Route53: list_hosted_zones() now supports pagination
        * S3: put_bucket_notification_configuration() now supports EventBridge-notifications
        * SES now returns errors in the correct format

5.0.1
-----
Docker Digest for 5.0.1: _sha256:b6004b2e112c0ba870b2103049548abecec476edeac7a724ed9c71249358e821_

    New Methods:
        * SecretsManager:
            * remove_regions_from_replication()
            * replicate_secret_to_regions()

    Miscellaneous:
        * AWSLambda: create_event_source_mapping() now supports Kinesis streams as targets
        * CloudFront: Removed error handling for InvalidOriginServer, as our validation was too strict
        * DynamoDB: batch_execute_statement() now supports for Update/Insert/Delete-statements
        * DynamoDB: query() now correctly handles calls where both Limit and ScanIndexForward are supplied
        * EC2: Now supports availability zones for eu-central-2 (Zurich)
        * S3: list_objects_v2() can now return more then 1000 results max (again)
        * S3: copy_object() now allows in-place copies when bucket versioning is enabled
        * SecretsManager: create_secrets() now supports the parameters AddReplicaRegions and ForceOverwriteReplicaSecret
        * SecretsManager: list_secrets() now supports the filters primary-region and owning-service


5.0.0
-----
Docker Digest for 5.0.0: _sha256:2faf2460a6446dfe472ac0d799e00341b1c84203d08540c247a6cc09be7c54e9_

    General:
        * All decorators have been replaced with a single decorator:
          `mock_aws`

        * The `mock_batch_simple` and `mock_lambda_simple` decorators can now be configured using the `config`-parameter:
          `@mock_aws(config={"batch": {"use_docker": False}, "lambda": {"use_docker": False}})`

        * It is now possible to configure methods/services which should reach out to AWS.
          @mock_aws(
              config={"core": {"mock_credentials": False, "passthrough": {"urls": [], "services": []}}}
          )

        * All requests now return a RequestId

    Miscellaneous:

        * IAM: The AWS managed Policies are no longer loaded by default.
          If your application depends on these policies, tell Moto explicitly to load them like so:

          @mock_aws(config={"iam": {"load_aws_managed_policies": True}})

          Or by setting an environment variable:
          MOTO_IAM_LOAD_MANAGED_POLICIES=true

        * S3: list_objects() now returns a hashed ContinuationToken


4.2.14
-----
Docker Digest for 4.2.14: _sha256:2fa10aa48e32f85c63c62a7d437b8a4b320a56a8494bc25d45ced370bc159c23_

    New Services:
        * Backup:
            * create_backup_plan()
            * create_backup_vault()
            * get_backup_plan()
            * describe_backup_vault()
            * delete_backup_plan()
            * list_backup_plans()
            * list_backup_vaults()
            * list_tags()
            * tag_resource()
            * untag_resource()

    New Methods:
        * RDS:
            * describe_db_cluster_snapshot_attributes()
            * describe_db_snapshot_attributes()
            * modify_db_cluster_snapshot_attribute()
            * modify_db_snapshot_attribute()
            * restore_db_instance_to_point_in_time()

        * SageMaker:
            * create_feature_group()

        * SageMakerRuntime:
            * invoke_endpoint_async()

    Miscellaneous:
        * Cognito: The ID-token now contains custom attributes
        * DynamoDB: query() now returns the correct ScannedCount
        * EC2: Security Group Rules now have tag support 
        * LakeFormation: grant_permissions() now has better support for known principal-resource pairs
        * SNS: set_subscription_attributes() can now unset the FilterPolicy


5.0.0alpha3
-----------

    Miscellaneous:
        * IAM: The AWS managed Policies are no longer loaded by default.
          If your application depends on these policies, tell Moto explicitly to load them like so:

          @mock_aws(config={"iam": {"load_aws_managed_policies": True}})

          Or by setting an environment variable:
          MOTO_IAM_LOAD_MANAGED_POLICIES=true


5.0.0alpha2:
------------

    General:
        * It is now possible to configure methods/services which should reach out to AWS.
          @mock_aws(
              config={"core": {"mock_credentials": False, "passthrough": {"urls": [], "services": []}}}
          )
        * All requests now return a RequestId

    Miscellaneous:
        * S3: list_objects() now returns a hashed ContinuationToken


5.0.0alpha1:
------------

    General:
        * All decorators have been replaced with a single decorator:
          `mock_aws`
        * The `mock_batch_simple` and `mock_lambda_simple` decorators can now be configured using the `config`-parameter:
          `@mock_aws(config={"batch": {"use_docker": False}, "lambda": {"use_docker": False}})`


4.2.13
-----
Docker Digest for 4.2.13: _sha256:20a2fdd4828b0ce1170ae26186ed28b64523cf6af83af892a74d9b3e23f84471_

    New Services:
        * Panorama:
            * delete_device()
            * describe_device()
            * list_devices()
            * provision_device()
            * update_device_metadata()

    New Methods:
        * CognitoIDP:
            * admin_respond_to_auth_challenge()

        * IdentityStore:
            *  list_group_memberships_for_member()

        * Rekognition:
            * compare_faces()
            * detect_labels()
            * detect_text()

        * SSO-Admin:
            * attach_customer_managed_policy_reference_to_permission_set()
            * attach_managed_policy_to_permission_set()
            * delete_inline_policy_from_permission_set()
            * detach_customer_managed_policy_reference_from_permission_set()
            * detach_managed_policy_from_permission_set()
            * get_inline_policy_for_permission_set()
            * list_account_assignments_for_principal()
            * list_customer_managed_policy_references_in_permission_set()
            * list_managed_policies_in_permission_set()
            * put_inline_policy_to_permission_set()

        * Textract:
            * detect_document_text()

    Miscellaneous:
        * ACM: describe_certificate() now returns a DomainValidationOption for each SN
        * CloudFormation: create_change_set() now longer throws an exception when supplying a YAML TemplateBody
        * CognitoIDP: create_resource_server() no longer crashes when the scope-parameter is not provided
        * DynamoDB: scan() now correctly handles the ScanFilter-attribute again (broken in 4.2.11)
        * EC2: launch templates created by CloudFormation now have a generated name if not provided
        * EC2: describe_instance_types() now handles unknown values for EnaSupport correctly
        * Sagemaker: create_model_package() nown supports Versioned packages
        * Scheduler: delete_scheduler() now throws the correct exception when a Schedule does not exist
        * SSO-Admin: list_account_assignments() now supports pagination


4.2.12
------

    Miscellaneous:
        * AWSLambda: list_functions() now returns a default PackageType (ZIP) if not specified
        * CloudFormation: AWS::EC2::LaunchTemplate resources now support Fn::GetAtt operations
        * CognitoIDP: admin_initiate_auth() now correctly returns a Challenge when 2FA is enabled
        * DynamoDB: execute_statement() now supports INSERT/UPDATE/DELETE queries
        * EC2: describe_availability_zones() now supports the ZoneNames/ZoneIds-parameters
        * KMS: encrypt() now validates payloads that are too large
        * ResourceGroupTaggingAPI: get_resources() now supports SQS queues
        * Route53: list_hosted_zone()/list_hosted_zones_by_name() now return the CallerReference
        * S3: copy() now respects the ExtraArgs-parameter when using MultiPart uploads
        * S3: list_object_versions() now supports pagination
        * S3: put_object_tagging() now validates the number of tags provided


4.2.11
-----
Docker Digest for 4.2.11: _sha256:f2a24d8a3440bf397705e461b33a032bbb6d3511cd9c643e71419dd962b3384e_

    New Methods:
        * Lambda:
            * DeleteFunctionEventInvokeConfig()
            * GetFunctionEventInvokeConfig()
            * ListFunctionEventInvokeConfigs()
            * PutFunctionEventInvokeConfig()
            * UpdateFunctionEventInvokeConfig()

        * Logs:
            * describe_export_tasks()

    Miscellaneous:
        * DynamoDB: put_item() now returns old item for ConditionalCheckFailed exceptions
        * DynamoDB: scan() now returns the correct ScannedCount when passing the Limit-parameter
        * DynamoDB: transact_write_items() now validates that Keys in Update-queries are not empty
        * IOT: create_thing()/describe_thing() now returns the thingId
        * Logs: create_export_task() now actually exports the data to S3
        * ResourceGroupsTaggingAPI: get_resources() now supports ACM certificates


4.2.10
-----
Docker Digest for 4.2.10: _sha256:f72acd62b994654d01bdec6f5cc779f4ab30083b441e2fb7eff0c13e0bbfdca7_

    New Methods:
        * CognitoIdentity: list_identity_pools()

    Miscellaneous:
        * Autoscaling: describe_tags() now supports the key/value filters
        * CloudFormation: AWS::Logs::LogGroup now supports tags
        * CloudWatch: get_metric_data() no longer throws an error when supplying >10 queries
        * CognitoIdentity: get_credentials_for_identity() now returns Expiration as a number, fixing compatibility with the GoLang SDK
        * EFS: describe_access_points() now supports the FileSystemId-parameter
        * LakeFormation: list_permissions() now supports the DataLocation-parameter
        * LakeFormation: register_resource() now throws an exception when registering an existing resource
        * SQS: Ensure all responses are in JSON-format when required, fixing compatibility with the Ruby SDK


4.2.9
-----
Docker Digest for 4.2.9: _sha256:4e9d89322b5ca9196fa7efda78b1269580be7aa6879894950e2728edc946573f_

    General:
        * Fix compatibility with botocore 1.32.1

    Miscellaneous:
        * ECS: Tagging is now supported for Tasks
        * LakeFormation: deregister_resource() now throws the correct error for unknown resources
        * LakeFormation: list_permissions() now supports Parameters
        * RDS: create_db_instance() now validates the engine parameter
        * Transcribe: TranscriptionJobs now support the Subtitles-parameter

4.2.8
-----
Docker Digest for 4.2.8: _sha256:937315c79dedcc86506fc22a60502fd73d0e6f3a6f3e5fc614dd3164740e1191_

    General:
        * Support for Python 3.12
        * Support for a Simple Lambda backend, that will mock functions without invoking a Docker container.
          Use the decorator `mock_lambda_simple` for this feature.

    New Methods:
        * IdentityStore:
            * describe_group()

        * Signer:
            * list_tags_by_resource()
            * tag_resource()
            * untag_resource()

    Miscellaneous:
        * DynamoDB: create_table() now throws an error when supplying an unknown KeyType
        * DynamoDB: query() now throws an error when supplying a ExpressionAttributeValue that doesn't start with a ':'
        * EC2: describe_hosts() now returns the AllocationTime-attribute
        * ECS: register_task_definition() now throws an exception if the ContainerDefinition has missing keys
        * ECR: describe_images() now returns the supplied imageDigest-values, instead of random values
        * EFS: AccessPoints now have the correct identifier format
        * Lambda: Various methods now support the FunctionName in the format 'name:qualifier'
        * MQ: create_configuration() is now possible for engine-type 'RABBITMQ'
        * RDS: create_db_cluster() now throws an error if the provided engine is not supported
        * RDS: create_db_instance() now throws an error if the provided engine does not match the cluster engine
        * RDS: delete_db_cluster() now throws an error if any instances are still active
        * SageMaker: list_model_packages() and list_model_package_groups() no longer throw an error on pagination

4.2.7
-----
Docker Digest for 4.2.7: _sha256:9149597856f5ce195ef451df1a1b96aa8db0692c4b8ed1f7952fc02952733103_

    New Services:
        * Inspector2:
            * associate_member()
            * batch_get_account_status()
            * create_filter()
            * delete_filter()
            * describe_organization_configuration()
            * disable()
            * disable_delegated_admin_account()
            * disassociate_member()
            * enable()
            * enable_delegated_admin_account()
            * get_member()
            * list_delegated_admin_accounts()
            * list_filters()
            * list_findings()
            * list_members()
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()
            * update_organization_configuration()

    New Methods:
        * ECR:
            * batch_get_repository_scanning_configuration()
            * put_registry_scanning_configuration()

    Miscellaneous:
        * Batch: submit_job() now returns the jobArn-attribute
        * DynamoDB: execute_statement() has now support for nested WHERE-clauses with functions
        * DynamoDB: update_item() now returns item for ConditionalCheckFailed-exceptions
        * EC2: create_key_pair() and describe_key_pair(s)() now support tags
        * Route53: get_hosted_zone() now returns the CallerReference
        * S3: get_object/put_object() now accepts AccessPoint ARN's
        * S3Control: create_access_point() now returns the correct Alias
        * SES: list_identities() now supports the IdentityType-parameter
        * SNS: create_platform_application has improved error handling

4.2.6
-----
Docker Digest for 4.2.6: _sha256:ad3265531405fd48489ddee7e1fa7301b4d0f46b55daca7ba5039e73eaf70ac1_

    New Services:
        * IVS:
            * batch_get_channel()
            * create_channel()
            * delete_channel()
            * get_channel()
            * list_channels()
            * update_channel()

    New Methods:
        * LakeFormation:
            * add_lf_tags_to_resource()
            * get_resource_lf_tags()
            * remove_lf_tags_from_resource()
            * update_lf_tag()

        * Sagemaker:
            * describe_model_package_group()
            * update_model_package()

    Miscellaneous:
        * Batch: submit_job() now behaves correctly when passing the arrayProperties-parameter
        * DynamoDB: Improved PartiQL parser, with support for different types (Decimals/Booleans) and queries with quoted table-names
        * EC2: TagSpecifications now throw an error if the ResourceType is not provided
        * EC2: run_instances()/describe_instances() now always return the same attributes (before, both operations were missing different fields)
        * EC2: associate_dhcp_options() now supports DhcpOptionsId=default
        * EC2: create_key_pair() now supports the KeyType-parameter
        * EC2: run_instances() now returns the Placement.HostId attribute
        * ELBv2: modify_target_group_attributes() now has additional validations
        * Events: put_events() now throws a warning when Detail field is not a dict
        * IOT: update_thing() now behaves correctly with empty attributes
        * S3: head_object() now raises a MethodNotAllowed for DeleteMarkers

4.2.5
-----
Docker Digest for 4.2.5: _sha256:076cecca9b8ba35b545d23eb5bf780902fbf23eb3610f332eef7adea1f4d2ef7_

    General:
        * Introducing: MotoProxy! An alternative to the MotoServer.
          See the docs: http://docs.getmoto.org/en/latest/docs/proxy_mode.html

    New Methods:
        * Sagemaker:
            * list_model_package_groups()

    Miscellaneous:
        * CognitoIDP: update_user_pool() no longer overrides default settings
        * CognitoIDP: set_user_mfa_preference() now allows the settings to be cleared
        * EC2: Transit Gateway Peering Attachments are now supported across accounts
        * EC2: delete_fleets() now sets the correct status
        * ECS: The Task-statuses now automatically advance
        * Glue: get_databases/get_tables() now return the CatalogId
        * IAM: list_groups() now returns the CreateDate-attribute
        * Redshift: describe_clusters() now returns the TotalStorageCapacityInMegabytes
        * SES: Templates now support if/else constructs

4.2.4
-----
Docker Digest for 4.2.4: _sha256:4cdda5b0245a28ae2ebf5f1d5d93425226fe00ace65819a9fa02c8aa77a7e0b6_

    New Methods:
        * OpenSearch:
            * list_domain_names()

    Miscellaneous:
        * DynamoDB: Fixed a bug where binary data could not be queried (introduced in 4.2.3)
        * EC2: VPC Peering Connections are now supported across accounts
        * ECS: register_task_definition() now validates the PidMode has the correct value
        * S3: put_bucket_notification_configuration() now supports SNS Topic targets

4.2.3
-----
Docker Digest for 4.2.3: <autopopulateddigest>

    New Services:
        * RoboMaker:
            * create_robot_application()
            * delete_robot_application()
            * describe_robot_application()
            * list_robot_applications()

    New Methods:
        * ElasticBeanstalk:
            * delete_application()

        * Events:
            * create_partner_event_source()
            * delete_partner_event_source()
            * describe_event_source()
            * describe_partner_event_source()
            * put_partner_events()

    Miscellaneous:
        * Core: The mocked ACCESS_KEY has been changed from `foobar_key` to `FOOBARKEY`, to align with AWS guidelines
        * Core: set_initial_no_auth_action_count() now supports SSM actions
        * Core: Fixed a memory leak when comparing requests (introduced in 4.1.13)
        * Athena: get_query_execution() now returns a StatementType dependent on the provided query
        * DynamoDB: query() now throws an exception when the KeyConditionExpression contains a literal value
        * EBS: put_snapshot_block() now supports random bytes
        * EC2: describe_transit_gateways() now supports filtering by tags
        * ELBv2: describe_target_groups() now throws an exception for invalid input parameters
        * ELBv2: describe_target_groups() now sorts the result before returning it
        * ELBv2: create_target_group() now has improved validation and default values
        * ELBv2: create_rule() now creates links between the TargetGroups and LoadBalancers
        * Events: put_events() now support HTTP targets
        * IAM policy validation now takes the provided Resource-argument into account when validating access to STS-resources
        * IAM: get_role() now returns the LastUsed-parameter, provided the role was assumed and used
        * KMS: sign/verify now uses the original message when signing, not the base64-version
        * Lambda: invoke() now loads any Layers provided in the create_function()
        * S3: put_bucket_logging() now supports bucket policies (as well as ACP's)
        * S3: Range requests are now more permissive (following AWS' behaviour)
        * SFN: list_executions() now returns the StopDate-attribute

4.2.2
------
Docker Digest for 4.2.2: <autopopulateddigest>

    See 4.2.1 - no functional changes.

4.2.1
------
Docker Digest for 4.2.1: <autopopulateddigest>

    New Services:
        * Sagemaker Runtime:
            * invoke_endpoint()

    New Methods:
        * CognitoIDP:
            * describe_resource_server()
            * list_resource_servers()

        * CognitoIDP:
            * create_cache_cluster()
            * delete_cache_cluster()
            * describe_cache_clusters()

        * IdentityStore:
            * list_users()

        * Logs:
            * describe_query_results()
            * get_query_results()
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()

        * Sagemaker:
            * list_notebook_instances()

    Miscellaneous:
        * EC2: describe_transit_gateways() now returns the ARN
        * IAM policies now allow S3 accesspoint arns
        * KMS: sign() now supports RSASSA_PSS_SHA_384, RSASSA_PSS_SHA_512 and RSASSA_PKCS1_* algorithms
        * Logs: Now supports two subscription filters
        * RDS: Clusters now support the ServerlessV2ScalingConfiguration parameter
        * ResourceGroupsTaggingAPI: tag_resource() now supports RDS resources
        * S3: CrossAccount access can now be disabled, using MOTO_S3_ALLOW_CROSSACCOUNT_ACCESS=false
        * SecretsManager: Allow creation/update of secrets without values
        * SES: set_identity_mail_from_domain() - the Identity can now also be an email


4.2.0
------
Docker Digest for 4.2.0: _sha256:92e59875783037b2558067d2d3f9dd2502c140881ff5c44c44ddbce6658a89b7_

    General:
        The Docker image is now based on Python 3.11 (instead of 3.7)

4.1.15
------
Docker Digest for 4.1.15: _sha256:eb63b1e0cbbd757e4596844e6ac1865660cbf8e358203b79e5404d57de94dd69_

    New Services:
        * APIGateway Management API:
            * delete_connection()
            * get_connection()
            * post_to_connection()

    New Methods:
        * Autoscaling:
            * delete_warm_pool()
            * describe_warm_pool()
            * put_warm_pool()

        * IdentityStore:
            * list_groups()

        * IOTData:
            * list_named_shadows_for_thing()

        * MQ:
            * list_tags()

        * ServiceDiscovery:
            * update_private_dns_namespace()
            * update_public_dns_namespace()

    Miscellaneous:
        * ACM-PCA: create_certificate_authority() now supports the KeyStorageSecurityStandard-parameter
        * Batch: create_job_definition() now returns more default fields in the containerProperties field
        * CloudTrail: get_trail_status now works with MultiRegion trails
        * CognitoIDP: UserPools now return the AccountRecoverySetting-field by default
        * DynamoDB: query() now throws an exception when providing empty ProjectionExpressions/FilterExpressions
        * EC2: describe_vpc_endpoint_services() now returns user-defined ones
        * EC2: run_instances() now supports the Monitoring-attribute
        * IOT: group names can now contain special characters
        * IOTData now supports named shadows
        * KMS: create_key() now supports KeySpecs RSA_3072 and RSA_4096
        * KMS: create_key() now validates the provided KeySpec
        * Lambda: create_function() now fails when creating a function with a name that already exists
        * Lambda: put_function_concurrency() now errors on a quota that exceeds the value set by MOTO_LAMBDA_CONCURRENCY_QUOTA
        * Lambda: update_function_code() now supports the ImageUri-attribute
        * RDS: describe_db_cluster_snapshots() now returns the TagList-property
        * ResourceTaggingsAPI: Now supports Glue resources
        * S3: Authentication now allows specific resources in the IAM access policy 
        * S3: select_object_content() now takes RecordDelimiter into account
        * Scheduler: create_scheduler() now errors on duplicate names
        * TimestreamWrite: create_table() now supports the Schema-attribute


4.1.14
------
Docker Digest for 4.1.14: _sha256:4cc82c0803c6b578d5c4146a8e38ff0387dec565483cfaa63eb238cb867e97e6_

    New Methods:
        * SageMaker:
            * create_model_package()
            * create_model_package_group()
            * describe_model_package()
            * list_model_packages()

    Miscellaneous:
        * CloudFormation: describe_stack_instances() now returns the StackInstanceStatus-attribute
        * CloudFront: update_distribution() now supports the DefaultRootObject-parameter
        * CloudWatch: get_metric_data() now support (simple) Expressions
        * CognitoIDP: initiate_auth() and admin_initiate_auth() now throw a NotAuthorizedError for disabled users
        * EC2 VPC's: Add CloudFront, Ground Station and Lattice prefix lists
        * IOT: search_index() now returns the connectivity-attribute
        * Organizations: Introduce more trusted service principals
        * RDS: create_db_cluster() now supports the VpcSecurityGroupIds-parameter
        * S3: Optional support for CRC32C checksums
        * SNS: publish_batch() now sends the required `MessageDeduplicationId` for FIFO queues
        * SQS: send_message_batch() now only throws a `BatchRequestTooLong` if the sum of all messages exceed the limit 

4.1.13
------
Docker Digest for 4.1.13: _sha256:ec471bcfbf66def946466398f002e8edfbb667bde7b1d8033aedbdd4453fbb8e_

    General:
        * The ISO-regions introduced in 4.1.12 are now locked behind an environment variable: `MOTO_ENABLE_ISO_REGIONS`
        * General performance improvements in the URL matching logic - especially `mock_all` users should notice improvements

    New Methods:
        * APIGatewayV2:
            * create_stage()
            * delete_stage()
            * get_stage()
            * get_stages()

        * CloudFront:
            * create_origin_access_control()
            * delete_origin_access_control()
            * get_origin_access_control()
            * list_origin_access_controls()
            * update_origin_access_control()

        * Lambda:
            * list_aliases()

        * Logs:
            * delete_destination()
            * describe_destinations()
            * get_destination()
            * put_destination()
            * put_destination_policy()

        * Route53:
            * get_health_check_status()

        * SSM:
            * deregister_task_from_maintenance_window()
            * describe_maintenance_window_tasks()
            * register_task_with_maintenance_window()

    Miscellaneous:
        * Batch: create_compute_environment() now validates instanceRole and minvCpu
        * CloudFront: create_distribution() now correctly handles a single alias
        * CloudFront - CustomOrigins now have default timeouts if not supplied
        * DynamoDB: delete_item() now throws the correct error when the table is not found
        * EC2: describe_security_group_rules() now returns the GroupId
        * ECR: create_repository() now validates the repositoryName-parameter
        * Lambda: create_function() now returns the ImageConfigResponse and EphemeralStorage parameters
        * IOTData: publish() can now handle non-Unicode bytes
        * RDS: Automated snapshots now have the appropriate SnapshotType
        * Route53: create_hosted_zone() now returns the Location
        * Scheduler: get_schedule() now returns the CreationDate and LastModificationDate
        * SecretsManager: delete_secret() now throws an error when setting the Recovery to 0 days
        * StepFunctions: start_execution() now validates the name-length


4.1.12
------
Docker Digest for 4.1.12: _sha256:38e34a1ee4042fd52f15703c2e750780fe0fd809b2745fd263b2d1de33566590_

    General:
        * Support for ISO regions
        * The official Docker image now comes with curl pre-installed

    New Services:
        * AppConfig:
            * create_application()
            * create_configuration_profile()
            * create_hosted_configuration_version()
            * delete_application()
            * delete_configuration_profile()
            * delete_hosted_configuration_version()
            * get_application()
            * get_configuration_profile()
            * get_hosted_configuration_version()
            * list_configuration_profiles()
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()
            * update_application()
            * update_configuration_profile()

    New Methods:
        * IdentityStore:
            * create_user()
            * describe_user()
            * delete_user()
            * get_group_id()
            * delete_group()
            * create_group_membership()
            * get_group_memberships()
            * delete_group_membership()

        * SSM:
            * create_patch_baseline()
            * describe_patch_baselines()
            * delete_patch_baseline()
            * register_target_with_maintenance_window()
            * describe_maintenance_window_targets()
            * deregister_target_from_maintenance_window()


    Miscellaneous:
        * Moto Dashboard no longer fails to load after an S3 file is overwritten
        * CloudFormation: AWS:SSM::Parameter now exposes the PhysicalResourceId
        * CloudFront: create_invalidation() now behaves correctly when supplying a single Path
        * CloudWatch: get_metrics_data() now validates the provided start/end times
        * CodeBuild: create_project() now accepts all ServiceRole ARN's, not just ARN's that end in /service-role/
        * Config: put_configuration_recorder() now supports resource type exclusions
        * DMS: describe_replication_tasks() now returns TableMappings and ReplicationTaskSettings in the correct format
        * DynamoDB now supports ProjectionExpressions on (nested) lists
        * EC2: New availability zones have been added for ap-south-1, sa-east-1, ca-central-1, us-west-2
        * EC2: create_flow_logs() now allows different LogDestinations for a single ResourceId
        * EC2: replace_route() now returns the appropriate error when called with missing route
        * EC2: create_volume() now supports the Throughput-parameter
        * ECR: put_image() now correctly overwrites tags on images with multiple tags
        * IAM: add_role_to_instance_profile() now validates whether a role was already attached (only one is allowed)
        * Lambda: delete_layer_version() now also accepts function ARNs
        * MediaConnect: create_flow_payload() no longer requires the Entitlements-parameter
        * RDS: Further improve Global Cluster behaviour
        * S3: GET/PUT requests now return Access-Control headers, if a CORS configuration has been set
        * S3: put_bucket_lifecycle_configuration() now supports multiple Transitions
        * SESv2: create_contact_list() now correctly reads Topics with special characters
        * SESv2: send_email() now correctly reads raw emails


4.1.11
------
Docker Digest for 4.1.11: _sha256:0ac1ec726e428bd3134c10c32639d72f814bbe002b9d2010420850aab8bc2550_

    New Methods:

        * AppSync:
            * get_introspection_schema()

        * Comprehend:
            * detect_key_phrases()
            * detect_pii_entities()
            * detect_sentiment()

    Miscellaneous:
        * EC2: describe_key_pairs() now returns the CreateTime-attribute
        * EC2: describe_spot_fleet_requests() now returns the Tags-attribute
        * ECR: put_image(): now behaves correctly on duplicate images with duplicate tags
        * Organizations: create_policy() now supports the Tags-parameter
        * RDS: creation times of all objects are now in UTC
        * Redshift: creation times of all objects are now in UTC
        * S3: Bucket names are now global, meaning they have to be unique across accounts
        * S3: select_object_content() now supports None-values
        * S3: select_object_content() now supports nested FROM-clauses (from x.y as xy)
        * SecretsManager - update_secret() now supports the Description-parameter
        * SNS now returns the correct error message for non-existing topics
        * SNS: Topics are no longer accessible across regions (only across accounts)
        * SNS: delete_topic() is now idempotent and no longer throws an error for non-existent topics
        * SQS: Requests and responses in JSON-format are now supported
        * SSM: MaintenanceWindows now have tagging support

4.1.10
------
Docker Digest for 4.1.10: _sha256:095d1dfadc71b4c68f05240129a32acf6dd7ba722c78afd4f01d8c7c3af0ebb4_

    New Services:
        * Glue:
            * create_session()
            * delete_session()
            * get_session()
            * list_sessions()
            * stop_session()

        * Sagemaker:
            * create_transform_job()
            * describe_transform_job()
            * list_transform_jobs()

    Miscellaneous:
        * Core: The `date`-header is now returned for all operations (set to the current date)
        * AutoScaling: describe_policies() now returns the field `TargetTrackingConfiguration.CustomizedMetricSpecification.Metrics`
        * Cloudformation: delete_stack_instances() now behaves correctly when deleting multiple regions
        * EC2: create_route() now takes the `VpcEndpointId`-parameter into account
        * EC2: describe_instances() now throws an exception when both the InstanceIds and PaginationConfig parameters are supplied
        * IAM: get_group() now returns the fields `CreateDate` and `PasswordLastUsed`
        * RDS: start_export_task() now returns the field `SourceType`
        * S3: aligned checksum calculation with how AWS behaves
        * S3: now returns `Accept-Ranges`-headers, instead of `AcceptRanges`, in-line with AWS
        * S3: copy_object() now behaves correctly when copying objects in encrypted buckets
        * S3: put_object_legal_hold() now takes the VersionId-parameter into account
        * S3: put_object_retention() now takes the VersionId-parameter into account
        * SecretsManager: list_secrets now returns the fields `LastRotatedDate` and `NextRotationDate`
        * SNS: Topics can now be accessed across accounts
        * SNS: Fixed a bug so that topics without properties can now be deleted using CloudFormation


4.1.9
-----
Docker Digest for 4.1.9: _sha256:121a51dcf0e42e53a601803bdeb25324d18b2d45f08a79923c65034f4f14448a_

    New Services:
        * Glue:
            * batch_get_triggers
            * create_trigger
            * delete_trigger
            * get_trigger
            * get_triggers
            * list_triggers
            * start_trigger
            * stop_trigger

        * Glue:
            * create_contact
            * create_contact_list
            * delete_contact
            * delete_contact_list
            * get_contact
            * get_contact_list
            * list_contact_lists
            * list_contacts
            * send_email

    Miscellaneous:
        * Kinesis: Improve calculations on stream limits
        * EC2: Improve logic behind describe_image_attribute()
        * S3: Various improvements to the logic behind copy_object()
        * Scheduler: update_schedule() now supports the GroupName-parameter
        * SNS: Improve and enhance validation of numeric parameters
        * SNS: MessageDeduplicationId is now forwarded to SQS queues (Fixes a bug in 4.1.7)


4.1.8
-----
Docker Digest for 4.1.8: _sha256:e83d868df71b193d625d9fb031282f6632c6c80d0314cfca6780f9a3f37d1f61_

    New Methods:
        * DynamoDB:
            * batch_execute_statement()
            * execute_statement()
            * execute_transaction()

        * Glue:
            * batch_get_jobs()
            * delete_job()

        * KMS:
            * get_public_key()

    Miscellaneous:
        * Athena: Fixed a bug causing every call to `get_workgroup(WorkGroup="primary")` to fail
        * AWSLambda: Performance improvement: Docker images are no longer re-downloaded if they already exist
        * BatchSimple now uses the environment variable MOTO_SIMPLE_BATCH_FAIL_AFTER=0 to determine whether the job should fail, and after how many seconds
        * EC2: replace_route() now supports the NetworkInterfaceId-parameter
        * ECR: batch_get_image() now correctly returns images when requested using an older tag
        * ELBv2: describe_target_health() now returns the correct error message for unregistered targets
        * S3: copy_object() now adds a checksum to a copied object if requested
        * S3: get_object() no longer returns a VersionId for non-versioned buckets
        * SES: Templates now allow a single curly brace, and no longer assume it's part of a variable
        * SSM: describe_parameters() now allows filtering by existence of tag-name
        * StepFunctions: The SF_EXECUTION_HISTORY_TYPE=FAILURE environment variable can now be used to generate failure responses for all operations
        * STS: assume_role() now stores the AccessKey in the requesting account


4.1.7
-----
Docker Digest for 4.1.7: _sha256:6b877d5efe86562d27f296638d6b163c7987913c203874578d00fa1f83eea000_

    New Services:
        * LakeFormation:
            * batch_grant_permissions()
            * batch_revoke_permissions()
            * create_lf_tag()
            * delete_lf_tag()
            * deregister_resource()
            * describe_resource()
            * get_data_lake_settings()
            * get_lf_tag()
            * grant_permissions()
            * list_data_cells_filter()
            * list_lf_tags()
            * list_permissions()
            * list_resources()
            * put_data_lake_settings()
            * register_resource()
            * revoke_permissions()
        * RDS Data:
            * execute_statement()
        * Scheduler:
            * create_schedule()
            * create_schedule_group()
            * delete_schedule()
            * delete_schedule_group()
            * get_schedule()
            * get_schedule_group()
            * list_schedule_groups()
            * list_schedules()
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()
            * update_schedule()

    New Methods:
        * Config: 
            * delete_retention_configuration()
            * describe_retention_configurations()
            * put_retention_configuration()
        * EC2: 
            * get_launch_template_data()
        * RDS:
            * create_db_cluster_parameter_group()
            * create_global_cluster()
            * delete_db_cluster_parameter_group()
            * delete_global_cluster()
            * describe_db_cluster_parameter_groups()
            * describe_db_cluster_parameters()
            * describe_db_subnet_groups()
            * describe_global_clusters()
            * promote_read_replica_db_cluster()
            * remove_from_global_cluster()

    Miscellaneous:
        * APIGateway now allows semicolons in paths
        * CloudFormation now supports Fn::ToJsonString
        * DynamoDB: update_item() now supports number-sets in the AttributeUpdates-parameter
        * DynamoDB: query() - The KeyConditionExpression now allows enclosing the sort key condition in brackets
        * EC2: assign_private_ip_addresses() now supports the PrivateIpAddresses-argument
        * ECR: put_image() now supports the imageManifestMediaType parameter
        * ECS: run_task() now validates the provided launch-type
        * Logs: put_subscription_filter() now supports KinesisStream destinations
        * RDS: describe_db_clusters() now supports filtering by db-cluster-id and engine
        * RDS: describe_db_clusters() now returns the parameters KmsKeyId, NetworkType, DBSubnetGroupName, ScalingConfiguration
        * S3: head_object() now returns the AcceptRanges header
        * SQS: Improvements in the deduplication-logic

4.1.6
-----
Docker Digest for 4.1.6: _sha256:36122dca33cb8f70d84734d1a0a6a5931f7a533fab3c58edd7ca0b2ebe325797_

    New Services:
        * OpenSearch:
            * add_tags()
            * create_domain()
            * delete_domain()
            * describe_domain()
            * describe_domain_config()
            * get_compatible_versions()
            * list_tags()
            * remove_tags()
            * update_domain_config()

    Methods:
        * S3: select_object_content()

    Miscellaneous:
        * Batch: The AWS_BATCH_JOB_MAIN_NODE_PRIVATE_IPV4_ADDRESS-variable now plays nicely with custom Docker networks
        * CloudFormation now supports deletion of AWS::EC2::Subnet, AWS::EC2::VPC
        * CloudFormation now supports variable mapping inside "Fn::Sub"
        * CloudFormation: delete_stack() now adheres to "DeletionPolicy": "Retain" set for individual resources
        * Events: The EventBusName-parameter is now supported for these methods:
          delete_rule(), describe_rule(), disable_rule(), enable_rule(), list_rule_names_by_target(), list_rules(), list_targets_by_rule()
        * RDS: describe_db_clusters() now accepts an ARN as identifier
        * RDS: describe_db_snapshots() now returns the TagList-attribute
        * S3: get_object() now returns the AcceptRanges header
        * S3: head_bucket() now returns the region-header
        * SecretsManager now supports partial ARN's


4.1.5
-----
Docker Digest for 4.1.5: _sha256:0e43c36e1b1390106ec43b2e383486c45fef27646838acaa8073cbd2b4a97a31_

    General: 
        * Our Docker-images are now also hosted in GHCR:
          https://github.com/getmoto/moto/pkgs/container/motoserver

    New Methods:
        * Athena:
            * create_prepared_statement()
            * get_prepared_statement()
            * list_named_queries()

        * S3:
            * get_object_attributes()

        * SecretsManager:
            * delete_resource_policy()
            * put_resource_policy()

    Miscellaneous:
        * Athena: Now automatically creates the default WorkGroup called `primary`
        * AWSLambda: the default data dir for Docker containers can now be customized using the environment variable MOTO_LAMBDA_DATA_DIR
        * CloudFormation now supports the resource AWS::CloudFormation::Stack 
        * CognitoIDP: the ID-token now uses the key cognito:username, instead of username
        * EC2: describe_security_group_rules() now provides the correct value for the IsEgress-parameter
        * EC2: revoke_security_group_egress() no longer throws an error when the IPProtocol-argument is not provided
        * Glue: get_job() now supports the parameters CodeGenConfigurationNodes, ExecutionClass, SourceControlDetails
        * IOT: delete_certificate() now supports the forceDelete-parameter


4.1.4
-----
Docker Digest for 4.1.4: _sha256:32ed22e2c69826a90482d0e473c460d60c3c7dc60819d95c0c165e0e978208db_

    General:
        Data is now deleted after the mock ends. If you use manual mocks, you can still choose the keep the data:
        mock = mock_sqs()
        mock.start()
        mock.stop(remove_data=False)

    New Services:
        * Neptune:
            * create_db_cluster()
            * create_global_cluster()
            * delete_db_cluster()
            * delete_global_cluster()
            * describe_db_clusters()
            * describe_global_clusters()
            * describe_orderable_db_instance_options()
            * modify_db_cluster()
            * start_db_cluster()

    New Methods:
        * Glue:
            * get_jobs()
            * get_table_version()

    Miscellaneous:
        * APIGateway: update_rest_api() now updates the policy-attribute
        * Athena now exposes an endpoint to store mock query results. See http://docs.getmoto.org/en/latest/docs/services/athena.html
        * CognitoIDP: The idToken now contains the cognito:groups attribute
        * DynamoDB: scan() now respects the Projection-attribute of a GSI/LSI
        * KMS: encrypt(), decrypt(), re_encrypt() now accept aliases as arguments
        * KMS: list_aliases() now supports the KeyId-parameter
        * Lambda: FIFO Queues are now supported event sources
        * RDS: create_option_group() now returns the OptionGroupArn-attribute
        * ResourceGroupsTaggingAPI: get_resources() now supports RDS Clusters and ClusterSnapshots
        * SSM now includes the parameters at /aws/service/ecs/optimized-ami 


4.1.3
-----
Docker Digest for 4.1.3: _sha256:3139cdae44d5da35d92d9e385cb878581eef8df3514cbda5cbc3e103488095a7_

    New Services:
        * IdentityStore:
            * create_group()

    Miscellaneous:
        * DynamoDB: create_table() now deals correctly with non-key attributes supplied as part of the KeySchema
        * Glue: get_partitions() now supports nano-second precision when filtering timestamps
        * Glue: get_table_version() now returns the Table.VersionId and Table.UpdateTime-attributes
        * Transcribe: start_transcription_job() now supports the IdentifyMultipleLanguages-parameter


4.1.2
-----
Docker Digest for 4.1.2: _sha256:742bd95faadb80133aa7082ca6f4d1d71af2f4802833e92348b082b11ec8d4ed_

    New Methods:
        * Batch:
            * create_scheduling_policy()
            * delete_scheduling_policy()
            * describe_scheduling_policies()
            * list_scheduling_policies()
            * update_scheduling_policy()

        * EC2:
            * allocate_hosts()
            * describe_hosts()
            * modify_hosts()
            * release_hosts()

        * ECS:
            * put_cluster_capacity_providers()
            * update_capacity_provider()
            * update_cluster()

        * Glue:
            * batch_get_crawlers()

    Miscellaneous:
        * AWSLambda: Base Images are now pulled from multiple repositories, increasing the number of supported language/versions out of the box
        * CognitoIDP: admin_update_user_attributes() now checks for duplicate emails
        * ECS: create_cluster() now supports the parameters configuration, capacityProviders, defaultCapacityProviderStrategy
        * ECS: delete_cluster() now marks the cluster as INACTIVE, rather than removing it outright, in-line with how AWS behaves
        * ECS: register_task_definition() now supports the parameters proxyConfiguration, inferenceAccelerators, runtimePlatform, ipcMode, pidMode, ephemeralStorage
        * ECS: run_task() no longer crashes when providing launchType=FARGATE
        * ECS now has improved tagging-support
        * EKS: create_nodegroup() now returns the correct launchTemplate-attributes
        * Kinesis now supports the streamARN-parameter for all arguments
        * S3: Improved bucket policy enforcement



4.1.1
-----
Docker Digest for 4.1.1: _sha256:abb85db28568fc355636dac710a8108ba3cdb01bf1c129118cf1ce49eb8c5f07_

    New Methods:
        * APIGateway:
            * get_export()

        * EC2:
            * describe_security_group_rules()

        * Glue:
            * delete_registry()
            * get_registry()
            * get_schema()
            * list_registries()
            * update_schema()

        * Sagemaker:
            * describe_pipeline()
            * describe_pipeline_definition_for_execution()
            * describe_pipeline_execution()
            * list_pipeline_executions()
            * list_pipeline_parameters_for_execution()
            * start_pipeline()

    Miscellaneous:
        * APIGateway: put_integration() now supports the connectionType-parameter
        * Batch: register_job_definition() now supports type="multinode"
        * EC2: describe_launch_template_versions() now supports $Latest and $Default versions
        * ECS: list_services() now throws correct error when providing unknown cluster
        * ECS: start_task() now supports the tags-parameter
        * Events: put_events() now supports sending events to an eventbus in another region/account
        * KMS: list_aliases() now returns the TargetKeyId-attribute
        * S3: put_bucket_logging() now actually logs incoming requests, when enabled
        * SES: Fixed a bug where the service was not region-aware, i.e. all resources were shared across regions
        * SES: improved parser support for email templates
        * SSM: put_parameter() now validates the value of the Type-parameter
        * RDS: create_db_instance() now supports the PreferredMaintenanceWindow and PreferredBackupWindow-parameters


4.1.0
-----
Docker Digest for 4.1.0: _sha256:1c38613f7273054650d08f3cb3ce118753296d08ffbfee8c96400c89a529c9ca_

    General:
        * Dropped support for Py 3.6
        * Moto now uses setup.cfg to hold our packaging configuration, instead of setup.py, making Moto compatible with more recent Pip-versions


4.0.13
-----
Docker Digest for 4.0.13: _sha256:703a9d464c11e1f4cacff66acdc9b46f9fa8fb0b969ca9f1e79fa4eb41678565_

    New Methods:
        * EC2:
            * get_password_data()
        * Sagemaker:
            * update_pipeline()
        * SecretsManager:
            * cancel_rotate_secret()

    Miscellaneous:
        * CloudWatch: put_metric_data() now supports the StatisticValues-parameter
        * CognitoIDP: sign_out() now also invalidates the AccessToken
        * IAM: get_account_authorization_details() now returns the Tags-attribute
        * IOT: create_keys_and_certificate() now creates valid certificates, instead of random data


4.0.12
-----
Docker Digest for 4.0.12: _sha256:06916d3f310c68fd445468f06d6d4ae6f855e7f2b80e007a90bd11eeb421b5ed_

    General:
        * Fixes our Kinesis-compatibility with botocore>=1.29.31 - earlier Moto-versions will connect to AWS when using this botocore-version 

    New Methods:
        * Athena:
            * get_query_results()
            * list_query_executions()
        * RDS:
            * promote_read_replica()
        * Sagemaker:
            * create_pipeline()
            * delete_pipeline()
            * list_pipelines()

    Miscellaneous:
        * AWSLambda: publish_function() and update_function_code() now only increment the version if the source code has changed
        * CognitoIDP: Passwords are now validated using the PasswordPolicy (either supplied, or the default)
        * CloudFormation: create_stack() now propagates parameters StackPolicyBody and TimeoutInMinutes
        * CloudFormation: create_stack_instances() now returns the actual OperationId
        * CloudFormation: create_stack_set() now validates the provided name
        * CloudFormation: create_stack_set() now supports the DeploymentTargets-parameter
        * CloudFormation: create_stack_set() now actually creates the provided resources
        * CloudFormation: create_stack_set() now propagates parameters AdministrationRoleARN and ExecutionRoleName
        * CloudFormation: describe_stack_set() now returns the attributes Description, PermissionModel
        * CloudFormation: delete_stack_set() now validates that no instances are present before deleting the set
        * CloudWatch: get_metric_data() now supports the Label-parameter
        * EC2: allocate_address() now has improved behaviour for the Domain-parameter
        * EC2: create_volume() now supports the Iops-parameter
        * ECR: Improved ImageManifest support
        * KMS: describe_key() now returns an AccessDeniedException if the supplied policy does not allow this action
        * Route53: change_resource_record_sets() has additional validations
        * Route53: create_hosted_zone() now also creates a SOA-record by default
        * S3: put_object() now returns the ChecksumAlgorithm-attribute if supplied
        * SSM: describe_parameters() now has improved support for filtering by tags 


4.0.11
-----
Docker Digest for 4.0.11: _sha256:ba07f61edd4f91b221ea20368586dce024e7da4d018e2741aceafa1f07f47ec5_

    New Services:
        * ACM-PCA:
            * create_certificate_authority()
            * delete_certificate_authority()
            * describe_certificate_authority()
            * get_certificate()
            * get_certificate_authority_certificate()
            * get_certificate_authority_csr()
            * import_certificate_authority_certificate()
            * issue_certificate()
            * list_tags()
            * revoke_certificate()
            * tag_certificate_authority()
            * update_certificate_authority()
            * untag_certificate_authority()

    New Methods:
        * create_api_mapping()
        * create_domain_name()
        * delete_api_mapping()
        * delete_domain_name()
        * get_api_mapping()
        * get_api_mappings()
        * get_domain_name()
        * get_domain_names()

    Miscellaneous:
        * APIGateway: create_rest_api() now supports the propagation of parameter disableExecuteApiEndpoint (not the actual behaviour)
        * APIGateway: put_integration() now supports the parameters contentHandling, credentials, tlsConfig
        * AWSLambda: create_function() is now able to validate the existence of the provided ImageURI. Set environment variable MOTO_LAMBDA_STUB_ECR=false to enable this.
        * Batch: submit_job() now adds validation for the jobName parameter
        * CloudWatch: get_metric_data() now adds support for filtering by the unit-value
        * DynamoDB: transact_write_items() now supports up to 100 items instead of 25, in line with AWS
        * ELB: describe_instance_health() now validates the existence of the provided LoadBalancer
        * Polly: The list of available voices has been updated.
        * S3: put_object() now has improved support for filenames containing spaces
        * SQS: send_message() and send_message_batch() now adds validation for the DelaySeconds-parameter


4.0.10
-----
Docker Digest for 4.0.10: _sha256:faf0e4b591c47c7775da4f827c2ec2e1ff48a32b31169236fa604ffb95dafb78_

    New Methods:
        * CloudFront:
            * get_distribution_config()
        * Organizations:
            * delete_organizational_unit()

    Miscellaneous:
        * APIGateway: put_integration_response() now supports the responseParameters-parameter
        * Cloudformation now supports the creation/update/deletion of AWS::SSM::Parameter
        * Cloudformation: create_stack() now returns the attribute EnableTerminationProtection
        * CloudWatch: put_metric_data() now supports the MetricData.Values parameter
        * DynamoDB: transact_write_items() now supports the ReturnValuesOnConditionCheckFailure-parameter
        * RDS: describe_db_cluster now returns the EarliestRestorableTime-attribute
        * S3: get_object() and head_object() now correctly handle the IfModifiedSince-parameter

4.0.9
-----
Docker Digest for 4.0.9: _sha256:0c7a87255814035794733764d497fcb659ae0d6c843fae41040bb1a29c0726ab_

    Miscellaneous:
        * CloudTrail: describe_trails() now returns the correct (MultiRegion) trails
        * CloudWatch:tag_resource() now allows tagting new Alarms that didn't have tags yet
        * EC2: create_instances() now supports the `IamInstanceProfile`-parameter
        * EC2: describe_route_tables() now supports the `route.vpc-peering-connection-id`-filter
        * EC2: modify_vpc_attribute() now supports the enableNetworkAddressUsageMetrics-attribute
        * S3: delete_objects() now works against the JS SDK v3.197.0


4.0.8
-----
Docker Digest for 4.0.8: _sha256:41883fb0f38572f3194dcbef6731eafdc6d8d7d4e319257d2ba2468c401c9881_

    General:
        * Unpins the werkzeug-dependency - Moto now works with werkzeug==2.2.2
        * Fixes the Docker-build to run on M1 Macbooks.

    New Services:
        * ServiceQuotas:
            * get_service_quota()
            * list_aws_default_service_quotas()

    New Methods:
        * CloudFront: list_invalidations()
        * RDS: modify_db_cluster()

    Miscellaneous:
        * Lambda:delete_function() - fixed an issue where the wrong Function would be deleted when providing a qualifier
        * ECR:put_image() now removes any existing images that have the provided tag
        * IAM:detach_user/group/role_policy() now throws the correct error message when the policy is not attached in the first place 
        * S3:list_object_versions(): Fix delimiter to take prefix into account 
        * S3: Now closes file handles as early as possible when deleting files/multipart uploads
        * Sagamaker:describe_training_job() now throws the correct exception when trying to explain a non-existing job


4.0.7
-----
Docker Digest for 4.0.7: _sha256:a8ecbdba177c91c557ff76814c1b9a4d6673dc8e1e4183b183e5cff4ce73c356_

    New Services:
        * Comprehend:
            * create_entity_recognizer()
            * delete_entity_recognizer()
            * describe_entity_recognizer()
            * list_entity_recognizers()
            * list_tags_for_resource()
            * stop_training_entity_recognizer()

        * MeteringMarketplace:
            * batch_meter_usage()

    New Methods:
        * EC2:
            * modify_vpc_endpoint()
        * MediaConnect:
            * grant_flow_entitlements()
            * revoke_flow_entitlement()
            * update_flow_entitlement()
            * update_flow_output()

    Miscellaneous:
        * DynamoDB:transact_write_items() - Now includes validation if multipel operations are provided in the same item
        * EC2:cancel_spot_fleet_request() - Fixed a bug where instances were always terminated
        * EC2:create_instances() - Now uses the private IP address as as provided in the NetworkInterface
        * EC2:describe_instance_types() - Now supports all filters
        * ECS:run_task() - Now creates/attaches an ENI if appropriate
        * S3: Fixed an issue where file handles were not closed on large uploads

4.0.6
-----
Docker Digest for 4.0.6: _sha256:01582a705be7c50bc15993acc2271cd190db9c08c5fc09d85c59c8ddae6bb260_

    General:
        * Moto can now be seeded, which will make identifiers deterministic.
          See http://docs.getmoto.org/en/latest/docs/configuration/recorder/index.html
        * The format for access-key and role ids has been changed, and is now generated using the same algorithm that AWS uses

    Miscellaneous:
        * AWSLambda:add_permission() now properly handles the PrincipalOrgID-param
        * DynamoDB:update_item() now validates duplicate UpdateExpressions
        * EC2 now exposes instance types in the correct availability zones for us-west-1 (us-west-1a and us-west-1b)
        * EC2 has various improvements around the handling of RouteTableAssociations
        * Glue:get_tables() now supports the Expression-parameter
        * Organizations:create_organization() now uses a default value for FeatureSet=ALL
        * RDS:describe_db_subnet_groups() now returns the DBSubnetGroupArn-attribute
        * S3:upload_file() now supports the ExtraArgs: ChecksumAlgorithm-parameter
        * SSM:list_commands() now returns the DeliveryTimedOutCount-attribute


4.0.5
-----
Docker Digest for 4.0.5: _sha256:d18f760f3498b212b0c8c205c9c28c2b41e8c7a108f44e1bd1d7ee86dfc37c03_

    General:
        * Moto now has a Recorder, to easily record and replay a given set of requests.
          See http://docs.getmoto.org/en/latest/docs/configuration/recorder/index.html

    Miscellaneous:
        * CloudFormation now supports the creation/update/deletion of AWS::EC2::LaunchTemplate
        * Glue:start_job_run() now respects the MaxConcurrentRuns-parameter
        * S3:get_object() now performs rudimentary BucketPolicy validation
        * StateManager now supports `glue::job_run`, managing how long it takes to for a Glue job to become 'SUCCEEDED'


4.0.3
-----
Docker Digest for 4.0.3: <autopopulateddigest>

    General:
        * Compatible with openapi-spec-validator 0.5.x

    New Methods:
        * Kinesis:
            * update_stream_mode()
        * WAFv2:
            * associate_web_acl()
            * delete_web_acl()
            * disassociate_web_acl()
            * get_web_acl()
            * get_web_acl_for_resource()
            * list_rule_groups()
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()
            * update_web_acl()

    Miscellaneous:
        * DynamoDB:query() now has improved support for KeyConditionExpression
        * Kinesis:put_records() now validates the size/number of records, following AWS' behaviour


4.0.2
-----
Docker Digest for 4.0.2: _sha256:32b30fef5d54d30eb7beca263dcb0ba08bd3718adb8b5d95f9f4b6e9cfc854f1_

    New Services:
        * Amazon Managed Prometheus (AMP)
            * create_rule_groups_namespace()
            * create_workspace()
            * delete_rule_groups_namespace()
            * delete_workspace()
            * describe_rule_groups_namespace()
            * describe_workspace()
            * list_rule_groups_namespaces()
            * list_tags_for_resource()
            * list_workspaces()
            * put_rule_groups_namespace()
            * tag_resource()
            * untag_resource()
            * update_workspace_alias()

    Miscellaneous:
        * APIGateway:put_method() now supports the requestParameters-parameter
        * AutoScaling:create_auto_scaling_group() now supports the MixedInstancesPolicy-parameter
        * CloudWatchLogs:filter_log_events() now supports the filterPattern-parameter
        * DynamoDB:batch_put_item() now has validatior for empty keys
        * Kinesis:create_stream() now supports stream-mode=OnDemand
        * S3:head_object() now returns the PartsCount-header
        * SNS:subscribe() now has increased support for the FilterPolicy-argument
        * SSM now returns the /aws/service/ami-amazon-linux-latest-parameters as provided by AWS


4.0.1
-----
Docker Digest for 4.0.1: _sha256:effbe303d0ac958569537b725e7632354deb6e9ce0a78ced1a2c6bdd4123831d_

    New Services:
        * Personalize:
            * create_schema()
            * delete_schema()
            * describe_schema()
            * list_schemas()

        * Signer:
            * cancel_signing_profile()
            * get_signing_profile()
            * list_signing_platforms()
            * put_signing_profile()

    New Methods:
        * AWS Lambda:
            * create_function_url_config()
            * delete_function_url_config()
            * get_function_url_config()
            * update_function_url_config()

        * Glue:
            * update_database()

        * EC2:
            * describe_volumes_modifications()
            * modify_volume()

        * S3:
            * delete_bucket_ownership_rule()
            * get_bucket_ownership_rule()
            * put_bucket_ownership_rule()

    Miscellaneous:
        * CloudFormation: Fixed a bug where deletion of AWS::Route53::RecordSet would result in an error
        * DynamoDB: Fixed a bug where a TableARN would always return region=us-east-1
        * EC2:create_launch_template() now supports the TagSpecifications-parameter
        * EC2:describe_instance_types() now supports the Filters-parameter
        * EC2:run_instances() now supports the HibernationOptions-param

4.0.0
-----
Docker Digest for 4.0.0: _sha256:348b516e706e19544dec3643d25304e24b75e48c92b1a6d347e5cd8c349cd8cd_

    General:
        * Introduces MultiAccount support (see http://docs.getmoto.org/en/latest/docs/multi_account.html)
        * Removes deprecated decorators mock_dynamodb2 and mock_rds2
        * The API for the TreadedMotoServer is now considered stable

    Dependencies:
        * The responses-module now has a minimum version of 0.13.0


3.1.18
-----
Docker Digest for 3.1.18: _sha256:52fa7fdf8deee66d47fa760fafce1231ec9007d7bfc9c7a3080a8badd372b300_

    General:
        * Flask has now also been pinned to 2.1.x, as that is the latest release that works with werkzeug 2.1.x

    New Methods:
        * EC2:
            * create_fleet()
            * describe_fleets()
            * describe_fleet_instances()
            * delete_fleets()

        * SES:
            * describe_configuration_set()
            * send_bulk_templated_email()

    Miscellaneous:
        * EC2: describe_key_pairs() now returns the KeyPairId-attribute
        * EC2: import_key_pair() now returns the KeyPairId-attribute
        * EC2: describe_launch_templates() now behaves correctly when called with an unknown template name
        * RDS: create_db_instance() now returns the AvailabilityZone-attribute
        * RDS: describe_db_instances() now returns the AvailabilityZone-attribute


3.1.17
-----
Docker Digest for 3.1.17: _sha256:8a7e397a8856a5e63ad50689cdc3638831112768b193ea0fc308ac7dfdac57f0_

    General:
        * Werkzeug has been pinned to 2.1.x, as the latest 2.2.x releases cause some issues

    New Services:

        * CodeBuild:
            * batch_get_builds()
            * delete_project()
            * list_builds()
            * list_builds_for_project()
            * start_build()
            * stop_build()

        * Cost Explorer:
            * create_cost_category_definition()
            * delete_cost_category_definition()
            * describe_cost_category_definition()
            * update_cost_category_definition()

        * EMR Serverless:
            * create_application()
            * delete_application()
            * get_application()
            * list_applications()
            * start_application()
            * start_job_run()
            * stop_application()
            * update_application()

    New Methods:

        * Autoscaling:
            * delete_scheduled_action()
            * describe_scheduled_actions()
            * put_scheduled_update_group_action()

        * CloudFront:
            * create_distribution_with_tags()
            * create_invalidation()
            * list_tags_for_resource()

        * Glue:
            * create_schema()
            * delete_schema()
            * get_schema_by_definition()
            * get_schema_version()
            * put_schema_version_metadata()
            * register_schema_version()

        * Greengrass:
            * associate_role_to_group()
            * create_deployment()
            * disassociate_role_from_group()
            * get_associated_role()
            * get_deployment_status()
            * list_deployments()
            * reset_deployments()

        * IAM:
            * update_assume_role_policy()

        * IOT:
            * list_targets_for_policy()

        * KMS:
            * replicate_key()

        * MediaConnect:
            * add_flow_sources()
            * update_flow_source()

    Miscellaneous:
        * CloudFormation now supports the creation of AWS::AutoScaling::ScheduledAction
        * CognitoIDP now supports pagination for list_groups() and list_users_in_group()
        * EC2:describe_instances() now supports the filter 'key-name'
        * IAM:create_access_key() now limits the number of keys per user to 2

3.1.16
-----
Docker Digest for 3.1.16: _sha256:e7d79262fac1553966fb8c894dc81a750c4a18745977da6a15dffc35c596f8c4_

    New Methods:
        * Autoscaling:
            * enable_metrics_collection()

    Miscellaneous:
        * Fixes a dependency-error that popped up in 3.1.15.

3.1.15
-----
Docker Digest for 3.1.15: _sha256:fad9fc39322cbabf4440ac5f6a3a158ee759dcd963995fea9672136c50bd2fc3_

    Known bugs:
        * Some services will throw an error: Missing module 'openapi_spec_validator'. This is fixed in 3.1.16.

    New Methods:
        * Databrew:
            * create_profile_job()
            * create_recipe_job()
            * delete_job()
            * describe_job()
            * list_jobs()
            * update_profile_job()
            * update_recipe_job()
        * Glue:
            * create_registry()
        * Greengrass:
            * create_group()
            * create_group_version()
            * delete_group()
            * get_group()
            * get_group_version()
            * list_groups()
            * list_group_versions()
            * update_group()
        * KMS:
            * sign()
            * verify()
        * Route53Resolver:
            * associate_resolver_endpoint_ip_address()
            * disassociate_resolver_endpoint_ip_address()

3.1.14
-----
Docker Digest for 3.1.14: _sha256:a8ad7f54d7c469e34454f6774f743251c02093c6b2d7e9d7961a5de366783e11_

    New Methods:
        * Greengrass:
            * create_function_definition()
            * create_resource_definition()
            * create_function_definition_version()
            * create_resource_definition_version()
            * create_subscription_definition()
            * create_subscription_definition_version()
            * delete_function_definition()
            * delete_resource_definition()
            * delete_subscription_definition()
            * get_function_definition()
            * get_function_definition_version()
            * get_resource_definition()
            * get_resource_definition_version()
            * get_subscription_definition()
            * get_subscription_definition_version()
            * list_function_definitions()
            * list_function_definition_versions()
            * list_resource_definitions()
            * list_resource_definition_versions()
            * list_subscription_definitions()
            * list_subscription_definition_versions()
            * update_function_definition()
            * update_resource_definition()
            * update_subscription_definition()
        * EKS:
            * list_tags_for_resources()
            * tag_resource()
            * untag_resource()
        * Route53:
            * associate_vpc_with_hosted_zone()
            * disassociate_vpc_from_hosted_zone()
            * update_health_check()
            * update_hosted_zone_comment()

    Miscellaneous:
        * APIGateway:put_integration() now supports the requestParameters-parameter
        * EC2:create_route() now validates whether a route already exists


3.1.13
-----
Docker Digest for 3.1.13: _sha256:d7f6c779c79f03b686747ae26b52bdca26fd81a50c6a41a8a6cba50c96982abf_

    New Methods:
        * EC2:
            * create_default_vpc()

        * Greengrass:
            * create_device_definition()
            * create_device_definition_version()
            * delete_core_definition()
            * delete_device_definition()
            * get_core_definition()
            * get_core_definition_version()
            * get_device_definition()
            * get_device_definition_version()
            * list_core_definitions()
            * list_core_definition_versions()
            * list_device_definitions()
            * list_device_definition_versions()
            * update_core_definition()
            * update_device_definition()

        * SSO Admin:
            * create_permission_set()
            * delete_permission_set()
            * describe_permission_set()
            * list_permission_sets()
            * update_permission_set()

        * Route53:
            * get_dnssec()
            * get_health_check()

    * Miscellaneous:
        * StateManager now supports `s3::keyrestore`, managing how long it takes to restore S3 objects from Glacier.


3.1.12
-----
Docker Digest for 3.1.12: _sha256:64dcfb63b252b3413481683b90f105d01644b6bec150b60e6f612a2569ee630c_

    New Services:
        * Greengrass:
            * create_core_definition()
            * create_core_definition_version()

    Internal Changes:
        * The data structure containing all of Moto's state has been updated to support multiple accounts


3.1.11
-----
Docker Digest for 3.1.11: _sha256:bb359c5e57e38534eb8e934757354277fff30598ca305d0f18f68ddfe4ce6359_

    New Methods:
        * GuardDuty:
            * create_filter()
            * delete_detector()
            * delete_filter()
            * enable_organization_admin_account()
            * get_detector()
            * get_filter()
            * list_organization_admin_accounts()
            * update_detector()
            * update_filter()
        * KMS:
            * create_grant()
            * list_grants()
            * list_retirable_grants()
            * retire_grant()
            * revoke_grant()

    Miscellaneous:
        * EC2:describe_network_acls() now supports the `entry.egress`-filter
        * EC2:run_instances() now supports validation for the KeyPair-parameter. This is disabled by default - set MOTO_ENABLE_KEYPAIR_VALIDATION to true to enable this.
        * EC2:run_instances() now supports validation for the ImageId-parameter. This is disabled by default - set MOTO_ENABLE_AMI_VALIDATION to true to enable this.


3.1.10
-----
Docker Digest for 3.1.10: _sha256:18c6367dbb843850a5b52bc2b74cde9fd2a03719da667aa01b7c80de26849fb6_

    New Methods:
        * APIGateway:
            * import_rest_api()
            * put_rest_api()
        * Glue:
            * get_tags()
            * tag_resource()
            * untag_resource()

    Miscellaneous:
        * APIGateway:put_integration() now supports the passthroughBehavior-parameter
        * APIGatewayV2:create_authorizer() now supports the AuthorizerPayloadFormatVersion-parameter
        * AWSLamba:publish_layer_version() now supports the CompatibleArchitectures-parameter
        * DAX:create_cluster() now supports the ClusterEndpointEncryptionType-parameter
        * EC2:describe_route_tables() now supports the filter `route.gateway-id`
        * EC2:run_instances() now validates whether the Placement-parameter has a valid availability zone
        * ECS:list_services() now supports the launchType-parameter
        * ELB:describe_instance_health() now returns the OutOfService-status when appropriate
        * Organizations:list_accounts_for_parent() now supports pagination
        * Organizations:list_organizational_units_for_parent() now supports pagination


3.1.9
-----
Docker Digest for 3.1.9: _sha256:eea31d2f99b2fef16cffb3ea86d21dd911647835a3182bedd8918074292ce552_

    New Services:
        * EBS:
            * complete_snapshot()
            * get_snapshot_block()
            * list_changed_blocks()
            * list_snapshot_blocks()
            * put_snapshot_block()
            * start_snapshot()

    New Methods:
        * CloudFront:
            * update_distribution()
        * Datasets:
            * create_dataset()
            * delete_dataset()
            * describe_dataset()
            * list_datasets()
            * update_dataset()
        * Glue:
            * list_crawlers()
        * Rekognition:
            * get_face_search()
            * start_face_seach()

    Miscellaneous:
        * EC2:describe_vpc_endpoints() now supports the `vpc-endpoint-type`-filter
        * RDS:create_db_cluster() now supports the EnableCloudwatchLogsExports-parameter
        * RDS:create_db_instance() now supports the EnableCloudwatchLogsExports-parameter
        * SSM now integrates with SecretsManager

3.1.8
-----
Docker Digest for 3.1.8: _sha256:a7d8c55eec8d75d75dd2532a6a0a9647935238236a54e4de7bb3f72bc28b7bf8_

    General:
        * Moto now supports a way to delay state transitions. 
          See http://docs.getmoto.org/en/latest/docs/configuration/state_transition/index.html
        * Moto now supports `@mock_batch_simple`, a way to mock the Batch-service without invoking Docker.

    New Methods:
        * CognitoIDP:
            * global_sign_out()
            * update_group()
            * update_user_attributes()
        * DataBrew:
            * delete_recipe_version()
            * list_recipe_versions()
            * publish_recipe()
        * IAM:
            * create_service_linked_role()
            * delete_service_linked_role()
            * get_service_linked_role_deletion_status()
        * Sagemaker:
            * update_endpoint_weights_and_capacities()

    Miscellaneous:
        * EC2: request_spot_fleet() now supports the parameters LaunchTemplateConfigs, InstanceInterruptionBehavior
        * EC2: request_spot_instances() now supports the InstanceInterruptionBehavior-parameter
        * EC2: The status of a SpotInstances request now automatically transitions to 'Active/Fulfilled'
        * EC2: Tags specified into create_launch_template() are now passed through when calling `run_instances()` with this template
        * RDS: describe_db_instances() now supports the filter `db-cluster-id`
        * TimestreamWrite: create_table() now supports the MagneticStoreWriteProps-parameter
        * TimestreamWrite: update_table() now supports the MagneticStoreWriteProps-parameter 


3.1.7
-----
Docker Digest for 3.1.7: _sha256:d9661c13c2f790cbe9ed6531cefec132494fc0e8c37fcceca1f709292ef0880f_

    New Methods:
        * SES:
            * get_identity_verification_attributes()

    Miscellaneous:
        * CognitoIDP: UserPools now come with default values for the following attributes: Policies, AdminCreateUserConfig, EmailConfiguration, VerificationMessageTemplate
        * ELBv2: Improved the response-format of the `create_rule()` and `set_rule_priorities()`-methods
        * MediaConnect: Now has the correct format for flow/source ARN's
        * Organizations: Fixes the behaviour for close_account()
        * Sagemaker: Now supports tagging of Models, EndpointConfigs, ProcessingJobs


3.1.6
-----
Docker Digest for 3.1.6: _sha256:722b9c05ad3454047688db4ba95991f6af4166c63d871149b1b1eef9d70be70f_

    New Methods:
        * Organizations:
            * close_account()

    Miscellaneous:
        * Autoscaling: the BlockDeviceMappings in LaunchConfigurations and LaunchTemplates are now respected when launching EC2 instances
        * CloudWatch: get_metric_data() now supports the Dimensions-parameter
        * ELB: set_rule_priorities() now correctly returns the Rules-attribute
        * ELBv2: create_target_group() now supports the Tags-parameter
        * Events: delete_rule() now verifies whether any targets are still attached before deletion


3.1.5
-----
Docker Digest for 3.1.5: _sha256:79050ce5b729f6eff3282a79dace9cb7e5983588250452f8821aeffa87eca334_

    New Methods:
        * ApplicationAutoscaling:
            * delete_scheduled_action()
            * describe_scheduled_actions()
            * put_scheduled_action()

        * Databrew:
            * create_ruleset()
            * delete_ruleset()
            * list_rulesets()
            * update_recipe()
            * update_ruleset()

        * EC2:
            * describe_network_interface_attribute()

    Miscellaneous:
        * Glue:get_partitions() now supports the Expression-parameter
        * RDS:delete_db_cluster() now supports the FinalDBSnapshotIdentifier-parameter
        * S3 actions can now send notifications for (a subset of) supported events and targets

3.1.4
-----
Docker Digest for 3.1.4: _sha256:795eb8a1d966ef30c53f504e358afb23ec262e5ad1cba18d474096c0fba794bd_

    General:
        * Compatible with botocore 1.24.30.
          The IOTData service in older versions of Moto is incompatible with botocore >= 1.24.30, due to the fact that AWS changed their URL endpoints. 

    New Services:
        * QuickSight:
            * create_data_set()
            * create_group()
            * create_group_membership()
            * create_ingestion()
            * delete_group()
            * delete_user()
            * describe_group()
            * describe_group_membership()
            * describe_user()
            * list_groups()
            * list_group_memberships()
            * list_users()
            * register_user()
            * update_group()
            * describe_group()
            * describe_group()
            * describe_group()

        * Rekognition:
            * get_text_detection()
            * start_text_detection()

    New Methods:
        * EC2:
            * delete_launch_template()

        * ECS:
            * create_capacity_provider()
            * delete_capacity_provider()
            * describe_capacity_providers()

    Miscellaneous:
        * Autoscaling:put_scaling_policy() now supports the parameters MetricAggregationType, MinAdjustmentMagnitude, EstimatedInstanceWarmup, PredictiveScalingConfiguration
        * Autoscaling:create_auto_scaling_group() now supports launch template versions '$Latest' and '$Default'
        * RDS: Improved tagging support for Clusters and ClusterSnapshots


3.1.3
-----
Docker Digest for 3.1.3: _sha256:d0716d84d376e7aafeb4a40a29d298725aa39e6553b64f55a6be1287e4bee80c_

    New Methods:
        * TimestreamWrite:
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()

    Miscellaneous:
        * EC2:run_instances(): Fixed a bug when supplying the NetworkInterfaces.Groups-parameter
        * Logs:delete_metric_filter(): Fixed a bug where the logGroupName-validator was too strict


3.1.2
-----
Docker Digest for 3.1.2: _sha256:884923ae6449b2db64e6805ef82209fcc5aab4991024c495aea07a191257aa4d_

    Known Bugs:
        * EC2:run_instances(): This call will fail when supplying the NetworkInterfaces.Groups-parameter 

    New Methods:
        * ELB
            * attach_load_balancer_to_subnets()
            * detach_load_balancer_from_subnets()
            * describe_load_balancer_policies()
            * delete_load_balancer_policy()
            * enable_availability_zones_for_load_balancer()
            * disable_availability_zones_for_load_balancer()

        * ELBv2:
            * add_listener_certificates()
            * describe_listener_certificates()
            * remove_listener_certificates()

        * Glue:
            * get_job()
            * get_job_run()
            * start_job_run()

    Miscellaneous:
        * AWSLambda:add_permission() now supports the Qualifier-parameter
        * ELB:create_load_balancer() now retrieves the subnets based on the AvailabilityZones-parameter
        * ELB:create_load_balancer() now creates a default SecurityGroup, if none is provided
        * ELBv2:create_load_balancer() now supports the SubnetMappings-parameter
        * ELBv2:create_listener() now supports the AlpnPolicy-parameter
        * ELBv2: Improved tagging support
        * ELBv2: Exposes the TargetGroupStickinessConfig-attribute when describing a Action of type ForwardConfig


3.1.1
-----
Docker Digest for 3.1.1: _sha256:e2b8145574e01d1630be307f418211e09e089b87d8d87b1ac69878a50d8dde0c_

    New Methods:
        * AWSLambda:
            * create_alias()
            * delete_alias()
            * delete_layer_version()
            * get_alias()
            * get_layer_version()
            * update_alias()

        * EFS:
            * create_access_point()
            * delete_access_point()
            * describe_access_points()
            * describe_lifecycle_configuration()
            * describe_mount_target_security_groups()
            * list_tags_for_resource()
            * modify_mount_target_security_groups()
            * put_lifecycle_configuration()
            * tag_resource()
            * untag_resource()

    Miscellaneous:
        * AWSLambda: get_function now returns the parameters Tags, LastUpdateStatus, TracingConfig
        * ELBV2:describe_tags() now supports ListenerRules.


3.1.0
-----
Docker Digest for 3.1.0: _sha256:1656754cf4de441d85b08f584d9dcb095880d3bf250f05da26a03ff219d586c8_

    General:
        * Users of `mock_dynamodb2` should start using `mock_dynamodb` instead. 
          The `mock_dynamodb`-decorator has been repurposed to mock the latest version of DynamoDB, making the behaviour equivalent to `mock_dynamodb2`. 
          The `mock_dynamodb2`-decorator is now considered deprecated, and will be removed in the next major version.

        * Similarly, users of the `mock_rds2` should start using `mock_rds` instead.
          The `mock_rds`-decorator has been repurposed to mock the latest version of RDS, making the behaviour equivalent to `mock_rds2`.
          The `mock_rds2`-decorator has also been deprecated, and will be removed in the next major version.

    Internal Changes:
        * We've upgraded our linting process to use Black 22.1.0, and have enabled more pylint rules.
          Please continue to run `make lint` prior to creating a PR, to ensure any changes are formatted correctly. 

3.0.7
-----
Docker Digest for 3.0.7: _sha256:4db9433e741de635606fd2d997e555c26f51fc82e69d5043d0d9de90bbade229_

    General:
        * Compatible with the latest `responses`-release (0.19.0)

    New Services:
        * DataBrew:
            * create_recipe()
            * get_recipe()
            * list_recipes()

        * Pinpoint:
            * create_app()
            * delete_app()
            * delete_event_stream()
            * get_app()
            * get_application_settings()
            * get_apps()
            * get_event_stream()
            * list_tags_for_resource()
            * put_event_stream()
            * tag_resource()
            * untag_resource()
            * update_application_settings()

3.0.6
-----
Docker Digest for 3.0.6: _sha256:de6b4ba576e143b3bbae250186b563c836f233afea5b3579629d3565824de74d_

    General:
        * Feature to start the MotoServer from within Python (in beta)

    Miscellaneous:
        * CloudFormation now supports creation of type AWS::EC2::VPCEndpoint
        * ECS: run_task() - The task count now defaults to 1

3.0.5
-----
Docker Digest for 3.0.5: _sha256:914ba446c1aad3917029fefe5d1c4a7a6a3866173391fb470151fe4a2163efcb_

    New Services:
        * Textract:
            * get_document_text_detection()
            * start_document_text_detection()

    New Methods:
        * APIGateway:
            * delete_gateway_responses()
            * get_gateway_response()
            * get_gateway_responses()
            * put_gateway_response()
        * CloudTrail:
            * add_tags()
            * get_event_selectors()
            * get_insight_selectors()
            * list_tags()
            * put_event_selectors()
            * put_insight_selectors()
            * remove_tags()
            * update_trail()
        * CognitoIDP:
            * admin_set_user_mfa_preference()
        * S3Control:
            * create_access_point()
            * delete_access_point()
            * delete_access_point_policy()
            * get_access_point()
            * get_access_point_policy()
            * get_access_point_policy_status()

    Miscellaneous:
        * APIGateway: put_integration() now supports the timeoutInMillis-parameter
        * AWSLambda: Made the docker image repository selectable via the `MOTO_DOCKER_LAMBDA_IMAGE` environment variable.
        * Batch: register_job_definition() now supports the parameters `platformCapabilities`, `propagateTags` and `retryStrategy`
        * IAM: list_entities_for_policy() now returns the RoleId/GroupId/UserId-attributes
        * S3Control is now available in ServerMode.

3.0.4
-----
Docker Digest for 3.0.4: _sha256:320e1d2ab89729d5580dbe08d8c2153a28db4c28023c57747fb292ffceee84b6_

    New Services:
        * Redshift-Data:
            * cancel_statement()
            * describe_statement()
            * execute_statement()
            * get_statement_result()
        * Servicediscovery/Cloudmap:
            * create_http_namespace()
            * create_private_dns_namespace()
            * create_public_dns_namespace()
            * create_service()
            * delete_namespace()
            * delete_service()
            * get_namespace()
            * get_operation()
            * get_service()
            * list_namespaces()
            * list_operations()
            * list_services()
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()
            * update_service()

    New Methods:
        * Athena:
            * create_data_catalog()
            * get_data_catalog()
            * list_data_catalogs()
        * SES:
            * get_identity_mail_from_domain_attributes()
            * set_identity_mail_from_domain()

    Miscellaneous:
        * SSM: Global infrastructure parameters supplied by AWS are now available in Moto

3.0.3
-----

    * New Services:
        * APIGatewayV2
            * create_api()
            * create_authorizer()
            * create_integration()
            * create_integration_response()
            * create_model()
            * create_route()
            * create_route_response()
            * create_vpc_link()
            * delete_api()
            * delete_authorizer()
            * delete_cors_configuration()
            * delete_integration()
            * delete_integration_response()
            * delete_model()
            * delete_route()
            * delete_route_request_parameter()
            * delete_route_response()
            * delete_vpc_link()
            * get_api()
            * get_apis()
            * get_authorizer()
            * get_integration()
            * get_integration_response()
            * get_integration_responses()
            * get_integrations()
            * get_model()
            * get_route()
            * get_route_response()
            * get_routes()
            * get_tags()
            * get_vpc_link()
            * get_vpc_links()
            * reimport_api()
            * tag_resource()
            * untag_resource()
            * update_api()
            * update_authorizer()
            * update_integration()
            * update_integration_response()
            * update_model()
            * update_route()
            * update_vpc_link()

    * New Methods:
        * APIGateway:
            * create_vpc_link()
            * delete_vpc_link()
            * get_vpc_link()
            * get_vpc_links()
        EC2:
            * create_vpc_endpoint_service_configuration()
            * delete_vpc_endpoint_service_configurations()
            * describe_vpc_endpoint_service_configurations()
            * describe_vpc_endpoint_service_permissions()
            * modify_vpc_endpoint_service_configuration()
            * modify_vpc_endpoint_service_permissions()
        * Route53:
            * create_reusable_delegation_set()
            * delete_reusable_delegation_set()
            * get_hosted_zone_count()
            * get_reusable_delegation_set()
            * list_reusable_delegation_sets()

    * Miscellaneous:
        * CognitoIDP:
            * initiate_auth()/admin_initiate_auth(): improved behaviour of the AuthFlow-parameter
        * EC2:
            * describe_instance_types() now returns the GpuInfo-attribute
        * Redshift:
            * describe_cluster_snapshots() now supports the SnapshotType-parameter

3.0.2
-----

    * New Methods:
        * Kinesis:
            * deregister_stream_consumer()
            * describe_stream_consumer()
            * disable_enhanced_monitoring()
            * enable_enhanced_monitoring()
            * list_stream_consumers()
            * register_stream_consumer()
            * start_stream_encryption()
            * stop_stream_encryption()
            * update_shard_count()
        * RDS:
            * cancel_export_task()
            * copy_db_cluster_snapshot()
            * copy_db_snapshot()
            * create_db_cluster_snapshot()
            * create_event_subscription()
            * delete_db_cluster_snapshot()
            * delete_event_subscription()
            * describe_db_cluster_snapshots()
            * describe_event_subscriptions()
            * describe_export_tasks()
            * start_export_task()
        * Route53
            * list_hosted_zones_by_vpc()

    * Miscellaneous:
        * Improved configuration options for Docker-instances started by AWSLambda and Batch

3.0.1
-----

    * New Services:
        * MQ:
            * create_broker()
            * create_configuration()
            * create_tags()
            * create_user()
            * delete_broker()
            * delete_tags()
            * delete_user()
            * describe_broker()
            * describe_configuration()
            * describe_configuration_revision()
            * describe_user()
            * list_brokers()
            * list_configurations()
            * list_tags()
            * list_users()
            * reboot_broker()
            * update_broker()
            * update_configuration()
            * update_user()

    * New Methods:
        * EC2:
            * create_snapshots()
        * Logs:
            * create_export_task()
        * Organizations:
            * remove_account_from_organization()

    * Miscellaneous:
        * DynamoDB: transact_write_items() now throws a MultipleTransactionsException when appropriate
        * DynamoDB: Now throws the appropriate InvalidConditionExpression when a ConditionExpression contains reserved keywords
        * Organizations: delete_organization() now validates whether all accounts are deleted
        * SecretsManager: The attributes CreatedDate and LastChangedDate are now returned for secrets
        * SNS: Simplistic email validation is now in place before sending emails

3.0.0
-----
    This is a major release, and as such contains some breaking changes.

    * Removed:
        - All deprecated decorators have been removed

    * Changes:
        - The behaviour of the class-decorator has been reworked - the state is now reset before every test-method.
        - ECS ARN's are now using the long format.

    * Rebranded:
        - The new mock_s3control-decorator has been introduced. The existing S3control methods (get/put/delete_public_access_block) are no longer available via mock_s3, only via mock_s3control.

    * General:
        - Python 3.5 support has been removed
        - Python 3.10 is now supported


2.3.2
-----
    General:
        * Compatible with the latest `responses`-release (0.17.0)

    New Services:
        * Appsync:
            * create_api_key()
            * create_graphql_api()
            * delete_api_key()
            * delete_graphql_api()
            * get_graphql_api()
            * get_schema_creation_status()
            * get_type()
            * list_api_keys()
            * list_graphql_apis()
            * list_tags_for_resource()
            * start_schema_creation()
            * tag_resource()
            * untag_resource()
            * update_api_key()
            * update_graphql_api()

    Miscellaneous:
        * AWSLambda:invoke() now throws an error when trying to return an oversized payload (>6MB)
        * EC2:describe_instances() now supports filtering by `dns-name`
        * EC2:describe_managed_prefix_lists() now supports filtering by tags
        * SQS:delete_message_batch() now correctly deals with invalid receipt handles

2.3.1
-----
    New Services:
        * DAX:
            * create_cluster()
            * decrease_replication_factor()
            * delete_cluster()
            * describe_clusters()
            * increase_replication_factor()
            * list_tags()
        * SSO-Admin:
            * create_account_assignment()
            * delete_account_assignment()
            * list_account_assignments()

    New Methods:
        * APIGateway:
            * update_base_path_mapping()
        * SNS:
            * publish_batch()

    Miscellaneous:
        * ECS: run_task() now supports the launchType-parameter
        * SNS: publish() now supports FIFO-topics
        * SWF: respond_decision_task_completed() now supports RecordMarker/StartTimer/CancelTimer/CancelWorkflowExecution decisions

2.3.0
-----
    General:
        * It is now possible to use a mocked region. This will throw an error by default, but can be enabled using the `MOTO_ALLOW_NONEXISTENT_REGION`-environment variable.
        * Performance improvements - only the backend for the requested region is now loaded into memory, instead of (naively) loading a backend for every region.

2.2.20
-----
    New Services:
        * ElasticsearchService:
            * create_elasticsearch_domain()
            * delete_elasticsearch_domain()
            * describe_elasticsearch_domain()
            * list_domain_names()

    New Methods:
        * EC2:
            * disable_ebs_encryption_by_default()
            * enable_ebs_encryption_by_default()
            * get_ebs_encryption_by_default()
        * Redshift:
            * pause_cluster()
            * resume_cluster()

    Miscellaneous:
        * ELBv2: create_listener now supports the DefaultActions.ForwardConfig parameter
        * Redshift: restore_from_cluster_snapshot() now supports the NodeType and NumberOfNodes-parameters
        * Sagemaker: list_experiments() now supports pagination
        * Sagemaker: list_trials() now supports pagination
        * Sagemaker: list_trial_components() now supports pagination


2.2.19
-----
    General:
        * Support for ap-southeast-3


2.2.18
------
    New Services:
        * ElastiCache:
            * create_user()
            * delete_user()
            * describe_users()
        * GuardDuty:
            * create_detector()
            * list_detectors()

    New Methods:
        * IAM:
            * list_open_id_connect_provider_tags()
            * tag_open_id_connect_provider()
            * untag_open_id_connect_provider()
            * update_open_id_connect_provider_thumbprint()
        * IOT:
            * create_domain_configuration()
            * delete_domain_configuration()
            * describe_domain_configuration()
            * list_domain_configurations()
            * update_domain_configuration()

    Miscellaneous:
        * ResourceGroupTaggingAPI now supports Lambda Functions
        * SecretsManager:list_secrets() now supports negative filters

2.2.17
------
    New Services:
        * CloudFront:
            * create_distribution()
            * delete_distribution()
            * get_distribution()
            * list_distributions()

    New Methods:
        * Autoscaling:
            * describe_tags()
        * CloudFormation:
            * get_stack_policy()
            * set_stack_policy()
        * DynamoDB:
            * restore_table_to_point_in_time()
        * Glue:
            * delete_database()
            * list_jobs()
        * IAM:
            * update_group()
        * Route53 Resolver:
            * associate_resolver_rule()
            * create_resolver_rule()
            * delete_resolver_rule()
            * disassociate_resolver_rule()
            * get_resolver_rule()
            * get_resolver_rule_association()
            * list_resolver_rules()
            * list_resolver_rule_associations()

    Miscellaneous:
        * Batch: register_job_definition() now supports the timeout-parameter
        * Batch: submit_job() now supports the timeout-parameter
        * EC2: describe_network_interfaces() now supports the `attachment.instance-id` filter


2.2.16
------
    New Services:
        * SimpleDB:
            * create_domain()
            * delete_domain()
            * get_attributes()
            * list_domains()
            * put_attributes()

    New Methods:
        * Glue:
            * create_job
        * Route53 Resolver:
            * create_resolver_endpoint()
            * delete_resolver_endpoint()
            * get_resolver_endpoint()
            * list_resolver_endpoints()
            * list_resolver_endpoint_ip_addresses()
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()
            * update_resolver_endpoint()

    Miscellaneous:
        * Moto now supports mocking S3-equivalent libraries such as Ceph
        * Cognito IDP now exposes the `cognito:groups`-attribute as part of the AccessToken

2.2.15
------
    General:
        * Fixed the dependency bug - `moto install[all]` now installs all required dependencies again.

2.2.14
------
    Known bugs:
        * Running `pip install moto[all]` will not install all required dependencies.

    General:
        * Improved documentation for both users and contributors:
          http://docs.getmoto.org/en/latest/
        * The `@mock_all`-decorator is now available to mock all services at the same time
        * The `moto.core.patch_client`/`moto.core.patch_resource`-methods are now available to patch boto3-clients and -resources instantiated after the mock was started.
          This provides a workaround when encountering InvalidAccessKeyId-errors.

    New Methods:
        * APIGateway:
            * delete_base_path_mapping()
        * EC2:
            * assign_ipv6_addresses()
            * assign_private_ip_addresses()
            * unassign_ipv6_addresses()
            * unassign_private_ip_addresses()
        * SSM:
            * create_maintenance_window()
            * delete_maintenance_window()
            * get_maintenance_window()

    Miscellaneous:
        * CloudFormation no longer throws errors when trying to update unsupported resources.
        * CloudTrail:get_trail_status() now also supports ARN's as a parameter
        * CognitoIDP:list_users() now supports the AttributesToGet-parameter
        * IOT:attach_policy() now supports Cognito IdentityPools as a target
        * IOT:list_job_executions_for_thing() now supports pagination
        * Kinesis:split_shards() now behaves more like AWS, by closing the original shard and creating two new ones
        * Logs:put_log_events() now enforces timestamp-validation
        * S3:create_multipart_upload() now supports the Tagging-parameter
        * SSM:get_parameters_by_path() now support filtering by label

2.2.13
-----
    General:
        * The mock_dynamodb and mock_rds-decorators have been deprecated, and will be repurposed in a later release.
          Please see https://github.com/getmoto/moto/issues/4526 for more information.

    New Methods:
        * API Gateway:
            * get_base_path_mappings()
        * Cognito Identity:
            * list_identities()
        * DirectoryService:
            * disable_sso()
            * enable_sso()
            * connect_directory()
            * create_alias()
            * create_microsoft_ad()
        * EMR Containers:
            * cancel_job_run()
            * describe_job_run()
            * list_job_runs()
            * start_job_run()
        * IAM:
            * list_policy_tags()
            * tag_policy()
            * untag_policy()
        * Sagemaker:
            * create_processing_job()
            * describe_processing_job()
            * list_processing_jobs()

    Miscellaneous:
        * CloudFormation: Now supports creation of Custom:: resources. Note that this only works in ServerMode.

2.2.12
-----
    New Services:
        * EMR Containers:
            * create_virtual_cluster()
            * delete_virtual_cluster()
            * describe_virtual_cluster()
            * list_virtual_clusters()
        * DirectoryService:
            * add_tags_to_resource()
            * create_directory()
            * delete_directory()
            * describe_directories()
            * get_directory_limits()
            * list_tags_for_resource()
            * remove_tags_for_resource()

    New Methods:
        * API Gateway:
            * create_base_path_mapping()
            * get_base_path_mappings()
        * CognitoIDP:
            * add_custom_attributes()
            * admin_delete_user_attributes()
        * Glue:
            * start_crawler()
            * stop_crawler()
        * Sagemaker:
            * add_tags()
            * associate_trial_component()
            * create_experiment()
            * create_trial()
            * create_trial_component()
            * delete_experiment()
            * delete_tags()
            * delete_trial()
            * delete_trial_component()
            * describe_experiment()
            * describe_trial()
            * describe_trial_component()
            * disassociate_trial_component()
            * list_associations()
            * list_experiments()
            * list_trial_components()
            * list_trials()
            * search()
        * SES:
            * describe_receipt_rule_set()
            * update_receipt_rule()

    Miscellaneous:
        * KMS: Now returns default AWS aliases (alias/aws/s3, etc)

2.2.11
-----
    General:
        * Support for AWS China regions
        * ECS now has an option to enable long-format ARNs, by setting the environment variable MOTO_ECS_NEW_ARN=true
          Alternatively, use the `put_account_setting` to enable long-format for the current user.

    New Services:
        * Timestream:
            * create_database()
            * create_table()
            * delete_database()
            * delete_table()
            * describe_database()
            * describe_endpoints()
            * describe_table()
            * list_databases()
            * list_tables()
            * update_database()
            * update_table()
            * write_records()

    New Methods:
        * CognitoIDP:
            * admin_confirm_sign_up()
            * update_user_pool()
        * ECS:
            * delete_account_setting()
            * list_account_settings()
            * put_account_setting()
        * Route53:
            * create_query_logging_config()
            * delete_query_logging_config()
            * get_query_logging_config()
            * list_query_logging_config()
        * SES
            * describe_receipt_rule()
            * get_identity_notification_attributes()
            * set_identity_feedback_forwarding_enabled()

    Miscellaneous:
        * CloudFormation: Support create/update/delete of resource AWS::Logs::ResourcePolicy
        * CloudFormation:get_template_summary() now returns the Parameters-attribute
        * CognitoIDP: Allow the UserAttributes email or phone_number to be used as username
        * CognitoIDP: Improved behaviour for the ForgotPassword()-feature 


2.2.10
------
    New Services:
        * CloudTrail:
            * create_trail()
            * delete_trail()
            * describe_trails()
            * get_trail()
            * get_trail_status()
            * list_trails()
            * start_logging()
            * stop_logging()

    New Methods:
        * CognitoIDP:
            * admin_reset_user_password()
        * S3:
            * delete_bucket_replication()
            * get_bucket_replication()
            * put_bucket_replication()

    Miscellaneous:
        * ACM: describe_certificate(): the InUseBy-attribute will now show the appropriate Elastic Load Balancers 
        * AWSLambda: If you're running Linux, 'host.docker.internal' is now added as an extra host in the Docker container used to invoke the function.
                     This makes it easier for Lambda-functions to communicate with other servers running on the host-system.
        * CloudFormation: Now supports update/deletion of type AWS::SNS::Topic
        * CognitoIdentityProvider: list_users() now has improved support for the Filter-parameter
        * Kinesis: describe_stream() now supports the Filter-parameter
        * S3: list_object_versions() now supports the Delimiter and KeyMarker-parameter

2.2.9
-----
    General:
        * Moto is now compatible with Sure 2.x

    New Methods:
        * Kinesis:
            * list_shards()
        * RDS:
            * create_db_cluster()
            * delete_db_cluster()
            * describe_db_clusters()
            * restore_db_instance_from_db_snapshot()
            * start_db_cluster()
            * stop_db_cluster()
        * S3:
            * get_object_legal_hold()

    Miscellaneous:
        * CF: Now supports creation of AWS::EC2::VPNGateway
        * CF: Now supports deletion of AWS::Events::Rule
        * EC2: create_volume() now supports the VolumeType-parameter
        * EC2: describe_customer_gateways() now supports the CustomerGatewayIds-parameter
        * EC2: describe_security_groups() now has improved support for the Filters-parameter
        * EC2: describe_spot_instance_requests() now supports the SpotInstanceRequestIds-parameter
        * EC2: describe_transit_gateways() now supports the TransitGatewayIds-parameter

2.2.8
-----
    New Services:
        * ACM:
            * export_certificate()
        * APIGateway:
            * create_request_validator()
            * delete_request_validator()
            * get_request_validators()
            * update_request_validator()

    Miscellaneous:
        * APIGateway: update_rest_api() now has improved support for the patchOperations-parameter
        * Batch: register_job_definition() now supports the tags-parameter
        * CloudFormation: Stack Events are now propagated to SNS when the NotificationARNs-parameter is supplied.
        * EC2: describe_vpc_endpoint_services() now returns the default endpoints for implemented services 
        * IOT: list_job_executions_for_job() now supports the status-parameter
        * IOT: list_job_executions_for_thing() now supports the status-parameter
        * KMS: list_resource_tags() now supports an ARN as the KeyId-parameter
        * KMS: tag_resource() now supports an ARN as the KeyId-parameter
        * KMS: untag_resource() now supports an ARN as the KeyId-parameter
        * SecretsManager: update_secret() now supports the ClientRequestToken-parameter

2.2.7
-----
    General:
        * Performance improvements when using Moto in Server Mode.
          Only services that are actually used will now be loaded into memory, greatly reducing the waiting times when starting the server, making an initial request and calling the reset-api.

    New Services:
        * Firehose
            * create_delivery_stream()
            * delete_delivery_stream()
            * describe_delivery_stream()
            * list_delivery_streams()
            * list_tags_for_delivery_stream()
            * put_record()
            * put_record_batch()
            * tag_delivery_stream()
            * untag_delivery_stream()
            * update_destination()

    New Methods:
        * Autoscaling:
            * delete_lifecycle_hook()
            * describe_lifecycle_hooks()
            * put_lifecycle_hook()
        * EC2:
            * associate_subnet_cidr_block()
            * create_carrier_gateway()
            * delete_carrier_gateway()
            * describe_carrier_gateways()
            * describe_spot_price_history()
            * disassociate_subnet_cidr_block()
            * update_security_group_rule_descriptions_egress()
            * update_security_group_rule_descriptions_ingress()
        * Logs:
            * delete_metric_filter()
            * describe_metric_filters()
            * put_metric_filter()
        * SageMaker:
            * list_training_jobs()
        * Transcribe
            * create_vocabulary()
            * delete_transcription_job()
            * delete_vocabulary()
            * get_transcription_job()
            * get_vocabulary()
            * list_transcription_jobs()
            * start_transcription_job()

    Miscellaneous:
        * DynamoDB: Improved support for the ReturnConsumedCapacity-parameter across all methods
        * EC2:create_route() now supports the parameters CarrierGatewayId, DestinationPrefixListId
        * EC2:create_subnet() now supports the Ipv6CidrBlock-parameter
        * EC2:describe_nat_gateways() now supports the NatGatewayIds-parameter
        * EC2:describe_vpn_gateways() now supports the VpnGatewayIds-parameter
        * EC2:modify_network_interface_attribute() now supports the SourceDestCheck-parameter
        * EC2:replace_route() now supports the parameters DestinationIpv6CidrBlock, DestinationPrefixListId, NatGatewayId, EgressOnlyInternetGatewayId, TransitGatewayId
        * EC2:run_instances() now supports the InstanceMarketOptions.MarketType-parameter
        * Logs:put_log_events() now supports Firehose as a destination
        * Logs:put_subscription_filter() now supports Firehose as a destination
        * S3:create_bucket(): Improved error handling for duplicate buckets
        * S3:head_object() now validates incoming calls when using the `set_initial_no_auth_action_count`-decorator
        * SSM:put_parameter() now supports the DataType-parameter

2.2.6
-----
    General:
        * `pip install` will no longer log a warning when installing a service that does not have any dependencies
          Example: `pip install moto[acm]`

    New Services:
        ElasticTranscoder:
            * create_pipeline
            * delete_pipeline
            * list_pipelines
            * read_pipeline
            * update_pipeline

    New Methods:
        * DynamoDB:
            * describe_endpoints()

    Miscellaneous:
        * AWSLambda now sends logs to CloudWatch when Docker encounters an error, to make debugging easier
        * AWSLambda: For all methods, the FunctionName-parameter can be either the Lambda name or the Lambda ARN
        * AWSLambda:list_functions() now returns only the latest version by default
        * AWSLambda:invoke() now returns the correct Payload for invocations that resulted in an error
        * CloudFormation now supports the creation of type AWS::IAM::ManagedPolicy
        * CloudFormation now supports the deletion of type AWS::IAM::InstanceProfile
        * CloudFormation now supports the deletion of type AWS::IAM::Role
        * CloudWatch:create_log_group() now has proper validation for the length of the logGroupName-parameter
        * CloudWatch:describe_log_groups() now has proper validation for the limit-parameter
        * CloudWatch:describe_log_streams() now has proper validation for the limit-parameter
        * CloudWatch:get_log_events() now has proper validation for the limit-parameter
        * CloudWatch:filter_log_events() now has proper validation for the limit-parameter
        * DynamoDB:update_item(): fixed a bug where an item was created, despite throwing an error
        * DynamoDB:update_item() now throws an error when both UpdateExpression and AttributeUpdates are supplied
        * EC2:modify_instance_attribute() now supports Attribute="disableApiTermination"
        * S3 now supports direct uploads using the requests-library without having to specify the 'Content-Type' header
        * S3 now supports creating S3 buckets that start with a service name, i.e. `iot-bucket`
        * S3 now returns the RequestID in every response
        * S3:list_parts() now supports the MaxPart-parameter
        * SQS:get_queue_attributes() now behaves correctly when the AttributeNames-parameter is not provided
        * SQS:receive_message() no longer accepts queue-names for the QueueUrl-parameter, as per AWS' spec
        * SQS: The sqs.Queue-class no longer accepts queue-names, only queue-URLs, as per AWS' spec

2.2.5
-----
    General:
        * Python 3.9 is now officially supported

    Known bugs:
        * SQS:get_queue_attributes() throws an error when the AttributeNames-parameter is not provided

    New Methods:
        * DynamoDB (API v20111205, now deprecated)
            * UpdateItem
        * EC2:
            * modify_vpc_peering_connection_options()
        * Glue:
            * create_crawler()
            * delete_crawler()
            * get_crawler()
            * get_crawlers()
        * SSM:
            * describe_document_permission()
            * modify_document_permission()

    Miscellaneous:
        * CloudFormation:create_stack() now has validation for an empty Outputs-parameter
        * EC2 now returns errors in the correct format, fixing various bugs with `terraform destroy`
        * EC2:authorize_security_group_egress() now returns the securityGroupRuleSet-attribute
        * EC2:authorize_security_group_ingress() now returns the securityGroupRuleSet-attribute
        * EC2:create_route() now supports the EgressOnlyInternetGatewayId-parameter
        * EC2:create_route_table() now adds an IPv6-route when enabled
        * EC2:describe_security_groups() now returns the ipv6Ranges-attribute
        * EC2:describe_vpc_peering_connection() now supports the VpcPeeringConnectionIds-parameter
        * Organisations:detach_policy() now actually detaches a policy - before it was essentially a no-op
        * Route53:create_health_check() now supports the CallerReference-parameter
        * Route53:create_health_check() now support default values for integer-parameters such as Port/RequestInterval/FailureThreshold
        * Route53:create_health_check() now supports several additional parameters such as MeasureLatency/Inverted/Disabled/EnableSNI/ChildHealthChecks
        * SQS:create_queue() now supports the queue-attributes FifoThroughputLimit and DeduplicationScope


2.2.4
-----
    New Methods:
        * ConfigService:
            * delete_config_rule()
            * describe_config_rule()
            * put_config_rule()
        * EC2:
            * create_egress_only_internet_gateway()
            * delete_egress_only_internet_gateway()
            * describe_egress_only_internet_gateways()
        * Fargate:
            * create_fargate_profile()
            * delete_fargate_profile()
            * describe_fargate_profile()
            * list_fargate_profiles()
        * IOT:
            * deprecate_thing_type()
        * S3:
            * get_object_lock_configuration()
            * put_object_legal_hold()
            * put_object_lock_configuration()
            * put_object_retention()

    Miscellaneous:
        * CloudFormation:describe_stack_resource() now throws an exception of the LogicalResourceId does not exist
        * CloudFormation: AWS::Events::Rule now supports the EventPattern-property
        * CloudFormation: Improved Parameter handling
        * EC2:describe_instances() now handles wildcards correctly when filtering by tags
        * EC2:terminate_instances() now throws an exception when trying to terminate a protected instance
        * ELBv2:describe_rules() now returns the correct value for the IsDefault-attribute
        * IOT:create_thing() now throws an exception if the thing type is deprecated
        * IOT:update_thing() now throws an exception if the thing type is deprecated
        * S3:create_bucket() now supports the ObjectLockEnabledForBucket-parameter
        * S3:putObject() is fixed for the Java SDK, which failed with a eTag-validation

2.2.3
-----
    New Methods:
        * EC2:
            * create_managed_prefix_list()
            * delete_managed_prefix_list()
            * describe_managed_prefix_lists()
            * describe_prefix_lists()
            * get_managed_prefix_list_entries()
            * delete_vpc_endpoints()
            * disassociate_transit_gateway_route_table()
            * modify_managed_prefix_list()
        * ECR:
            * delete_lifecycle_policy()
            * delete_registry_policy()
            * describe_image_scan_findings()
            * describe_registry()
            * get_lifecycle_policy()
            * get_registry_policy()
            * put_lifecycle_policy()
            * put_registry_policy()
            * put_replication_configuration()
            * start_image_scan()
        * CloudWatch:
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()

    Miscellaneous:
        * CloudWatch: put_metric_alarm() now supports the parameters ExtendedStatistic, TreatMissingData, EvaluateLowSampleCountPercentile, ThresholdMetricId, Tags 
        * CognitoIdentity: create_identity_pool() now supports the IdentityPoolTags-parameter
        * CognitoIDP: initiate_auth() now supports the 'USER_PASSWORD_AUTH'-flow
        * EC2: allocate_address()  now supports the TagSpecifications-parameter
        * EC2: create_route() now supports the TransitGatewayId-parameter
        * EC2: delete_route() now supports the DestinationIpv6CidrBlock-parameter
        * EC2: describe_nat_gateways() now returns the connectivityType-attribute
        * ECR: delete_repository() now supports the force-parameter
        * EventBridge: put_events() now supports ARN's for the EventBusName-parameter
        * EventBridge: put_rule() now supports the Tags-parameter
        * IOT: create_policy_version() now throws the VersionsLimitExceededException if appropriate


2.2.2
-----
    General:
        * Removed the dependency on pkg_resources that was broken in 2.2.1
        
    New Services:
        * WafV2:
            * create_web_acl()
            * list_web_acls()
        
    New Methods:
        * Autoscaling:
            * delete_tags()
            * resume_processes()
        * ConfigService:
            * list_tags_for_resource()
            * tag_resource()
            * untag_resource()
        * EC2:
            * accept_transit_gateway_peering_attachment()
            * create_transit_gateway_peering_attachment()
            * delete_transit_gateway_peering_attachment()
            * describe_transit_gateway_peering_attachments()
            * reject_transit_gateway_peering_attachment()
        * ECR:
            * delete_repository_policy()
            * get_repository_policy()
            * list_tags_for_resource()
            * put_image_tag_mutability()
            * put_image_scanning_configuration()
            * set_repository_policy()
            * tag_resource()
            * untag_resource()
        * KMS:
            * update_alias()
        * Logs:
            * delete_resource_policy()
            * describe_resource_policies()
        * RDS:
            * modify_db_subnet_group()

    Miscellaneous:
        * CloudFormation: Improved support for AWS::ECR::Repository
        * CloudFormation: execute_change_set() now properly updates the status of a stack
        * CognitoIDP: list_users() now supports username/status in the Filter-attribute
        * ECR: create_repository() now supports the parameters encryptionConfiguration, imageScanningConfiguration, imageTagMutability
        * Events: put_permission() now supports the Policy and Condition-parameters
        * Events: remove_permission() now supports the RemoveAllPermissions-parameter
        * Kinesis: create_delivery_stream() now supports the ElasticsearchDestinationConfiguration-parameter
        * SecretsManager: create_secret() now supports the KmsKeyId-parameter
        * SecretsManager: update_secret() now supports the KmsKeyId-parameter

2.2.1
-----
    Known bugs:
        * Moto still depends on setuptools (or more specifically pkg_resources), 
          but this module is not listed as a dependency.

    General:
        * We removed Py3.5 support
        * We removed some unnecessary dependencies for the EC2/SQS services.

    New Services:
        * EFS:
            * create_file_system
            * create_mount_target
            * delete_file_system
            * delete_mount_target
            * describe_backup_policy
            * describe_file_systems
            * describe_mount_target

    New Methods:
        * CognitoIDP:
            * admin_user_global_sign_out()
        * EC2:
            * associate_transit_gateway_route_table()
            * delete_transit_gateway_vpc_attachment()
            * disable_transit_gateway_route_table_propagation()
            * enable_transit_gateway_route_table_propagation()
            * modify_vpc_tenancy()
            * modify_transit_gateway_vpc_attachment()
        * Events:
            * update_connection()

    Miscellaneous:
        * EC2 - describe_route_tables() now returns the associationState-attribute
        * EKS - list_clusters() received a pagination bug fix
        * IOT - describe_certificate() now returns the validity-attribute
        * SQS - create_queue() now supports empty tags
        * SQS - set_queue_attributes() now supports setting an empty policy


2.2.0
-----
    General Changes:
        * Support for Python 2.7 has been removed.
          The last release with Python2 support is now 2.1.0

    New Methods:
        * API Gateway:
            * delete_domain_name()
            * delete_method()
            * update_domain_name()
            * update_method()
            * update_method_response()
        * CognitoIdentity:
            * update_identity_pool()
        * EC2:
            * create_transit_gateway()
            * create_transit_gateway_route()
            * create_transit_gateway_route_table()
            * create_transit_gateway_vpc_attachment()
            * delete_transit_gateway()
            * delete_transit_gateway_route()
            * delete_transit_gateway_route_table()
            * describe_transit_gateway_attachments()
            * describe_transit_gateway_route_tables()
            * describe_transit_gateway_vpc_attachments()
            * describe_transit_gateways()
            * modify_transit_gateway()
            * search_transit_gateway_routes()
        * Events:
            * delete_api_destination()
            * delete_connection()
            * describe_connection()
            * update_api_destination()
        * Logs:
            * put_resource_policy()
        * Organizations:
            * delete_organization()
        * S3:
            * delete_bucket_website()

    Miscellaneous:
        * API Gateway - add_integration() now supports the parameters integration_method, tls_config, cache_namespace
        * API Gateway - add_method() now supports the parameters request_models, operation_name, authorizer_id, authorization_scopes, request_validator_id
        * API Gateway - create_integration() now supports the parameters tls_config, cache_namespace
        * API Gateway - create_method() now supports the parameters request_models, operation_name, authorizer_id, authorization_scopes, request_validator_id
        * API Gateway - create_method_response() now supports the parameters response_models, response_parameters
        * API Gateway - create_response() now supports the parameters response_models, response_parameters
        * API Gateway - create_rest_api() now supports the parameters minimum_compression_size
        * API Gateway - create_stage() now supports the parameters tags, tracing_enabled
        * API Gateway - delete_stage() now throws a StageNotFoundException when appropriate
        * API Gateway - get_api_key() now throws a ApiKeyNotFoundException when appropriate
        * API Gateway - get_integration_response() now throws a NoIntegrationResponseDefined when appropriate
        * API Gateway - get_method() now throws a MethodNotFoundException when appropriate

        * ApplicationAutoscaling - put_scaling_policy() now correctly processes the policy_type and policy_body parameters when overwriting an existing policy

        * CloudFormation - now supports the creation of AWS::EC2::TransitGateway

        * CloudWatch - put_metric_alarm() now supports the parameter rule
        * CloudWatch - get_metric_statistics() now supports the parameter dimensions

        * EC2 - create_customer_gateway() now supports the parameter tags
        * EC2 - create_security_group() now supports the parameter tags
        * EC2 - create_vpn_connection() now supports the parameter transit_gateway_id, tags
        * EC2 - create_vpn_gateway() now supports the parameter amazon_side_asn, availability_zone, tags
        * EC2 - get_all_customer_gateways() now has improved support for the filter parameter

        * ECS - create_service() now has support for the parameter service_registries

        * ELBv2 - create_load_balancer() now has support for the parameter loadbalancer_type

        * Events - create_api_destination() now has support for the parameter invocation_rate_limit_per_second
        * Events - create_event_bus() now has support for the parameter tags

        * IAM - create_instance_profile() now has support for the parameter tags
        * IAM - create_policy() now has support for the parameter tags

        * Logs - create_log_group() now has support for the parameter kms_key_id

        * SecretsManager - list_secrets() now supports pagination

2.1.0
-----
    General Changes:
        * Reduced the default value of DEFAULT_KEY_BUFFER_SIZE (introduced in 2.0.9).
          In practice, this means that large S3 uploads will now be cached on disk, instead of in-memory.
        * Removes `cfn-lint` as a dependency for the SSM-module.

    New Methods:
        * Kinesis
            * decrease_stream_retention_period
            * increase_stream_retention_period

    Miscellaneous:
        * CognitoIDP:admin_create_user(): Fixed a bug where user-supplied attributes would be ignored/overwritten
        * ELBv2:create_rule(): Increased support for Condition-parameter, to also allow http-header/http-request-method/host-header/path-pattern/query-string/source-ip

2.0.11
------
    New Services:
        * MediaStoreData
            * delete_object
            * get_object
            * list_items
            * put_object

    New Methods:
        * CognitoIDP
            * get_user
        * MediaConnect
            * add_flow_outputs
            * add_flow_vpc_interfaces
            * remove_flow_output
            * remove_flow_vpc_interface

    Miscellaneous:
        * ApplicationAutoscaling:put_scaling_policy() now supports StepScaling
        * ApplicationAutoscaling:register_scalable_target() now supports custom resources
        * CloudFormation: Now resolves default SSM parameters (AWS::SSM::Parameter::Value<>)
        * DynamoDB:update_item(): Fix bug for Action:DELETE without value supplied
        * EC2:create_network_interface() now supports the TagSpecification-parameter
        * ELBv2:modify_listener(): improved behaviour for the Certificates-parameter
        * Lambda:invoke() now returns header: content-type=application/json
        * Logs:put_log_events() now returns the correct error message when the stream does not exist
        * IOT:update_thing_shadow() now properly maintains state
        * S3: Listing parts on an aborted upload now throws the correct error
        * S3:delete_objects() now correctly ignores unknown keys
        * S3:list_object_versions() now returns the Prefix-attribute
        * S3:upload_part() now throws the correct error when providing a negative part number
        * SES:verify_domain_identity() and verify_domain_identity() are now idempotent
        * SNS:create_platform_endpoint() now returns an existing endpoint if the token and attributes are the same
        * SQS:delete_message_batch() now throws an error when duplicate messages are supplied
        * SQS:send_messages() now throws an error for FIFO queues if the MessageGroupId-parameter is not supplied

2.0.10
------

    New Services:
        * EKS
            * create_cluster
            * create_nodegroup
            * delete_cluster
            * delete_nodegroup
            * list_clusters
            * list_nodegroup

    Miscellaneous:
        * DynamoDB: Fixed a bug where it's not possible to call update_item on a GSI
        * EMR: now supports clusters with multiple master nodes
        * EMR:terminate_job_flows() now throws an exception when trying to terminate; protected job flows
        * MediaPackage: Implement NotFoundExceptions for delete_channel/describe_origin_endpoint/delete_origin_endpoint/update_origin_endpoint
        * S3:list_users_response() now returns the IsTruncated-attribute

2.0.9
-----
    General Changes:
        * Introduction of a new environment variable: MOTO_S3_DEFAULT_KEY_BUFFER_SIZE
          This allows you to set the in-memory buffer size for multipart uploads. The default size is (and always was) 16MB.
          Exceeding this buffer size will cause the contents to be written/saved to a temporary file.

    New Methods:
        * API Gateway:
            * update_rest_api()
        * DynamoDB:
            * create_backup()
            * delete_backup()
            * describe_backup()
            * list_backups()
            * restore_table_from_backup()
        * Events:
            * create_api_destination()
            * create_connection()
            * describe_api_destination()
            * list_api_destinations()
            * list_connections()
        * Logs
            * start_query()
            
    Miscellaneous:
        * Batch:
            * Now uses the exit code of the Docker-container to decide job status
            * Supports job-dependencies
        * CloudFormation:
            * Create/Update support for AWS::ElasticLoadBalancingV2::ListenerRule
            * Update support for AWS::ElasticLoadBalancingV2::Listener
        * Glacier:
            * Vault names can now contain special characters
        * MediaPackage:
            * describe_channel() now throws a NotFoundException for unknown channels
        * Organisations:
            * Improve tagging support 
        * S3:
            * Now supports '.' as a metadata character
        * S3 Config:
            * Fixed the response format for ACLs
        * SSM:
            * get_parameter() now throws correct exception for unknown parameters/versions
            * get_parameters() can now fetch specific versions and labeled parameters
            * get_parameter_history() now supports pagination
            * Parameter-names can now contain hyphens
            * Only the last 100 parameter versions are now kept, as per AWS' behaviour

2.0.8
-----
    General Changes:
        * Moto is now compatible with Flask/werkzeug 2.0

    New Methods:
        * MediaStore:
            * delete_container()
            * list_tags_for_resource()
        * Resource Groups:
            * get_group_configuration()
            * put_group_configuration()

    Miscellaneous:
        * APIGateway:update_usage_plan() now also supports the '/name', '/description' and '/productCode' paths.
        * CloudWatch:get_metric_statistics() now supports the 'unit'-parameter
        * EC2:run_instances() now supports the 'KmsKeyId'-parameter
        * EC2:run_instances() now supports TagSpecifications with ResourceType: 'Volume'
        * SES:test_render_template() now throws an exception if not all attributes are supplied
        * SSM:put_parameter() now supports the 'tags'-parameter
        * SQS:change_message_visibility() now throws an exception if the VisibilityTimeout is too large (> 43200 seconds)
        * SQS:receive_messages() has a bugfix: it now calculates the MessageRetentionPeriod from when the message was send, rather than from when the queue was created


2.0.7
-----
    General Changes:
        * When running Moto Server inside Docker, it is now possible to specify the service you want to run, using an environment variable (MOTO_SERVICE)
        * CloudWatchLogs models now appear in the Moto API dashboard

    New Services:
        * DMS
            * create_replication_task()
            * delete_replication_task()
            * describe_replication_tasks()
            * start_replication_task()
            * stop_replication_task()

    New Methods:
        * AWSLambda:
            * update_secret_version_stage()
        * CognitoIDP:
            * get_user_pool_mfa_config()
            * set_user_pool_mfa_config()

    Miscellaneous:
        * CloudWatchLogs:filter_log_events() now supports pagination
        * CloudWatchLogs:describe_log_streams() now supports pagination
        * EC2:describe_network_acls() now supports the filter 'owner-id'
        * EC2:modify_network_interface_attribute() now allows multiple security groups to be specified
        * SecretsManager:rotate_secret() now triggers the Lambda that is specified


2.0.6
-----
    New Methods:
        * EMR
            * list_instances()

    Miscellaneous:
        * API Gateway:put_integration_response() - Fixed a bug where an error would be thrown if the responseTemplates-parameter was not specified
        * Autoscaling - Fixed a bug where creating an ASG would remove manually created EC2-instances
        * CloudFormation support for:
            * AWS::SageMaker::Endpoint
            * AWS::SageMaker::EndpointConfig
            * AWS::SageMaker::Model
            * AWS::SageMaker::NotebookInstanceLifecycleConfig
        * CloudWatchLogs:filter_log_events() now supports pagination
        * DynamoDB: Now enforces Hash and Range key size limits
        * ECS:register_task_definition() now persists the taskRoleArn and executionRoleArn-parameters
        * EMR:describe_cluster() now returns the ClusterArn-attribute
        * EMR:run_job_flow() now returns the ClusterArn-attribute
        * EMR:describe_job_flows() now returns the ClusterArn-attribute
        * IOT:list_principal_thigns() now returns the name, instead of the ARN
        * Route53:get_all_rrsets() now returns the record sets in the right sort order
        * S3:get_object() now returns the NoSuchVersion-exception when the versionId was not found (instead of the InvalidVersion)
        * SQS:send_message() now supports the MessageSystemAttributes-parameter

2.0.5
-----
    New Services:
        * MediaStore
            * create_container()
            * describe_container()
            * list_containers()
            * put_lifecycle_policy()
            * get_lifecycle_policy()
            * put_container_policy()
            * get_container_policy()
            * put_metric_policy()
            * get_metric_policy

    Miscellaneous:
        * ACM now supports the MOTO_ACM_VALIDATION_WAIT-environment variable, to configure the wait time before the status on new certificates move from PENDING_VALIDATION to ISSUED
        * CloudFormation support for AWS::SageMaker::NotebookInstance
        * EMR:run_job_flow() now creates the appropriate EC2 security groups in a private subnet
        * Events:put_events() has improved support for the EventPattern-parameter in create_archive/put_rule
        * Events:put_targets() now support SQS queues
        * IAM:get_user() now returns the Tags-attribute
        * Fixed a bug where Moto would break on systems with a default encoding other than UTF-8

2.0.4
-----
    Miscelleaneous:
        * Events:put_targets() now supports SQS queues
        * Support:describe_cases() no longer requires the caseIdList-parameter

2.0.3
-----
    New Methods:
        * Support
            * create_case
            * describe_cases
            * resolve_case
    Miscelleaneous:
        * CF now returns the PhysicalResourceId-attributes for AWS::EC2::NatGateway/AWS::EC2::Route/AWS::EC2::SubnetRouteTableAssociation
        * CognitoIDP:sign_up() now throws an UsernameExistsException if appropriate
        * DynamoDB now validates the case sensitivity for begins_with/between operators
        * EC2:associate_route_table() now supports the GatewayId-parameter
        * EC2:authorize_egress() now throws a InvalidPermission.Duplicate-exception if appropriate
        * EC2:authorize_security_group_egress() now throws a InvalidGroup.NotFound-exception
        * EC2:authorize_security_group_ingress() now throws a InvalidGroup.NotFound-exception
        * Events:describe_rule() now returns the ManagedBy/CreatedBy-parameters
        * Events:put_events() now supports providing an ARN for the EventBusName-parameter
        * Route53:list_hosted_zones_by_name() now returns the DNSName-parameter
        * S3:put_object_acl() now throws a NoSuchKey-exception if the object does not exist
        * SES:send_templated_email() now throws a TemplateDoesNotExist-exception if the template has not been created first
        * SSM:put_parameter() now throws an exception for empty values
    Known bugs:
        * Support:describe_cases() throws an exception when called without the caseIdList-parameter


2.0.2
-----
    General Changes:
        * New Osaka region is now supported

    New Services:
        * MediaPackage

    New Methods:
        * Redshift
            * authorize_cluster_security_group_ingress
        * Secrets Manager:
            * untag_resource

    Miscellaneous:
        * IAM:list_roles() now contains the MaxSessionDuration-attribute
        * Kinesis:get_records(): Fix formatting of the ApproximateArrivalTimestamp-parameter
        * SQS:receive_message(): Fix behaviour of the AttributeNames-parameter

2.0.1
-----
    New Services:
        * Media Connect

    New Methods:
        * API Gateway: 
            * update_usage_plan
        * Events
            * cancel_replay
            * describe_replay
            * start_replay
            * list_replays
        
    Miscellaneous:
        * ECS TaskDefinitions now have the 'status' attribute
        * Events: the put_rule now updates an existing rule, instead of removing the old one (and the associated targets)
        * IAM create_roles and list_roles now return the Description
        * SSM: put_parameter and describe_parameters now supports tags


2.0.0
----
Full list of PRs merged in this release:
https://github.com/getmoto/moto/pulls?q=is%3Apr+is%3Aclosed+merged%3A2020-09-07..2021-02-23

    General Changes:
        * When installing, it is now required to specify the service you want to use:
          pip install moto[service1,service2]
          pip install moto[all]
          
          This will ensure that only the required dependencies are downloaded. 
          See the README for more information.
          
        * Moved CI to Github Actions
        
        * Moto no longer hogs the _default_mock from responses
        
        * Internal testing is now executed using Pytest (instead of Nose)
        
        * CORS is now enabled when running MotoServer

        * AWS Lambda and Batch now support Podman as an alternative to Docker
    
    New Services:
        * Forecast
        * MediaLive
        * Support
        * Transcribe
    
    New Methods:
        * Application Autoscaling
            * delete_scaling_policy
            * deregister_scalable_target
            * describe_scaling_policies
            * put_scaling_policy
        * Batch
            * batch_update_partition
        * Cognito IDP
            * admin_set_user_password
        * EC2
            * create_flow_logs
            * delete_flow_logs
            * describe_flow_logs
            * describe_instance_type_offerings
            * describe_vpc_endpoints
        * EMR
            * create_security_configuration
            * delete_security_configuration
            * get_security_configuration
            * modify_cluster
            * put_autoscaling_policy
            * remove_auto_scaling_policy
        * Events
            * create_archive
            * delete_archive
            * describe_archive
            * list_archives
            * update_archive
        * Lambda
            * get_function_configuration
            * get_layer_version
            * list_layers
            * publish_layer_version
        * IAM
            * associate_iam_instance_profile
            * delete_role_permissions_boundary
            * describe_iam_instance_profile_associations
            * disassociate_iam_instance_profile
            * put_role_permissions_boundary
            * replace_iam_instance_profile_association
            * set_default_policy_version
            * tag_user
            * untag_user
        * IOT
            * create_topic_rule
            * delete_topic_rule
            * disable_topic_rule
            * enable_topic_rule
            * get_topic_rule
            * list_topic_rules
            * replace_topic_rule
        * Redshift
            * get_cluster_credentials
        * Route53
            * get_change (dummy)
        * SageMaker
            * create_notebook_instance_lifecycle_config
            * delete_notebook_instance_lifecycle_config
            * describe_notebook_instance_lifecycle_config
        * Secrets Manager
            * tag_resource
        * SES
            * test_render_template
            * update_template
        * Step Functions
            * get_execution_history
            * tag_resource
            * untag_resource
            * update_state_machine

    General Changes:
        * ACM - import_certificate() now supports the Tags-parameter
        * ACM - request_certificate() now supports the Tags-parameter
        * CF - SSHIngressRule now supports CidrIp and Description
        * CF - Now fully supports:
             AWS::StepFunctions::StateMachine
        * CF - Now supports creation of:
             AWS::ApiGateway::Deployment
             AWS::ApiGateway::Method
             AWS::ApiGateway::Resource
             AWS::ApiGateway::RestApi
             AWS::Lambda::Permission
        * CF - Now supports S3 outputs: Arn, DomainName, DualStackDomainName, RegionalDomainName, WebsiteURL
        * CloudWatch - list_metrics() no longer returns duplicate entries
        * CloudWatch - put_metric_alarm() now supports the Metrics and DatapointsToAlarm parameters
        * Config - Now supports IAM (Role, Policy)
        * Cognito - admin_initiate_auth() now supports the ADMIN_USER_PASSWORD_AUTH-flow
        * CognitoIDP - list_users() now supports spaces in the Filter-parameter
        * DynamoDB - GSI's now support the ProjectionType=INCLUDE parameter
        * DynamoDB - put_item() now supports empty values (in non-key attributes)
        * DynamoDB - update_item() now supports the ADD operation to a list (using the AttributeUpdates-parameter)
        * DynamoDB - update_item() now supports the PUT operation to a StringSet (using the AttributeUpdates-parameter)
        * DynamoDB - update_item() now supports ReturnValues='UPDATED_NEW'
        * DynamoDB - update_item() now defaults to PUT if the action is not supplied
        * DynamoDB Streams - The event name for deletions has been corrected to REMOVE (was DELETE before)
        * EB - create()/describe_applications() now return a properly formatted ARN (that contains the application-name)
        * EC2 - copy_snapshot() now supports the TagSpecifications-parameter
        * EC2 - create_image() now supports the TagSpecifications-parameter
        * EC2 - create_internet_gateway() now supports the TagSpecifications-parameter
        * EC2 - create_nat_gateway() now supports the TagSpecification-parameter
        * EC2 - create_network_acl() now supports the TagSpecification-parameter
        * EC2 - create_route_table() now supports the TagSpecifications-parameter
        * EC2 - create_subnet() now supports the TagSpecifications-parameter
        * EC2 - create_subnet() now supports secondary CidrBlock-values 
        * EC2 - create_tags() now supports empty values
        * EC2 - create_volume() now supports the KmsKeyId-parameter
        * EC2 - create_vpc now supports the TagSpecifications-parameter
        * EC2 - create_vpc_endpoint() now properly handles private_dns_enabled-parameter in CF/TF
        * EC2 - create_vpn_endpoint() now supports the VpnGatewayId-parameter
        * EC2 - describe_addresses() now returns Tags
        * EC2 - describe_instances() now supports filtering by the subnet-id-attribute
        * EC2 - describe_subnets() now supports filtering by the state-attribute
        * ECR - list_images() now returns a proper value for the imageDigest-attribute
        * ECS - the default cluster is now used in a variety of methods, if the Cluster-parameter is not supplied
        * ECS - create_service() now supports the launchType-parameter
        * ECS - delete_service() now supports the force-parameter
        * ECS - describe_container_instances() now returns the registeredAt-attribute
        * ECS - list_tasks now supports the filters family/service_name/desired_status
        * ECS - register_scalable_target() now supports updates
        * ECS - register_task_definition() now returns some attributes that were missing before
        * ECS - run_task() now supports the tags-parameter
        * EMR - ReleaseLabel now respects semantic versioning
        * Events - Now supports the Go SDK
        * Events - list_rules() now returns the EventBusName-parameter
        * Events - put_events() now has basic input validation 
        * Glue - create_database() now returns some attributes that were missing before
        * IAM - create_user() now returns the Tags-attribute
        * IAM - list_roles() now supports the parameters PathPrefix/Marker/MaxItems
        * IOT - delete_thing_group() is now idempotent
        * Lambda - update_function_configuration() now supports the VpcConfig-parameter
        * RDS - create_db_parameter_group() now returns the DBParameterGroupArn-attribute
        * RDS - describe_db_instances() now returns the TagList-attribute
        * RDS - describe_db_instances() now supports the filters-parameter
        * RDS - describe_db_snapshots() now supports the filters-parameter
        * Redshift - modify_cluster() now checks for invalid ClusterType/NumberOfNodes combinations
        * ResourceGroupTagging: Now supports EC2 VPC resources
        * ResourceGroupTagging: Now supports RDS DBInstance, DBSnapshot resources
        * ResourceGroupTagging - get_resources() has improved support for the TagFilters-parameter
        * S3 - copy_object() now supports copying deleted and subsequently restored objects with storage class Glacier
        * S3 - get_object() now throws the correct error for an unknown VersionId
        * S3 - get_object() now supports an empty Range-parameter
        * S3 - get_object() now returns headers that were missing in some cases (ContentLength/ActualObjectSize/RangeRequested)
        * S3 - put_object/get_object now support the ServerSideEncryption/SSEKMSKeyId/BucketKeyEnabled parameters
        * S3 - list_object_versions now returns the object in the correct sort order (last modified time)
        * SecretsManager - describe_secret() now returns a persistent ARN
        * SecretsManager - get_secret_value() now requires a version to exist
        * SecretsManager - put_secret_value() now requires a secret to exist
        * SES - get-template() now returns the HtmlPart-attribute
        * SNS - Support KmsMasterKeyId-attribute
        * SNS - create_topic() no longer throws an error when creating a FIFO queue
        * SNS - delete_topic() now also deletes the corresponding subscriptions
        * SNS - delete_topic() now raises an appropriate exception if the supplied topic not exists
        * Step Functions - list_executions() now supports filtering and pagination
        * SQS - The MD5OfMessageAttributes is now computed correctly 
        * SQS - a message in the DLQ now no longer blocks other messages with that MessageGroupId
        * SQS - create_queue() now supports the MaximumMessageSize-attribute
        * SQS - receive_message() now supports MessageAttributeNames=["All"]
        * SQS - send_message() now deduplicates properly using the MessageDeduplicationId



1.3.16
-----
Full list of PRs merged in this release:
https://github.com/getmoto/moto/pulls?q=is%3Apr+is%3Aclosed+merged%3A2019-11-14..2020-09-07


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
