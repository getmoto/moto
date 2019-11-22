from datetime import datetime

import boto3
from moto import mock_meteringmarketplace


@mock_meteringmarketplace()
def test_batch_meter_usage():
    client = boto3.client("meteringmarketplace", region_name="us-east-1")

    res = client.batch_meter_usage(
        UsageRecords=[
            {
                "Timestamp": datetime(2015, 1, 1),
                "CustomerIdentifier": "string",
                "Dimension": "string",
                "Quantity": 123,
            }
        ],
        ProductCode="string",
    )

    for record in res["Results"]:
        ...

    for record in res["UnprocessedRecords"]:
        ...
