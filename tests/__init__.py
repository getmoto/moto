import logging
import os


# Disable extra logging for tests
logging.getLogger("boto").setLevel(logging.CRITICAL)
logging.getLogger("boto3").setLevel(logging.CRITICAL)
logging.getLogger("botocore").setLevel(logging.CRITICAL)

# Sample pre-loaded Image Ids for use with tests.
# (Source: moto/ec2/resources/amis.json)
EXAMPLE_AMI_ID = "ami-12c6146b"
EXAMPLE_AMI_ID2 = "ami-03cf127a"
EXAMPLE_AMI_PARAVIRTUAL = "ami-fa7cdd89"
EXAMPLE_AMI_WINDOWS = "ami-f4cf1d8d"

DEFAULT_ACCOUNT_ID = "123456789012"

# For the majority of tests we don't need the default AMI's
os.environ["MOTO_EC2_LOAD_DEFAULT_AMIS"] = "false"
