from __future__ import unicode_literals

import importlib


def lazy_load(module_name, element):
    def f(*args, **kwargs):
        module = importlib.import_module(module_name, "moto")
        return getattr(module, element)(*args, **kwargs)

    return f


mock_acm = lazy_load(".acm", "mock_acm")
mock_apigateway = lazy_load(".apigateway", "mock_apigateway")
mock_apigateway_deprecated = lazy_load(".apigateway", "mock_apigateway_deprecated")
mock_athena = lazy_load(".athena", "mock_athena")
mock_applicationautoscaling = lazy_load(
    ".applicationautoscaling", "mock_applicationautoscaling"
)
mock_autoscaling = lazy_load(".autoscaling", "mock_autoscaling")
mock_autoscaling_deprecated = lazy_load(".autoscaling", "mock_autoscaling_deprecated")
mock_lambda = lazy_load(".awslambda", "mock_lambda")
mock_lambda_deprecated = lazy_load(".awslambda", "mock_lambda_deprecated")
mock_batch = lazy_load(".batch", "mock_batch")
mock_batch = lazy_load(".batch", "mock_batch")
mock_cloudformation = lazy_load(".cloudformation", "mock_cloudformation")
mock_cloudformation_deprecated = lazy_load(
    ".cloudformation", "mock_cloudformation_deprecated"
)
mock_cloudwatch = lazy_load(".cloudwatch", "mock_cloudwatch")
mock_cloudwatch_deprecated = lazy_load(".cloudwatch", "mock_cloudwatch_deprecated")
mock_codecommit = lazy_load(".codecommit", "mock_codecommit")
mock_codepipeline = lazy_load(".codepipeline", "mock_codepipeline")
mock_cognitoidentity = lazy_load(".cognitoidentity", "mock_cognitoidentity")
mock_cognitoidentity_deprecated = lazy_load(
    ".cognitoidentity", "mock_cognitoidentity_deprecated"
)
mock_cognitoidp = lazy_load(".cognitoidp", "mock_cognitoidp")
mock_cognitoidp_deprecated = lazy_load(".cognitoidp", "mock_cognitoidp_deprecated")
mock_config = lazy_load(".config", "mock_config")
mock_datapipeline = lazy_load(".datapipeline", "mock_datapipeline")
mock_datapipeline_deprecated = lazy_load(
    ".datapipeline", "mock_datapipeline_deprecated"
)
mock_datasync = lazy_load(".datasync", "mock_datasync")
mock_dms = lazy_load(".dms", "mock_dms")
mock_dynamodb = lazy_load(".dynamodb", "mock_dynamodb")
mock_dynamodb_deprecated = lazy_load(".dynamodb", "mock_dynamodb_deprecated")
mock_dynamodb2 = lazy_load(".dynamodb2", "mock_dynamodb2")
mock_dynamodb2_deprecated = lazy_load(".dynamodb2", "mock_dynamodb2_deprecated")
mock_dynamodbstreams = lazy_load(".dynamodbstreams", "mock_dynamodbstreams")
mock_elasticbeanstalk = lazy_load(".elasticbeanstalk", "mock_elasticbeanstalk")
mock_ec2 = lazy_load(".ec2", "mock_ec2")
mock_ec2_deprecated = lazy_load(".ec2", "mock_ec2_deprecated")
mock_ec2instanceconnect = lazy_load(".ec2instanceconnect", "mock_ec2instanceconnect")
mock_ecr = lazy_load(".ecr", "mock_ecr")
mock_ecr_deprecated = lazy_load(".ecr", "mock_ecr_deprecated")
mock_ecs = lazy_load(".ecs", "mock_ecs")
mock_ecs_deprecated = lazy_load(".ecs", "mock_ecs_deprecated")
mock_elb = lazy_load(".elb", "mock_elb")
mock_elb_deprecated = lazy_load(".elb", "mock_elb_deprecated")
mock_elbv2 = lazy_load(".elbv2", "mock_elbv2")
mock_emr = lazy_load(".emr", "mock_emr")
mock_emr_deprecated = lazy_load(".emr", "mock_emr_deprecated")
mock_events = lazy_load(".events", "mock_events")
mock_forecast = lazy_load(".forecast", "mock_forecast")
mock_glacier = lazy_load(".glacier", "mock_glacier")
mock_glacier_deprecated = lazy_load(".glacier", "mock_glacier_deprecated")
mock_glue = lazy_load(".glue", "mock_glue")
mock_iam = lazy_load(".iam", "mock_iam")
mock_iam_deprecated = lazy_load(".iam", "mock_iam_deprecated")
mock_iot = lazy_load(".iot", "mock_iot")
mock_iotdata = lazy_load(".iotdata", "mock_iotdata")
mock_kinesis = lazy_load(".kinesis", "mock_kinesis")
mock_kinesis_deprecated = lazy_load(".kinesis", "mock_kinesis_deprecated")
mock_kms = lazy_load(".kms", "mock_kms")
mock_kms_deprecated = lazy_load(".kms", "mock_kms_deprecated")
mock_logs = lazy_load(".logs", "mock_logs")
mock_logs_deprecated = lazy_load(".logs", "mock_logs_deprecated")
mock_managedblockchain = lazy_load(".managedblockchain", "mock_managedblockchain")
mock_opsworks = lazy_load(".opsworks", "mock_opsworks")
mock_opsworks_deprecated = lazy_load(".opsworks", "mock_opsworks_deprecated")
mock_organizations = lazy_load(".organizations", "mock_organizations")
mock_polly = lazy_load(".polly", "mock_polly")
mock_ram = lazy_load(".ram", "mock_ram")
mock_rds = lazy_load(".rds", "mock_rds")
mock_rds_deprecated = lazy_load(".rds", "mock_rds_deprecated")
mock_rds2 = lazy_load(".rds2", "mock_rds2")
mock_rds2_deprecated = lazy_load(".rds2", "mock_rds2_deprecated")
mock_redshift = lazy_load(".redshift", "mock_redshift")
mock_redshift_deprecated = lazy_load(".redshift", "mock_redshift_deprecated")
mock_resourcegroups = lazy_load(".resourcegroups", "mock_resourcegroups")
mock_resourcegroupstaggingapi = lazy_load(
    ".resourcegroupstaggingapi", "mock_resourcegroupstaggingapi"
)
mock_route53 = lazy_load(".route53", "mock_route53")
mock_route53_deprecated = lazy_load(".route53", "mock_route53_deprecated")
mock_s3 = lazy_load(".s3", "mock_s3")
mock_s3_deprecated = lazy_load(".s3", "mock_s3_deprecated")
mock_sagemaker = lazy_load(".sagemaker", "mock_sagemaker")
mock_secretsmanager = lazy_load(".secretsmanager", "mock_secretsmanager")
mock_ses = lazy_load(".ses", "mock_ses")
mock_ses_deprecated = lazy_load(".ses", "mock_ses_deprecated")
mock_sns = lazy_load(".sns", "mock_sns")
mock_sns_deprecated = lazy_load(".sns", "mock_sns_deprecated")
mock_sqs = lazy_load(".sqs", "mock_sqs")
mock_sqs_deprecated = lazy_load(".sqs", "mock_sqs_deprecated")
mock_ssm = lazy_load(".ssm", "mock_ssm")
mock_stepfunctions = lazy_load(".stepfunctions", "mock_stepfunctions")
mock_sts = lazy_load(".sts", "mock_sts")
mock_sts_deprecated = lazy_load(".sts", "mock_sts_deprecated")
mock_swf = lazy_load(".swf", "mock_swf")
mock_swf_deprecated = lazy_load(".swf", "mock_swf_deprecated")
mock_transcribe = lazy_load(".transcribe", "mock_transcribe")
XRaySegment = lazy_load(".xray", "XRaySegment")
mock_xray = lazy_load(".xray", "mock_xray")
mock_xray_client = lazy_load(".xray", "mock_xray_client")
mock_kinesisvideo = lazy_load(".kinesisvideo", "mock_kinesisvideo")
mock_kinesisvideoarchivedmedia = lazy_load(
    ".kinesisvideoarchivedmedia", "mock_kinesisvideoarchivedmedia"
)
mock_medialive = lazy_load(".medialive", "mock_medialive")
mock_support = lazy_load(".support", "mock_support")
mock_mediaconnect = lazy_load(".mediaconnect", "mock_mediaconnect")
mock_mediapackage = lazy_load(".mediapackage", "mock_mediapackage")
mock_mediastore = lazy_load(".mediastore", "mock_mediastore")

# import logging
# logging.getLogger('boto').setLevel(logging.CRITICAL)

__title__ = "moto"
__version__ = "2.0.3.22"


try:
    # Need to monkey-patch botocore requests back to underlying urllib3 classes
    from botocore.awsrequest import (
        HTTPSConnectionPool,
        HTTPConnectionPool,
        HTTPConnection,
        VerifiedHTTPSConnection,
    )
except ImportError:
    pass
else:
    HTTPSConnectionPool.ConnectionCls = VerifiedHTTPSConnection
    HTTPConnectionPool.ConnectionCls = HTTPConnection
