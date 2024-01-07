import boto3
import requests

from moto import mock_aws, settings


@mock_aws
def test_set_findings():
    base_url = (
        "localhost:5000" if settings.TEST_SERVER_MODE else "motoapi.amazonaws.com"
    )

    findings = {
        "results": [
            [
                {
                    "awsAccountId": "111122223333",
                    "codeVulnerabilityDetails": {"cwes": ["a"], "detectorId": ".."},
                }
            ]
        ],
        "region": "us-west-1",
    }
    resp = requests.post(
        f"http://{base_url}/moto-api/static/inspector2/findings-results",
        json=findings,
    )
    assert resp.status_code == 201

    inspector2 = boto3.client("inspector2", region_name="us-west-1")

    assert inspector2.list_findings()["findings"] == [
        {
            "awsAccountId": "111122223333",
            "codeVulnerabilityDetails": {
                "cwes": ["a"],
                "detectorId": "..",
            },
        }
    ]

    # Calling list_findings with different arguments returns an empty list
    assert (
        inspector2.list_findings(
            filterCriteria={"awsAccountId": [{"comparison": "EQUALS", "value": "x"}]}
        )["findings"]
        == []
    )

    # Calling list_findings with original arguments returns original list
    assert inspector2.list_findings()["findings"] == [
        {
            "awsAccountId": "111122223333",
            "codeVulnerabilityDetails": {
                "cwes": ["a"],
                "detectorId": "..",
            },
        }
    ]
