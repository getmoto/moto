#!/usr/bin/env python
# This updates our local copies of AWS' managed policies
# Invoked via `make update_managed_policies`
#
# Credit goes to
#   https://gist.github.com/gene1wood/55b358748be3c314f956

from botocore.exceptions import NoCredentialsError
from datetime import datetime
import boto3
import json
import sys

output_file = "./moto/iam/aws_managed_policies.py"


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")


client = boto3.client('iam')

policies = {}

paginator = client.get_paginator('list_policies')
try:
    response_iterator = paginator.paginate(Scope='AWS')
    for response in response_iterator:
        for policy in response['Policies']:
            policies[policy['PolicyName']] = policy
except NoCredentialsError:
    print("USAGE:")
    print("Put your AWS credentials into ~/.aws/credentials and run:")
    print(__file__)
    print("")
    print("Or specify them on the command line:")
    print("AWS_ACCESS_KEY_ID=your_personal_access_key AWS_SECRET_ACCESS_KEY=your_personal_secret {}".format(__file__))
    print("")
    sys.exit(1)

for policy_name in policies:
    response = client.get_policy_version(
        PolicyArn=policies[policy_name]['Arn'],
        VersionId=policies[policy_name]['DefaultVersionId'])
    for key in response['PolicyVersion']:
        if key != "CreateDate":  # the policy's CreateDate should not be overwritten by its version's CreateDate
            policies[policy_name][key] = response['PolicyVersion'][key]

with open(output_file, 'w') as f:
    triple_quote = '\"\"\"'

    f.write("# Imported via `make aws_managed_policies`\n")
    f.write('aws_managed_policies_data = {}\n'.format(triple_quote))
    f.write(json.dumps(policies,
                     sort_keys=True,
                     indent=4,
                     separators=(',', ': '),
                     default=json_serial))
    f.write('{}\n'.format(triple_quote))
