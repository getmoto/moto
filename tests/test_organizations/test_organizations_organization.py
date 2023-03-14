from datetime import datetime

import boto3
import pytest
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from moto import mock_organizations
from moto.core import DEFAULT_ACCOUNT_ID
from moto.organizations import utils
from .helpers import MatchingRegex, boto_response


class TestOrganizationBasicCRUD:
    @mock_organizations
    @pytest.mark.parametrize(
        "kwargs,expected_feature_set",
        (
            ({}, "ALL"),
            ({"FeatureSet": "ALL"}, "ALL"),
            ({"FeatureSet": "CONSOLIDATED_BILLING"}, "CONSOLIDATED_BILLING"),
        ),
    )
    def test_create_organization(
        self, kwargs: dict[str, str], expected_feature_set: str
    ):
        client = boto3.client("organizations", region_name="us-east-1")
        org = client.create_organization(**kwargs)["Organization"]

        assert sorted(org.keys()) == sorted(
            [
                "Arn",
                "AvailablePolicyTypes",
                "FeatureSet",
                "Id",
                "MasterAccountArn",
                "MasterAccountEmail",
                "MasterAccountId",
            ]
        )
        assert org["Id"] == MatchingRegex(utils.ORG_ID_REGEX)
        assert org["Arn"] == (
            utils.ORGANIZATION_ARN_FORMAT.format(org["MasterAccountId"], org["Id"])
        )
        assert org["MasterAccountId"] == DEFAULT_ACCOUNT_ID
        assert org["MasterAccountArn"] == (
            utils.MASTER_ACCOUNT_ARN_FORMAT.format(org["MasterAccountId"], org["Id"])
        )
        assert org["MasterAccountEmail"] == utils.MASTER_ACCOUNT_EMAIL
        assert org["AvailablePolicyTypes"] == (
            [{"Type": "SERVICE_CONTROL_POLICY", "Status": "ENABLED"}]
        )
        assert org["FeatureSet"] == expected_feature_set

    @pytest.mark.usefixtures("created_organization")
    def test_create_organization_creates_master_account(self, client: BaseClient):
        accounts = client.list_accounts()["Accounts"]

        assert len(accounts) == 1
        assert accounts[0]["Name"] == "master"
        assert accounts[0]["Id"] == DEFAULT_ACCOUNT_ID
        assert accounts[0]["Email"] == utils.MASTER_ACCOUNT_EMAIL

    @pytest.mark.usefixtures("created_organization")
    def test_create_organization_creates_policy(self, client: BaseClient):
        policies = client.list_policies(Filter="SERVICE_CONTROL_POLICY")["Policies"]

        assert len(policies) == 1
        assert policies[0]["Name"] == "FullAWSAccess"
        assert policies[0]["Id"] == utils.DEFAULT_POLICY_ID
        assert policies[0]["AwsManaged"] is True

        targets = client.list_targets_for_policy(PolicyId=policies[0]["Id"])["Targets"]
        root_targets = [target for target in targets if target["Type"] == "ROOT"]
        account_targets = [target for target in targets if target["Type"] == "ACCOUNT"]

        assert len(targets) == 2
        assert len(root_targets) == 1
        assert root_targets[0]["Name"] == "Root"
        assert len(account_targets) == 1
        assert account_targets[0]["Name"] == "master"

    def test_describe_organization(self, client: BaseClient):
        created = client.create_organization(FeatureSet="CONSOLIDATED_BILLING")[
            "Organization"
        ]

        described = client.describe_organization()["Organization"]

        assert described == created

    def test_describe_organization_never_created(self, client: BaseClient):
        with pytest.raises(ClientError) as e:
            client.describe_organization()
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DescribeOrganization"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "AWSOrganizationsNotInUseException"
        assert error["Message"] == "Your account is not a member of an organization."

    @pytest.mark.usefixtures("created_organization")
    def test_describe_deleted_organization(self, client: BaseClient):
        client.delete_organization()

        with pytest.raises(ClientError) as e:
            client.describe_organization()
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DescribeOrganization"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "AWSOrganizationsNotInUseException"
        assert error["Message"] == "Your account is not a member of an organization."

    @pytest.mark.usefixtures("created_organization")
    def test_list_roots(self, client: BaseClient, dummy_organization):
        roots = client.list_roots()["Roots"]

        assert len(roots) == 1
        assert roots[0]["Id"] == MatchingRegex(utils.ROOT_ID_REGEX)
        assert roots[0]["Arn"] == (
            utils.ROOT_ARN_FORMAT.format(
                dummy_organization["MasterAccountId"],
                dummy_organization["Id"],
                roots[0]["Id"],
            )
        )
        assert roots[0]["Name"] == "Root"
        assert len(roots[0]["PolicyTypes"]) == 0

    @pytest.mark.usefixtures("created_organization")
    def test_delete_organization(self, client: BaseClient):
        response = client.delete_organization()

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    @pytest.mark.usefixtures("created_organization", "dummy_account")
    def test_delete_organization_with_existing_account(self, client: BaseClient):
        with pytest.raises(ClientError) as e:
            client.delete_organization()
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DeleteOrganization"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "400"
        assert "OrganizationNotEmptyException" in error["Message"]
        assert (
            "To delete an organization you must first remove all member accounts (except the master)."
            in error["Message"]
        )

    @pytest.mark.usefixtures("created_organization")
    def test_delete_organization_with_existing_account_procedure(
        self, client: BaseClient, dummy_account: boto_response
    ):
        account_id = dummy_account["Id"]

        client.remove_account_from_organization(AccountId=account_id)
        response = client.delete_organization()

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


