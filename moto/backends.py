from __future__ import unicode_literals

from moto.apigateway import apigateway_backends
from moto.autoscaling import autoscaling_backends
from moto.awslambda import lambda_backends
from moto.cloudformation import cloudformation_backends
from moto.cloudwatch import cloudwatch_backends
from moto.core import moto_api_backends
from moto.datapipeline import datapipeline_backends
from moto.dynamodb import dynamodb_backends
from moto.dynamodb2 import dynamodb_backends2
from moto.ec2 import ec2_backends
from moto.ecr import ecr_backends
from moto.ecs import ecs_backends
from moto.elb import elb_backends
from moto.emr import emr_backends
from moto.events import events_backends
from moto.glacier import glacier_backends
from moto.iam import iam_backends
from moto.instance_metadata import instance_metadata_backends
from moto.kinesis import kinesis_backends
from moto.kms import kms_backends
from moto.opsworks import opsworks_backends
from moto.rds2 import rds2_backends
from moto.redshift import redshift_backends
from moto.route53 import route53_backends
from moto.s3 import s3_backends
from moto.ses import ses_backends
from moto.sns import sns_backends
from moto.sqs import sqs_backends
from moto.ssm import ssm_backends
from moto.sts import sts_backends

BACKENDS = {
    'apigateway': apigateway_backends,
    'autoscaling': autoscaling_backends,
    'cloudformation': cloudformation_backends,
    'cloudwatch': cloudwatch_backends,
    'datapipeline': datapipeline_backends,
    'dynamodb': dynamodb_backends,
    'dynamodb2': dynamodb_backends2,
    'ec2': ec2_backends,
    'ecr': ecr_backends,
    'ecs': ecs_backends,
    'elb': elb_backends,
    'events': events_backends,
    'emr': emr_backends,
    'glacier': glacier_backends,
    'iam': iam_backends,
    'moto_api': moto_api_backends,
    'instance_metadata': instance_metadata_backends,
    'opsworks': opsworks_backends,
    'kinesis': kinesis_backends,
    'kms': kms_backends,
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
    'lambda': lambda_backends,
}


def get_model(name, region_name):
    for backends in BACKENDS.values():
        for region, backend in backends.items():
            if region == region_name:
                models = getattr(backend.__class__, '__models__', {})
                if name in models:
                    return list(getattr(backend, models[name])())
