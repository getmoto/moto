import importlib
import sys
from contextlib import ContextDecorator


def lazy_load(
    module_name,
    element,
    boto3_name=None,
    backend=None,
    warn_repurpose=False,
    use_instead=None,
):
    def f(*args, **kwargs):
        if warn_repurpose:
            import warnings

            warnings.warn(
                f"Module {element} has been deprecated, and will be repurposed in a later release. "
                "Please see https://github.com/spulec/moto/issues/4526 for more information."
            )
        if use_instead:
            import warnings

            used, recommended = use_instead
            warnings.warn(
                f"Module {used} has been deprecated, and will be removed in a later release. Please use {recommended} instead. "
                "See https://github.com/spulec/moto/issues/4526 for more information."
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
mock_apigatewayv2 = lazy_load(".apigatewayv2", "mock_apigatewayv2")
mock_appsync = lazy_load(".appsync", "mock_appsync")
mock_athena = lazy_load(".athena", "mock_athena")
mock_applicationautoscaling = lazy_load(
    ".applicationautoscaling", "mock_applicationautoscaling"
)
mock_autoscaling = lazy_load(".autoscaling", "mock_autoscaling")
mock_lambda = lazy_load(
    ".awslambda", "mock_lambda", boto3_name="lambda", backend="lambda_backends"
)
mock_batch = lazy_load(".batch", "mock_batch")
mock_batch_simple = lazy_load(
    ".batch_simple",
    "mock_batch_simple",
    boto3_name="batch",
    backend="batch_simple_backends",
)
mock_budgets = lazy_load(".budgets", "mock_budgets")
mock_cloudformation = lazy_load(".cloudformation", "mock_cloudformation")
mock_cloudfront = lazy_load(".cloudfront", "mock_cloudfront")
mock_cloudtrail = lazy_load(".cloudtrail", "mock_cloudtrail")
mock_cloudwatch = lazy_load(".cloudwatch", "mock_cloudwatch")
mock_codecommit = lazy_load(".codecommit", "mock_codecommit")
mock_codepipeline = lazy_load(".codepipeline", "mock_codepipeline")
mock_cognitoidentity = lazy_load(
    ".cognitoidentity", "mock_cognitoidentity", boto3_name="cognito-identity"
)
mock_cognitoidp = lazy_load(".cognitoidp", "mock_cognitoidp", boto3_name="cognito-idp")
mock_config = lazy_load(".config", "mock_config")
mock_databrew = lazy_load(".databrew", "mock_databrew")
mock_datapipeline = lazy_load(".datapipeline", "mock_datapipeline")
mock_datasync = lazy_load(".datasync", "mock_datasync")
mock_dax = lazy_load(".dax", "mock_dax")
mock_dms = lazy_load(".dms", "mock_dms")
mock_ds = lazy_load(".ds", "mock_ds")
mock_dynamodb = lazy_load(".dynamodb", "mock_dynamodb")
mock_dynamodb2 = lazy_load(
    ".dynamodb", "mock_dynamodb", use_instead=("mock_dynamodb2", "mock_dynamodb")
)
mock_dynamodbstreams = lazy_load(".dynamodbstreams", "mock_dynamodbstreams")
mock_elasticbeanstalk = lazy_load(
    ".elasticbeanstalk", "mock_elasticbeanstalk", backend="eb_backends"
)
mock_ebs = lazy_load(".ebs", "mock_ebs")
mock_ec2 = lazy_load(".ec2", "mock_ec2")
mock_ec2instanceconnect = lazy_load(".ec2instanceconnect", "mock_ec2instanceconnect")
mock_ecr = lazy_load(".ecr", "mock_ecr")
mock_ecs = lazy_load(".ecs", "mock_ecs")
mock_efs = lazy_load(".efs", "mock_efs")
mock_eks = lazy_load(".eks", "mock_eks")
mock_elasticache = lazy_load(
    ".elasticache", "mock_elasticache", boto3_name="elasticache"
)
mock_elastictranscoder = lazy_load(".elastictranscoder", "mock_elastictranscoder")
mock_elb = lazy_load(".elb", "mock_elb")
mock_elbv2 = lazy_load(".elbv2", "mock_elbv2")
mock_emr = lazy_load(".emr", "mock_emr")
mock_emrcontainers = lazy_load(
    ".emrcontainers", "mock_emrcontainers", boto3_name="emr-containers"
)
mock_es = lazy_load(".es", "mock_es")
mock_events = lazy_load(".events", "mock_events")
mock_firehose = lazy_load(".firehose", "mock_firehose")
mock_forecast = lazy_load(".forecast", "mock_forecast")
mock_glacier = lazy_load(".glacier", "mock_glacier")
mock_glue = lazy_load(".glue", "mock_glue")
mock_guardduty = lazy_load(".guardduty", "mock_guardduty")
mock_iam = lazy_load(".iam", "mock_iam")
mock_iot = lazy_load(".iot", "mock_iot")
mock_iotdata = lazy_load(".iotdata", "mock_iotdata", boto3_name="iot-data")
mock_kinesis = lazy_load(".kinesis", "mock_kinesis")
mock_kinesisvideo = lazy_load(".kinesisvideo", "mock_kinesisvideo")
mock_kinesisvideoarchivedmedia = lazy_load(
    ".kinesisvideoarchivedmedia",
    "mock_kinesisvideoarchivedmedia",
    boto3_name="kinesis-video-archived-media",
)
mock_kms = lazy_load(".kms", "mock_kms")
mock_logs = lazy_load(".logs", "mock_logs")
mock_managedblockchain = lazy_load(".managedblockchain", "mock_managedblockchain")
mock_mediaconnect = lazy_load(".mediaconnect", "mock_mediaconnect")
mock_medialive = lazy_load(".medialive", "mock_medialive")
mock_mediapackage = lazy_load(".mediapackage", "mock_mediapackage")
mock_mediastore = lazy_load(".mediastore", "mock_mediastore")
mock_mediastoredata = lazy_load(
    ".mediastoredata", "mock_mediastoredata", boto3_name="mediastore-data"
)
mock_mq = lazy_load(".mq", "mock_mq", boto3_name="mq")
mock_opsworks = lazy_load(".opsworks", "mock_opsworks")
mock_organizations = lazy_load(".organizations", "mock_organizations")
mock_pinpoint = lazy_load(".pinpoint", "mock_pinpoint")
mock_polly = lazy_load(".polly", "mock_polly")
mock_quicksight = lazy_load(".quicksight", "mock_quicksight")
mock_ram = lazy_load(".ram", "mock_ram")
mock_rds = lazy_load(".rds", "mock_rds")
mock_rds2 = lazy_load(".rds", "mock_rds", use_instead=("mock_rds2", "mock_rds"))
mock_redshift = lazy_load(".redshift", "mock_redshift")
mock_redshiftdata = lazy_load(
    ".redshiftdata", "mock_redshiftdata", boto3_name="redshift-data"
)
mock_rekognition = lazy_load(
    ".rekognition", "mock_rekognition", boto3_name="rekognition"
)
mock_resourcegroups = lazy_load(
    ".resourcegroups", "mock_resourcegroups", boto3_name="resource-groups"
)
mock_resourcegroupstaggingapi = lazy_load(
    ".resourcegroupstaggingapi", "mock_resourcegroupstaggingapi"
)
mock_route53 = lazy_load(".route53", "mock_route53")
mock_route53resolver = lazy_load(
    ".route53resolver", "mock_route53resolver", boto3_name="route53resolver"
)
mock_s3 = lazy_load(".s3", "mock_s3")
mock_s3control = lazy_load(".s3control", "mock_s3control")
mock_sagemaker = lazy_load(".sagemaker", "mock_sagemaker")
mock_sdb = lazy_load(".sdb", "mock_sdb")
mock_secretsmanager = lazy_load(".secretsmanager", "mock_secretsmanager")
mock_ses = lazy_load(".ses", "mock_ses")
mock_servicediscovery = lazy_load(".servicediscovery", "mock_servicediscovery")
mock_sns = lazy_load(".sns", "mock_sns")
mock_sqs = lazy_load(".sqs", "mock_sqs")
mock_ssm = lazy_load(".ssm", "mock_ssm")
mock_ssoadmin = lazy_load(".ssoadmin", "mock_ssoadmin", boto3_name="sso-admin")
mock_stepfunctions = lazy_load(
    ".stepfunctions", "mock_stepfunctions", backend="stepfunction_backends"
)
mock_sts = lazy_load(".sts", "mock_sts")
mock_support = lazy_load(".support", "mock_support")
mock_swf = lazy_load(".swf", "mock_swf")
mock_timestreamwrite = lazy_load(
    ".timestreamwrite", "mock_timestreamwrite", boto3_name="timestream-write"
)
mock_transcribe = lazy_load(".transcribe", "mock_transcribe")
XRaySegment = lazy_load(".xray", "XRaySegment")
mock_xray = lazy_load(".xray", "mock_xray")
mock_xray_client = lazy_load(".xray", "mock_xray_client")
mock_wafv2 = lazy_load(".wafv2", "mock_wafv2")
mock_textract = lazy_load(".textract", "mock_textract")


class MockAll(ContextDecorator):
    def __init__(self):
        self.mocks = []
        for mock in dir(sys.modules["moto"]):
            if (
                mock.startswith("mock_")
                and not mock.endswith("_deprecated")
                and not mock == ("mock_all")
            ):
                self.mocks.append(globals()[mock]())

    def __enter__(self):
        for mock in self.mocks:
            mock.start()

    def __exit__(self, *exc):
        for mock in self.mocks:
            mock.stop()


mock_all = MockAll

# import logging
# logging.getLogger('boto').setLevel(logging.CRITICAL)

__title__ = "moto"
__version__ = "3.1.12.dev"


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
