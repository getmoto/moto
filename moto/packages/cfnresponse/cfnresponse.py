# Sourced from https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-lambda-function-code-cfnresponsemodule.html
# 01/Nov/2021

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from __future__ import print_function
import urllib3
import json

SUCCESS = "SUCCESS"
FAILED = "FAILED"

http = urllib3.PoolManager()


def send(
    event,
    context,
    responseStatus,
    responseData,
    physicalResourceId=None,
    noEcho=False,
    reason=None,
):
    responseUrl = event["ResponseURL"]

    print(responseUrl)

    responseBody = {
        "Status": responseStatus,
        "Reason": reason
        or "See the details in CloudWatch Log Stream: {}".format(
            context.log_stream_name
        ),
        "PhysicalResourceId": physicalResourceId or context.log_stream_name,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "NoEcho": noEcho,
        "Data": responseData,
    }

    json_responseBody = json.dumps(responseBody)

    print("Response body:")
    print(json_responseBody)

    headers = {"content-type": "", "content-length": str(len(json_responseBody))}

    try:
        response = http.request(
            "PUT", responseUrl, headers=headers, body=json_responseBody
        )
        print("Status code:", response.status)

    except Exception as e:

        print("send(..) failed executing http.request(..):", e)
