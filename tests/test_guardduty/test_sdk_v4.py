"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_guardduty import GuardDutyClient, GuardDutyConfig
    from aws_sdk_guardduty.models import BadRequestException
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-guardduty is not installed", allow_module_level=True)


@mock_aws
def test_threat_detection_setup():
    """Enable threat detection, trust the office network and auto-archive low-severity findings."""
    config = GuardDutyConfig.resolve(region="us-east-1")
    filter_name = f"archive-low-severity-{str(uuid4())[:8]}"

    with GuardDutyClient(config=config) as client:
        detector_id = client.create_detector(
            enable=True,
            finding_publishing_frequency="SIX_HOURS",
            data_sources={"s3_logs": {"enable": True}},
            tags={"team": "security"},
        ).detector_id
        assert detector_id in client.list_detectors().detector_ids

        client.update_detector(
            detector_id=detector_id, finding_publishing_frequency="FIFTEEN_MINUTES"
        )
        detector = client.get_detector(detector_id=detector_id)
        assert detector.status == "ENABLED"
        assert detector.finding_publishing_frequency == "FIFTEEN_MINUTES"
        assert detector.data_sources.s3_logs.status == "ENABLED"
        assert detector.tags == {"team": "security"}

        ip_set_id = client.create_ip_set(
            detector_id=detector_id,
            name="office-network",
            format="TXT",
            location="https://s3.amazonaws.com/security-config/trusted-ips.txt",
            activate=True,
        ).ip_set_id
        ip_set = client.get_ip_set(detector_id=detector_id, ip_set_id=ip_set_id)
        assert ip_set.name == "office-network"
        assert ip_set.format == "TXT"

        client.create_filter(
            detector_id=detector_id,
            name=filter_name,
            action="ARCHIVE",
            rank=1,
            finding_criteria={"criterion": {"severity": {"lt": 4}}},
        )
        client.update_filter(
            detector_id=detector_id,
            filter_name=filter_name,
            description="Archive findings with a low severity",
        )
        finding_filter = client.get_filter(
            detector_id=detector_id, filter_name=filter_name
        )
        assert finding_filter.action == "ARCHIVE"
        assert finding_filter.description == "Archive findings with a low severity"
        assert finding_filter.finding_criteria.criterion["severity"].lt == 4

        client.delete_detector(detector_id=detector_id)
        with pytest.raises(BadRequestException):
            client.get_detector(detector_id=detector_id)
