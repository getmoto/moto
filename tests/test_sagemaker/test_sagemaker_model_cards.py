"""Unit tests for sagemaker-supported APIs."""

import time
from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError
from dateutil.tz import tzutc

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

ACCOUNT_ID = "123456789012"


@mock_aws
def test_create_model_card():
    client = boto3.client("sagemaker", region_name="us-east-1")
    resp = client.create_model_card(
        ModelCardName="my-first-model-card",
        ModelCardStatus="Draft",
        Content='{"model_overview": {"model_description": "my first model"}}',
    )

    assert (
        resp["ModelCardArn"]
        == f"arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:model-card/my-first-model-card"
    )

    with pytest.raises(ClientError) as e:
        resp = client.create_model_card(
            ModelCardName="my-first-model-card",
            ModelCardStatus="Draft",
            Content='{"model_overview": {"model_description": "my first model"}}',
        )
    assert e.value.response["Error"]["Code"] == "ConflictException"
    assert (
        e.value.response["Error"]["Message"]
        == "Modelcard my-first-model-card already exists"
    )


@mock_aws
def test_update_model_card():
    client = boto3.client("sagemaker", region_name="us-east-1")
    client.create_model_card(
        ModelCardName="my-first-model-card",
        ModelCardStatus="Draft",
        Content='{"model_overview": {"model_description": "my first model"}}',
    )
    client.update_model_card(
        ModelCardName="my-first-model-card",
        ModelCardStatus="Draft",
        Content='{"model_overview": {"model_description": "my first model ."}}',
    )

    resp = client.list_model_card_versions(ModelCardName="my-first-model-card").get(
        "ModelCardVersionSummaryList"
    )
    assert (len(resp)) == 2

    with pytest.raises(ClientError) as e:
        client.update_model_card(
            ModelCardName="my-second-model-card",
            ModelCardStatus="Draft",
            Content='{"model_overview": {"model_description": "my first model ."}}',
        )
    assert e.value.response["Error"]["Code"] == "ResourceNotFound"
    assert (
        e.value.response["Error"]["Message"]
        == "Modelcard my-second-model-card does not exist."
    )


@mock_aws
def test_model_card_tags():
    client = boto3.client("sagemaker", region_name="us-east-1")
    client.create_model_card(
        ModelCardName="my-first-model-card",
        ModelCardStatus="Draft",
        Content='{"model_overview": {"model_description": "my first model"}}',
        Tags=[{"Key": "Mytag", "Value": "MyValue"}],
    )

    model_card_arn = (
        f"arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:model-card/my-first-model-card"
    )
    tags = client.list_tags(ResourceArn=model_card_arn).get("Tags")
    assert [{"Key": "Mytag", "Value": "MyValue"}] == tags

    client.update_model_card(
        ModelCardName="my-first-model-card",
        ModelCardStatus="Draft",
        Content='{"model_overview": {"model_description": "my first model >:)"}}',
    )

    model_card_arn = (
        f"arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:model-card/my-first-model-card"
    )
    tags = client.list_tags(ResourceArn=model_card_arn).get("Tags")
    assert [{"Key": "Mytag", "Value": "MyValue"}] == tags

    client.add_tags(
        ResourceArn=model_card_arn, Tags=[{"Key": "Mytag2", "Value": "MyValue2"}]
    )
    tags = client.list_tags(ResourceArn=model_card_arn).get("Tags")
    assert {"Key": "Mytag2", "Value": "MyValue2"} in tags

    tags_to_delete = ["Mytag"]
    client.delete_tags(ResourceArn=model_card_arn, TagKeys=tags_to_delete)
    tags = client.list_tags(ResourceArn=model_card_arn).get("Tags")
    assert {"Key": "Mytag", "Value": "MyValue"} not in tags


@mock_aws
def test_list_model_cards_basic():
    client = boto3.client("sagemaker", region_name="us-east-1")

    cards_to_create = ["first", "second", "third"]
    for c in cards_to_create:
        client.create_model_card(
            ModelCardName=f"my-{c}-model-card",
            ModelCardStatus="Draft",
            Content='{"model_overview": {"model_description": f"my {c} model"}}',
        )
    resp = client.list_model_cards().get("ModelCardSummaries")
    assert len(resp) == 3
    for i, r in enumerate(resp):
        assert (
            r["ModelCardName"] == f"my-{cards_to_create[i]}-model-card"
        ), "model card name didn't match expected"
        assert (
            r["ModelCardArn"]
            == f"arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:model-card/my-{cards_to_create[i]}-model-card"
        ), "model_card_arn didn't match expected"
        assert (
            r["ModelCardStatus"] == "Draft"
        ), "model card status didn't match expected"


