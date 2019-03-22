# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError
from functools import wraps
from gzip import GzipFile
from io import BytesIO
import zlib
import pickle

import json
import boto
import boto3
from botocore.client import ClientError
import botocore.exceptions
from botocore.handlers import disable_signing
from freezegun import freeze_time
import six
import requests
import tests.backport_assert_raises  # noqa
from nose.tools import assert_raises
from moto import mock_sagemaker
import sure  # noqa

from moto.sagemaker.models import Model
from moto.sagemaker.models import Container

@mock_sagemaker
def test_describe_model():

    client = boto3.client('sagemaker', region_name='us-east-1')
    test_model = MySageMakerModel('blah', 'blah')
    test_model.save
    model = client.describe_model('blah')
    assert model.get('ModelName') == 'blah'

@mock_sagemaker
def test_create_model():
    client = boto3.client('sagemaker', region_name='us-east-1')
    container = Container("localhost", "none", None, None, None)
    model = Model(
        'blah', 'arn:blah', 
        container
    )
    client.create_model(model.response_object)

class MySageMakerModel(object):

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def save(self):
        sagemaker = boto3.client('sagemaker', region_name='us-east-1')
        container = Container("localhost", self.value, None, None, None)
        model = Model(
            self.name, 
            'arn:blah', 
            container
        )
        sagemaker.create_model(model.__dict__)