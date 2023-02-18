"""Unit tests for identitystore-supported APIs."""
from uuid import UUID

import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_identitystore


# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_identitystore
def test_create_group():
    client = boto3.client("identitystore", region_name="ap-southeast-1")
    identity_store_id = "d-9067028cf5"
    create_resp = client.create_group(
        IdentityStoreId=identity_store_id,
        DisplayName="test_group",
        Description="description",
    )
    assert create_resp["IdentityStoreId"] == identity_store_id
    assert UUID(create_resp["GroupId"])
