from datetime import datetime

import pytest
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from moto.core import DEFAULT_ACCOUNT_ID
from moto.organizations import utils
from .helpers import MatchingRegex, boto_response, boto_factory


class TestAccountBasicCRUD:
    @pytest.mark.usefixtures("created_organization")
    def test_create_account(
        self, client: BaseClient, dummy_name: str, dummy_email: str
    ):
        account = client.create_account(AccountName=dummy_name, Email=dummy_email)[
            "CreateAccountStatus"
        ]
        assert sorted(account.keys()) == sorted(
            [
                "AccountId",
                "AccountName",
                "CompletedTimestamp",
                "Id",
                "RequestedTimestamp",
                "State",
            ]
        )
        assert account["Id"] == MatchingRegex(utils.CREATE_ACCOUNT_STATUS_ID_REGEX)
        assert account["AccountId"] == MatchingRegex(utils.ACCOUNT_ID_REGEX)
        assert account["AccountName"] == dummy_name
        assert account["State"] == "SUCCEEDED"
        assert isinstance(account["RequestedTimestamp"], datetime)
        assert isinstance(account["CompletedTimestamp"], datetime)

    @pytest.mark.usefixtures("created_organization")
    def test_describe_create_account_status(
        self, client: BaseClient, dummy_name: str, dummy_email: str
    ):
        created = client.create_account(AccountName=dummy_name, Email=dummy_email)[
            "CreateAccountStatus"
        ]

        described = client.describe_create_account_status(
            CreateAccountRequestId=created["Id"]
        )["CreateAccountStatus"]

        assert described == created

    @pytest.mark.usefixtures("created_organization")
    def test_describe_account(
        self,
        client: BaseClient,
        dummy_organization: boto_response,
        dummy_name: str,
        dummy_email: str,
    ):
        created = client.create_account(AccountName=dummy_name, Email=dummy_email)[
            "CreateAccountStatus"
        ]

        described = client.describe_account(AccountId=created["AccountId"])["Account"]

        assert sorted(described.keys()) == sorted(
            ["Arn", "Email", "Id", "JoinedMethod", "JoinedTimestamp", "Name", "Status"]
        )
        assert described["Id"] == created["AccountId"]
        assert described["Arn"] == utils.ACCOUNT_ARN_FORMAT.format(
            dummy_organization["MasterAccountId"],
            dummy_organization["Id"],
            described["Id"],
        )
        assert described["Email"] == dummy_email
        assert described["JoinedMethod"] in ["INVITED", "CREATED"]
        assert described["Status"] in ["ACTIVE", "SUSPENDED"]
        assert described["Name"] == created["AccountName"]
        assert isinstance(described["JoinedTimestamp"], datetime)

    @pytest.mark.usefixtures("created_organization")
    def test_list_create_account_status_default(self, client: BaseClient):
        accounts = client.list_create_account_status()["CreateAccountStatuses"]

        assert len(accounts) == 1
        assert accounts[0]["AccountName"] == "master"
        assert accounts[0]["State"] == "SUCCEEDED"

    @pytest.mark.usefixtures("created_organization")
    def test_list_create_account_status(
        self, client: BaseClient, account_factory: boto_factory
    ):
        created = account_factory(2)
        accounts = client.list_create_account_status()["CreateAccountStatuses"]

        assert len(accounts) == len(created) + 1
        assert accounts[-1] == created[-1]["CreateAccountStatus"]

    @pytest.mark.usefixtures("created_organization")
    def test_list_create_account_status_succeeded(self, client: BaseClient):
        accounts = client.list_create_account_status(States=["SUCCEEDED"])[
            "CreateAccountStatuses"
        ]

        assert len(accounts) == 1

    @pytest.mark.usefixtures("created_organization")
    def test_list_create_account_status_in_progress(self, client: BaseClient):
        accounts = client.list_create_account_status(States=["IN_PROGRESS"])[
            "CreateAccountStatuses"
        ]

        assert len(accounts) == 0

    @pytest.mark.usefixtures("created_organization")
    def test_list_create_account_status_paginated(
        self, client: BaseClient, account_factory: boto_factory
    ):
        created = account_factory(5)
        max_results = 3

        response_first = client.list_create_account_status(MaxResults=max_results)
        accounts_first = response_first["CreateAccountStatuses"]

        assert len(accounts_first) == max_results
        assert response_first["NextToken"] is not None

        response_next = client.list_create_account_status(
            NextToken=(response_first["NextToken"])
        )
        accounts_next = response_next["CreateAccountStatuses"]
        accounts = accounts_first + accounts_next

        assert len(accounts) == len(created) + 1
        assert "NextToken" not in response_next

    @pytest.mark.usefixtures("created_organization")
    def test_list_accounts(self, client: BaseClient, account_factory: boto_factory):
        created = account_factory(25)

        response = client.list_accounts()
        accounts = response["Accounts"]

        assert "NextToken" not in response
        assert len(accounts) == len(created) + 1
        assert accounts[4]["Name"] == created[3]["CreateAccountStatus"]["AccountName"]

    @pytest.mark.usefixtures("created_organization")
    def test_list_accounts_pagination(
        self, client: BaseClient, account_factory: boto_factory
    ):
        created = account_factory(23)
        max_results = 5

        paginator = client.get_paginator("list_accounts")
        page_iterator = paginator.paginate(MaxResults=max_results)

        for page in page_iterator:
            assert len(page["Accounts"]) <= max_results
        assert (
            page["Accounts"][-1]["Name"]
            == created[-1]["CreateAccountStatus"]["AccountName"]
        )

    @pytest.mark.usefixtures("created_organization")
    def test_describe_account_not_existing(self, client: BaseClient):
        with pytest.raises(ClientError) as e:
            client.describe_account(AccountId=utils.make_random_account_id())
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DescribeAccount"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "AccountNotFoundException"
        assert error["Message"] == "You specified an account that doesn't exist."

    @pytest.mark.usefixtures("created_organization")
    def test_close_account_returns_nothing(
        self, client: BaseClient, dummy_account: boto_response
    ):
        response = client.close_account(AccountId=(dummy_account["Id"]))

        del response["ResponseMetadata"]
        assert response == {}

    @pytest.mark.usefixtures("created_organization")
    def test_close_account_puts_account_in_suspended_status(
        self, client: BaseClient, dummy_account: boto_response
    ):
        client.close_account(AccountId=(dummy_account["Id"]))
        account = client.describe_account(AccountId=(dummy_account["Id"]))["Account"]

        assert account["Status"] == "SUSPENDED"

    @pytest.mark.usefixtures("created_organization")
    def test_close_account_id_not_in_org_raises_exception(self, client: BaseClient):
        with pytest.raises(ClientError) as e:
            client.close_account(AccountId=(utils.make_random_account_id()))
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "CloseAccount"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "AccountNotFoundException"
        assert error["Message"] == "You specified an account that doesn't exist."

    @pytest.mark.usefixtures("created_organization")
    def test_remove_account_from_organization(
        self,
        client: BaseClient,
        dummy_account: boto_response,
    ):
        client.remove_account_from_organization(AccountId=(dummy_account["Id"]))

        accounts = client.list_accounts()["Accounts"]
        assert len(accounts) == 1
        assert accounts[0]["Id"] != dummy_account["Id"]


