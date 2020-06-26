# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import boto3
import sure  # noqa

from moto import mock_sagemaker, mock_iam

@mock_sagemaker
@mock_iam
def test_create_notebook_instance():

    iam = boto3.client("iam", region_name="us-east-1")
    exec_role = iam.create_role(
        RoleName="execution-role",
        AssumeRolePolicyDocument="some policy"
    )["Role"]

    sagemaker = boto3.client("sagemaker", region_name="us-east-1")

    args = {
        "NotebookInstanceName": "MyNotebookInstance",
        "InstanceType": "ml.t2.medium",
        "RoleArn": exec_role["Arn"]
    }
    resp = sagemaker.create_notebook_instance(**args)

