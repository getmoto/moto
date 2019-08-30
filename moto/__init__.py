from __future__ import unicode_literals
import logging
# logging.getLogger('boto').setLevel(logging.CRITICAL)

__title__ = 'moto'
__version__ = '1.3.14.dev'

from .acm import mock_acm  # flake8: noqa
from .apigateway import mock_apigateway, mock_apigateway_deprecated  # flake8: noqa
from .autoscaling import mock_autoscaling, mock_autoscaling_deprecated  # flake8: noqa
from .awslambda import mock_lambda, mock_lambda_deprecated  # flake8: noqa
from .cloudformation import mock_cloudformation, mock_cloudformation_deprecated  # flake8: noqa
from .cloudwatch import mock_cloudwatch, mock_cloudwatch_deprecated  # flake8: noqa
from .cognitoidentity import mock_cognitoidentity, mock_cognitoidentity_deprecated  # flake8: noqa
from .cognitoidp import mock_cognitoidp, mock_cognitoidp_deprecated  # flake8: noqa
from .config import mock_config  # flake8: noqa
from .datapipeline import mock_datapipeline, mock_datapipeline_deprecated  # flake8: noqa
from .dynamodb import mock_dynamodb, mock_dynamodb_deprecated  # flake8: noqa
from .dynamodb2 import mock_dynamodb2, mock_dynamodb2_deprecated  # flake8: noqa
from .dynamodbstreams import mock_dynamodbstreams # flake8: noqa
from .ec2 import mock_ec2, mock_ec2_deprecated  # flake8: noqa
from .ecr import mock_ecr, mock_ecr_deprecated  # flake8: noqa
from .ecs import mock_ecs, mock_ecs_deprecated  # flake8: noqa
from .elb import mock_elb, mock_elb_deprecated  # flake8: noqa
from .elbv2 import mock_elbv2  # flake8: noqa
from .emr import mock_emr, mock_emr_deprecated  # flake8: noqa
from .events import mock_events  # flake8: noqa
from .glacier import mock_glacier, mock_glacier_deprecated  # flake8: noqa
from .glue import mock_glue  # flake8: noqa
from .iam import mock_iam, mock_iam_deprecated  # flake8: noqa
from .kinesis import mock_kinesis, mock_kinesis_deprecated  # flake8: noqa
from .kms import mock_kms, mock_kms_deprecated  # flake8: noqa
from .organizations import mock_organizations  # flake8: noqa
from .opsworks import mock_opsworks, mock_opsworks_deprecated  # flake8: noqa
from .polly import mock_polly  # flake8: noqa
from .rds import mock_rds, mock_rds_deprecated  # flake8: noqa
from .rds2 import mock_rds2, mock_rds2_deprecated  # flake8: noqa
from .redshift import mock_redshift, mock_redshift_deprecated  # flake8: noqa
from .resourcegroups import mock_resourcegroups  # flake8: noqa
from .s3 import mock_s3, mock_s3_deprecated  # flake8: noqa
from .ses import mock_ses, mock_ses_deprecated  # flake8: noqa
from .secretsmanager import mock_secretsmanager  # flake8: noqa
from .sns import mock_sns, mock_sns_deprecated  # flake8: noqa
from .sqs import mock_sqs, mock_sqs_deprecated  # flake8: noqa
from .sts import mock_sts, mock_sts_deprecated  # flake8: noqa
from .ssm import mock_ssm  # flake8: noqa
from .route53 import mock_route53, mock_route53_deprecated  # flake8: noqa
from .swf import mock_swf, mock_swf_deprecated  # flake8: noqa
from .xray import mock_xray, mock_xray_client, XRaySegment  # flake8: noqa
from .logs import mock_logs, mock_logs_deprecated # flake8: noqa
from .batch import mock_batch  # flake8: noqa
from .resourcegroupstaggingapi import mock_resourcegroupstaggingapi  # flake8: noqa
from .iot import mock_iot  # flake8: noqa
from .iotdata import mock_iotdata  # flake8: noqa


try:
    # Need to monkey-patch botocore requests back to underlying urllib3 classes
    from botocore.awsrequest import HTTPSConnectionPool, HTTPConnectionPool, HTTPConnection, VerifiedHTTPSConnection
except ImportError:
    pass
else:
    HTTPSConnectionPool.ConnectionCls = VerifiedHTTPSConnection
    HTTPConnectionPool.ConnectionCls = HTTPConnection
