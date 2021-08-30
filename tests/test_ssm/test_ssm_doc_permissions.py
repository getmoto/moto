import boto3
import pytest
import yaml

from botocore.exceptions import ClientError
from moto import mock_ssm
from .test_ssm_docs import _get_yaml_template


@mock_ssm
def test_describe_document_permissions_unknown_document():
    client = boto3.client("ssm", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_document_permission(
            Name="UnknownDocument", PermissionType="Share"
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidDocument")
    err["Message"].should.equal("The specified document does not exist.")


def get_client():
    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)
    client = boto3.client("ssm", region_name="us-east-1")
    client.create_document(
        Content=yaml.dump(json_doc),
        Name="TestDocument",
        DocumentType="Command",
        DocumentFormat="YAML",
        VersionName="Base",
    )
    return client


@mock_ssm
def test_describe_document_permissions_initial():
    client = get_client()

    res = client.describe_document_permission(
        Name="TestDocument", PermissionType="Share"
    )
    res.should.have.key("AccountIds").equal([])
    res.should.have.key("AccountSharingInfoList").equal([])


@pytest.mark.parametrize(
    "ids",
    [["111111111111"], ["all"], ["All"], ["111111111111", "222222222222"]],
    ids=["one_value", "all", "All", "multiple_values"],
)
@mock_ssm
def test_modify_document_permission_add_account_id(ids):
    client = get_client()
    client.modify_document_permission(
        Name="TestDocument", PermissionType="Share", AccountIdsToAdd=ids
    )

    res = client.describe_document_permission(
        Name="TestDocument", PermissionType="Share"
    )
    res.should.have.key("AccountIds")
    set(res["AccountIds"]).should.equal(set(ids))
    res.should.have.key("AccountSharingInfoList").length_of(len(ids))

    expected_account_sharing = [
        {"AccountId": _id, "SharedDocumentVersion": "$DEFAULT"} for _id in ids
    ]
    res.should.have.key("AccountSharingInfoList").equal(expected_account_sharing)


@pytest.mark.parametrize(
    "initial,to_remove",
    [
        (["all"], ["all"]),
        (["111111111111"], ["111111111111"]),
        (["111111111111", "222222222222"], ["222222222222"]),
        (
            ["111111111111", "222222222222", "333333333333"],
            ["111111111111", "333333333333"],
        ),
    ],
    ids=["all", "one_value", "multiple_initials", "multiple_to_remove"],
)
@mock_ssm
def test_modify_document_permission_remove_account_id(initial, to_remove):
    client = get_client()
    client.modify_document_permission(
        Name="TestDocument", PermissionType="Share", AccountIdsToAdd=initial
    )
    client.modify_document_permission(
        Name="TestDocument", PermissionType="Share", AccountIdsToRemove=to_remove
    )

    res = client.describe_document_permission(
        Name="TestDocument", PermissionType="Share"
    )
    res.should.have.key("AccountIds")
    expected_new_list = set([x for x in initial if x not in to_remove])
    set(res["AccountIds"]).should.equal(expected_new_list)

    expected_account_sharing = [
        {"AccountId": _id, "SharedDocumentVersion": "$DEFAULT"}
        for _id in expected_new_list
    ]
    res.should.have.key("AccountSharingInfoList").equal(expected_account_sharing)


@mock_ssm
def test_fail_modify_document_permission_wrong_permission_type():
    client = get_client()
    with pytest.raises(ClientError) as ex:
        client.modify_document_permission(
            Name="TestDocument", PermissionType="WrongValue", AccountIdsToAdd=[]
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidPermissionType")
    err["Message"].should.match(r"Member must satisfy enum value set: \[Share\]")


@mock_ssm
def test_fail_modify_document_permission_wrong_document_version():
    client = get_client()
    with pytest.raises(ClientError) as ex:
        client.modify_document_permission(
            Name="TestDocument",
            PermissionType="Share",
            SharedDocumentVersion="unknown",
            AccountIdsToAdd=[],
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.match(r"Member must satisfy regular expression pattern")


@pytest.mark.parametrize(
    "value",
    [["alll"], ["1234"], ["1234123412341234"], ["account_id"]],
    ids=["all?", "too_short", "too_long", "no-digits"],
)
@mock_ssm
def test_fail_modify_document_permission_add_invalid_account_ids(value):
    client = get_client()
    with pytest.raises(ClientError) as ex:
        client.modify_document_permission(
            Name="TestDocument", PermissionType="Share", AccountIdsToAdd=value
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.match(r"Member must satisfy regular expression pattern:")


@pytest.mark.parametrize(
    "value",
    [["alll"], ["1234"], ["1234123412341234"], ["account_id"]],
    ids=["all?", "too_short", "too_long", "no-digits"],
)
@mock_ssm
def test_fail_modify_document_permission_remove_invalid_account_ids(value):
    client = get_client()
    with pytest.raises(ClientError) as ex:
        client.modify_document_permission(
            Name="TestDocument", PermissionType="Share", AccountIdsToRemove=value
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.match(r"Member must satisfy regular expression pattern:")


@mock_ssm
def test_fail_modify_document_permission_add_all_and_specific():
    client = get_client()
    with pytest.raises(ClientError) as ex:
        client.modify_document_permission(
            Name="TestDocument",
            PermissionType="Share",
            AccountIdsToAdd=["all", "123412341234"],
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("DocumentPermissionLimit")
    err["Message"].should.equal("Accounts can either be all or a group of AWS accounts")


@mock_ssm
def test_fail_modify_document_permission_remove_all_and_specific():
    client = get_client()
    with pytest.raises(ClientError) as ex:
        client.modify_document_permission(
            Name="TestDocument",
            PermissionType="Share",
            AccountIdsToRemove=["all", "123412341234"],
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("DocumentPermissionLimit")
    err["Message"].should.equal("Accounts can either be all or a group of AWS accounts")
