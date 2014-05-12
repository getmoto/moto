import logging
logging.getLogger('boto').setLevel(logging.CRITICAL)

from .autoscaling import mock_autoscaling
from .cloudformation import mock_cloudformation
from .dynamodb import mock_dynamodb
from .dynamodb2 import mock_dynamodb2
from .ec2 import mock_ec2
from .elb import mock_elb
from .emr import mock_emr
from .iam import mock_iam
from .s3 import mock_s3
from .s3bucket_path import mock_s3bucket_path
from .ses import mock_ses
from .sns import mock_sns
from .sqs import mock_sqs
from .sts import mock_sts
from .route53 import mock_route53
