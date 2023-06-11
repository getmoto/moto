import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_appconfig


@mock_appconfig
class TestHostedConfigurationVersions:
    def setup_method(self, *args):  # pylint: disable=unused-argument
        self.client = boto3.client("appconfig", region_name="us-west-1")
        self.app_id = self.client.create_application(Name="testapp")["Id"]
        self.config_profile_id = self.client.create_configuration_profile(
            ApplicationId=self.app_id,
            Name="config_name",
            Description="desc",
            LocationUri="luri",
            RetrievalRoleArn="rrarn:rrarn:rrarn:rrarn",
            Validators=[{"Type": "JSON", "Content": "c"}],
            Type="freeform",
        )["Id"]

    def test_create_hosted_configuration_version(self):
        resp = self.client.create_hosted_configuration_version(
            ApplicationId=self.app_id,
            ConfigurationProfileId=self.config_profile_id,
            Description="desc",
            Content=b"asdf",
            ContentType="text/xml",
            VersionLabel="vl",
        )
        assert resp["ApplicationId"] == self.app_id
        assert resp["ConfigurationProfileId"] == self.config_profile_id
        assert resp["VersionNumber"] == 1
        assert resp["Description"] == "desc"
        assert resp["VersionLabel"] == "vl"
        assert resp["ContentType"] == "text/xml"
        assert resp["Content"].read() == b"asdf"

        resp = self.client.create_hosted_configuration_version(
            ApplicationId=self.app_id,
            ConfigurationProfileId=self.config_profile_id,
            Content=b"asdf",
            ContentType="text/xml",
        )
        assert resp["VersionNumber"] == 2

    def test_get_hosted_configuration_version(self):
        self.client.create_hosted_configuration_version(
            ApplicationId=self.app_id,
            ConfigurationProfileId=self.config_profile_id,
            Description="desc",
            Content=b"asdf",
            ContentType="text/xml",
            VersionLabel="vl",
        )
        get = self.client.get_hosted_configuration_version(
            ApplicationId=self.app_id,
            ConfigurationProfileId=self.config_profile_id,
            VersionNumber=1,
        )
        assert get["ApplicationId"] == self.app_id
        assert get["ConfigurationProfileId"] == self.config_profile_id
        assert get["Description"] == "desc"
        assert get["VersionLabel"] == "vl"
        assert get["ContentType"] == "text/xml"
        assert get["Content"].read() == b"asdf"

    def test_delete_hosted_configuration_version(self):
        self.client.create_hosted_configuration_version(
            ApplicationId=self.app_id,
            ConfigurationProfileId=self.config_profile_id,
            Content=b"asdf",
            ContentType="text/xml",
        )
        self.client.delete_hosted_configuration_version(
            ApplicationId=self.app_id,
            ConfigurationProfileId=self.config_profile_id,
            VersionNumber=1,
        )
        with pytest.raises(ClientError) as exc:
            self.client.get_hosted_configuration_version(
                ApplicationId=self.app_id,
                ConfigurationProfileId=self.config_profile_id,
                VersionNumber=1,
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