class TestOrganizationServiceAccess:
    @pytest.mark.usefixtures("created_organization")
    def test_enable_aws_service_access(
        self, client: BaseClient, known_service_principal: str
    ):
        response = client.enable_aws_service_access(
            ServicePrincipal=known_service_principal
        )
        enabled = client.list_aws_service_access_for_organization()[
            "EnabledServicePrincipals"
        ]

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        assert len(enabled) == 1

    @pytest.mark.usefixtures("created_organization")
    def test_enable_aws_service_access_again(
        self, client: BaseClient, known_service_principal: str
    ):
        client.enable_aws_service_access(ServicePrincipal=known_service_principal)
        enabled = client.list_aws_service_access_for_organization()[
            "EnabledServicePrincipals"
        ]

        client.enable_aws_service_access(ServicePrincipal=known_service_principal)
        enabled_again = client.list_aws_service_access_for_organization()[
            "EnabledServicePrincipals"
        ]
        assert len(enabled_again) == 1
        assert enabled_again == enabled

    @pytest.mark.usefixtures("created_organization")
    def test_enable_aws_service_access_unknown(
        self, client: BaseClient, unknown_service_principal: str
    ):
        with pytest.raises(ClientError) as e:
            client.enable_aws_service_access(ServicePrincipal=unknown_service_principal)
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "EnableAWSServiceAccess"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == "You specified an unrecognized service principal."

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize(
        "service_principals",
        (("config.amazonaws.com", "ram.amazonaws.com"),),
    )
    def test_list_aws_service_access(
        self, client: BaseClient, service_principals: list[str]
    ):
        for service_principal in service_principals:
            client.enable_aws_service_access(ServicePrincipal=service_principal)
        enabled = client.list_aws_service_access_for_organization()[
            "EnabledServicePrincipals"
        ]

        assert len(enabled) == len(service_principals)
        for i in range(len(service_principals)):
            assert enabled[i]["ServicePrincipal"] == service_principals[i]
            assert isinstance(enabled[i]["DateEnabled"], datetime)

    @pytest.mark.usefixtures("created_organization")
    def test_disable_aws_service_access(
        self, client: BaseClient, known_service_principal: str
    ):
        client.enable_aws_service_access(ServicePrincipal=known_service_principal)

        client.disable_aws_service_access(ServicePrincipal=known_service_principal)
        response = client.list_aws_service_access_for_organization()

        assert len(response["EnabledServicePrincipals"]) == 0

        client.disable_aws_service_access(ServicePrincipal=known_service_principal)
        response_again = client.list_aws_service_access_for_organization()

        assert len(response_again["EnabledServicePrincipals"]) == 0

    @pytest.mark.usefixtures("created_organization")
    def test_disable_aws_service_access_unknown(
        self, client: BaseClient, unknown_service_principal: str
    ):
        with pytest.raises(ClientError) as e:
            client.disable_aws_service_access(
                ServicePrincipal=unknown_service_principal
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DisableAWSServiceAccess"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == "You specified an unrecognized service principal."
