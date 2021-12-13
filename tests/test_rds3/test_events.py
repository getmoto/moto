from __future__ import unicode_literals

import boto3
from botocore.exceptions import ClientError

from . import mock_rds
from sure import this


@mock_rds
def test_cannot_specify_source_identifier_without_source_type():
    client = boto3.client("rds", region_name="us-west-2")
    client.describe_events.when.called_with(
        SourceIdentifier="test-identifier"
    ).should.throw(ClientError, "Cannot specify source identifier without source type")
