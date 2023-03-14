import pytest
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from moto.core import DEFAULT_ACCOUNT_ID
from moto.organizations import utils
from .helpers import boto_response, MatchingRegex, boto_factory


class TestOrganizationalUnitBasicCRUD:
    @pytest.mark.usefixtures("created_organization")
    def test_create_organizational_unit(
        self,
        client: BaseClient,
        dummy_organization: boto_response,
        root_id_dummy_organization: str,
        dummy_name: str,
    ):
        ou = client.create_organizational_unit(
            ParentId=root_id_dummy_organization, Name=dummy_name
        )["OrganizationalUnit"]

        assert ou["Id"] == MatchingRegex(utils.OU_ID_REGEX)
        assert ou["Arn"] == (
            utils.OU_ARN_FORMAT.format(
                dummy_organization["MasterAccountId"],
                dummy_organization["Id"],
                ou["Id"],
            )
        )
        assert ou["Name"] == dummy_name

    @pytest.mark.usefixtures("created_organization")
    def test_describe_organizational_unit(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        dummy_name: str,
    ):
        created = client.create_organizational_unit(
            ParentId=root_id_dummy_organization, Name=dummy_name
        )["OrganizationalUnit"]

        described = client.describe_organizational_unit(
            OrganizationalUnitId=created["Id"]
        )["OrganizationalUnit"]

        assert described == created

    @pytest.mark.usefixtures("created_organization")
    def test_describe_organizational_unit_unknown_ou(self, client: BaseClient):
        with pytest.raises(ClientError) as e:
            client.describe_organizational_unit(
                OrganizationalUnitId=utils.make_random_root_id()
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DescribeOrganizationalUnit"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "400"
        assert "OrganizationalUnitNotFoundException" in error["Message"]

    @pytest.mark.usefixtures("created_organization")
    def test_list_organizational_units_pagination(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        ou_factory: boto_factory,
    ):
        created = ou_factory(20)

        response = client.list_organizational_units_for_parent(
            ParentId=root_id_dummy_organization
        )

        assert "NextToken" not in response
        assert len(response["OrganizationalUnits"]) == len(created)

    @pytest.mark.usefixtures("created_organization")
    def test_list_organizational_units_paginator(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        ou_factory: boto_factory,
    ):
        created = ou_factory(20)
        max_results = 5

        paginator = client.get_paginator("list_organizational_units_for_parent")
        page_iterator = paginator.paginate(
            MaxResults=max_results, ParentId=root_id_dummy_organization
        )

        for page in page_iterator:
            assert len(page["OrganizationalUnits"]) <= max_results
        assert (
            page["OrganizationalUnits"][-1]["Name"]
            == created[-1]["OrganizationalUnit"]["Name"]
        )

    @pytest.mark.usefixtures("created_organization")
    def test_update_organizational_unit(
        self, client: BaseClient, dummy_ou: boto_response
    ):
        old_name = dummy_ou["Name"]
        new_name = "test-change-name"

        client.update_organizational_unit(
            OrganizationalUnitId=dummy_ou["Id"], Name=new_name
        )
        described = client.describe_organizational_unit(
            OrganizationalUnitId=dummy_ou["Id"]
        )["OrganizationalUnit"]

        assert described["Name"] == new_name
        assert described["Name"] != old_name

    @pytest.mark.usefixtures("created_organization")
    def test_update_organizational_unit_same_name(
        self, client: BaseClient, dummy_ou: boto_response
    ):
        with pytest.raises(ClientError) as e:
            client.update_organizational_unit(
                OrganizationalUnitId=dummy_ou["Id"], Name=dummy_ou["Name"]
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "UpdateOrganizationalUnit"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "DuplicateOrganizationalUnitException"
        assert error["Message"] == "An OU with the same name already exists."

    @pytest.mark.usefixtures("created_organization")
    def test_delete_organizational_unit(
        self, client: BaseClient, dummy_ou: boto_response
    ):
        response = client.delete_organizational_unit(
            OrganizationalUnitId=dummy_ou["Id"]
        )

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        with pytest.raises(ClientError) as e:
            client.describe_organizational_unit(OrganizationalUnitId=dummy_ou["Id"])
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DescribeOrganizationalUnit"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "400"
        assert "OrganizationalUnitNotFoundException" in error["Message"]


class TestOrganizationalUnitStructure:
    @pytest.mark.usefixtures("created_organization")
    def test_list_children(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        account_factory: boto_factory,
    ):
        ou_1 = client.create_organizational_unit(
            ParentId=root_id_dummy_organization, Name="ou_1"
        )["OrganizationalUnit"]
        #
        ou_2 = client.create_organizational_unit(ParentId=ou_1["Id"], Name="ou_2")[
            "OrganizationalUnit"
        ]
        created_accounts = account_factory(2)
        account_1 = created_accounts[0]["CreateAccountStatus"]
        account_2 = created_accounts[1]["CreateAccountStatus"]
        client.move_account(
            AccountId=account_2["AccountId"],
            SourceParentId=root_id_dummy_organization,
            DestinationParentId=ou_1["Id"],
        )

        root_children_account = client.list_children(
            ParentId=root_id_dummy_organization, ChildType="ACCOUNT"
        )["Children"]
        root_children_ou = client.list_children(
            ParentId=root_id_dummy_organization, ChildType="ORGANIZATIONAL_UNIT"
        )["Children"]
        ou_1_children_account = client.list_children(
            ParentId=ou_1["Id"], ChildType="ACCOUNT"
        )["Children"]
        ou_1_children_ou = client.list_children(
            ParentId=ou_1["Id"], ChildType="ORGANIZATIONAL_UNIT"
        )["Children"]

        assert len(root_children_account) == 2
        assert sorted([account["Id"] for account in root_children_account]) == sorted(
            [DEFAULT_ACCOUNT_ID, account_1["AccountId"]]
        )
        assert len(root_children_ou) == 1
        assert root_children_ou[0]["Id"] == ou_1["Id"]
        assert len(ou_1_children_account) == 1
        assert ou_1_children_account[0]["Id"] == account_2["AccountId"]
        assert len(ou_1_children_ou) == 1
        assert ou_1_children_ou[0]["Id"] == ou_2["Id"]

    @pytest.mark.usefixtures("created_organization")
    def test_list_children_unknown_parent(
        self,
        client: BaseClient,
    ):
        with pytest.raises(ClientError) as e:
            client.list_children(
                ParentId=utils.make_random_root_id(), ChildType="ACCOUNT"
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "ListChildren"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "400"
        assert "ParentNotFoundException" in error["Message"]

    @pytest.mark.usefixtures("created_organization")
    def test_list_children_unknown_child_type(
        self, client: BaseClient, root_id_dummy_organization: str
    ):
        with pytest.raises(ClientError) as e:
            client.list_children(ParentId=root_id_dummy_organization, ChildType="BLEE")
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "ListChildren"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == "You specified an invalid value."

    @pytest.mark.usefixtures("created_organization")
    def test_list_organizational_units_for_parent(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        ou_factory: boto_factory,
    ):
        created = [ou["OrganizationalUnit"] for ou in ou_factory(3)]

        listed = client.list_organizational_units_for_parent(
            ParentId=root_id_dummy_organization
        )["OrganizationalUnits"]

        assert listed == created

    @pytest.mark.usefixtures("created_organization")
    def test_list_organizational_units_for_parent_unknown_parent(
        self, client: BaseClient
    ):
        with pytest.raises(ClientError) as e:
            client.list_organizational_units_for_parent(
                ParentId=utils.make_random_root_id()
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "ListOrganizationalUnitsForParent"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "400"
        assert "ParentNotFoundException" in error["Message"]

    @pytest.mark.usefixtures("created_organization")
    def test_list_parents_for_ou(
        self, client: BaseClient, root_id_dummy_organization: str
    ):
        ou_1 = client.create_organizational_unit(
            ParentId=root_id_dummy_organization, Name="ou_1"
        )["OrganizationalUnit"]
        #
        ou_2 = client.create_organizational_unit(ParentId=ou_1["Id"], Name="ou_2")[
            "OrganizationalUnit"
        ]

        parents_ou_1 = client.list_parents(ChildId=ou_1["Id"])["Parents"]
        parents_ou_2 = client.list_parents(ChildId=ou_2["Id"])["Parents"]

        assert len(parents_ou_1) == 1
        assert parents_ou_1[0]["Id"] == root_id_dummy_organization
        assert parents_ou_1[0]["Type"] == "ROOT"
        assert len(parents_ou_2) == 1
        assert parents_ou_2[0]["Id"] == ou_1["Id"]
        assert parents_ou_2[0]["Type"] == "ORGANIZATIONAL_UNIT"
