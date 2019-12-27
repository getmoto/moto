from __future__ import unicode_literals

from .acm import mock_acm  # noqa
from .apigateway import mock_apigateway, mock_apigateway_deprecated  # noqa
from .athena import mock_athena  # noqa
from .autoscaling import mock_autoscaling, mock_autoscaling_deprecated  # noqa
from .awslambda import mock_lambda, mock_lambda_deprecated  # noqa
from .batch import mock_batch  # noqa
from .cloudformation import mock_cloudformation  # noqa
from .cloudformation import mock_cloudformation_deprecated  # noqa
from .cloudwatch import mock_cloudwatch, mock_cloudwatch_deprecated  # noqa
from .codecommit import mock_codecommit  # noqa
from .codepipeline import mock_codepipeline  # noqa
from .cognitoidentity import mock_cognitoidentity  # noqa
from .cognitoidentity import mock_cognitoidentity_deprecated  # noqa
from .cognitoidp import mock_cognitoidp, mock_cognitoidp_deprecated  # noqa
from .config import mock_config  # noqa
from .datapipeline import mock_datapipeline  # noqa
from .datapipeline import mock_datapipeline_deprecated  # noqa
from .datasync import mock_datasync  # noqa
from .dynamodb import mock_dynamodb, mock_dynamodb_deprecated  # noqa
from .dynamodb2 import mock_dynamodb2, mock_dynamodb2_deprecated  # noqa
from .dynamodbstreams import mock_dynamodbstreams  # noqa
from .ec2 import mock_ec2, mock_ec2_deprecated  # noqa
from .ec2_instance_connect import mock_ec2_instance_connect  # noqa
from .ecr import mock_ecr, mock_ecr_deprecated  # noqa
from .ecs import mock_ecs, mock_ecs_deprecated  # noqa
from .elb import mock_elb, mock_elb_deprecated  # noqa
from .elbv2 import mock_elbv2  # noqa
from .emr import mock_emr, mock_emr_deprecated  # noqa
from .events import mock_events  # noqa
from .glacier import mock_glacier, mock_glacier_deprecated  # noqa
from .glue import mock_glue  # noqa
from .iam import mock_iam, mock_iam_deprecated  # noqa
from .iot import mock_iot  # noqa
from .iotdata import mock_iotdata  # noqa
from .kinesis import mock_kinesis, mock_kinesis_deprecated  # noqa
from .kms import mock_kms, mock_kms_deprecated  # noqa
from .logs import mock_logs, mock_logs_deprecated  # noqa
from .opsworks import mock_opsworks, mock_opsworks_deprecated  # noqa
from .organizations import mock_organizations  # noqa
from .polly import mock_polly  # noqa
from .rds import mock_rds, mock_rds_deprecated  # noqa
from .rds2 import mock_rds2, mock_rds2_deprecated  # noqa
from .redshift import mock_redshift, mock_redshift_deprecated  # noqa
from .resourcegroups import mock_resourcegroups  # noqa
from .resourcegroupstaggingapi import mock_resourcegroupstaggingapi  # noqa
from .route53 import mock_route53, mock_route53_deprecated  # noqa
from .s3 import mock_s3, mock_s3_deprecated  # noqa
from .secretsmanager import mock_secretsmanager  # noqa
from .ses import mock_ses, mock_ses_deprecated  # noqa
from .sns import mock_sns, mock_sns_deprecated  # noqa
from .sqs import mock_sqs, mock_sqs_deprecated  # noqa
from .ssm import mock_ssm  # noqa
from .stepfunctions import mock_stepfunctions  # noqa
from .sts import mock_sts, mock_sts_deprecated  # noqa
from .swf import mock_swf, mock_swf_deprecated  # noqa
from .xray import XRaySegment, mock_xray, mock_xray_client  # noqa

# import logging
# logging.getLogger('boto').setLevel(logging.CRITICAL)

__title__ = "moto"
__version__ = "1.3.15.dev"


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
