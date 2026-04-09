import boto3
import pytest

from moto import mock_aws


@mock_aws
def test_list_release_labels():
    client = boto3.client("emr", "us-east-1")

    release_labels = client.list_release_labels()["ReleaseLabels"]
    assert len(release_labels) > 10
    for label in release_labels:
        # The exact label is dynamic, but they all start with emr-
        # (emr-7.9.0, emr-7.8.0, etc.)
        assert label.startswith("emr-")


@mock_aws
@pytest.mark.parametrize("region", ["us-east-1", "us-east-2", "eu-central-1"])
def test_list_supported_instance_types(region):
    client = boto3.client("emr", region)

    release_label = client.list_release_labels()["ReleaseLabels"][0]

    instance_types = client.list_supported_instance_types(ReleaseLabel=release_label)[
        "SupportedInstanceTypes"
    ]
    # Instance types are dynamic, so we can't be sure how many there are
    assert len(instance_types) > 10

    # We also can't be sure about the exact values - but we do know that these values should be present
    for instance_type in instance_types:
        assert instance_type["Type"]
        assert "MemoryGB" in instance_type
        assert "StorageGB" in instance_type
