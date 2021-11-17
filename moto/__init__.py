import importlib
import sys


def lazy_load(
    module_name, element, boto3_name=None, backend=None, warn_repurpose=False
):
    def f(*args, **kwargs):
        if warn_repurpose:
            import warnings

            warnings.warn(
                f"Module {element} has been deprecated, and will be repurposed in a later release. "
                "Please see https://github.com/spulec/moto/issues/4526 for more information."
            )
        module = importlib.import_module(module_name, "moto")
        return getattr(module, element)(*args, **kwargs)

    setattr(f, "name", module_name.replace(".", ""))
    setattr(f, "element", element)
    setattr(f, "boto3_name", boto3_name or f.name)
    setattr(f, "backend", backend or f"{f.name}_backends")
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
mock_lambda = lazy_load(
    ".awslambda", "mock_lambda", boto3_name="lambda", backend="lambda_backends"
)
mock_lambda_deprecated = lazy_load(".awslambda", "mock_lambda_deprecated")
mock_batch = lazy_load(".batch", "mock_batch")
mock_batch = lazy_load(".batch", "mock_batch")
mock_cloudformation = lazy_load(".cloudformation", "mock_cloudformation")
mock_cloudformation_deprecated = lazy_load(
    ".cloudformation", "mock_cloudformation_deprecated"
)
mock_cloudtrail = lazy_load(".cloudtrail", "mock_cloudtrail", boto3_name="cloudtrail")
mock_cloudwatch = lazy_load(".cloudwatch", "mock_cloudwatch")
mock_cloudwatch_deprecated = lazy_load(".cloudwatch", "mock_cloudwatch_deprecated")
mock_codecommit = lazy_load(".codecommit", "mock_codecommit")
mock_codepipeline = lazy_load(".codepipeline", "mock_codepipeline")
mock_cognitoidentity = lazy_load(
    ".cognitoidentity", "mock_cognitoidentity", boto3_name="cognito-identity"
)
mock_cognitoidentity_deprecated = lazy_load(
    ".cognitoidentity", "mock_cognitoidentity_deprecated"
)
mock_cognitoidp = lazy_load(".cognitoidp", "mock_cognitoidp", boto3_name="cognito-idp")
mock_cognitoidp_deprecated = lazy_load(".cognitoidp", "mock_cognitoidp_deprecated")
mock_config = lazy_load(".config", "mock_config")
mock_datapipeline = lazy_load(".datapipeline", "mock_datapipeline")
mock_datapipeline_deprecated = lazy_load(
    ".datapipeline", "mock_datapipeline_deprecated"
)
mock_datasync = lazy_load(".datasync", "mock_datasync")
mock_dms = lazy_load(".dms", "mock_dms")
mock_ds = lazy_load(".ds", "mock_ds", boto3_name="ds")
mock_dynamodb = lazy_load(".dynamodb", "mock_dynamodb", warn_repurpose=True)
mock_dynamodb_deprecated = lazy_load(".dynamodb", "mock_dynamodb_deprecated")
mock_dynamodb2 = lazy_load(".dynamodb2", "mock_dynamodb2", backend="dynamodb_backends2")
mock_dynamodb2_deprecated = lazy_load(".dynamodb2", "mock_dynamodb2_deprecated")
mock_dynamodbstreams = lazy_load(".dynamodbstreams", "mock_dynamodbstreams")
mock_elasticbeanstalk = lazy_load(
    ".elasticbeanstalk", "mock_elasticbeanstalk", backend="eb_backends"
)
mock_ec2 = lazy_load(".ec2", "mock_ec2")
mock_ec2_deprecated = lazy_load(".ec2", "mock_ec2_deprecated")
mock_ec2instanceconnect = lazy_load(".ec2instanceconnect", "mock_ec2instanceconnect")
mock_ecr = lazy_load(".ecr", "mock_ecr")
mock_ecr_deprecated = lazy_load(".ecr", "mock_ecr_deprecated")
mock_ecs = lazy_load(".ecs", "mock_ecs")
mock_ecs_deprecated = lazy_load(".ecs", "mock_ecs_deprecated")
mock_elastictranscoder = lazy_load(".elastictranscoder", "mock_elastictranscoder")
mock_elb = lazy_load(".elb", "mock_elb")
mock_elb_deprecated = lazy_load(".elb", "mock_elb_deprecated")
mock_elbv2 = lazy_load(".elbv2", "mock_elbv2")
mock_emr = lazy_load(".emr", "mock_emr")
mock_emr_deprecated = lazy_load(".emr", "mock_emr_deprecated")
mock_emrcontainers = lazy_load(
    ".emrcontainers", "mock_emrcontainers", boto3_name="emr-containers"
)
mock_events = lazy_load(".events", "mock_events")
mock_firehose = lazy_load(".firehose", "mock_firehose")
mock_forecast = lazy_load(".forecast", "mock_forecast")
mock_glacier = lazy_load(".glacier", "mock_glacier")
mock_glacier_deprecated = lazy_load(".glacier", "mock_glacier_deprecated")
mock_glue = lazy_load(".glue", "mock_glue")
mock_iam = lazy_load(".iam", "mock_iam")
mock_iam_deprecated = lazy_load(".iam", "mock_iam_deprecated")
mock_iot = lazy_load(".iot", "mock_iot")
mock_iotdata = lazy_load(".iotdata", "mock_iotdata", boto3_name="iot-data")
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
mock_rds = lazy_load(".rds", "mock_rds", warn_repurpose=True)
mock_rds_deprecated = lazy_load(".rds", "mock_rds_deprecated")
mock_rds2 = lazy_load(".rds2", "mock_rds2", boto3_name="rds")
mock_rds2_deprecated = lazy_load(".rds2", "mock_rds2_deprecated")
mock_redshift = lazy_load(".redshift", "mock_redshift")
mock_redshift_deprecated = lazy_load(".redshift", "mock_redshift_deprecated")
mock_resourcegroups = lazy_load(
    ".resourcegroups", "mock_resourcegroups", boto3_name="resource-groups"
)
mock_resourcegroupstaggingapi = lazy_load(
    ".resourcegroupstaggingapi", "mock_resourcegroupstaggingapi"
)
mock_route53 = lazy_load(".route53", "mock_route53")
mock_route53_deprecated = lazy_load(".route53", "mock_route53_deprecated")
mock_route53resolver = lazy_load(
    ".route53resolver", "mock_route53resolver", boto3_name="route53resolver"
)
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
mock_stepfunctions = lazy_load(
    ".stepfunctions", "mock_stepfunctions", backend="stepfunction_backends"
)
mock_sts = lazy_load(".sts", "mock_sts")
mock_sts_deprecated = lazy_load(".sts", "mock_sts_deprecated")
mock_swf = lazy_load(".swf", "mock_swf")
mock_swf_deprecated = lazy_load(".swf", "mock_swf_deprecated")
mock_timestreamwrite = lazy_load(
    ".timestreamwrite", "mock_timestreamwrite", boto3_name="timestream-write"
)
mock_transcribe = lazy_load(".transcribe", "mock_transcribe")
XRaySegment = lazy_load(".xray", "XRaySegment")
mock_xray = lazy_load(".xray", "mock_xray")
mock_xray_client = lazy_load(".xray", "mock_xray_client")
mock_kinesisvideo = lazy_load(".kinesisvideo", "mock_kinesisvideo")
mock_kinesisvideoarchivedmedia = lazy_load(
    ".kinesisvideoarchivedmedia",
    "mock_kinesisvideoarchivedmedia",
    boto3_name="kinesis-video-archived-media",
)
mock_medialive = lazy_load(".medialive", "mock_medialive")
mock_support = lazy_load(".support", "mock_support")
mock_mediaconnect = lazy_load(".mediaconnect", "mock_mediaconnect")
mock_mediapackage = lazy_load(".mediapackage", "mock_mediapackage")
mock_mediastore = lazy_load(".mediastore", "mock_mediastore")
mock_eks = lazy_load(".eks", "mock_eks")
mock_mediastoredata = lazy_load(
    ".mediastoredata", "mock_mediastoredata", boto3_name="mediastore-data"
)
mock_efs = lazy_load(".efs", "mock_efs")
mock_wafv2 = lazy_load(".wafv2", "mock_wafv2")
mock_sdb = lazy_load(".sdb", "mock_sdb", boto3_name="sdb")


def mock_all():
    dec_names = [
        d
        for d in dir(sys.modules["moto"])
        if d.startswith("mock_")
        and not d.endswith("_deprecated")
        and not d == "mock_all"
    ]

    def deco(f):
        for dec_name in reversed(dec_names):
            dec = globals()[dec_name]
            f = dec(f)
        return f

    return deco


# import logging
# logging.getLogger('boto').setLevel(logging.CRITICAL)

__title__ = "moto"
__version__ = "2.2.16.dev"


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
