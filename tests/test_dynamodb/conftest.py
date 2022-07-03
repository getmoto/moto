import pytest
from moto.core import DEFAULT_ACCOUNT_ID
from moto.dynamodb.models import Table


@pytest.fixture
def table():
    return Table(
        "Forums",
        account_id=DEFAULT_ACCOUNT_ID,
        region="us-east-1",
        schema=[
            {"KeyType": "HASH", "AttributeName": "forum_name"},
            {"KeyType": "RANGE", "AttributeName": "subject"},
        ],
        attr=[
            {"AttributeType": "S", "AttributeName": "forum_name"},
            {"AttributeType": "S", "AttributeName": "subject"},
        ],
    )
