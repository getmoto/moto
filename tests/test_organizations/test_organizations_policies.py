from typing import Callable

import pytest
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from moto.organizations import utils
from .helpers import boto_response, MatchingRegex, boto_factory


class TestPolicyBasicCRUD:
    @pytest.mark.usefixtures("created_organization")
    def test_create_policy(
        self,
        client: BaseClient,
        dummy_organization: boto_response,
        dummy_policy_content: str,
    ):
        policy = client.create_policy(
            Content=dummy_policy_content,
            Description="A dummy service control policy",
            Name="MockServiceControlPolicy",
            Type="SERVICE_CONTROL_POLICY",
        )["Policy"]
        summary = policy["PolicySummary"]

        assert policy["Content"] == dummy_policy_content
        assert summary["Id"] == MatchingRegex(utils.POLICY_ID_REGEX)
        assert summary["Arn"] == utils.SCP_ARN_FORMAT.format(
            dummy_organization["MasterAccountId"],
            dummy_organization["Id"],
            summary["Id"],
        )
        assert summary["Description"] == "A dummy service control policy"
        assert summary["Name"] == "MockServiceControlPolicy"
        assert summary["Type"] == "SERVICE_CONTROL_POLICY"
        assert isinstance(summary["AwsManaged"], bool)

    @pytest.mark.usefixtures("created_organization")
    def test_create_policy_unknown(self, client: BaseClient, dummy_policy_content: str):
        with pytest.raises(ClientError) as e:
            client.create_policy(
                Content=dummy_policy_content,
                Description="A dummy service control policy",
                Name="MockServiceControlPolicy",
                Type="MOTO",
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "CreatePolicy"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == "You specified an invalid value."

    @pytest.mark.usefixtures("created_organization")
    def test_describe_policy(
        self, client: BaseClient, dummy_policy_config: boto_response
    ):
        created = client.create_policy(**dummy_policy_config)["Policy"]
        policy_id = created["PolicySummary"]["Id"]

        described = client.describe_policy(PolicyId=policy_id)["Policy"]

        assert described["PolicySummary"]["Name"] == dummy_policy_config["Name"]
        assert (
            described["PolicySummary"]["Description"]
            == dummy_policy_config["Description"]
        )
        assert described["Content"] == dummy_policy_config["Content"]

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize(
        "policy_id,err_code,err_message",
        (
            (utils.make_random_policy_id(), "400", "PolicyNotFoundException"),
            (
                "invalid-id",
                "InvalidInputException",
                "You specified an invalid value.",
            ),
        ),
    )
    def test_describe_policy_exception(
        self, client: BaseClient, policy_id: str, err_code: str, err_message: str
    ):
        with pytest.raises(ClientError) as e:
            client.describe_policy(PolicyId=policy_id)
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DescribePolicy"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == err_code
        assert err_message in error["Message"]

    @pytest.mark.usefixtures("created_organization")
    def test_list_policies(self, client: BaseClient, policy_factory: boto_factory):
        created = policy_factory(4)

        policies = client.list_policies(Filter="SERVICE_CONTROL_POLICY")["Policies"]

        assert len(policies) == len(created) + 1
        assert policies[-1]["Name"] == created[-1]["Policy"]["PolicySummary"]["Name"]

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize(
        "key,helper",
        (
            ("Description", lambda policy: policy["PolicySummary"]),
            ("Name", lambda policy: policy["PolicySummary"]),
            ("Content", lambda policy: policy),
        ),
    )
    def test_update_policy(
        self,
        client: BaseClient,
        dummy_policy: boto_response,
        key: str,
        helper: Callable[[boto_response], boto_response],
    ):
        policy_id = dummy_policy["PolicySummary"]["Id"]

        client.update_policy(PolicyId=policy_id, **{key: "foobar"})
        policy = client.describe_policy(PolicyId=policy_id)["Policy"]

        assert helper(policy)[key] == "foobar"

    @pytest.mark.usefixtures("created_organization")
    def test_update_policy_unknown(self, client: BaseClient):
        with pytest.raises(ClientError) as e:
            client.update_policy(PolicyId=utils.make_random_policy_id())
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "UpdatePolicy"
        assert error["Code"] == "400"
        assert "PolicyNotFoundException" in error["Message"]

    @pytest.mark.usefixtures("created_organization")
    def test_delete_policy(self, client: BaseClient, dummy_policy_content: str):
        base_policies = client.list_policies(Filter="SERVICE_CONTROL_POLICY")[
            "Policies"
        ]
        policy_id = client.create_policy(
            Content=dummy_policy_content,
            Description="A dummy service control policy",
            Name="MockServiceControlPolicy",
            Type="SERVICE_CONTROL_POLICY",
        )["Policy"]["PolicySummary"]["Id"]

        response = client.delete_policy(PolicyId=policy_id)
        new_policies = client.list_policies(Filter="SERVICE_CONTROL_POLICY")["Policies"]

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        assert new_policies == base_policies
        assert len(base_policies) == 1

    @pytest.mark.usefixtures("created_organization")
    def test_delete_policy_not_existing(self, client: BaseClient):
        with pytest.raises(ClientError) as e:
            client.delete_policy(PolicyId=(utils.make_random_policy_id()))
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DeletePolicy"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "400"
        assert "PolicyNotFoundException" in error["Message"]

    @pytest.mark.usefixtures("created_organization")
    def test_delete_policy_in_use(
        self,
        client: BaseClient,
        dummy_policy: boto_response,
        root_id_dummy_organization: str,
    ):
        policy_id = dummy_policy["PolicySummary"]["Id"]
        client.attach_policy(PolicyId=policy_id, TargetId=root_id_dummy_organization)

        with pytest.raises(ClientError) as e:
            client.delete_policy(PolicyId=policy_id)
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DeletePolicy"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "400"
        assert "PolicyInUseException" in error["Message"]


class TestPolicyStatus:
    @pytest.mark.usefixtures("created_organization")
    def test_enable_policy_type(
        self,
        client: BaseClient,
        dummy_organization: boto_response,
        root_id_dummy_organization: str,
        known_policy_type: str,
    ):
        root = client.enable_policy_type(
            RootId=root_id_dummy_organization, PolicyType=known_policy_type
        )["Root"]

        assert root["Id"] == root_id_dummy_organization
        assert root["Arn"] == (
            utils.ROOT_ARN_FORMAT.format(
                dummy_organization["MasterAccountId"],
                dummy_organization["Id"],
                root_id_dummy_organization,
            )
        )
        assert root["Name"] == "Root"
        assert len(root["PolicyTypes"]) == 1
        assert root["PolicyTypes"] == [{"Type": known_policy_type, "Status": "ENABLED"}]

    @pytest.mark.usefixtures("created_organization")
    def test_enable_policy_type_exception_root_not_found(
        self, client: BaseClient, known_policy_type: str
    ):
        with pytest.raises(ClientError) as e:
            client.enable_policy_type(
                RootId=utils.make_random_root_id(), PolicyType=known_policy_type
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "EnablePolicyType"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "RootNotFoundException"
        assert error["Message"] == "You specified a root that doesn't exist."

    @pytest.mark.usefixtures("created_organization")
    def test_enable_policy_type_exception_already_enabled(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        known_policy_type: str,
    ):
        client.enable_policy_type(
            RootId=root_id_dummy_organization,
            PolicyType=known_policy_type,
        )

        with pytest.raises(ClientError) as e:
            client.enable_policy_type(
                RootId=root_id_dummy_organization,
                PolicyType=known_policy_type,
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "EnablePolicyType"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "PolicyTypeAlreadyEnabledException"
        assert error["Message"] == "The specified policy type is already enabled."

    @pytest.mark.usefixtures("created_organization")
    def test_enable_policy_type_exception_unknown_policy(
        self, client: BaseClient, root_id_dummy_organization: str
    ):
        with pytest.raises(ClientError) as e:
            client.enable_policy_type(
                RootId=root_id_dummy_organization, PolicyType="MOTO"
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "EnablePolicyType"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == "You specified an invalid value."

    @pytest.mark.usefixtures("created_organization")
    def test_disable_policy_type(
        self,
        client: BaseClient,
        dummy_organization: boto_response,
        root_id_dummy_organization: str,
        known_policy_type: str,
    ):
        client.enable_policy_type(
            RootId=root_id_dummy_organization, PolicyType=known_policy_type
        )

        root = client.disable_policy_type(
            RootId=root_id_dummy_organization, PolicyType=known_policy_type
        )["Root"]

        assert root["Id"] == root_id_dummy_organization
        assert root["Arn"] == utils.ROOT_ARN_FORMAT.format(
            dummy_organization["MasterAccountId"],
            dummy_organization["Id"],
            root_id_dummy_organization,
        )
        assert root["Name"] == "Root"
        assert root["PolicyTypes"] == []

    @pytest.mark.usefixtures("created_organization")
    def test_disable_policy_type_exception_root_not_found(
        self, client: BaseClient, known_policy_type: str
    ):
        with pytest.raises(ClientError) as e:
            client.disable_policy_type(
                RootId=utils.make_random_root_id(), PolicyType=known_policy_type
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DisablePolicyType"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "RootNotFoundException"
        assert error["Message"] == "You specified a root that doesn't exist."

    @pytest.mark.usefixtures("created_organization")
    def test_disable_policy_type_exception_not_enabled(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        known_policy_type: str,
    ):
        with pytest.raises(ClientError) as e:
            client.disable_policy_type(
                RootId=root_id_dummy_organization, PolicyType=known_policy_type
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DisablePolicyType"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "PolicyTypeNotEnabledException"
        assert (
            error["Message"]
            == "This operation can be performed only for enabled policy types."
        )

    @pytest.mark.usefixtures("created_organization")
    def test_disable_policy_type_exception_unknown_policy(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
    ):
        with pytest.raises(ClientError) as e:
            client.disable_policy_type(
                RootId=root_id_dummy_organization, PolicyType="MOTO"
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DisablePolicyType"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == "You specified an invalid value."


class TestPolicyAttaching:
    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize(
        "targets", (("ou",), ("account",), ("root",), ("root", "ou", "account"))
    )
    def test_attach_policy(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        dummy_ou: boto_response,
        dummy_account: boto_response,
        dummy_policy: boto_response,
        targets: list[str],
    ):
        lookup = dict(
            ou=dummy_ou["Id"],
            account=dummy_account["Id"],
            root=root_id_dummy_organization,
        )
        policy_id = dummy_policy["PolicySummary"]["Id"]

        for target in targets:
            response = client.attach_policy(PolicyId=policy_id, TargetId=lookup[target])

            assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize(
        "resource_id,error_code,error_message",
        (
            (utils.make_random_root_id(), "400", "OrganizationalUnitNotFoundException"),
            (
                utils.make_random_ou_id(utils.make_random_root_id()),
                "400",
                "OrganizationalUnitNotFoundException",
            ),
            (
                utils.make_random_account_id(),
                "AccountNotFoundException",
                "You specified an account that doesn't exist.",
            ),
            (
                "meaninglessstring",
                "InvalidInputException",
                "You specified an invalid value.",
            ),
        ),
    )
    def test_attach_policy_exception(
        self,
        client: BaseClient,
        dummy_policy: boto_response,
        resource_id: str,
        error_code: str,
        error_message: str,
    ):
        policy_id = dummy_policy["PolicySummary"]["Id"]

        with pytest.raises(ClientError) as e:
            client.attach_policy(PolicyId=policy_id, TargetId=resource_id)
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "AttachPolicy"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == error_code
        assert error_message in error["Message"]

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize("target", ("ou", "account"))
    def test_list_policies_for_target(
        self,
        client: BaseClient,
        dummy_ou: boto_response,
        dummy_account: boto_response,
        dummy_policy: boto_response,
        target: str,
    ):
        lookup = dict(
            ou=dummy_ou["Id"],
            account=dummy_account["Id"],
        )
        resource_id = lookup[target]
        policy_id = dummy_policy["PolicySummary"]["Id"]
        client.attach_policy(PolicyId=policy_id, TargetId=resource_id)

        policies = client.list_policies_for_target(
            TargetId=resource_id, Filter="SERVICE_CONTROL_POLICY"
        )["Policies"]

        assert len(policies) == 2
        assert policies[0]["AwsManaged"]
        assert policies[1]["Id"] == policy_id

    @pytest.mark.parametrize(
        "resource_id,error_code,error_message",
        (
            (
                utils.make_random_root_id(),
                "TargetNotFoundException",
                "You specified a target that doesn't exist.",
            ),
            (
                utils.make_random_ou_id(utils.make_random_root_id()),
                "400",
                "OrganizationalUnitNotFoundException",
            ),
            (
                utils.make_random_account_id(),
                "AccountNotFoundException",
                "You specified an account that doesn't exist.",
            ),
            (
                "meaninglessstring",
                "InvalidInputException",
                "You specified an invalid value.",
            ),
        ),
    )
    @pytest.mark.usefixtures("created_organization")
    def test_list_policies_for_target_target_exception(
        self,
        client: BaseClient,
        resource_id: str,
        error_code: str,
        error_message: str,
    ):
        with pytest.raises(ClientError) as e:
            client.list_policies_for_target(
                TargetId=resource_id, Filter="SERVICE_CONTROL_POLICY"
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "ListPoliciesForTarget"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == error_code
        assert error_message in error["Message"]

    @pytest.mark.usefixtures("created_organization")
    def test_list_policies_for_target_filter_exception(
        self, client: BaseClient, root_id_dummy_organization: str
    ):
        with pytest.raises(ClientError) as e:
            client.list_policies_for_target(
                TargetId=root_id_dummy_organization, Filter="MOTO"
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "ListPoliciesForTarget"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == "You specified an invalid value."

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize(
        "target,expected_type",
        (("ou", "ORGANIZATIONAL_UNIT"), ("account", "ACCOUNT"), ("root", "ROOT")),
    )
    def test_list_targets_for_policy(
        self,
        client: BaseClient,
        root_dummy_organization: boto_response,
        dummy_ou: boto_response,
        dummy_account: boto_response,
        dummy_policy: boto_response,
        target: str,
        expected_type: str,
    ):
        lookup = dict(
            ou=dummy_ou,
            account=dummy_account,
            root=root_dummy_organization,
        )
        resource = lookup[target]
        policy_id = dummy_policy["PolicySummary"]["Id"]
        client.attach_policy(PolicyId=policy_id, TargetId=resource["Id"])

        targets = client.list_targets_for_policy(PolicyId=policy_id)["Targets"]

        assert len(targets) == 1
        assert targets[0]["Type"] == expected_type
        assert targets[0]["TargetId"] == resource["Id"]
        assert targets[0]["Name"] == resource["Name"]
        assert targets[0]["Arn"] == resource["Arn"]

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize(
        "resource_id,expected_code,expected_message",
        (
            (utils.make_random_policy_id(), "400", "PolicyNotFoundException"),
            (
                "meaninglessstring",
                "InvalidInputException",
                "You specified an invalid value.",
            ),
        ),
    )
    def test_list_targets_for_policy_exception(
        self,
        client: BaseClient,
        resource_id: str,
        expected_code: str,
        expected_message: str,
    ):
        with pytest.raises(ClientError) as e:
            client.list_targets_for_policy(PolicyId=resource_id)
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "ListTargetsForPolicy"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == expected_code
        assert expected_message in error["Message"]

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize("resource", ("ou", "account", "root"))
    def test_detach_policy(
        self,
        client: BaseClient,
        root_dummy_organization: boto_response,
        dummy_ou: boto_response,
        dummy_account: boto_response,
        dummy_policy: boto_response,
        resource: str,
    ):
        lookup = dict(
            ou=dummy_ou,
            account=dummy_account,
            root=root_dummy_organization,
        )
        resource_id = lookup[resource]["Id"]
        policy_id = dummy_policy["PolicySummary"]["Id"]
        base_policies = client.list_policies_for_target(
            TargetId=resource_id, Filter="SERVICE_CONTROL_POLICY"
        )["Policies"]
        client.attach_policy(PolicyId=policy_id, TargetId=resource_id)

        response = client.detach_policy(PolicyId=policy_id, TargetId=resource_id)
        policies = client.list_policies_for_target(
            TargetId=resource_id, Filter="SERVICE_CONTROL_POLICY"
        )["Policies"]

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        assert policies == base_policies

    @pytest.mark.parametrize(
        "resource_id,error_code,error_message",
        (
            (
                utils.make_random_root_id(),
                "400",
                "OrganizationalUnitNotFoundException",
            ),
            (
                utils.make_random_ou_id(utils.make_random_root_id()),
                "400",
                "OrganizationalUnitNotFoundException",
            ),
            (
                utils.make_random_account_id(),
                "AccountNotFoundException",
                "You specified an account that doesn't exist.",
            ),
            (
                "meaninglessstring",
                "InvalidInputException",
                "You specified an invalid value.",
            ),
        ),
    )
    @pytest.mark.usefixtures("created_organization")
    def test_detach_policy_exception(
        self,
        client: BaseClient,
        dummy_policy: boto_response,
        resource_id: str,
        error_code: str,
        error_message: str,
    ):
        policy_id = dummy_policy["PolicySummary"]["Id"]

        with pytest.raises(ClientError) as e:
            client.detach_policy(PolicyId=policy_id, TargetId=resource_id)
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "DetachPolicy"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == error_code
        assert error_message in error["Message"]