@mock_aws
def test_list_model_cards_advanced():
    client = boto3.client("sagemaker", region_name="us-east-1")

    cards_to_create = ["first", "second", "third"]
    for c in cards_to_create:
        client.create_model_card(
            ModelCardName=f"my-{c}-model-card",
            ModelCardStatus="Draft",
            Content='{"model_overview": {"model_description": f"my {c} model"}}',
        )
    time.sleep(1)
    datetime_now = datetime.now(tzutc())
    client.create_model_card(
        ModelCardName="my-fourth-model-card",
        ModelCardStatus="Approved",
        Content='{"model_overview": {"model_description": "my fourth model"}}',
    )

    resp = client.list_model_cards(NameContains="first").get("ModelCardSummaries")
    assert len(resp) == 1
    assert resp[0].get("ModelCardName") == "my-first-model-card"

    resp = client.list_model_cards().get("ModelCardSummaries")
    assert len(resp) == 4
    assert resp[-1].get("ModelCardName") == "my-fourth-model-card"

    # Ascending by default
    resp = client.list_model_cards(SortOrder="Descending").get("ModelCardSummaries")
    assert len(resp) == 4
    assert resp[0].get("ModelCardName") == "my-fourth-model-card"

    resp = client.list_model_cards(ModelCardStatus="Approved").get("ModelCardSummaries")
    assert len(resp) == 1
    assert resp[0].get("ModelCardName") == "my-fourth-model-card"

    resp = client.list_model_cards(SortBy="Name").get("ModelCardSummaries")
    assert len(resp) == 4
    assert resp[-1].get("ModelCardName") == "my-third-model-card"

    resp = client.list_model_cards(CreationTimeBefore=datetime_now).get(
        "ModelCardSummaries"
    )
    assert len(resp) == 3
    assert resp[-1].get("ModelCardName") == "my-third-model-card"

    resp = client.list_model_cards(CreationTimeAfter=datetime_now).get(
        "ModelCardSummaries"
    )
    assert len(resp) == 1
    assert resp[0].get("ModelCardName") == "my-fourth-model-card"


@mock_aws
def test_list_model_card_versions_basic():
    client = boto3.client("sagemaker", region_name="us-east-1")
    client.create_model_card(
        ModelCardName="my-first-model-card",
        ModelCardStatus="Draft",
        Content='{"model_overview": {"model_description": "my first model"}}',
    )
    time.sleep(1)
    client.update_model_card(
        ModelCardName="my-first-model-card",
        ModelCardStatus="Draft",
        Content='{"model_overview": {"model_description": "my first model. :))"}}',
    )
    resp = client.list_model_card_versions(ModelCardName="my-first-model-card").get(
        "ModelCardVersionSummaryList"
    )
    assert len(resp) == 2, f"Expected 2 model card versions, found {len(resp)}"
    assert resp[0].get("ModelCardVersion") == 1
    assert resp[1].get("ModelCardVersion") == 2
    assert resp[0].get("CreationTime") == resp[1].get("CreationTime")
    assert resp[0].get("LastModifiedTime") < resp[1].get("LastModifiedTime")  # type: ignore


@mock_aws
def test_list_model_card_versions_advanced():
    client = boto3.client("sagemaker", region_name="us-east-1")
    client.create_model_card(
        ModelCardName="my-first-model-card",
        ModelCardStatus="Draft",
        Content='{"model_overview": {"model_description": "my first model"}}',
    )
    client.update_model_card(
        ModelCardName="my-first-model-card",
        ModelCardStatus="Draft",
        Content='{"model_overview": {"model_description": "my first model. :))"}}',
    )
    client.update_model_card(
        ModelCardName="my-first-model-card",
        ModelCardStatus="Approved",
        Content='{"model_overview": {"model_description": "my first model. :))"}}',
    )
    client.create_model_card(
        ModelCardName="my-second-model-card",
        ModelCardStatus="Draft",
        Content='{"model_overview": {"model_description": "my first model. :))"}}',
    )

    resp = client.list_model_card_versions(ModelCardName="my-first-model-card").get(
        "ModelCardVersionSummaryList"
    )
    assert len(resp) == 3
    assert [r.get("ModelCardVersion") for r in resp] == [1, 2, 3]

    resp = client.list_model_card_versions(
        ModelCardName="my-first-model-card", SortOrder="Descending"
    ).get("ModelCardVersionSummaryList")
    assert len(resp) == 3
    assert [r.get("ModelCardVersion") for r in resp] == [3, 2, 1]

    resp = client.list_model_card_versions(
        ModelCardName="my-first-model-card", ModelCardStatus="Approved"
    ).get("ModelCardVersionSummaryList")
    assert len(resp) == 1
    assert [r.get("ModelCardVersion") for r in resp] == [3]

    resp = client.list_model_card_versions(ModelCardName="my-second-model-card").get(
        "ModelCardVersionSummaryList"
    )
    assert len(resp) == 1

    with pytest.raises(ClientError) as e:
        client.list_model_card_versions(ModelCardName="I-dont-exist")
    assert e.value.response["Error"]["Code"] == "ResourceNotFound"