class TestAccountsWithOrganizationalUnits:
    @pytest.mark.usefixtures("created_organization")
    def test_list_accounts_for_parent(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        account_factory: boto_factory,
    ):
        created = account_factory(5)
        created_account_ids = [
            account["CreateAccountStatus"]["AccountId"] for account in created
        ]

        response = client.list_accounts_for_parent(ParentId=root_id_dummy_organization)
        accounts = response["Accounts"]
        account_ids = [account["Id"] for account in accounts]

        assert len(accounts) == len(created) + 1
        for account_id in created_account_ids:
            assert account_id in account_ids
        assert "NextToken" not in response

    @pytest.mark.usefixtures("created_organization")
    def test_list_accounts_for_parent_pagination(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        account_factory: boto_factory,
    ):
        created = account_factory(23)
        max_results = 5

        paginator = client.get_paginator("list_accounts_for_parent")
        page_iterator = paginator.paginate(
            MaxResults=max_results, ParentId=root_id_dummy_organization
        )

        for page in page_iterator:
            assert len(page["Accounts"]) <= max_results
        assert (
            page["Accounts"][-1]["Name"]
            == created[-1]["CreateAccountStatus"]["AccountName"]
        )

    @pytest.mark.usefixtures("created_organization")
    def test_list_parents_for_accounts(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        dummy_ou: boto_response,
        account_factory: boto_factory,
    ):
        created = account_factory(2)
        created_ids = [
            response["CreateAccountStatus"]["AccountId"] for response in created
        ]

        client.move_account(
            AccountId=created_ids[1],
            SourceParentId=root_id_dummy_organization,
            DestinationParentId=dummy_ou["Id"],
        )

        response_1 = client.list_parents(ChildId=created_ids[0])
        response_2 = client.list_parents(ChildId=created_ids[1])

        assert len(response_1["Parents"]) == 1
        assert response_1["Parents"][0]["Id"] == root_id_dummy_organization
        assert response_1["Parents"][0]["Type"] == "ROOT"

        assert len(response_2["Parents"]) == 1
        assert response_2["Parents"][0]["Id"] == dummy_ou["Id"]
        assert response_2["Parents"][0]["Type"] == "ORGANIZATIONAL_UNIT"

    @pytest.mark.usefixtures("created_organization")
    def test_move_account(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        dummy_ou: boto_response,
        dummy_account: boto_response,
    ):
        client.move_account(
            AccountId=dummy_account["Id"],
            SourceParentId=root_id_dummy_organization,
            DestinationParentId=dummy_ou["Id"],
        )
        root_response = client.list_accounts_for_parent(
            ParentId=root_id_dummy_organization
        )
        root_accounts = [account["Id"] for account in root_response["Accounts"]]
        ou_response = client.list_accounts_for_parent(ParentId=dummy_ou["Id"])
        ou_accounts = [account["Id"] for account in ou_response["Accounts"]]

        assert dummy_account["Id"] not in root_accounts
        assert dummy_account["Id"] in ou_accounts


