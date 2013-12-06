from moto.autoscaling import autoscaling_backend
from moto.dynamodb import dynamodb_backend
from moto.ec2 import ec2_backend
from moto.elb import elb_backend
from moto.emr import emr_backend
from moto.s3 import s3_backend
from moto.s3bucket_path import s3bucket_path_backend
from moto.ses import ses_backend
from moto.sqs import sqs_backend
from moto.sts import sts_backend
from moto.route53 import route53_backend

BACKENDS = {
    'autoscaling': autoscaling_backend,
    'dynamodb': dynamodb_backend,
    'ec2': ec2_backend,
    'elb': elb_backend,
    'emr': emr_backend,
    's3': s3_backend,
    's3bucket_path': s3bucket_path_backend,
    'ses': ses_backend,
    'sqs': sqs_backend,
    'sts': sts_backend,
    'route53': route53_backend
}