@mock_aws
def test_describe_model_card():
    client = boto3.client("sagemaker", region_name="us-east-1")

    client.create_model_card(
        ModelCardName="my-first-model-card",
        SecurityConfig={"KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab"},
        ModelCardStatus="Draft",
        Content='{"model_overview": {"model_description": "my first model"}}',
    )

    resp = client.describe_model_card(ModelCardName="my-first-model-card")
    assert (
        resp["ModelCardArn"]
        == f"arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:model-card/my-first-model-card"
    )
    assert resp["ModelCardName"] == "my-first-model-card"
    assert resp["ModelCardVersion"] == 1
    assert (
        resp["Content"] == '{"model_overview": {"model_description": "my first model"}}'
    )
    assert resp["ModelCardStatus"] == "Draft"
    assert resp["SecurityConfig"] == {
        "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab"
    }
    assert resp["CreatedBy"] == {}
    assert resp["LastModifiedBy"] == {}

    client.update_model_card(
        ModelCardName="my-first-model-card",
        Content='{"model_overview": {"model_description": "my first model >:)"}}',
        ModelCardStatus="Approved",
    )

    resp = client.describe_model_card(
        ModelCardName="my-first-model-card", ModelCardVersion=1
    )

    assert (
        resp["ModelCardArn"]
        == f"arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:model-card/my-first-model-card"
    )
    assert resp["ModelCardName"] == "my-first-model-card"
    assert resp["ModelCardVersion"] == 1
    assert (
        resp["Content"] == '{"model_overview": {"model_description": "my first model"}}'
    )
    assert resp["ModelCardStatus"] == "Draft"
    assert resp["SecurityConfig"] == {
        "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab"
    }
    assert resp["CreatedBy"] == {}
    assert resp["LastModifiedBy"] == {}

    resp = client.describe_model_card(ModelCardName="my-first-model-card")

    assert (
        resp["ModelCardArn"]
        == f"arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:model-card/my-first-model-card"
    )
    assert resp["ModelCardName"] == "my-first-model-card"
    assert resp["ModelCardVersion"] == 2
    assert (
        resp["Content"]
        == '{"model_overview": {"model_description": "my first model >:)"}}'
    )
    assert resp["ModelCardStatus"] == "Approved"
    assert resp["SecurityConfig"] == {
        "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab"
    }
    assert resp["CreatedBy"] == {}
    assert resp["LastModifiedBy"] == {}

    resp = client.describe_model_card(
        ModelCardName="my-first-model-card", ModelCardVersion=2
    )

    assert (
        resp["ModelCardArn"]
        == f"arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:model-card/my-first-model-card"
    )
    assert resp["ModelCardName"] == "my-first-model-card"
    assert resp["ModelCardVersion"] == 2
    assert (
        resp["Content"]
        == '{"model_overview": {"model_description": "my first model >:)"}}'
    )
    assert resp["ModelCardStatus"] == "Approved"
    assert resp["SecurityConfig"] == {
        "KmsKeyId": "1234abcd-12ab-34cd-56ef-1234567890ab"
    }
    assert resp["CreatedBy"] == {}
    assert resp["LastModifiedBy"] == {}

    with pytest.raises(ClientError) as e:
        client.describe_model_card(
            ModelCardName="my-first-model-card", ModelCardVersion=3
        )
    assert e.value.response["Error"]["Code"] == "ResourceNotFound"
    assert (
        e.value.response["Error"]["Message"]
        == "Modelcard with name my-first-model-card and version: 3 does not exist"
    )


@mock_aws
def test_delete_model_card():
    client = boto3.client("sagemaker", region_name="eu-west-1")

    _ = client.create_model_card(
        ModelCardName="my-first-model-card",
        ModelCardStatus="Draft",
        Content='{"model_overview": {"model_description": f"my first model"}}',
    )

    _ = client.delete_model_card(ModelCardName="my-first-model-card")
    resp = client.list_model_cards().get("ModelCardSummaries")
    assert len(resp) == 0

    with pytest.raises(ClientError) as e:
        client.delete_model_card(ModelCardName="my-first-model-card")
    assert e.value.response["Error"]["Code"] == "ResourceNotFound"
