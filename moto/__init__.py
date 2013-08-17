import logging
logging.getLogger('boto').setLevel(logging.CRITICAL)

from .autoscaling import mock_autoscaling
from .cloudwatch import mock_cloudwatch
from .dynamodb import mock_dynamodb
from .ec2 import mock_ec2
from .elb import mock_elb
from .emr import mock_emr
from .s3 import mock_s3
from .ses import mock_ses
from .sqs import mock_sqs
from .sts import mock_sts
