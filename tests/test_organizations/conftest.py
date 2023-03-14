import json

import boto3
import pytest
from botocore.client import BaseClient

from moto import mock_organizations
from tests.test_organizations.helpers import boto_response, boto_factory


@pytest.fixture()
def client() -> BaseClient:
    with mock_organizations():
        yield boto3.client("organizations", region_name="us-east-1")


@pytest.fixture()
@pytest.mark.usefixtures("created_organization")
def dummy_organization(
    client: BaseClient,  # pylint: disable=redefined-outer-name
) -> boto_response:
    return client.describe_organization()["Organization"]


@pytest.fixture()
def dummy_name() -> str:
    return "dummy-name"


@pytest.fixture()
def dummy_email(dummy_name: str) -> str:  # pylint: disable=redefined-outer-name
    return f"{dummy_name}@moto-example.invalid"


@pytest.fixture()
def created_organization(
    client: BaseClient,  # pylint: disable=redefined-outer-name
) -> boto_response:
    return client.create_organization(FeatureSet="ALL")


@pytest.fixture()
@pytest.mark.usefixtures("created_organization")
def root_id_dummy_organization(
    client: BaseClient,  # pylint: disable=redefined-outer-name
) -> str:
    return client.list_roots()["Roots"][0]["Id"]


@pytest.fixture()
@pytest.mark.usefixtures("created_organization")
def root_dummy_organization(
    client: BaseClient,  # pylint: disable=redefined-outer-name
) -> str:
    return client.list_roots()["Roots"][0]


@pytest.fixture()
def dummy_ou(
    client: BaseClient,  # pylint: disable=redefined-outer-name
    created_dummy_ou: boto_response,  # pylint: disable=redefined-outer-name
) -> boto_response:
    return client.describe_organizational_unit(
        OrganizationalUnitId=created_dummy_ou["OrganizationalUnit"]["Id"]
    )["OrganizationalUnit"]


@pytest.fixture()
def created_dummy_ou(
    ou_factory: boto_factory,  # pylint: disable=redefined-outer-name
) -> boto_response:
    return ou_factory(1)[0]


@pytest.fixture()
@pytest.mark.usefixtures("created_organization")
def ou_factory(
    client: BaseClient,  # pylint: disable=redefined-outer-name
    root_id_dummy_organization: str,  # pylint: disable=redefined-outer-name
    dummy_name: str,  # pylint: disable=redefined-outer-name
) -> boto_factory:
    def factory(qty: int = 1) -> list[boto_response]:
        return [
            client.create_organizational_unit(
                ParentId=root_id_dummy_organization, Name=f"{dummy_name}-ou-{i}"
            )
            for i in range(qty)
        ]

    return factory


@pytest.fixture()
def dummy_account(
    client: BaseClient,  # pylint: disable=redefined-outer-name
    created_dummy_account: boto_response,  # pylint: disable=redefined-outer-name
) -> boto_response:
    return client.describe_account(
        AccountId=created_dummy_account["CreateAccountStatus"]["AccountId"]
    )["Account"]


@pytest.fixture()
def created_dummy_account(
    account_factory: boto_factory,  # pylint: disable=redefined-outer-name
) -> boto_response:
    return account_factory(1)[0]


@pytest.fixture()
@pytest.mark.usefixtures("created_organization")
def account_factory(
    client: BaseClient,  # pylint: disable=redefined-outer-name
    dummy_name: str,  # pylint: disable=redefined-outer-name
) -> boto_factory:
    def factory(qty: int = 1) -> list[boto_response]:
        return [
            client.create_account(
                AccountName=f"{dummy_name}-{i}",
                Email=f"{dummy_name}-{i}@moto-example.invalid",
            )
            for i in range(qty)
        ]

    return factory


@pytest.fixture()
def known_service_principal() -> str:
    return "ssm.amazonaws.com"


@pytest.fixture()
def known_service_principals() -> list[str]:
    return ["guardduty.amazonaws.com", "ssm.amazonaws.com"]


@pytest.fixture()
def unknown_service_principal() -> str:
    return "moto.amazonaws.com"


@pytest.fixture()
def known_policy_type():
    return "AISERVICES_OPT_OUT_POLICY"


@pytest.fixture()
def dummy_policy(
    client: BaseClient,  # pylint: disable=redefined-outer-name
    created_dummy_policy: boto_response,  # pylint: disable=redefined-outer-name
) -> boto_response:
    return client.describe_policy(PolicyId=created_dummy_policy["PolicySummary"]["Id"])[
        "Policy"
    ]


@pytest.fixture()
def created_dummy_policy(
    policy_factory: boto_factory,  # pylint: disable=redefined-outer-name
) -> boto_response:
    return policy_factory(1)[0]["Policy"]


@pytest.fixture()
def policy_factory(
    client: BaseClient,  # pylint: disable=redefined-outer-name
    policy_config_factory: boto_factory,  # pylint: disable=redefined-outer-name
) -> boto_factory:
    def factory(qty: int = 1) -> list[boto_response]:
        return [client.create_policy(**config) for config in policy_config_factory(qty)]

    return factory


@pytest.fixture()
def dummy_policy_config(
    policy_config_factory: boto_factory,  # pylint: disable=redefined-outer-name
) -> boto_response:
    return policy_config_factory(1)[0]


@pytest.fixture()
def policy_config_factory(
    dummy_policy_content: str,  # pylint: disable=redefined-outer-name
) -> boto_factory:
    def factory(qty: int = 1) -> list[boto_response]:
        return [
            dict(
                Content=dummy_policy_content,
                Description="A dummy service control policy",
                Name=f"MockServiceControlPolicy-{i}",
                Type="SERVICE_CONTROL_POLICY",
            )
            for i in range(qty)
        ]

    return factory


@pytest.fixture()
def dummy_policy_content() -> str:
    return json.dumps(
        dict(
            Version="2012-10-17",
            Statement=[
                dict(
                    Sid="MockPolicyStatement",
                    Effect="Allow",
                    Action="s3:*",
                    Resource="*",
                )
            ],
        )
    )
