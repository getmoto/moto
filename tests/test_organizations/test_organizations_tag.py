import pytest
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from moto.organizations import utils
from .helpers import boto_response


class TestTag:
    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize("resource", ("account", "root", "ou", "policy"))
    def test_tag_resource(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        dummy_account: boto_response,
        dummy_ou: boto_response,
        dummy_policy: boto_response,
        resource: str,
    ):
        lookup = dict(
            account=dummy_account["Id"],
            root=root_id_dummy_organization,
            ou=dummy_ou["Id"],
            policy=dummy_policy["PolicySummary"]["Id"],
        )
        resource_id = lookup[resource]

        response = client.tag_resource(
            ResourceId=resource_id, Tags=[{"Key": "key", "Value": "value"}]
        )
        initial_tags = client.list_tags_for_resource(ResourceId=resource_id)["Tags"]

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        assert initial_tags == [{"Key": "key", "Value": "value"}]

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize("resource", ("account", "root", "ou", "policy"))
    def test_tag_resource_update(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        dummy_account: boto_response,
        dummy_ou: boto_response,
        dummy_policy: boto_response,
        resource: str,
    ):
        lookup = dict(
            account=dummy_account["Id"],
            root=root_id_dummy_organization,
            ou=dummy_ou["Id"],
            policy=dummy_policy["PolicySummary"]["Id"],
        )
        resource_id = lookup[resource]
        client.tag_resource(
            ResourceId=resource_id, Tags=[{"Key": "key", "Value": "value"}]
        )

        # adding a tag with an existing key, will update the value
        response = client.tag_resource(
            ResourceId=resource_id, Tags=[{"Key": "key", "Value": "new-value"}]
        )
        updated_tags = client.list_tags_for_resource(ResourceId=resource_id)["Tags"]

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        assert updated_tags == [{"Key": "key", "Value": "new-value"}]

    @pytest.mark.usefixtures("created_organization")
    def test_tag_resource_unknown_id_pattern(
        self,
        client: BaseClient,
    ):
        with pytest.raises(ClientError) as e:
            client.tag_resource(
                ResourceId="BLAH", Tags=[{"Key": "key", "Value": "value"}]
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "TagResource"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == (
            "You provided a value that does not match the required pattern."
        )

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize(
        "resource_id",
        (
            utils.make_random_account_id(),
            utils.make_random_root_id(),
            utils.make_random_policy_id(),
            utils.make_random_ou_id(utils.make_random_root_id()),
        ),
    )
    def test_tag_resource_unknown_target(self, client: BaseClient, resource_id: str):
        with pytest.raises(ClientError) as e:
            client.tag_resource(
                ResourceId=resource_id, Tags=[{"Key": "key", "Value": "value"}]
            )
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "TagResource"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "TargetNotFoundException"
        assert error["Message"] == "You specified a target that doesn't exist."

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize("resource", ("account", "root", "ou", "policy"))
    def test_list_tags_for_resource(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        dummy_account: boto_response,
        dummy_ou: boto_response,
        dummy_policy: boto_response,
        resource: str,
    ):
        lookup = dict(
            account=dummy_account["Id"],
            root=root_id_dummy_organization,
            ou=dummy_ou["Id"],
            policy=dummy_policy["PolicySummary"]["Id"],
        )
        resource_id = lookup[resource]
        client.tag_resource(
            ResourceId=resource_id, Tags=[{"Key": "key", "Value": "value"}]
        )

        response = client.list_tags_for_resource(ResourceId=resource_id)
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        assert response["Tags"] == [{"Key": "key", "Value": "value"}]

    @pytest.mark.usefixtures("created_organization")
    def test_list_tags_for_resource_unknown_pattern(
        self,
        client: BaseClient,
    ):
        with pytest.raises(ClientError) as e:
            client.list_tags_for_resource(ResourceId="000x00000A00")
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "ListTagsForResource"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == (
            "You provided a value that does not match the required pattern."
        )

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize(
        "resource_id",
        (
            utils.make_random_account_id(),
            utils.make_random_root_id(),
            utils.make_random_policy_id(),
            utils.make_random_ou_id(utils.make_random_root_id()),
        ),
    )
    def test_list_tags_for_resource_unknown_resource(
        self, client: BaseClient, resource_id: str
    ):
        with pytest.raises(ClientError) as e:
            client.list_tags_for_resource(ResourceId=resource_id)
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "ListTagsForResource"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "TargetNotFoundException"
        assert error["Message"] == "You specified a target that doesn't exist."

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize("resource", ("account", "root", "ou", "policy"))
    def test_untag_resource(
        self,
        client: BaseClient,
        root_id_dummy_organization: str,
        dummy_account: boto_response,
        dummy_ou: boto_response,
        dummy_policy: boto_response,
        resource: str,
    ):
        lookup = dict(
            account=dummy_account["Id"],
            root=root_id_dummy_organization,
            ou=dummy_ou["Id"],
            policy=dummy_policy["PolicySummary"]["Id"],
        )
        resource_id = lookup[resource]
        client.tag_resource(
            ResourceId=resource_id, Tags=[{"Key": "key", "Value": "value"}]
        )

        response = client.untag_resource(ResourceId=resource_id, TagKeys=["key"])
        removed_tags = client.list_tags_for_resource(ResourceId=resource_id)["Tags"]

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        assert removed_tags == []

    @pytest.mark.usefixtures("created_organization")
    def test_untag_resource_unknown_pattern(self, client: BaseClient):
        with pytest.raises(ClientError) as e:
            client.untag_resource(ResourceId="0X00000000A0", TagKeys=["key"])
        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "UntagResource"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "InvalidInputException"
        assert error["Message"] == (
            "You provided a value that does not match the required pattern."
        )

    @pytest.mark.usefixtures("created_organization")
    @pytest.mark.parametrize(
        "resource_id",
        (
            utils.make_random_account_id(),
            utils.make_random_root_id(),
            utils.make_random_policy_id(),
            utils.make_random_ou_id(utils.make_random_root_id()),
        ),
    )
    def test_untag_resource_unknown_resource(
        self, client: BaseClient, resource_id: str
    ):
        with pytest.raises(ClientError) as e:
            client.untag_resource(ResourceId=resource_id, TagKeys=["key"])

        ex = e.value
        error = ex.response["Error"]

        assert ex.operation_name == "UntagResource"
        assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
        assert error["Code"] == "TargetNotFoundException"
        assert error["Message"] == "You specified a target that doesn't exist."
