import copy
from datetime import datetime

import boto3

from moto import mock_meteringmarketplace
from moto.meteringmarketplace.models import Result


USAGE_RECORDS = [
    {
        "Timestamp": datetime(2019, 8, 25, 21, 1, 38),
        "CustomerIdentifier": "EqCDbVpkMBaQzPQv",
        "Dimension": "HIDaByYzIxgGZqyz",
        "Quantity": 6984,
    },
    {
        "Timestamp": datetime(2019, 9, 7, 16, 4, 47),
        "CustomerIdentifier": "ITrDnpWEiebXybRJ",
        "Dimension": "BSWatHqyhbyTQHCS",
        "Quantity": 6388,
    },
    {
        "Timestamp": datetime(2019, 6, 15, 23, 17, 49),
        "CustomerIdentifier": "YfzTVRheDsXEehgQ",
        "Dimension": "FsVxwLkTAynaWwGT",
        "Quantity": 3532,
    },
    {
        "Timestamp": datetime(2019, 9, 10, 19, 56, 35),
        "CustomerIdentifier": "kmgmFPcWhpDGSSDm",
        "Dimension": "PBXGdBHQWVOwudRK",
        "Quantity": 9897,
    },
    {
        "Timestamp": datetime(2019, 1, 12, 1, 28, 36),
        "CustomerIdentifier": "OyxECDjaaDVUeQIB",
        "Dimension": "VzwLdmFjbTBBbHJg",
        "Quantity": 5142,
    },
    {
        "Timestamp": datetime(2019, 8, 5, 18, 27, 41),
        "CustomerIdentifier": "PkeNkaJVfceGvYAX",
        "Dimension": "mHTtIbsLAYrCVSNM",
        "Quantity": 6503,
    },
    {
        "Timestamp": datetime(2019, 7, 18, 3, 22, 18),
        "CustomerIdentifier": "ARzQRYYuXGHCVDkW",
        "Dimension": "RMjZbVpxehPTNtDL",
        "Quantity": 5465,
    },
    {
        "Timestamp": datetime(2019, 6, 24, 9, 19, 14),
        "CustomerIdentifier": "kzlvIayJzpyfBPaH",
        "Dimension": "MmsydkBEHERXDooi",
        "Quantity": 6135,
    },
    {
        "Timestamp": datetime(2019, 9, 28, 20, 29, 5),
        "CustomerIdentifier": "nygdXONtkiqktTMn",
        "Dimension": "GKbTFPMGRyZObEEz",
        "Quantity": 3416,
    },
    {
        "Timestamp": datetime(2019, 6, 17, 2, 5, 34),
        "CustomerIdentifier": "JlIGIXHHPphnBhfV",
        "Dimension": "dcBPhccyHYSdPUUO",
        "Quantity": 2184,
    },
]


@mock_meteringmarketplace()
def test_batch_meter_usage():
    client = boto3.client("meteringmarketplace", region_name="us-east-1")

    res = client.batch_meter_usage(
        UsageRecords=USAGE_RECORDS, ProductCode="PUFXZLyUElvQvrsG"
    )

    assert len(res["Results"]) == 10

    records_without_time = copy.copy(USAGE_RECORDS)
    for r in records_without_time:
        r.pop("Timestamp")

    for record in res["Results"]:
        record["UsageRecord"].pop("Timestamp")
        assert record["UsageRecord"] in records_without_time
        assert record["MeteringRecordId"]
        assert record["Status"] in [
            Result.DUPLICATE_RECORD,
            Result.CUSTOMER_NOT_SUBSCRIBED,
            Result.SUCCESS,
        ]
