from __future__ import unicode_literals
import logging
#logging.getLogger('boto').setLevel(logging.CRITICAL)

__title__ = 'moto'
__version__ = '0.4.31'

from .apigateway import mock_apigateway  # flake8: noqa
from .autoscaling import mock_autoscaling  # flake8: noqa
from .awslambda import mock_lambda  # flake8: noqa
from .cloudformation import mock_cloudformation  # flake8: noqa
from .cloudwatch import mock_cloudwatch  # flake8: noqa
from .datapipeline import mock_datapipeline  # flake8: noqa
from .dynamodb import mock_dynamodb  # flake8: noqa
from .dynamodb2 import mock_dynamodb2  # flake8: noqa
from .ec2 import mock_ec2  # flake8: noqa
from .ecs import mock_ecs  # flake8: noqa
from .elb import mock_elb  # flake8: noqa
from .emr import mock_emr  # flake8: noqa
from .glacier import mock_glacier  # flake8: noqa
from .opsworks import mock_opsworks  # flake8: noqa
from .iam import mock_iam  # flake8: noqa
from .kinesis import mock_kinesis  # flake8: noqa
from .kms import mock_kms  # flake8: noqa
from .rds import mock_rds  # flake8: noqa
from .rds2 import mock_rds2  # flake8: noqa
from .redshift import mock_redshift  # flake8: noqa
from .s3 import mock_s3  # flake8: noqa
from .s3bucket_path import mock_s3bucket_path  # flake8: noqa
from .ses import mock_ses  # flake8: noqa
from .sns import mock_sns  # flake8: noqa
from .sqs import mock_sqs  # flake8: noqa
from .sts import mock_sts  # flake8: noqa
from .route53 import mock_route53  # flake8: noqa
from .swf import mock_swf  # flake8: noqa


try:
    # Need to monkey-patch botocore requests back to underlying urllib3 classes
    from botocore.awsrequest import HTTPSConnectionPool, HTTPConnectionPool, HTTPConnection, VerifiedHTTPSConnection
except ImportError:
    pass
else:
    HTTPSConnectionPool.ConnectionCls = VerifiedHTTPSConnection
    HTTPConnectionPool.ConnectionCls = HTTPConnection