class TestAccountDelegatedAdministrator:
    @pytest.mark.usefixtures("created_organization")
    def test_register_delegated_administrator(
        self, client: BaseClient, dummy_account: boto_response
    ):
        account_id = dummy_account["Id"]

        response = client.register_delegated_administrator(
            AccountId=account_id, ServicePrincipal="ssm.amazonaws.com"
        )

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        administrators = client.list_delegated_administrators()[
            "DelegatedAdministrators"
        ]

        assert len(administrators) == 1
        assert list(administrators[0].keys()) == list(dummy_account.keys()) + [
            "DelegationEnabledDate"
        ]
        for key in dummy_account.keys():
            assert administrators[0][key] == dummy_account[key]
        assert isinstance(administrators[0]["DelegationEnabledDate"], datetime)

    @pytest.mark.usefixtures("created_organization")
    def test_register_delegated_administrator_using_master(
        self, client: BaseClient, known_service_principal: str
    ):
        # when
        with pytest.raises(ClientError) as e:
            client.register_delegated_administrator(
                AccountId=DEFAULT_ACCOUNT_ID, ServicePrincipal=known_service_principal
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "RegisterDelegatedAdministrator"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "ConstraintViolationException"
        assert error["Message"] == (
            "You cannot register master account/yourself as delegated administrator for your organization."
        )

    @pytest.mark.usefixtures("created_organization")
    def test_register_delegated_administrator_uknown_account(
        self, client: BaseClient, known_service_principal: str
    ):
        with pytest.raises(ClientError) as e:
            client.register_delegated_administrator(
                AccountId=utils.make_random_account_id(),
                ServicePrincipal=known_service_principal,
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "RegisterDelegatedAdministrator"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "AccountNotFoundException"
        assert error["Message"] == "You specified an account that doesn't exist."

    @pytest.mark.usefixtures("created_organization")
    def test_register_delegated_administrator_unknown_service(
        self,
        client: BaseClient,
        dummy_account: boto_response,
        unknown_service_principal: str,
    ):
        with pytest.raises(ClientError) as e:
            client.register_delegated_administrator(
                AccountId=dummy_account["Id"],
                ServicePrincipal=unknown_service_principal,
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "RegisterDelegatedAdministrator"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == "You specified an unrecognized service principal."

    @pytest.mark.usefixtures("created_organization")
    def test_register_delegated_administrator_again(
        self,
        client: BaseClient,
        dummy_account: boto_response,
        known_service_principal: str,
    ):
        client.register_delegated_administrator(
            AccountId=dummy_account["Id"],
            ServicePrincipal=known_service_principal,
        )

        with pytest.raises(ClientError) as e:
            client.register_delegated_administrator(
                AccountId=dummy_account["Id"],
                ServicePrincipal=known_service_principal,
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "RegisterDelegatedAdministrator"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "AccountAlreadyRegisteredException"
        assert error["Message"] == (
            "The provided account is already a delegated administrator for your organization."
        )

    @pytest.mark.usefixtures("created_organization")
    def test_list_delegated_administrators(
        self,
        client: BaseClient,
        account_factory: boto_factory,
    ):
        created = account_factory(2)
        created_ids = [
            response["CreateAccountStatus"]["AccountId"] for response in created
        ]
        client.register_delegated_administrator(
            AccountId=created_ids[0], ServicePrincipal="ssm.amazonaws.com"
        )
        client.register_delegated_administrator(
            AccountId=created_ids[1], ServicePrincipal="guardduty.amazonaws.com"
        )

        administrators = client.list_delegated_administrators()[
            "DelegatedAdministrators"
        ]
        ssm_administrators = client.list_delegated_administrators(
            ServicePrincipal="ssm.amazonaws.com"
        )["DelegatedAdministrators"]

        assert len(administrators) == 2
        assert sorted([admin["Id"] for admin in administrators]) == sorted(created_ids)
        assert len(ssm_administrators) == 1
        assert ssm_administrators[0]["Id"] == created_ids[0]

    @pytest.mark.usefixtures("created_organization")
    def test_list_delegated_administrators_unknown_service(
        self, client: BaseClient, unknown_service_principal: str
    ):
        with pytest.raises(ClientError) as e:
            client.list_delegated_administrators(
                ServicePrincipal=unknown_service_principal
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "ListDelegatedAdministrators"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == "You specified an unrecognized service principal."

    @pytest.mark.usefixtures("created_organization")
    def test_list_delegated_services_for_account(
        self,
        client: BaseClient,
        dummy_account: boto_response,
        known_service_principals: list[str],
    ):
        account_id = dummy_account["Id"]
        for service_principal in known_service_principals:
            client.register_delegated_administrator(
                AccountId=account_id, ServicePrincipal=service_principal
            )

        delegated = client.list_delegated_services_for_account(AccountId=account_id)[
            "DelegatedServices"
        ]

        assert len(delegated) == len(known_service_principals)
        assert sorted([service["ServicePrincipal"] for service in delegated]) == sorted(
            known_service_principals
        )

    @pytest.mark.usefixtures("created_organization")
    def test_list_delegated_services_for_account_unknown_account(
        self, client: BaseClient
    ):
        with pytest.raises(ClientError) as e:
            client.list_delegated_services_for_account(
                AccountId=utils.make_random_account_id()
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "ListDelegatedServicesForAccount"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "AWSOrganizationsNotInUseException"
        assert error["Message"] == "Your account is not a member of an organization."

    @pytest.mark.usefixtures("created_organization")
    def test_list_delegated_services_for_unregistered_account(self, client: BaseClient):
        with pytest.raises(ClientError) as e:
            client.list_delegated_services_for_account(AccountId=DEFAULT_ACCOUNT_ID)
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "ListDelegatedServicesForAccount"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "AccountNotRegisteredException"
        assert error["Message"] == (
            "The provided account is not a registered delegated administrator for your organization."
        )

    @pytest.mark.usefixtures("created_organization")
    def test_deregister_delegated_administrator(
        self,
        client: BaseClient,
        dummy_account: boto_response,
        known_service_principal: str,
    ):
        client.register_delegated_administrator(
            AccountId=(dummy_account["Id"]), ServicePrincipal=known_service_principal
        )

        client.deregister_delegated_administrator(
            AccountId=(dummy_account["Id"]), ServicePrincipal=known_service_principal
        )
        administrators = client.list_delegated_administrators()[
            "DelegatedAdministrators"
        ]

        assert len(administrators) == 0

    @pytest.mark.usefixtures("created_organization")
    def test_deregister_delegated_administrator_master_account(
        self, client: BaseClient, known_service_principal: str
    ):
        with pytest.raises(ClientError) as e:
            client.deregister_delegated_administrator(
                AccountId=DEFAULT_ACCOUNT_ID, ServicePrincipal=known_service_principal
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DeregisterDelegatedAdministrator"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "ConstraintViolationException"
        assert error["Message"] == (
            "You cannot register master account/yourself as delegated administrator for your organization."
        )

    @pytest.mark.usefixtures("created_organization")
    def test_deregister_delegated_administrator_unknown_account(
        self, client: BaseClient, known_service_principal: str
    ):
        with pytest.raises(ClientError) as e:
            client.deregister_delegated_administrator(
                AccountId=utils.make_random_account_id(),
                ServicePrincipal=known_service_principal,
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DeregisterDelegatedAdministrator"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "AccountNotFoundException"
        assert error["Message"] == "You specified an account that doesn't exist."

    @pytest.mark.usefixtures("created_organization")
    def test_deregister_delegated_administrator_unregistered_account(
        self,
        client: BaseClient,
        dummy_account: boto_response,
        known_service_principal: str,
    ):
        with pytest.raises(ClientError) as e:
            client.deregister_delegated_administrator(
                AccountId=(dummy_account["Id"]),
                ServicePrincipal=known_service_principal,
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DeregisterDelegatedAdministrator"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "AccountNotRegisteredException"
        assert error["Message"] == (
            "The provided account is not a registered delegated administrator for your organization."
        )

    @pytest.mark.usefixtures("created_organization")
    def test_deregister_delegated_administrator_unregister_account(
        self,
        client: BaseClient,
        dummy_account: boto_response,
    ):
        client.register_delegated_administrator(
            AccountId=(dummy_account["Id"]), ServicePrincipal="ssm.amazonaws.com"
        )

        with pytest.raises(ClientError) as e:
            client.deregister_delegated_administrator(
                AccountId=(dummy_account["Id"]),
                ServicePrincipal="guardduty.amazonaws.com",
            )

        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DeregisterDelegatedAdministrator"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == "You specified an unrecognized service principal."
