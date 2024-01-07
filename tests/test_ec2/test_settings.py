import boto3

from moto import mock_aws


@mock_aws
def test_disable_ebs_encryption_by_default():
    ec2 = boto3.client("ec2", "eu-central-1")

    ec2.enable_ebs_encryption_by_default()
    response = ec2.get_ebs_encryption_by_default()
    assert response["EbsEncryptionByDefault"] is True

    ec2.disable_ebs_encryption_by_default()
    after_disable_response = ec2.get_ebs_encryption_by_default()
    assert after_disable_response["EbsEncryptionByDefault"] is False


@mock_aws
def test_enable_ebs_encryption_by_default():
    ec2 = boto3.client("ec2", region_name="eu-central-1")
    response = ec2.enable_ebs_encryption_by_default()

    ec2.get_ebs_encryption_by_default()
    assert response["EbsEncryptionByDefault"] is True


@mock_aws
def test_get_ebs_encryption_by_default():
    ec2 = boto3.client("ec2", region_name="eu-west-1")

    response = ec2.get_ebs_encryption_by_default()
    assert response["EbsEncryptionByDefault"] is False


@mock_aws
def test_enable_ebs_encryption_by_default_region():
    ec2_eu = boto3.client("ec2", region_name="eu-central-1")
    ec2_eu.enable_ebs_encryption_by_default()

    response = ec2_eu.get_ebs_encryption_by_default()
    assert response["EbsEncryptionByDefault"] is True

    ec2_us = boto3.client("ec2", region_name="us-east-1")
    response = ec2_us.get_ebs_encryption_by_default()
    assert response["EbsEncryptionByDefault"] is False
