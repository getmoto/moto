from __future__ import unicode_literals

import logging

# Disable extra logging for tests
logging.getLogger("boto").setLevel(logging.CRITICAL)
logging.getLogger("boto3").setLevel(logging.CRITICAL)
logging.getLogger("botocore").setLevel(logging.CRITICAL)


EXAMPLE_AMI_ID = "ami-12c6146b"
EXAMPLE_AMI_ID2 = "ami-03cf127a"
