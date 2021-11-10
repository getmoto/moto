import pytest
from moto.dynamodb2.models import Table


@pytest.fixture
def table():
    return Table(
        "Forums",
        schema=[
            {"KeyType": "HASH", "AttributeName": "forum_name"},
            {"KeyType": "RANGE", "AttributeName": "subject"},
        ],
        attr=[
            {"AttributeType": "S", "AttributeName": "forum_name"},
            {"AttributeType": "S", "AttributeName": "subject"},
        ],
    )
