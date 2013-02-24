import logging
logging.getLogger('boto').setLevel(logging.CRITICAL)

from .dynamodb import mock_dynamodb
from .ec2 import mock_ec2
from .s3 import mock_s3
from .sqs import mock_sqs
