from __future__ import unicode_literals

from .compat import SUPPORTS_LAMBDA

from moto.acm import acm_backends
from moto.apigateway import apigateway_backends
from moto.autoscaling import autoscaling_backends

if SUPPORTS_LAMBDA:
    from moto.awslambda import lambda_backends

from moto.cloudformation import cloudformation_backends  # noqa: E402
from moto.cloudwatch import cloudwatch_backends  # noqa: E402
from moto.core import moto_api_backends  # noqa: E402
from moto.datapipeline import datapipeline_backends  # noqa: E402
from moto.dynamodb import dynamodb_backends  # noqa: E402
from moto.dynamodb2 import dynamodb_backends2  # noqa: E402
from moto.ec2 import ec2_backends  # noqa: E402
from moto.ecr import ecr_backends  # noqa: E402
from moto.ecs import ecs_backends  # noqa: E402
from moto.elb import elb_backends  # noqa: E402
from moto.elbv2 import elbv2_backends  # noqa: E402
from moto.emr import emr_backends  # noqa: E402
from moto.events import events_backends  # noqa: E402
from moto.glacier import glacier_backends  # noqa: E402
from moto.iam import iam_backends  # noqa: E402
from moto.instance_metadata import instance_metadata_backends  # noqa: E402
from moto.kinesis import kinesis_backends  # noqa: E402
from moto.kms import kms_backends  # noqa: E402
from moto.logs import logs_backends  # noqa: E402
from moto.opsworks import opsworks_backends  # noqa: E402
from moto.polly import polly_backends  # noqa: E402
from moto.rds2 import rds2_backends  # noqa: E402
from moto.redshift import redshift_backends  # noqa: E402
from moto.route53 import route53_backends  # noqa: E402
from moto.s3 import s3_backends  # noqa: E402
from moto.ses import ses_backends  # noqa: E402
from moto.sns import sns_backends  # noqa: E402
from moto.sqs import sqs_backends  # noqa: E402
from moto.ssm import ssm_backends  # noqa: E402
from moto.sts import sts_backends  # noqa: E402
from moto.xray import xray_backends  # noqa: E402
from moto.iot import iot_backends  # noqa: E402
from moto.iotdata import iotdata_backends  # noqa: E402
from moto.batch import batch_backends  # noqa: E402


BACKENDS = {
    'acm': acm_backends,
    'apigateway': apigateway_backends,
    'autoscaling': autoscaling_backends,
    'batch': batch_backends,
    'cloudformation': cloudformation_backends,
    'cloudwatch': cloudwatch_backends,
    'datapipeline': datapipeline_backends,
    'dynamodb': dynamodb_backends,
    'dynamodb2': dynamodb_backends2,
    'ec2': ec2_backends,
    'ecr': ecr_backends,
    'ecs': ecs_backends,
    'elb': elb_backends,
    'elbv2': elbv2_backends,
    'events': events_backends,
    'emr': emr_backends,
    'glacier': glacier_backends,
    'iam': iam_backends,
    'moto_api': moto_api_backends,
    'instance_metadata': instance_metadata_backends,
    'logs': logs_backends,
    'kinesis': kinesis_backends,
    'kms': kms_backends,
    'opsworks': opsworks_backends,
    'polly': polly_backends,
    'redshift': redshift_backends,
    'rds': rds2_backends,
    's3': s3_backends,
    's3bucket_path': s3_backends,
    'ses': ses_backends,
    'sns': sns_backends,
    'sqs': sqs_backends,
    'ssm': ssm_backends,
    'sts': sts_backends,
    'route53': route53_backends,
    'xray': xray_backends,
    'iot': iot_backends,
    'iot-data': iotdata_backends,
}

if SUPPORTS_LAMBDA:
    BACKENDS['lambda'] = lambda_backends


def get_model(name, region_name):
    for backends in BACKENDS.values():
        for region, backend in backends.items():
            if region == region_name:
                models = getattr(backend.__class__, '__models__', {})
                if name in models:
                    return list(getattr(backend, models[name])())
