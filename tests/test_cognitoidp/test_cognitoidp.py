import base64
import datetime
import hashlib
import hmac
import json
import os
import random
import re
import time
import uuid
from unittest import SkipTest, mock

import boto3
import pycognito
import pyotp
import pytest
import requests
from botocore.exceptions import ClientError, ParamValidationError
from joserfc import jwk, jws, jwt

import moto.cognitoidp.models
from moto import cognitoidp, mock_aws, settings
from moto.cognitoidp.utils import create_id
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.core import set_initial_no_auth_action_count
from moto.utilities.utils import load_resource
from tests import allow_aws_request
from tests.test_cognitoidp import cognitoidp_aws_verified

private_key = load_resource(cognitoidp.__name__, "resources/jwks-private.json")
PUBLIC_KEY = jwk.RSAKey.import_key(private_key)


@mock_aws
def test_create_user_pool():
    conn = boto3.client("cognito-idp", "us-west-2")

    name = str(uuid.uuid4())
    value = str(uuid.uuid4())
    result = conn.create_user_pool(PoolName=name, LambdaConfig={"PreSignUp": value})

    assert (
        result["UserPool"]["Arn"]
        == f"arn:aws:cognito-idp:us-west-2:{ACCOUNT_ID}:userpool/{result['UserPool']['Id']}"
    )
    assert result["UserPool"]["Name"] == name
    assert result["UserPool"]["LambdaConfig"]["PreSignUp"] == value

    assert "RequestId" in result["ResponseMetadata"]


@mock_aws
def test_create_user_pool__overwrite_template_messages():
    client = boto3.client("cognito-idp", "us-east-2")
    resp = client.create_user_pool(
        PoolName="test",
        VerificationMessageTemplate={
            "DefaultEmailOption": "CONFIRM_WITH_LINK",
            "EmailMessage": "foo {####} bar",
            "EmailMessageByLink": "{##foobar##}",
            "EmailSubject": "foobar {####}",
            "EmailSubjectByLink": "foobar",
            "SmsMessage": "{####} baz",
        },
    )
    pool = resp["UserPool"]
    assert pool["SmsVerificationMessage"] == "{####} baz"
    assert pool["EmailVerificationSubject"] == "foobar {####}"
    assert pool["EmailVerificationMessage"] == "foo {####} bar"


@mock_aws
def test_create_user_pool_should_have_all_default_attributes_in_schema():
    conn = boto3.client("cognito-idp", "us-west-2")

    name = str(uuid.uuid4())
    result = conn.create_user_pool(PoolName=name)

    result_schema = result["UserPool"]["SchemaAttributes"]
    result_schema = {s["Name"]: s for s in result_schema}

    described_schema = conn.describe_user_pool(UserPoolId=result["UserPool"]["Id"])[
        "UserPool"
    ]["SchemaAttributes"]
    described_schema = {s["Name"]: s for s in described_schema}

    for schema in result_schema, described_schema:
        for (
            default_attr_name,
            default_attr,
        ) in moto.cognitoidp.models.CognitoIdpUserPoolAttribute.STANDARD_SCHEMA.items():
            attribute = schema[default_attr_name]
            assert attribute["Required"] == default_attr["Required"]
            assert attribute["AttributeDataType"] == default_attr["AttributeDataType"]
            assert attribute["Mutable"] == default_attr["Mutable"]
            assert attribute.get("StringAttributeConstraints") == default_attr.get(
                "StringAttributeConstraints"
            )
            assert attribute.get("NumberAttributeConstraints") == default_attr.get(
                "NumberAttributeConstraints"
            )
            assert attribute["DeveloperOnlyAttribute"] is False


@mock_aws
def test_create_user_pool_unknown_attribute_data_type():
    conn = boto3.client("cognito-idp", "us-west-2")

    name = str(uuid.uuid4())

    attribute_data_type = "Banana"
    with pytest.raises(ClientError) as ex:
        conn.create_user_pool(
            PoolName=name,
            Schema=[{"Name": "custom", "AttributeDataType": attribute_data_type}],
        )

    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == f"Validation error detected: Value '{attribute_data_type}' failed to satisfy constraint: Member must satisfy enum value set: [Boolean, Number, String, DateTime]"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_create_user_pool_custom_attribute_without_data_type():
    conn = boto3.client("cognito-idp", "us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.create_user_pool(PoolName=str(uuid.uuid4()), Schema=[{"Name": "custom"}])

    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid AttributeDataType input, consider using the provided AttributeDataType enum."
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_create_user_pool_custom_attribute_defaults():
    conn = boto3.client("cognito-idp", "us-west-2")
    res = conn.create_user_pool(
        PoolName=str(uuid.uuid4()),
        Schema=[
            {"Name": "string", "AttributeDataType": "String"},
            {"Name": "number", "AttributeDataType": "Number"},
        ],
    )
    string_attribute = next(
        attr
        for attr in res["UserPool"]["SchemaAttributes"]
        if attr["Name"] == "custom:string"
    )
    assert string_attribute["DeveloperOnlyAttribute"] is False
    assert string_attribute["Mutable"] is True

    number_attribute = next(
        attr
        for attr in res["UserPool"]["SchemaAttributes"]
        if attr["Name"] == "custom:number"
    )
    assert number_attribute["DeveloperOnlyAttribute"] is False
    assert number_attribute["Mutable"] is True
    assert "NumberAttributeConstraints" not in number_attribute


@mock_aws
def test_create_user_pool_custom_attribute_developer_only():
    conn = boto3.client("cognito-idp", "us-west-2")
    res = conn.create_user_pool(
        PoolName=str(uuid.uuid4()),
        Schema=[
            {
                "Name": "banana",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": True,
            },
        ],
    )
    # Note that this time we are looking for 'dev:xyz' attribute
    attribute = next(
        attr
        for attr in res["UserPool"]["SchemaAttributes"]
        if attr["Name"] == "dev:custom:banana"
    )
    assert attribute["DeveloperOnlyAttribute"] is True


@mock_aws
def test_create_user_pool_custom_attribute_required():
    conn = boto3.client("cognito-idp", "us-west-2")

    with pytest.raises(ClientError) as ex:
        conn.create_user_pool(
            PoolName=str(uuid.uuid4()),
            Schema=[
                {"Name": "banana", "AttributeDataType": "String", "Required": True},
            ],
        )
    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == "Required custom attributes are not supported currently."
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
@pytest.mark.parametrize(
    "attribute",
    [
        {"Name": "email", "AttributeDataType": "Number"},
        {"Name": "email", "DeveloperOnlyAttribute": True},
    ],
    ids=["standard_attribute", "developer_only"],
)
def test_create_user_pool_standard_attribute_with_changed_data_type_or_developer_only(
    attribute,
):
    conn = boto3.client("cognito-idp", "us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.create_user_pool(PoolName=str(uuid.uuid4()), Schema=[attribute])
    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == f"You can not change AttributeDataType or set developerOnlyAttribute for standard schema attribute {attribute['Name']}"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_create_user_pool_attribute_with_schema():
    conn = boto3.client("cognito-idp", "us-west-2")
    res = conn.create_user_pool(
        PoolName=str(uuid.uuid4()),
        Schema=[
            {
                "Name": "string",
                "AttributeDataType": "String",
                "NumberAttributeConstraints": {"MinValue": "10", "MaxValue": "20"},
                "StringAttributeConstraints": {"MinLength": "10", "MaxLength": "20"},
            },
            {
                "Name": "number",
                "AttributeDataType": "Number",
                "NumberAttributeConstraints": {"MinValue": "10", "MaxValue": "20"},
                "StringAttributeConstraints": {"MinLength": "10", "MaxLength": "20"},
            },
            {
                "Name": "boolean",
                "AttributeDataType": "Boolean",
                "NumberAttributeConstraints": {"MinValue": "10", "MaxValue": "20"},
                "StringAttributeConstraints": {"MinLength": "10", "MaxLength": "20"},
            },
        ],
    )
    string_attribute = next(
        attr
        for attr in res["UserPool"]["SchemaAttributes"]
        if attr["Name"] == "custom:string"
    )
    assert string_attribute["StringAttributeConstraints"] == {
        "MinLength": "10",
        "MaxLength": "20",
    }
    assert "NumberAttributeConstraints" not in string_attribute

    number_attribute = next(
        attr
        for attr in res["UserPool"]["SchemaAttributes"]
        if attr["Name"] == "custom:number"
    )
    assert number_attribute["NumberAttributeConstraints"] == {
        "MinValue": "10",
        "MaxValue": "20",
    }
    assert "StringAttributeConstraints" not in number_attribute

    boolean_attribute = next(
        attr
        for attr in res["UserPool"]["SchemaAttributes"]
        if attr["Name"] == "custom:boolean"
    )
    assert "NumberAttributeConstraints" not in boolean_attribute
    assert "StringAttributeConstraints" not in boolean_attribute


@mock_aws
def test_create_user_pool_attribute_partial_schema():
    conn = boto3.client("cognito-idp", "us-west-2")
    res = conn.create_user_pool(
        PoolName=str(uuid.uuid4()),
        Schema=[
            {
                "Name": "string_no_min",
                "AttributeDataType": "String",
                "StringAttributeConstraints": {"MaxLength": "10"},
            },
            {
                "Name": "string_no_max",
                "AttributeDataType": "String",
                "StringAttributeConstraints": {"MinLength": "10"},
            },
            {
                "Name": "number_no_min",
                "AttributeDataType": "Number",
                "NumberAttributeConstraints": {"MaxValue": "10"},
            },
            {
                "Name": "number_no_max",
                "AttributeDataType": "Number",
                "NumberAttributeConstraints": {"MinValue": "10"},
            },
        ],
    )
    string_no_min = next(
        attr
        for attr in res["UserPool"]["SchemaAttributes"]
        if attr["Name"] == "custom:string_no_min"
    )
    string_no_max = next(
        attr
        for attr in res["UserPool"]["SchemaAttributes"]
        if attr["Name"] == "custom:string_no_max"
    )
    number_no_min = next(
        attr
        for attr in res["UserPool"]["SchemaAttributes"]
        if attr["Name"] == "custom:number_no_min"
    )
    number_no_max = next(
        attr
        for attr in res["UserPool"]["SchemaAttributes"]
        if attr["Name"] == "custom:number_no_max"
    )

    assert string_no_min["StringAttributeConstraints"]["MaxLength"] == "10"
    assert "MinLength" not in string_no_min["StringAttributeConstraints"]
    assert string_no_max["StringAttributeConstraints"]["MinLength"] == "10"
    assert "MaxLength" not in string_no_max["StringAttributeConstraints"]
    assert number_no_min["NumberAttributeConstraints"]["MaxValue"] == "10"
    assert "MinValue" not in number_no_min["NumberAttributeConstraints"]
    assert number_no_max["NumberAttributeConstraints"]["MinValue"] == "10"
    assert "MaxValue" not in number_no_max["NumberAttributeConstraints"]


@mock_aws
@pytest.mark.parametrize(
    ("constraint_type", "attribute"),
    [
        (
            "StringAttributeConstraints",
            {
                "Name": "email",
                "AttributeDataType": "String",
                "StringAttributeConstraints": {"MinLength": "invalid_value"},
            },
        ),
        (
            "StringAttributeConstraints",
            {
                "Name": "email",
                "AttributeDataType": "String",
                "StringAttributeConstraints": {"MaxLength": "invalid_value"},
            },
        ),
        (
            "NumberAttributeConstraints",
            {
                "Name": "updated_at",
                "AttributeDataType": "Number",
                "NumberAttributeConstraints": {"MaxValue": "invalid_value"},
            },
        ),
        (
            "NumberAttributeConstraints",
            {
                "Name": "updated_at",
                "AttributeDataType": "Number",
                "NumberAttributeConstraints": {"MinValue": "invalid_value"},
            },
        ),
    ],
    ids=[
        "invalid_min_length",
        "invalid_max_length",
        "invalid_max_value",
        "invalid_min_value",
    ],
)
def test_create_user_pool_invalid_schema_values(constraint_type, attribute):
    conn = boto3.client("cognito-idp", "us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.create_user_pool(PoolName=str(uuid.uuid4()), Schema=[attribute])
    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == f"Invalid {constraint_type} for schema attribute {attribute['Name']}"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
@pytest.mark.parametrize(
    "attribute",
    [
        {
            "Name": "email",
            "AttributeDataType": "String",
            "StringAttributeConstraints": {"MinLength": "2049"},
        },
        {
            "Name": "email",
            "AttributeDataType": "String",
            "StringAttributeConstraints": {"MaxLength": "2049"},
        },
    ],
    ids=["invalid_min_length", "invalid_max_length"],
)
def test_create_user_pool_string_schema_max_length_over_2048(attribute):
    conn = boto3.client("cognito-idp", "us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.create_user_pool(PoolName=str(uuid.uuid4()), Schema=[attribute])
    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == f"user.{attribute['Name']}: String attributes cannot have a length of more than 2048"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_create_user_pool_string_schema_min_bigger_than_max():
    conn = boto3.client("cognito-idp", "us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.create_user_pool(
            PoolName=str(uuid.uuid4()),
            Schema=[
                {
                    "Name": "email",
                    "AttributeDataType": "String",
                    "StringAttributeConstraints": {"MinLength": "2", "MaxLength": "1"},
                }
            ],
        )
    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == "user.email: Max length cannot be less than min length."
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_create_user_pool_number_schema_min_bigger_than_max():
    conn = boto3.client("cognito-idp", "us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.create_user_pool(
            PoolName=str(uuid.uuid4()),
            Schema=[
                {
                    "Name": "updated_at",
                    "AttributeDataType": "Number",
                    "NumberAttributeConstraints": {"MinValue": "2", "MaxValue": "1"},
                }
            ],
        )
    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == "user.updated_at: Max value cannot be less than min value."
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_add_custom_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")
    pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    custom_attribute = {"Name": "banana", "AttributeDataType": "String"}

    res = conn.add_custom_attributes(
        UserPoolId=pool_id, CustomAttributes=[custom_attribute]
    )
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 200

    res = conn.describe_user_pool(UserPoolId=pool_id)
    described_attribute = next(
        attr
        for attr in res["UserPool"]["SchemaAttributes"]
        if attr["Name"] == "custom:banana"
    )
    # Skip verification - already covered by create_user_pool with custom attributes
    assert described_attribute is not None


@mock_aws
def test_add_custom_attributes_existing_attribute():
    conn = boto3.client("cognito-idp", "us-west-2")

    custom_attribute = {
        "Name": "banana",
        "AttributeDataType": "String",
        "DeveloperOnlyAttribute": True,
    }
    pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), Schema=[custom_attribute]
    )["UserPool"]["Id"]

    with pytest.raises(ClientError) as ex:
        conn.add_custom_attributes(
            UserPoolId=pool_id, CustomAttributes=[custom_attribute]
        )

    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == "custom:banana: Existing attribute already has name dev:custom:banana."
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_create_user_pool_default_id_strategy():
    conn = boto3.client("cognito-idp", "us-west-2")

    first_pool = conn.create_user_pool(PoolName="default-pool")
    second_pool = conn.create_user_pool(PoolName="default-pool")

    assert first_pool["UserPool"]["Id"] != second_pool["UserPool"]["Id"]


@mock_aws
@mock.patch.dict(os.environ, {"MOTO_COGNITO_IDP_USER_POOL_ID_STRATEGY": "HASH"})
def test_create_user_pool_hash_id_strategy_with_equal_pool_name():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cannot set environemnt variables in ServerMode")

    conn = boto3.client("cognito-idp", "us-west-2")

    first_pool = conn.create_user_pool(PoolName="default-pool")
    second_pool = conn.create_user_pool(PoolName="default-pool")

    assert first_pool["UserPool"]["Id"] == second_pool["UserPool"]["Id"]


@mock_aws
@mock.patch.dict(os.environ, {"MOTO_COGNITO_IDP_USER_POOL_ID_STRATEGY": "HASH"})
def test_create_user_pool_hash_id_strategy_with_different_pool_name():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cannot set environemnt variables in ServerMode")

    conn = boto3.client("cognito-idp", "us-west-2")

    first_pool = conn.create_user_pool(PoolName="first-pool")
    second_pool = conn.create_user_pool(PoolName="second-pool")

    assert first_pool["UserPool"]["Id"] != second_pool["UserPool"]["Id"]


@mock_aws
@mock.patch.dict(os.environ, {"MOTO_COGNITO_IDP_USER_POOL_ID_STRATEGY": "HASH"})
def test_create_user_pool_hash_id_strategy_with_different_attributes():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cannot set environemnt variables in ServerMode")

    conn = boto3.client("cognito-idp", "us-west-2")

    first_pool = conn.create_user_pool(
        PoolName="default-pool",
        Schema=[
            {
                "Name": "first",
                "AttributeDataType": "String",
            }
        ],
    )
    second_pool = conn.create_user_pool(
        PoolName="default-pool",
        Schema=[
            {
                "Name": "second",
                "AttributeDataType": "String",
            }
        ],
    )

    assert first_pool["UserPool"]["Id"] != second_pool["UserPool"]["Id"]


@mock_aws
def test_list_user_pools():
    conn = boto3.client("cognito-idp", "us-west-2")

    name = str(uuid.uuid4())
    conn.create_user_pool(PoolName=name)
    result = conn.list_user_pools(MaxResults=10)
    assert len(result["UserPools"]) == 1
    assert result["UserPools"][0]["Name"] == name


@pytest.mark.aws_verified
@cognitoidp_aws_verified()
def test_authorize_user_with_force_password_change_status(
    user_pool=None, user_pool_client=None
):
    conn = boto3.client("cognito-idp", "us-west-2")
    pool_id = user_pool["UserPool"]["Id"]
    client_id = user_pool_client["UserPoolClient"]["ClientId"]

    username = "test@example.com"
    temp_password = "Tempor@ryPassword123"
    new_password = "NewP@ssword456"

    aws_srp = pycognito.aws_srp.AWSSRP(
        username=username,
        password=temp_password,
        pool_id=pool_id,
        client_id=client_id,
        client=conn,
    )
    auth_params = aws_srp.get_auth_params()

    conn.admin_create_user(
        UserPoolId=pool_id,
        Username=username,
        TemporaryPassword=temp_password,
    )

    # Initiate USER_SRP_AUTH flow
    result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_SRP_AUTH",
        AuthParameters=auth_params,
    )

    # Try to log in with user in status FORCE_CHANGE_PASSWORD
    challenge_response = aws_srp.process_challenge(
        result["ChallengeParameters"], auth_params
    )
    result = conn.respond_to_auth_challenge(
        ClientId=client_id,
        ChallengeName=result["ChallengeName"],
        ChallengeResponses=challenge_response,
    )
    assert result["ChallengeName"] == "NEW_PASSWORD_REQUIRED"
    assert result["Session"] is not None

    # Sets a new password to the user and log it in
    result = conn.respond_to_auth_challenge(
        ClientId=client_id,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        Session=result["Session"],
        ChallengeResponses={
            "USERNAME": username,
            "NEW_PASSWORD": new_password,
        },
    )
    assert result["AuthenticationResult"]["TokenType"] == "Bearer"
    assert result["AuthenticationResult"]["AccessToken"] is not None
    assert result["AuthenticationResult"]["RefreshToken"] is not None


@mock_aws
def test_set_user_pool_mfa_config():
    conn = boto3.client("cognito-idp", "us-west-2")

    name = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=name)["UserPool"]["Id"]

    # Test error for when neither token nor sms configuration is provided
    with pytest.raises(ClientError) as ex:
        conn.set_user_pool_mfa_config(UserPoolId=user_pool_id, MfaConfiguration="ON")

    assert ex.value.operation_name == "SetUserPoolMfaConfig"
    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == "At least one of [SmsMfaConfiguration] or [SoftwareTokenMfaConfiguration] must be provided."
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400

    # Test error for when sms config is missing `SmsConfiguration`
    with pytest.raises(ClientError) as ex:
        conn.set_user_pool_mfa_config(
            UserPoolId=user_pool_id, SmsMfaConfiguration={}, MfaConfiguration="ON"
        )

    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == "[SmsConfiguration] is a required member of [SoftwareTokenMfaConfiguration]."
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400

    # Test error for when `SmsConfiguration` is missing `SnsCaller`
    # This is asserted by boto3
    with pytest.raises(ParamValidationError) as ex:
        conn.set_user_pool_mfa_config(
            UserPoolId=user_pool_id,
            SmsMfaConfiguration={"SmsConfiguration": {}},
            MfaConfiguration="ON",
        )

    # Test error for when `MfaConfiguration` is not one of the expected values
    with pytest.raises(ClientError) as ex:
        conn.set_user_pool_mfa_config(
            UserPoolId=user_pool_id,
            SoftwareTokenMfaConfiguration={"Enabled": True},
            MfaConfiguration="Invalid",
        )

    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == "[MfaConfiguration] must be one of 'ON', 'OFF', or 'OPTIONAL'."
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400

    # Enable software token MFA
    mfa_config = conn.set_user_pool_mfa_config(
        UserPoolId=user_pool_id,
        SoftwareTokenMfaConfiguration={"Enabled": True},
        MfaConfiguration="ON",
    )

    assert "SmsMfaConfiguration" not in mfa_config
    assert mfa_config["MfaConfiguration"] == "ON"
    assert mfa_config["SoftwareTokenMfaConfiguration"] == {"Enabled": True}

    # Response from describe should match
    pool = conn.describe_user_pool(UserPoolId=user_pool_id)["UserPool"]
    assert pool["MfaConfiguration"] == "ON"

    # Disable MFA
    mfa_config = conn.set_user_pool_mfa_config(
        UserPoolId=user_pool_id, MfaConfiguration="OFF"
    )

    assert "SmsMfaConfiguration" not in mfa_config
    assert "SoftwareTokenMfaConfiguration" not in mfa_config
    assert mfa_config["MfaConfiguration"] == "OFF"

    # Response from describe should match
    pool = conn.describe_user_pool(UserPoolId=user_pool_id)["UserPool"]
    assert pool["MfaConfiguration"] == "OFF"

    # `SnsCallerArn` needs to be at least 20 long
    sms_config = {"SmsConfiguration": {"SnsCallerArn": "01234567890123456789"}}

    # Enable SMS MFA
    mfa_config = conn.set_user_pool_mfa_config(
        UserPoolId=user_pool_id, SmsMfaConfiguration=sms_config, MfaConfiguration="ON"
    )

    assert "SoftwareTokenMfaConfiguration" not in mfa_config
    assert mfa_config["SmsMfaConfiguration"] == sms_config
    assert mfa_config["MfaConfiguration"] == "ON"


@mock_aws
def test_list_user_pools_returns_max_items():
    conn = boto3.client("cognito-idp", "us-west-2")

    # Given 10 user pools
    pool_count = 10
    for _ in range(pool_count):
        conn.create_user_pool(PoolName=str(uuid.uuid4()))

    max_results = 5
    result = conn.list_user_pools(MaxResults=max_results)
    assert len(result["UserPools"]) == max_results
    assert "NextToken" in result


@mock_aws
def test_list_user_pools_returns_next_tokens():
    conn = boto3.client("cognito-idp", "us-west-2")

    # Given 10 user pool clients
    pool_count = 10
    for _ in range(pool_count):
        conn.create_user_pool(PoolName=str(uuid.uuid4()))

    max_results = 5
    result = conn.list_user_pools(MaxResults=max_results)
    assert len(result["UserPools"]) == max_results
    assert "NextToken" in result

    next_token = result["NextToken"]
    result_2 = conn.list_user_pools(MaxResults=max_results, NextToken=next_token)
    assert len(result_2["UserPools"]) == max_results
    assert "NextToken" not in result_2


@mock_aws
def test_list_user_pools_when_max_items_more_than_total_items():
    conn = boto3.client("cognito-idp", "us-west-2")

    # Given 10 user pool clients
    pool_count = 10
    for _ in range(pool_count):
        conn.create_user_pool(PoolName=str(uuid.uuid4()))

    max_results = pool_count + 5
    result = conn.list_user_pools(MaxResults=max_results)
    assert len(result["UserPools"]) == pool_count
    assert "NextToken" not in result


@mock_aws
def test_describe_user_pool():
    conn = boto3.client("cognito-idp", "us-west-2")

    name = str(uuid.uuid4())
    value = str(uuid.uuid4())
    recovery_mechanisms = [{"Name": "verified_email", "Priority": 1}]
    user_pool_details = conn.create_user_pool(
        PoolName=name,
        LambdaConfig={"PreSignUp": value},
        AccountRecoverySetting={"RecoveryMechanisms": recovery_mechanisms},
    )
    result = conn.describe_user_pool(UserPoolId=user_pool_details["UserPool"]["Id"])
    assert result["UserPool"]["Name"] == name
    assert result["UserPool"]["LambdaConfig"]["PreSignUp"] == value
    assert (
        result["UserPool"]["AccountRecoverySetting"]["RecoveryMechanisms"]
        == recovery_mechanisms
    )


@mock_aws
def test_describe_user_pool_estimated_number_of_users():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    result = conn.describe_user_pool(UserPoolId=user_pool_id)
    assert result["UserPool"]["EstimatedNumberOfUsers"] == 0

    users_count = random.randint(2, 6)
    for _ in range(users_count):
        conn.admin_create_user(UserPoolId=user_pool_id, Username=str(uuid.uuid4()))

    result = conn.describe_user_pool(UserPoolId=user_pool_id)
    assert result["UserPool"]["EstimatedNumberOfUsers"] == users_count


@mock_aws
def test_describe_user_pool_resource_not_found():
    conn = boto3.client("cognito-idp", "us-east-1")

    user_pool_id = "us-east-1_FooBar123"
    with pytest.raises(ClientError) as exc:
        conn.describe_user_pool(UserPoolId=user_pool_id)

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"User pool {user_pool_id} does not exist."


@mock_aws
def test_update_user_pool():
    conn = boto3.client("cognito-idp", "us-east-1")

    name = str(uuid.uuid4())
    user_pool_details = conn.create_user_pool(
        PoolName=name,
        Policies={
            "PasswordPolicy": {
                "MinimumLength": 12,
                "RequireUppercase": False,
                "RequireLowercase": False,
                "RequireNumbers": False,
                "RequireSymbols": False,
            }
        },
    )

    new_policies = {
        "PasswordPolicy": {
            "MinimumLength": 16,
            "RequireUppercase": True,
            "RequireLowercase": True,
            "RequireNumbers": True,
            "RequireSymbols": True,
        }
    }
    conn.update_user_pool(
        UserPoolId=user_pool_details["UserPool"]["Id"], Policies=new_policies
    )

    updated_user_pool_details = conn.describe_user_pool(
        UserPoolId=user_pool_details["UserPool"]["Id"]
    )
    assert updated_user_pool_details["UserPool"]["Policies"] == new_policies
    assert updated_user_pool_details["UserPool"]["AdminCreateUserConfig"] is not None
    assert updated_user_pool_details["UserPool"]["EmailConfiguration"] is not None
    assert (
        updated_user_pool_details["UserPool"]["VerificationMessageTemplate"] is not None
    )
    assert updated_user_pool_details["UserPool"]["AccountRecoverySetting"] is not None


@mock_aws
def test_delete_user_pool():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    assert len(conn.list_user_pools(MaxResults=10)["UserPools"]) == 1
    conn.delete_user_pool(UserPoolId=user_pool_id)
    assert len(conn.list_user_pools(MaxResults=10)["UserPools"]) == 0


@mock_aws
def test_create_user_pool_domain():
    conn = boto3.client("cognito-idp", "us-west-2")

    domain = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    result = conn.create_user_pool_domain(UserPoolId=user_pool_id, Domain=domain)
    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert result["CloudFrontDomain"] is not None


@mock_aws
def test_create_user_pool_domain_custom_domain_config():
    conn = boto3.client("cognito-idp", "us-west-2")

    domain = str(uuid.uuid4())
    custom_domain_config = {
        "CertificateArn": f"arn:aws:acm:us-east-1:{ACCOUNT_ID}:certificate/123456789012"
    }
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    result = conn.create_user_pool_domain(
        UserPoolId=user_pool_id, Domain=domain, CustomDomainConfig=custom_domain_config
    )
    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert result["CloudFrontDomain"] == "e2c343b3293ee505.cloudfront.net"


@mock_aws
def test_describe_user_pool_domain():
    conn = boto3.client("cognito-idp", "us-west-2")

    domain = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_user_pool_domain(UserPoolId=user_pool_id, Domain=domain)
    result = conn.describe_user_pool_domain(Domain=domain)
    assert result["DomainDescription"]["Domain"] == domain
    assert result["DomainDescription"]["UserPoolId"] == user_pool_id
    assert result["DomainDescription"]["AWSAccountId"] is not None
    result = conn.describe_user_pool(UserPoolId=user_pool_id)
    assert result["UserPool"]["Domain"] == domain


@mock_aws
def test_delete_user_pool_domain():
    conn = boto3.client("cognito-idp", "us-west-2")

    domain = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_user_pool_domain(UserPoolId=user_pool_id, Domain=domain)
    result = conn.delete_user_pool_domain(UserPoolId=user_pool_id, Domain=domain)
    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200
    result = conn.describe_user_pool_domain(Domain=domain)
    # This is a surprising behavior of the real service: describing a missing domain comes
    # back with status 200 and a DomainDescription of {}
    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(result["DomainDescription"].keys()) == 0


@mock_aws
def test_update_user_pool_domain():
    conn = boto3.client("cognito-idp", "us-west-2")

    domain = str(uuid.uuid4())
    custom_domain_config = {
        "CertificateArn": f"arn:aws:acm:us-east-1:{ACCOUNT_ID}:certificate/123456789012"
    }
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_user_pool_domain(UserPoolId=user_pool_id, Domain=domain)
    result = conn.update_user_pool_domain(
        UserPoolId=user_pool_id, Domain=domain, CustomDomainConfig=custom_domain_config
    )
    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert result["CloudFrontDomain"] == "e2c343b3293ee505.cloudfront.net"


@mock_aws
def test_create_user_pool_client():
    conn = boto3.client("cognito-idp", "us-west-2")

    client_name = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    result = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=client_name, CallbackURLs=[value]
    )

    assert result["UserPoolClient"]["UserPoolId"] == user_pool_id
    assert bool(re.match(r"^[0-9a-z]{26}$", result["UserPoolClient"]["ClientId"]))
    assert result["UserPoolClient"]["ClientName"] == client_name
    assert "ClientSecret" not in result["UserPoolClient"]
    assert len(result["UserPoolClient"]["CallbackURLs"]) == 1
    assert result["UserPoolClient"]["CallbackURLs"][0] == value


@mock_aws
def test_create_user_pool_client_returns_secret():
    conn = boto3.client("cognito-idp", "us-west-2")

    client_name = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    result = conn.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=client_name,
        GenerateSecret=True,
        CallbackURLs=[value],
    )

    assert result["UserPoolClient"]["UserPoolId"] == user_pool_id
    assert bool(re.match(r"^[0-9a-z]{26}$", result["UserPoolClient"]["ClientId"]))
    assert result["UserPoolClient"]["ClientName"] == client_name
    assert result["UserPoolClient"]["ClientSecret"] is not None
    assert len(result["UserPoolClient"]["CallbackURLs"]) == 1
    assert result["UserPoolClient"]["CallbackURLs"][0] == value


@mock_aws
def test_list_user_pool_clients():
    conn = boto3.client("cognito-idp", "us-west-2")

    client_name = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_user_pool_client(UserPoolId=user_pool_id, ClientName=client_name)
    result = conn.list_user_pool_clients(UserPoolId=user_pool_id, MaxResults=10)
    assert len(result["UserPoolClients"]) == 1
    assert result["UserPoolClients"][0]["ClientName"] == client_name


@mock_aws
def test_list_user_pool_clients_returns_max_items():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    # Given 10 user pool clients
    client_count = 10
    for _ in range(client_count):
        client_name = str(uuid.uuid4())
        conn.create_user_pool_client(UserPoolId=user_pool_id, ClientName=client_name)
    max_results = 5
    result = conn.list_user_pool_clients(
        UserPoolId=user_pool_id, MaxResults=max_results
    )
    assert len(result["UserPoolClients"]) == max_results
    assert "NextToken" in result


@mock_aws
def test_list_user_pool_clients_returns_next_tokens():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    # Given 10 user pool clients
    client_count = 10
    for _ in range(client_count):
        client_name = str(uuid.uuid4())
        conn.create_user_pool_client(UserPoolId=user_pool_id, ClientName=client_name)
    max_results = 5
    result = conn.list_user_pool_clients(
        UserPoolId=user_pool_id, MaxResults=max_results
    )
    assert len(result["UserPoolClients"]) == max_results
    assert "NextToken" in result

    next_token = result["NextToken"]
    result_2 = conn.list_user_pool_clients(
        UserPoolId=user_pool_id, MaxResults=max_results, NextToken=next_token
    )
    assert len(result_2["UserPoolClients"]) == max_results
    assert "NextToken" not in result_2


@mock_aws
def test_list_user_pool_clients_when_max_items_more_than_total_items():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    # Given 10 user pool clients
    client_count = 10
    for _ in range(client_count):
        client_name = str(uuid.uuid4())
        conn.create_user_pool_client(UserPoolId=user_pool_id, ClientName=client_name)
    max_results = client_count + 5
    result = conn.list_user_pool_clients(
        UserPoolId=user_pool_id, MaxResults=max_results
    )
    assert len(result["UserPoolClients"]) == client_count
    assert "NextToken" not in result


@mock_aws
def test_describe_user_pool_client():
    conn = boto3.client("cognito-idp", "us-west-2")

    client_name = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_details = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=client_name, CallbackURLs=[value]
    )

    result = conn.describe_user_pool_client(
        UserPoolId=user_pool_id, ClientId=client_details["UserPoolClient"]["ClientId"]
    )

    assert result["UserPoolClient"]["ClientName"] == client_name
    assert len(result["UserPoolClient"]["CallbackURLs"]) == 1
    assert result["UserPoolClient"]["CallbackURLs"][0] == value


@mock_aws
def test_update_user_pool_client():
    conn = boto3.client("cognito-idp", "us-west-2")

    old_client_name = str(uuid.uuid4())
    new_client_name = str(uuid.uuid4())
    old_value = str(uuid.uuid4())
    new_value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_details = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=old_client_name, CallbackURLs=[old_value]
    )

    result = conn.update_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=client_details["UserPoolClient"]["ClientId"],
        ClientName=new_client_name,
        CallbackURLs=[new_value],
    )

    assert result["UserPoolClient"]["ClientName"] == new_client_name
    assert "ClientSecret" not in result["UserPoolClient"]
    assert len(result["UserPoolClient"]["CallbackURLs"]) == 1
    assert result["UserPoolClient"]["CallbackURLs"][0] == new_value


@mock_aws
def test_update_user_pool_client_returns_secret():
    conn = boto3.client("cognito-idp", "us-west-2")

    old_client_name = str(uuid.uuid4())
    new_client_name = str(uuid.uuid4())
    old_value = str(uuid.uuid4())
    new_value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_details = conn.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=old_client_name,
        GenerateSecret=True,
        CallbackURLs=[old_value],
    )
    client_secret = client_details["UserPoolClient"]["ClientSecret"]

    result = conn.update_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=client_details["UserPoolClient"]["ClientId"],
        ClientName=new_client_name,
        CallbackURLs=[new_value],
    )

    assert result["UserPoolClient"]["ClientName"] == new_client_name
    assert result["UserPoolClient"]["ClientSecret"] == client_secret
    assert len(result["UserPoolClient"]["CallbackURLs"]) == 1
    assert result["UserPoolClient"]["CallbackURLs"][0] == new_value


@mock_aws
def test_delete_user_pool_client():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_details = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4())
    )

    conn.delete_user_pool_client(
        UserPoolId=user_pool_id, ClientId=client_details["UserPoolClient"]["ClientId"]
    )

    with pytest.raises(ClientError) as exc:
        conn.describe_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_details["UserPoolClient"]["ClientId"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_create_identity_provider():
    conn = boto3.client("cognito-idp", "us-west-2")

    provider_name = str(uuid.uuid4())
    provider_type = "Facebook"
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    result = conn.create_identity_provider(
        UserPoolId=user_pool_id,
        ProviderName=provider_name,
        ProviderType=provider_type,
        ProviderDetails={"thing": value},
    )

    assert result["IdentityProvider"]["UserPoolId"] == user_pool_id
    assert result["IdentityProvider"]["ProviderName"] == provider_name
    assert result["IdentityProvider"]["ProviderType"] == provider_type
    assert result["IdentityProvider"]["ProviderDetails"]["thing"] == value


@mock_aws
def test_list_identity_providers():
    conn = boto3.client("cognito-idp", "us-west-2")

    provider_name = str(uuid.uuid4())
    provider_type = "Facebook"
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_identity_provider(
        UserPoolId=user_pool_id,
        ProviderName=provider_name,
        ProviderType=provider_type,
        ProviderDetails={},
    )

    result = conn.list_identity_providers(UserPoolId=user_pool_id, MaxResults=10)

    assert len(result["Providers"]) == 1
    assert result["Providers"][0]["ProviderName"] == provider_name
    assert result["Providers"][0]["ProviderType"] == provider_type


@mock_aws
def test_list_identity_providers_returns_max_items():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    # Given 10 identity providers linked to a user pool
    identity_provider_count = 10
    for _ in range(identity_provider_count):
        provider_name = str(uuid.uuid4())
        provider_type = "Facebook"
        conn.create_identity_provider(
            UserPoolId=user_pool_id,
            ProviderName=provider_name,
            ProviderType=provider_type,
            ProviderDetails={},
        )

    max_results = 5
    result = conn.list_identity_providers(
        UserPoolId=user_pool_id, MaxResults=max_results
    )
    assert len(result["Providers"]) == max_results
    assert "NextToken" in result


@mock_aws
def test_list_identity_providers_returns_next_tokens():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    # Given 10 identity providers linked to a user pool
    identity_provider_count = 10
    for _ in range(identity_provider_count):
        provider_name = str(uuid.uuid4())
        provider_type = "Facebook"
        conn.create_identity_provider(
            UserPoolId=user_pool_id,
            ProviderName=provider_name,
            ProviderType=provider_type,
            ProviderDetails={},
        )

    max_results = 5
    result = conn.list_identity_providers(
        UserPoolId=user_pool_id, MaxResults=max_results
    )
    assert len(result["Providers"]) == max_results
    assert "NextToken" in result

    next_token = result["NextToken"]
    result_2 = conn.list_identity_providers(
        UserPoolId=user_pool_id, MaxResults=max_results, NextToken=next_token
    )
    assert len(result_2["Providers"]) == max_results
    assert "NextToken" not in result_2


@mock_aws
def test_list_identity_providers_when_max_items_more_than_total_items():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    # Given 10 identity providers linked to a user pool
    identity_provider_count = 10
    for _ in range(identity_provider_count):
        provider_name = str(uuid.uuid4())
        provider_type = "Facebook"
        conn.create_identity_provider(
            UserPoolId=user_pool_id,
            ProviderName=provider_name,
            ProviderType=provider_type,
            ProviderDetails={},
        )

    max_results = identity_provider_count + 5
    result = conn.list_identity_providers(
        UserPoolId=user_pool_id, MaxResults=max_results
    )
    assert len(result["Providers"]) == identity_provider_count
    assert "NextToken" not in result


@mock_aws
def test_describe_identity_providers():
    conn = boto3.client("cognito-idp", "us-west-2")

    provider_name = str(uuid.uuid4())
    provider_type = "Facebook"
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_identity_provider(
        UserPoolId=user_pool_id,
        ProviderName=provider_name,
        ProviderType=provider_type,
        ProviderDetails={"thing": value},
    )

    result = conn.describe_identity_provider(
        UserPoolId=user_pool_id, ProviderName=provider_name
    )

    assert result["IdentityProvider"]["UserPoolId"] == user_pool_id
    assert result["IdentityProvider"]["ProviderName"] == provider_name
    assert result["IdentityProvider"]["ProviderType"] == provider_type
    assert result["IdentityProvider"]["ProviderDetails"]["thing"] == value


@mock_aws
def test_update_identity_provider():
    conn = boto3.client("cognito-idp", "us-west-2")

    provider_name = str(uuid.uuid4())
    provider_type = "Facebook"
    value = str(uuid.uuid4())
    new_value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_identity_provider(
        UserPoolId=user_pool_id,
        ProviderName=provider_name,
        ProviderType=provider_type,
        ProviderDetails={"thing": value},
    )

    result = conn.update_identity_provider(
        UserPoolId=user_pool_id,
        ProviderName=provider_name,
        ProviderDetails={"thing": new_value},
        AttributeMapping={"email": "email", "username": "sub"},
    )["IdentityProvider"]

    assert result["UserPoolId"] == user_pool_id
    assert result["ProviderName"] == provider_name
    assert result["ProviderType"] == provider_type
    assert result["ProviderDetails"]["thing"] == new_value
    assert result["AttributeMapping"] == {"email": "email", "username": "sub"}


@mock_aws
def test_update_identity_provider_no_user_pool():
    conn = boto3.client("cognito-idp", "us-west-2")

    new_value = str(uuid.uuid4())

    with pytest.raises(conn.exceptions.ResourceNotFoundException) as cm:
        conn.update_identity_provider(
            UserPoolId="foo", ProviderName="bar", ProviderDetails={"thing": new_value}
        )

    assert cm.value.operation_name == "UpdateIdentityProvider"
    assert cm.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert cm.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_update_identity_provider_no_identity_provider():
    conn = boto3.client("cognito-idp", "us-west-2")

    new_value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    with pytest.raises(conn.exceptions.ResourceNotFoundException) as cm:
        conn.update_identity_provider(
            UserPoolId=user_pool_id,
            ProviderName="foo",
            ProviderDetails={"thing": new_value},
        )

    assert cm.value.operation_name == "UpdateIdentityProvider"
    assert cm.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert cm.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_delete_identity_providers():
    conn = boto3.client("cognito-idp", "us-west-2")

    provider_name = str(uuid.uuid4())
    provider_type = "Facebook"
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_identity_provider(
        UserPoolId=user_pool_id,
        ProviderName=provider_name,
        ProviderType=provider_type,
        ProviderDetails={"thing": value},
    )

    conn.delete_identity_provider(UserPoolId=user_pool_id, ProviderName=provider_name)

    with pytest.raises(ClientError) as exc:
        conn.describe_identity_provider(
            UserPoolId=user_pool_id, ProviderName=provider_name
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_create_group():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    description = str(uuid.uuid4())
    role_arn = "arn:aws:iam:::role/my-iam-role"
    precedence = random.randint(0, 100000)

    result = conn.create_group(
        GroupName=group_name,
        UserPoolId=user_pool_id,
        Description=description,
        RoleArn=role_arn,
        Precedence=precedence,
    )

    assert result["Group"]["GroupName"] == group_name
    assert result["Group"]["UserPoolId"] == user_pool_id
    assert result["Group"]["Description"] == description
    assert result["Group"]["RoleArn"] == role_arn
    assert result["Group"]["Precedence"] == precedence
    assert isinstance(result["Group"]["LastModifiedDate"], datetime.datetime)
    assert isinstance(result["Group"]["CreationDate"], datetime.datetime)


@mock_aws
def test_update_group():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    description = str(uuid.uuid4())
    description2 = str(uuid.uuid4())
    role_arn = "arn:aws:iam:::role/my-iam-role"
    role_arn2 = "arn:aws:iam:::role/my-iam-role2"
    precedence = random.randint(0, 100000)
    precedence2 = random.randint(0, 100000)

    conn.create_group(
        GroupName=group_name,
        UserPoolId=user_pool_id,
        Description=description,
        RoleArn=role_arn,
        Precedence=precedence,
    )

    result = conn.update_group(
        GroupName=group_name,
        UserPoolId=user_pool_id,
        Description=description2,
        RoleArn=role_arn2,
        Precedence=precedence2,
    )

    assert result["Group"]["GroupName"] == group_name
    assert result["Group"]["UserPoolId"] == user_pool_id
    assert result["Group"]["Description"] == description2
    assert result["Group"]["RoleArn"] == role_arn2
    assert result["Group"]["Precedence"] == precedence2
    assert isinstance(result["Group"]["LastModifiedDate"], datetime.datetime)
    assert isinstance(result["Group"]["CreationDate"], datetime.datetime)


@pytest.mark.aws_verified
@cognitoidp_aws_verified(
    read_attributes=["given_name"], explicit_auth_flows=["ADMIN_NO_SRP_AUTH"]
)
def test_group_in_access_token(user_pool=None, user_pool_client=None):
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    temporary_password = "P2$Sword"
    user_pool_id = user_pool["UserPool"]["Id"]
    user_attribute_value = str(uuid.uuid4())
    group_name = str(uuid.uuid4())
    client_id = user_pool_client["UserPoolClient"]["ClientId"]

    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        TemporaryPassword=temporary_password,
        UserAttributes=[{"Name": "given_name", "Value": user_attribute_value}],
    )

    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )

    result = conn.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": temporary_password},
    )

    # A newly created user is forced to set a new password
    assert result["ChallengeName"] == "NEW_PASSWORD_REQUIRED"
    assert result["Session"] is not None

    # This sets a new password and logs the user in (creates tokens)
    new_password = "P2$Sword"
    result = conn.admin_respond_to_auth_challenge(
        UserPoolId=user_pool_id,
        Session=result["Session"],
        ClientId=client_id,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        ChallengeResponses={"USERNAME": username, "NEW_PASSWORD": new_password},
    )

    payload = get_jwt_payload(result["AuthenticationResult"]["AccessToken"])
    assert payload.claims["cognito:groups"] == [group_name]


@mock_aws
def test_other_attributes_in_id_token():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    temporary_password = "P2$Sword"
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()),
        Schema=[{"Name": "myattr", "AttributeDataType": "String"}],
    )["UserPool"]["Id"]

    user_attribute_name = str(uuid.uuid4())
    user_attribute_value = str(uuid.uuid4())
    group_name = str(uuid.uuid4())
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=str(uuid.uuid4()),
        ReadAttributes=[user_attribute_name],
    )["UserPoolClient"]["ClientId"]

    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        TemporaryPassword=temporary_password,
        UserAttributes=[
            {"Name": user_attribute_name, "Value": user_attribute_value},
            {"Name": "custom:myattr", "Value": "some val"},
        ],
    )

    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )

    result = conn.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": temporary_password},
    )

    # A newly created user is forced to set a new password
    assert result["ChallengeName"] == "NEW_PASSWORD_REQUIRED"
    assert result["Session"] is not None

    # This sets a new password and logs the user in (creates tokens)
    new_password = "P2$Sword"
    result = conn.admin_respond_to_auth_challenge(
        UserPoolId=user_pool_id,
        Session=result["Session"],
        ClientId=client_id,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        ChallengeResponses={"USERNAME": username, "NEW_PASSWORD": new_password},
    )

    payload = jwt.decode(result["AuthenticationResult"]["IdToken"], PUBLIC_KEY)
    claims = payload.claims
    assert claims["cognito:groups"] == [group_name]
    assert claims["custom:myattr"] == "some val"


@mock_aws
def test_create_group_with_duplicate_name_raises_error():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())

    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    with pytest.raises(ClientError) as cm:
        conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)
    assert cm.value.operation_name == "CreateGroup"
    assert cm.value.response["Error"]["Code"] == "GroupExistsException"
    assert cm.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_get_group():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    result = conn.get_group(GroupName=group_name, UserPoolId=user_pool_id)

    assert result["Group"]["GroupName"] == group_name
    assert result["Group"]["UserPoolId"] == user_pool_id
    assert isinstance(result["Group"]["LastModifiedDate"], datetime.datetime)
    assert isinstance(result["Group"]["CreationDate"], datetime.datetime)


@mock_aws
def test_list_groups():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    result = conn.list_groups(UserPoolId=user_pool_id)

    assert len(result["Groups"]) == 1
    assert result["Groups"][0]["GroupName"] == group_name


@mock_aws
def test_list_groups_returns_pagination_tokens():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    # Given 10 groups
    group_count = 10
    for _ in range(group_count):
        conn.create_group(UserPoolId=user_pool_id, GroupName=str(uuid.uuid4()))

    max_results = 5
    result = conn.list_groups(UserPoolId=user_pool_id, Limit=max_results)
    assert len(result["Groups"]) == max_results
    assert "NextToken" in result

    next_token = result["NextToken"]
    result_2 = conn.list_groups(
        UserPoolId=user_pool_id, Limit=max_results, NextToken=next_token
    )
    assert len(result_2["Groups"]) == max_results
    assert "NextToken" not in result_2


@mock_aws
def test_list_groups_when_limit_more_than_total_items():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    # Given 10 users
    group_count = 10
    for _ in range(group_count):
        conn.create_group(UserPoolId=user_pool_id, GroupName=str(uuid.uuid4()))

    max_results = group_count + 5
    result = conn.list_groups(UserPoolId=user_pool_id, Limit=max_results)
    assert len(result["Groups"]) == group_count
    assert "NextToken" not in result


@mock_aws
def test_delete_group():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    result = conn.delete_group(GroupName=group_name, UserPoolId=user_pool_id)
    assert list(result.keys()) == ["ResponseMetadata"]  # No response expected

    with pytest.raises(ClientError) as cm:
        conn.get_group(GroupName=group_name, UserPoolId=user_pool_id)
    assert cm.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_admin_add_user_to_group():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    username = str(uuid.uuid4())
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    result = conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )
    assert list(result.keys()) == ["ResponseMetadata"]  # No response expected


@mock_aws
def test_admin_add_user_to_group_with_username_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    username = "test@example.com"
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    result = conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )
    assert list(result.keys()) == ["ResponseMetadata"]  # No response expected


@mock_aws
def test_admin_add_user_to_group_again_is_noop():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    username = str(uuid.uuid4())
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )
    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )


@mock_aws
def test_list_users_in_group():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    username = str(uuid.uuid4())
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )

    result = conn.list_users_in_group(UserPoolId=user_pool_id, GroupName=group_name)

    assert len(result["Users"]) == 1
    assert result["Users"][0]["Username"] == username


@mock_aws
def test_list_users_in_group_ignores_deleted_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    username = str(uuid.uuid4())
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
    username2 = str(uuid.uuid4())
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username2)

    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )
    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username2, GroupName=group_name
    )
    conn.admin_delete_user(UserPoolId=user_pool_id, Username=username)

    result = conn.list_users_in_group(UserPoolId=user_pool_id, GroupName=group_name)

    assert len(result["Users"]) == 1
    assert result["Users"][0]["Username"] == username2


@mock_aws
def test_list_users_in_group_returns_pagination_tokens():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    # Given 10 users
    usernames = [str(uuid.uuid4()) for _ in range(10)]
    for username in usernames:
        conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
        conn.admin_add_user_to_group(
            UserPoolId=user_pool_id, Username=username, GroupName=group_name
        )

    max_results = 5
    result = conn.list_users_in_group(
        UserPoolId=user_pool_id, GroupName=group_name, Limit=max_results
    )
    assert len(result["Users"]) == max_results
    assert "NextToken" in result

    next_token = result["NextToken"]
    result_2 = conn.list_users_in_group(
        UserPoolId=user_pool_id,
        GroupName=group_name,
        Limit=max_results,
        NextToken=next_token,
    )
    assert len(result_2["Users"]) == max_results
    assert "NextToken" not in result_2


@mock_aws
def test_list_users_in_group_when_limit_more_than_total_items():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    # Given 10 users
    usernames = [str(uuid.uuid4()) for _ in range(10)]
    for username in usernames:
        conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
        conn.admin_add_user_to_group(
            UserPoolId=user_pool_id, Username=username, GroupName=group_name
        )

    max_results = len(usernames) + 5
    result = conn.list_users_in_group(
        UserPoolId=user_pool_id, GroupName=group_name, Limit=max_results
    )
    assert len(result["Users"]) == len(usernames)
    assert "NextToken" not in result


@mock_aws
def test_admin_list_groups_for_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    username = str(uuid.uuid4())
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )

    result = conn.admin_list_groups_for_user(Username=username, UserPoolId=user_pool_id)

    assert len(result["Groups"]) == 1
    assert result["Groups"][0]["GroupName"] == group_name


@mock_aws
def test_admin_list_groups_for_user_with_username_attribute():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    username = "test@example.com"
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )

    result = conn.admin_list_groups_for_user(Username=username, UserPoolId=user_pool_id)

    assert len(result["Groups"]) == 1
    assert result["Groups"][0]["GroupName"] == group_name


@mock_aws
def test_admin_list_groups_for_user_ignores_deleted_group():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)
    group_name2 = str(uuid.uuid4())
    conn.create_group(GroupName=group_name2, UserPoolId=user_pool_id)

    username = str(uuid.uuid4())
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )
    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name2
    )
    conn.delete_group(GroupName=group_name, UserPoolId=user_pool_id)

    result = conn.admin_list_groups_for_user(Username=username, UserPoolId=user_pool_id)

    assert len(result["Groups"]) == 1
    assert result["Groups"][0]["GroupName"] == group_name2


@mock_aws
def test_admin_list_groups_for_users_returns_pagination_tokens():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    # Given a user
    username = str(uuid.uuid4())
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
    # And given 10 groups
    group_count = 10
    for idx in range(group_count):
        group_name = f"group_{idx}"
        conn.create_group(UserPoolId=user_pool_id, GroupName=group_name)
        conn.admin_add_user_to_group(
            UserPoolId=user_pool_id, Username=username, GroupName=group_name
        )

    # When listing groups for the user pagination tokens are returned if limit is reached.
    max_results = 5
    result = conn.admin_list_groups_for_user(
        UserPoolId=user_pool_id, Username=username, Limit=max_results
    )
    assert len(result["Groups"]) == max_results
    assert "NextToken" in result

    next_token = result["NextToken"]
    result_2 = conn.admin_list_groups_for_user(
        UserPoolId=user_pool_id,
        Username=username,
        Limit=max_results,
        NextToken=next_token,
    )
    assert len(result_2["Groups"]) == max_results
    assert "NextToken" not in result_2


@mock_aws
def test_admin_remove_user_from_group():
    conn = boto3.client("cognito-idp", "us-west-2")

    pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=pool_id)

    uname = str(uuid.uuid4())
    conn.admin_create_user(UserPoolId=pool_id, Username=uname)

    conn.admin_add_user_to_group(
        UserPoolId=pool_id, Username=uname, GroupName=group_name
    )

    result = conn.admin_remove_user_from_group(
        UserPoolId=pool_id, Username=uname, GroupName=group_name
    )
    assert list(result.keys()) == ["ResponseMetadata"]  # No response expected

    resp = conn.list_users_in_group(UserPoolId=pool_id, GroupName=group_name)
    assert resp["Users"] == []
    resp = conn.admin_list_groups_for_user(Username=uname, UserPoolId=pool_id)
    assert resp["Groups"] == []


@mock_aws
def test_admin_remove_user_from_group_with_username_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=pool_id)

    uname = "test@example.com"
    conn.admin_create_user(UserPoolId=pool_id, Username=uname)

    conn.admin_add_user_to_group(
        UserPoolId=pool_id, Username=uname, GroupName=group_name
    )

    result = conn.admin_remove_user_from_group(
        UserPoolId=pool_id, Username=uname, GroupName=group_name
    )
    assert list(result.keys()) == ["ResponseMetadata"]  # No response expected

    resp = conn.list_users_in_group(UserPoolId=pool_id, GroupName=group_name)
    assert resp["Users"] == []
    resp = conn.admin_list_groups_for_user(Username=uname, UserPoolId=pool_id)
    assert resp["Groups"] == []


@mock_aws
def test_admin_remove_user_from_group_again_is_noop():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    group_name = str(uuid.uuid4())
    conn.create_group(GroupName=group_name, UserPoolId=user_pool_id)

    username = str(uuid.uuid4())
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )
    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username=username, GroupName=group_name
    )


@mock_aws
def test_admin_create_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    result = conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "thing", "Value": value}],
    )

    assert result["User"]["Username"] == username
    assert result["User"]["UserStatus"] == "FORCE_CHANGE_PASSWORD"
    assert len(result["User"]["Attributes"]) == 2

    def _verify_attribute(name, v):
        attr = [a for a in result["User"]["Attributes"] if a["Name"] == name]
        assert len(attr) == 1
        assert attr[0]["Value"] == v

    _verify_attribute("thing", value)
    assert result["User"]["Enabled"] is True


@mock_aws
def test_admin_create_user_with_username_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = "test@example.com"
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    result = conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "thing", "Value": value}],
    )

    assert result["User"]["Username"] != username
    assert result["User"]["UserStatus"] == "FORCE_CHANGE_PASSWORD"
    assert len(result["User"]["Attributes"]) == 3

    def _verify_attribute(name, v):
        attr = [a for a in result["User"]["Attributes"] if a["Name"] == name]
        assert len(attr) == 1
        assert attr[0]["Value"] == v

    _verify_attribute("thing", value)
    _verify_attribute("email", username)
    assert result["User"]["Enabled"] is True


@mock_aws
def test_admin_create_user_with_incorrect_username_attribute_type_fails():
    conn = boto3.client("cognito-idp", "us-west-2")

    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]

    with pytest.raises(ClientError) as ex:
        username = str(uuid.uuid4())
        conn.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[{"Name": "thing", "Value": value}],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert err["Message"] == "Username should be either an email or a phone number."


@mock_aws
def test_admin_create_user_with_existing_username_attribute_fails():
    conn = boto3.client("cognito-idp", "us-west-2")

    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]

    username = "test@example.com"
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "thing", "Value": value}],
    )

    with pytest.raises(ClientError) as ex:
        username = "test@example.com"
        conn.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[{"Name": "thing", "Value": value}],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "UsernameExistsException"
    assert err["Message"] == "test@example.com"


@mock_aws
def test_admin_create_existing_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "thing", "Value": value}],
    )

    with pytest.raises(ClientError) as exc:
        conn.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[{"Name": "thing", "Value": value}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "UsernameExistsException"


@mock_aws
def test_admin_confirm_sign_up():
    conn = boto3.client("cognito-idp", "us-east-1")

    username = str(uuid.uuid4())
    password = "Passw0rd!"
    user_pool_id = conn.create_user_pool(
        PoolName="us-east-1_aaaaaaaa", AutoVerifiedAttributes=["email"]
    )["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=False
    )["UserPoolClient"]["ClientId"]
    conn.sign_up(ClientId=client_id, Username=username, Password=password)
    user = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)

    assert user["UserStatus"] == "UNCONFIRMED"

    conn.admin_confirm_sign_up(UserPoolId=user_pool_id, Username=username)
    user = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)

    assert user["UserStatus"] == "CONFIRMED"


@mock_aws
def test_admin_confirm_sign_up_non_existing_user():
    conn = boto3.client("cognito-idp", "us-east-1")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(
        PoolName="us-east-1_aaaaaaaa", AutoVerifiedAttributes=["email"]
    )["UserPool"]["Id"]

    with pytest.raises(ClientError) as exc:
        conn.admin_confirm_sign_up(UserPoolId=user_pool_id, Username=username)

    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotFoundException"
    assert err["Message"] == "User does not exist."


@mock_aws
def test_admin_confirm_sign_up_non_existing_pool():
    conn = boto3.client("cognito-idp", "us-east-1")

    user_pool_id = "us-east-1_aaaaaaaa"
    with pytest.raises(ClientError) as exc:
        conn.admin_confirm_sign_up(UserPoolId=user_pool_id, Username=str(uuid.uuid4()))

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"User pool {user_pool_id} does not exist."


@mock_aws
def test_admin_resend_invitation_existing_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "thing", "Value": value}],
    )

    # Resending this should not throw an error
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "thing", "Value": value}],
        MessageAction="RESEND",
    )


@mock_aws
def test_admin_resend_invitation_missing_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    with pytest.raises(ClientError) as exc:
        conn.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[{"Name": "thing", "Value": value}],
            MessageAction="RESEND",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotFoundException"
    assert err["Message"] == "User does not exist."


@mock_aws
def test_admin_get_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "thing", "Value": value}],
    )

    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert result["Username"] == username
    assert len(result["UserAttributes"]) == 2


@mock_aws
def test_admin_get_user_with_username_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = "test@example.com"
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email", "phone_number"]
    )["UserPool"]["Id"]
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[
            {"Name": "thing", "Value": value},
            {"Name": "phone_number", "Value": "+123456789"},
        ],
    )
    # verify user can be queried by email
    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert result["Username"] != username
    assert len(result["UserAttributes"]) == 4

    def _verify_attribute(name, v):
        attr = [a for a in result["UserAttributes"] if a["Name"] == name]
        assert len(attr) == 1
        assert attr[0]["Value"] == v

    _verify_attribute("phone_number", "+123456789")
    _verify_attribute("email", "test@example.com")

    # verify user can be queried by phone number
    result = conn.admin_get_user(UserPoolId=user_pool_id, Username="+123456789")

    assert result["Username"] != username
    assert len(result["UserAttributes"]) == 4
    _verify_attribute("phone_number", "+123456789")
    _verify_attribute("email", "test@example.com")

    # verify that the generate user sub is a valid UUID v4
    [user_sub] = [
        attr["Value"] for attr in result["UserAttributes"] if attr["Name"] == "sub"
    ]
    uuid.UUID(user_sub)

    # verify user should be queried by user sub
    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=user_sub)

    assert result["Username"] != username
    assert len(result["UserAttributes"]) == 4
    _verify_attribute("phone_number", "+123456789")
    _verify_attribute("email", "test@example.com")


@mock_aws
def test_admin_get_missing_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    with pytest.raises(ClientError) as exc:
        conn.admin_get_user(UserPoolId=user_pool_id, Username=username)

    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotFoundException"
    assert err["Message"] == "User does not exist."


@mock_aws
def test_admin_get_missing_user_with_username_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = "test@example.com"
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]

    with pytest.raises(ClientError) as exc:
        conn.admin_get_user(UserPoolId=user_pool_id, Username=username)

    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotFoundException"
    assert err["Message"] == "User does not exist."


@mock_aws
def test_new_user_contains_same_created_and_updated_dates():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = "test@example.com"
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]

    resp = conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
    new_user = resp["User"]

    assert new_user["UserCreateDate"] == new_user["UserLastModifiedDate"]


@mock_aws
def test_update_user_attributes_also_changes_last_modified_date():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = "test@example.com"
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    time.sleep(1)  # Wait enough to account for a different in the time format
    conn.admin_update_user_attributes(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "phone_number", "Value": "+123456789"}],
    )

    user = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert user["UserCreateDate"] < user["UserLastModifiedDate"]


@mock_aws
def test_delete_user_attributes_also_changes_last_modified_date():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = "test@example.com"
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "phone_number", "Value": "+123456789"}],
    )

    time.sleep(1)  # Wait enough to account for a different in the time format
    conn.admin_delete_user_attributes(
        UserPoolId=user_pool_id, Username=username, UserAttributeNames=["phone_number"]
    )

    user = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert user["UserCreateDate"] < user["UserLastModifiedDate"]


@mock_aws
def test_get_user():
    conn = boto3.client("cognito-idp", "us-west-2")
    outputs = authentication_flow(conn, "ADMIN_NO_SRP_AUTH")
    result = conn.get_user(AccessToken=outputs["access_token"])
    assert result["Username"] == outputs["username"]
    assert len(result["UserAttributes"]) == 2

    def _verify_attribute(name, v):
        attr = [a for a in result["UserAttributes"] if a["Name"] == name]
        assert len(attr) == 1
        assert attr[0]["Value"] == v

    for key, value in outputs["additional_fields"].items():
        _verify_attribute(key, value)


@mock_aws
@set_initial_no_auth_action_count(0)
def test_get_user_unknown_accesstoken():
    conn = boto3.client("cognito-idp", "us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.get_user(AccessToken="n/a")
    err = ex.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"
    assert err["Message"] == "Invalid token"


@mock_aws
def test_list_users():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
    result = conn.list_users(UserPoolId=user_pool_id)
    assert len(result["Users"]) == 1
    assert result["Users"][0]["Username"] == username

    username_bis = str(uuid.uuid4())
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username_bis,
        UserAttributes=[{"Name": "phone_number", "Value": "+33666666666"}],
    )
    result = conn.list_users(
        UserPoolId=user_pool_id, Filter='phone_number="+33666666666"'
    )
    assert len(result["Users"]) == 1
    assert result["Users"][0]["Username"] == username_bis

    # checking Filter with space
    result = conn.list_users(
        UserPoolId=user_pool_id, Filter='phone_number = "+33666666666"'
    )
    assert len(result["Users"]) == 1
    assert result["Users"][0]["Username"] == username_bis

    user0_username = "user0@example.com"
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=user0_username,
        UserAttributes=[{"Name": "phone_number", "Value": "+48555555555"}],
    )

    # checking Filter with prefix operator
    result = conn.list_users(UserPoolId=user_pool_id, Filter='phone_number ^= "+48"')
    assert len(result["Users"]) == 1
    assert result["Users"][0]["Username"] == user0_username

    # empty value Filter should also be supported
    result = conn.list_users(UserPoolId=user_pool_id, Filter='family_name=""')
    assert len(result["Users"]) == 0


@mock_aws
def test_list_users_incorrect_filter():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    with pytest.raises(conn.exceptions.InvalidParameterException) as exc:
        conn.list_users(UserPoolId=user_pool_id, Filter="username = foo")
    _assert_filter_parsing_error(exc)

    with pytest.raises(conn.exceptions.InvalidParameterException) as exc:
        conn.list_users(UserPoolId=user_pool_id, Filter="username=")
    _assert_filter_parsing_error(exc)


def _assert_filter_parsing_error(exc):
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert err["Message"] == "Error while parsing filter"


@mock_aws
def test_list_users_invalid_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    with pytest.raises(conn.exceptions.InvalidParameterException) as exc:
        conn.list_users(UserPoolId=user_pool_id, Filter='custom:foo = "bar"')
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert err["Message"] == "Invalid search attribute: custom:foo"


@mock_aws
def test_list_users_with_username_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = "test@example.com"
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
    result = conn.list_users(UserPoolId=user_pool_id)
    assert len(result["Users"]) == 1
    assert result["Users"][0]["Username"] != username

    def _verify_attribute(name, v):
        attr = [a for a in result["Users"][0]["Attributes"] if a["Name"] == name]
        assert len(attr) == 1
        assert attr[0]["Value"] == v

    _verify_attribute("email", username)

    username_bis = "test2@uexample.com"
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username_bis,
        UserAttributes=[{"Name": "phone_number", "Value": "+33666666666"}],
    )
    result = conn.list_users(
        UserPoolId=user_pool_id, Filter='phone_number="+33666666666"'
    )
    assert len(result["Users"]) == 1
    assert result["Users"][0]["Username"] != username_bis
    uuid.UUID(result["Users"][0]["Username"])

    _verify_attribute("email", username_bis)

    # checking Filter with space
    result = conn.list_users(
        UserPoolId=user_pool_id, Filter='phone_number = "+33666666666"'
    )
    assert len(result["Users"]) == 1
    assert result["Users"][0]["Username"] != username_bis
    _verify_attribute("email", username_bis)


@mock_aws
def test_list_users_inherent_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
    result = conn.list_users(UserPoolId=user_pool_id)
    assert len(result["Users"]) == 1
    assert result["Users"][0]["Username"] == username

    # create a confirmed disabled user
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4())
    )["UserPoolClient"]["ClientId"]
    disabled_user_username = str(uuid.uuid4())
    conn.admin_create_user(UserPoolId=user_pool_id, Username=disabled_user_username)
    conn.confirm_sign_up(
        ClientId=client_id, Username=disabled_user_username, ConfirmationCode="123456"
    )
    conn.admin_disable_user(UserPoolId=user_pool_id, Username=disabled_user_username)

    # filter, filter value, response field, response field expected value - all target confirmed disabled user
    filters = [
        ("username", disabled_user_username, "Username", disabled_user_username),
        ("status", "Disabled", "Enabled", False),
        ("cognito:user_status", "CONFIRMED", "UserStatus", "CONFIRMED"),
    ]

    for name, filter_value, response_field, response_field_expected_value in filters:
        result = conn.list_users(
            UserPoolId=user_pool_id, Filter=f'{name}="{filter_value}"'
        )
        assert len(result["Users"]) == 1
        assert result["Users"][0][response_field] == response_field_expected_value


@mock_aws
def test_get_user_unconfirmed():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cant patch attributes in server mode.")
    conn = boto3.client("cognito-idp", "us-west-2")
    outputs = authentication_flow(conn, "ADMIN_NO_SRP_AUTH")

    backend = moto.cognitoidp.models.cognitoidp_backends[ACCOUNT_ID]["us-west-2"]
    user_pool = backend.user_pools[outputs["user_pool_id"]]
    user_pool.users[outputs["username"]].status = "UNCONFIRMED"

    with pytest.raises(ClientError) as ex:
        conn.get_user(AccessToken=outputs["access_token"])
    err = ex.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"
    assert err["Message"] == "username"


@mock_aws
def test_list_users_returns_limit_items():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    # Given 10 users
    user_count = 10
    for _ in range(user_count):
        conn.admin_create_user(UserPoolId=user_pool_id, Username=str(uuid.uuid4()))
    max_results = 5
    result = conn.list_users(UserPoolId=user_pool_id, Limit=max_results)
    assert len(result["Users"]) == max_results
    assert "PaginationToken" in result


@mock_aws
def test_list_users_returns_pagination_tokens():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    # Given 10 users
    user_count = 10
    for _ in range(user_count):
        conn.admin_create_user(UserPoolId=user_pool_id, Username=str(uuid.uuid4()))

    max_results = 5
    result = conn.list_users(UserPoolId=user_pool_id, Limit=max_results)
    assert len(result["Users"]) == max_results
    assert "PaginationToken" in result

    next_token = result["PaginationToken"]
    result_2 = conn.list_users(
        UserPoolId=user_pool_id, Limit=max_results, PaginationToken=next_token
    )
    assert len(result_2["Users"]) == max_results
    assert "PaginationToken" not in result_2


@mock_aws
def test_list_users_when_limit_more_than_total_items():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    # Given 10 users
    user_count = 10
    for _ in range(user_count):
        conn.admin_create_user(UserPoolId=user_pool_id, Username=str(uuid.uuid4()))

    max_results = user_count + 5
    result = conn.list_users(UserPoolId=user_pool_id, Limit=max_results)
    assert len(result["Users"]) == user_count
    assert "PaginationToken" not in result


@mock_aws
def test_list_users_with_attributes_to_get():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    for _ in range(5):
        conn.admin_create_user(
            UserPoolId=user_pool_id,
            Username=str(uuid.uuid4()),
            UserAttributes=[
                {"Name": "family_name", "Value": "Doe"},
                {"Name": "given_name", "Value": "Jane"},
                {"Name": "custom:foo", "Value": "bar"},
            ],
        )

    result = conn.list_users(
        UserPoolId=user_pool_id, AttributesToGet=["given_name", "custom:foo", "unknown"]
    )
    users = result["Users"]
    assert len(users) == 5
    for user in users:
        assert len(user["Attributes"]) == 2
        assert {"Name": "given_name", "Value": "Jane"} in user["Attributes"]
        assert {"Name": "custom:foo", "Value": "bar"} in user["Attributes"]


@mock_aws
def test_admin_disable_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    result = conn.admin_disable_user(UserPoolId=user_pool_id, Username=username)
    assert list(result.keys()) == ["ResponseMetadata"]  # No response expected

    assert (
        conn.admin_get_user(UserPoolId=user_pool_id, Username=username)["Enabled"]
        is False
    )


@mock_aws
def test_admin_disable_user_with_username_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = "test@example.com"
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    result = conn.admin_disable_user(UserPoolId=user_pool_id, Username=username)
    assert list(result.keys()) == ["ResponseMetadata"]  # No response expected

    assert (
        conn.admin_get_user(UserPoolId=user_pool_id, Username=username)["Enabled"]
        is False
    )


@mock_aws
def test_admin_enable_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
    conn.admin_disable_user(UserPoolId=user_pool_id, Username=username)

    result = conn.admin_enable_user(UserPoolId=user_pool_id, Username=username)
    assert list(result.keys()) == ["ResponseMetadata"]  # No response expected

    assert conn.admin_get_user(UserPoolId=user_pool_id, Username=username)["Enabled"]


@mock_aws
def test_admin_enable_user_with_username_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = "test@example.com"
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
    conn.admin_disable_user(UserPoolId=user_pool_id, Username=username)

    result = conn.admin_enable_user(UserPoolId=user_pool_id, Username=username)
    assert list(result.keys()) == ["ResponseMetadata"]  # No response expected

    assert conn.admin_get_user(UserPoolId=user_pool_id, Username=username)["Enabled"]


@mock_aws
def test_admin_delete_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
    conn.admin_delete_user(UserPoolId=user_pool_id, Username=username)

    with pytest.raises(ClientError) as exc:
        conn.admin_get_user(UserPoolId=user_pool_id, Username=username)

    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotFoundException"


@mock_aws
def test_admin_delete_user_with_username_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = "test@example.com"
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
    conn.admin_delete_user(UserPoolId=user_pool_id, Username=username)

    with pytest.raises(ClientError) as ex:
        conn.admin_get_user(UserPoolId=user_pool_id, Username=username)

    err = ex.value.response["Error"]
    assert err["Code"] == "UserNotFoundException"


def authentication_flow(conn, auth_flow):
    username = str(uuid.uuid4())
    temporary_password = "P2$Sword"
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    user_attribute_name = str(uuid.uuid4())
    user_attribute_value = str(uuid.uuid4())
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=str(uuid.uuid4()),
        ReadAttributes=[user_attribute_name],
    )["UserPoolClient"]["ClientId"]

    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        TemporaryPassword=temporary_password,
        UserAttributes=[{"Name": user_attribute_name, "Value": user_attribute_value}],
    )

    result = conn.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow=auth_flow,
        AuthParameters={"USERNAME": username, "PASSWORD": temporary_password},
    )

    # A newly created user is forced to set a new password
    assert result["ChallengeName"] == "NEW_PASSWORD_REQUIRED"
    assert result["Session"] is not None

    # This sets a new password and logs the user in (creates tokens)
    new_password = "P2$Sword"
    result = conn.admin_respond_to_auth_challenge(
        UserPoolId=user_pool_id,
        Session=result["Session"],
        ClientId=client_id,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        ChallengeResponses={"USERNAME": username, "NEW_PASSWORD": new_password},
    )

    assert result["AuthenticationResult"]["IdToken"] is not None
    assert result["AuthenticationResult"]["AccessToken"] is not None

    return {
        "user_pool_id": user_pool_id,
        "client_id": client_id,
        "id_token": result["AuthenticationResult"]["IdToken"],
        "access_token": result["AuthenticationResult"]["AccessToken"],
        "username": username,
        "password": new_password,
        "additional_fields": {user_attribute_name: user_attribute_value},
    }


@mock_aws
def test_authentication_flow():
    conn = boto3.client("cognito-idp", "us-west-2")

    for auth_flow in ["ADMIN_NO_SRP_AUTH", "ADMIN_USER_PASSWORD_AUTH"]:
        authentication_flow(conn, auth_flow)


@mock_aws
def test_authentication_flow_invalid_flow():
    conn = boto3.client("cognito-idp", "us-west-2")

    with pytest.raises(ClientError) as ex:
        authentication_flow(conn, "NO_SUCH_FLOW")

    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "1 validation error detected: Value 'NO_SUCH_FLOW' at 'authFlow' failed to satisfy constraint: Member must satisfy enum value set: ['ADMIN_NO_SRP_AUTH', 'ADMIN_USER_PASSWORD_AUTH', 'USER_SRP_AUTH', 'REFRESH_TOKEN_AUTH', 'REFRESH_TOKEN', 'CUSTOM_AUTH', 'USER_PASSWORD_AUTH']"
    )


@mock_aws
def test_authentication_flow_invalid_user_flow():
    """Pass a user authFlow to admin_initiate_auth"""
    conn = boto3.client("cognito-idp", "us-west-2")

    with pytest.raises(ClientError) as ex:
        authentication_flow(conn, "USER_PASSWORD_AUTH")

    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert err["Message"] == "Initiate Auth method not supported"


def user_authentication_flow(
    conn, user_pool=None, user_pool_client=None, with_mfa=True, use_email=False
):
    username = "test@moto.com" if use_email else str(uuid.uuid4())
    password = "P2$Sword"
    if not user_pool:
        user_pool = conn.create_user_pool(PoolName=str(uuid.uuid4()))

    user_pool_id = user_pool["UserPool"]["Id"]
    user_attribute_name = str(uuid.uuid4())
    user_attribute_value = str(uuid.uuid4())
    if not user_pool_client:
        user_pool_client = conn.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=str(uuid.uuid4()),
            ReadAttributes=[user_attribute_name],
            GenerateSecret=True,
        )
    client_id = user_pool_client["UserPoolClient"]["ClientId"]
    client_secret = user_pool_client["UserPoolClient"]["ClientSecret"]

    secret_hash = pycognito.aws_srp.AWSSRP.get_secret_hash(
        username=username, client_id=client_id, client_secret=client_secret
    )
    conn.sign_up(
        ClientId=client_id, Username=username, Password=password, SecretHash=secret_hash
    )

    client_secret = conn.describe_user_pool_client(
        UserPoolId=user_pool_id, ClientId=client_id
    )["UserPoolClient"]["ClientSecret"]

    conn.admin_confirm_sign_up(UserPoolId=user_pool_id, Username=username)

    aws_srp = pycognito.aws_srp.AWSSRP(
        username=username,
        password=password,
        pool_id=user_pool_id,
        client_id=client_id,
        client_secret=client_secret,
        client=conn,
    )
    auth_params = aws_srp.get_auth_params()

    result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_SRP_AUTH",
        AuthParameters=auth_params,
    )

    challenge_response = aws_srp.process_challenge(
        result["ChallengeParameters"], auth_params
    )
    result = conn.respond_to_auth_challenge(
        ClientId=client_id,
        ChallengeName=result["ChallengeName"],
        ChallengeResponses=challenge_response,
    )

    refresh_token = result["AuthenticationResult"]["RefreshToken"]

    # add mfa token
    if with_mfa:
        resp = conn.associate_software_token(
            AccessToken=result["AuthenticationResult"]["AccessToken"]
        )
        secret_code = resp["SecretCode"]
        totp = pyotp.TOTP(secret_code)
        user_code = totp.now()

        resp = conn.verify_software_token(
            AccessToken=result["AuthenticationResult"]["AccessToken"],
            UserCode=user_code,
        )
        assert resp["Status"] == "SUCCESS"

        conn.set_user_mfa_preference(
            AccessToken=result["AuthenticationResult"]["AccessToken"],
            SoftwareTokenMfaSettings={"Enabled": True, "PreferredMfa": True},
        )

    result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="REFRESH_TOKEN",
        AuthParameters={"SECRET_HASH": secret_hash, "REFRESH_TOKEN": refresh_token},
    )

    assert result["AuthenticationResult"]["IdToken"] is not None
    assert result["AuthenticationResult"]["AccessToken"] is not None
    assert result["AuthenticationResult"]["TokenType"] == "Bearer"

    # authenticate user once again this time with mfa token
    if with_mfa:
        result = conn.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_SRP_AUTH",
            AuthParameters={
                "USERNAME": username,
                "SRP_A": pycognito.aws_srp.long_to_hex(aws_srp.large_a_value),
                "SECRET_HASH": secret_hash,
            },
        )

        challenge_response = aws_srp.process_challenge(
            result["ChallengeParameters"], auth_params
        )
        result = conn.respond_to_auth_challenge(
            ClientId=client_id,
            ChallengeName=result["ChallengeName"],
            ChallengeResponses=challenge_response,
        )
        assert result["ChallengeName"] == "SOFTWARE_TOKEN_MFA"

        # AWS needs a new user code, otherwise they will throw an exception
        #    ExpiredCodeException: Your software token has already been used once.
        new_user_code = totp.now()
        if allow_aws_request():
            while user_code == new_user_code:
                new_user_code = totp.now()
                time.sleep(1)
        result = conn.respond_to_auth_challenge(
            ClientId=client_id,
            Session=result["Session"],
            ChallengeName=result["ChallengeName"],
            ChallengeResponses={
                "SOFTWARE_TOKEN_MFA_CODE": new_user_code,
                "USERNAME": username,
                "SECRET_HASH": auth_params["SECRET_HASH"],
            },
        )

    return {
        "user_pool_id": user_pool_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "secret_hash": secret_hash,
        "id_token": result["AuthenticationResult"]["IdToken"],
        "access_token": result["AuthenticationResult"]["AccessToken"],
        "refresh_token": refresh_token,
        "username": username,
        "password": password,
        "additional_fields": {user_attribute_name: user_attribute_value},
    }


@cognitoidp_aws_verified(generate_secret=True, with_mfa="ON")
@pytest.mark.aws_verified
def test_user_authentication_flow_mfa_on(user_pool=None, user_pool_client=None):
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    password = "P2$Sword"

    user_pool_id = user_pool["UserPool"]["Id"]
    client_id = user_pool_client["UserPoolClient"]["ClientId"]
    client_secret = user_pool_client["UserPoolClient"]["ClientSecret"]

    secret_hash = pycognito.aws_srp.AWSSRP.get_secret_hash(
        username=username, client_id=client_id, client_secret=client_secret
    )
    conn.sign_up(
        ClientId=client_id, Username=username, Password=password, SecretHash=secret_hash
    )

    client_secret = conn.describe_user_pool_client(
        UserPoolId=user_pool_id, ClientId=client_id
    )["UserPoolClient"]["ClientSecret"]

    conn.admin_confirm_sign_up(UserPoolId=user_pool_id, Username=username)

    aws_srp = pycognito.aws_srp.AWSSRP(
        username=username,
        password=password,
        pool_id=user_pool_id,
        client_id=client_id,
        client_secret=client_secret,
        client=conn,
    )
    auth_params = aws_srp.get_auth_params()

    result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_SRP_AUTH",
        AuthParameters=auth_params,
    )

    challenge_response = aws_srp.process_challenge(
        result["ChallengeParameters"], auth_params
    )
    result = conn.respond_to_auth_challenge(
        ClientId=client_id,
        ChallengeName=result["ChallengeName"],
        ChallengeResponses=challenge_response,
    )
    assert result["ChallengeName"] == "MFA_SETUP"

    # add mfa token
    resp = conn.associate_software_token(Session=result["Session"])
    secret_code = resp["SecretCode"]
    totp = pyotp.TOTP(secret_code)
    user_code = totp.now()

    resp = conn.verify_software_token(Session=resp["Session"], UserCode=user_code)
    assert resp["Status"] == "SUCCESS"

    # authenticate user once again
    result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_SRP_AUTH",
        AuthParameters={
            "USERNAME": username,
            "SRP_A": pycognito.aws_srp.long_to_hex(aws_srp.large_a_value),
            "SECRET_HASH": secret_hash,
        },
    )

    challenge_response = aws_srp.process_challenge(
        result["ChallengeParameters"], auth_params
    )
    result = conn.respond_to_auth_challenge(
        ClientId=client_id,
        ChallengeName=result["ChallengeName"],
        ChallengeResponses=challenge_response,
    )
    assert result["ChallengeName"] == "SOFTWARE_TOKEN_MFA"

    # AWS needs a new user code, otherwise they will throw an exception
    #    ExpiredCodeException: Your software token has already been used once.
    new_user_code = totp.now()
    if allow_aws_request():
        while user_code == new_user_code:
            new_user_code = totp.now()
            time.sleep(1)
    result = conn.respond_to_auth_challenge(
        ClientId=client_id,
        Session=result["Session"],
        ChallengeName=result["ChallengeName"],
        ChallengeResponses={
            "SOFTWARE_TOKEN_MFA_CODE": new_user_code,
            "USERNAME": username,
            "SECRET_HASH": auth_params["SECRET_HASH"],
        },
    )
    assert result["AuthenticationResult"]["AccessToken"]
    assert result["AuthenticationResult"]["IdToken"]
    assert result["AuthenticationResult"]["RefreshToken"]


@cognitoidp_aws_verified(generate_secret=True, with_mfa="OPTIONAL")
@pytest.mark.aws_verified
def test_user_authentication_flow_mfa_optional(user_pool=None, user_pool_client=None):
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    password = "P2$Sword"

    user_pool_id = user_pool["UserPool"]["Id"]
    client_id = user_pool_client["UserPoolClient"]["ClientId"]
    client_secret = user_pool_client["UserPoolClient"]["ClientSecret"]

    secret_hash = pycognito.aws_srp.AWSSRP.get_secret_hash(
        username=username, client_id=client_id, client_secret=client_secret
    )
    conn.sign_up(
        ClientId=client_id, Username=username, Password=password, SecretHash=secret_hash
    )

    client_secret = conn.describe_user_pool_client(
        UserPoolId=user_pool_id, ClientId=client_id
    )["UserPoolClient"]["ClientSecret"]

    conn.admin_confirm_sign_up(UserPoolId=user_pool_id, Username=username)

    aws_srp = pycognito.aws_srp.AWSSRP(
        username=username,
        password=password,
        pool_id=user_pool_id,
        client_id=client_id,
        client_secret=client_secret,
        client=conn,
    )
    auth_params = aws_srp.get_auth_params()

    result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_SRP_AUTH",
        AuthParameters=auth_params,
    )

    challenge_response = aws_srp.process_challenge(
        result["ChallengeParameters"], auth_params
    )
    result = conn.respond_to_auth_challenge(
        ClientId=client_id,
        ChallengeName=result["ChallengeName"],
        ChallengeResponses=challenge_response,
    )

    # add mfa token
    resp = conn.associate_software_token(
        AccessToken=result["AuthenticationResult"]["AccessToken"]
    )
    secret_code = resp["SecretCode"]
    totp = pyotp.TOTP(secret_code)
    user_code = totp.now()

    resp = conn.verify_software_token(
        AccessToken=result["AuthenticationResult"]["AccessToken"],
        UserCode=user_code,
    )
    assert resp["Status"] == "SUCCESS"

    conn.set_user_mfa_preference(
        AccessToken=result["AuthenticationResult"]["AccessToken"],
        SoftwareTokenMfaSettings={"Enabled": True, "PreferredMfa": True},
    )

    # authenticate user once again
    result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_SRP_AUTH",
        AuthParameters={
            "USERNAME": username,
            "SRP_A": pycognito.aws_srp.long_to_hex(aws_srp.large_a_value),
            "SECRET_HASH": secret_hash,
        },
    )

    challenge_response = aws_srp.process_challenge(
        result["ChallengeParameters"], auth_params
    )
    result = conn.respond_to_auth_challenge(
        ClientId=client_id,
        ChallengeName=result["ChallengeName"],
        ChallengeResponses=challenge_response,
    )
    assert result["ChallengeName"] == "SOFTWARE_TOKEN_MFA"

    # AWS needs a new user code, otherwise they will throw an exception
    #    ExpiredCodeException: Your software token has already been used once.
    new_user_code = totp.now()
    if allow_aws_request():
        while user_code == new_user_code:
            new_user_code = totp.now()
            time.sleep(1)
    result = conn.respond_to_auth_challenge(
        ClientId=client_id,
        Session=result["Session"],
        ChallengeName=result["ChallengeName"],
        ChallengeResponses={
            "SOFTWARE_TOKEN_MFA_CODE": new_user_code,
            "USERNAME": username,
            "SECRET_HASH": auth_params["SECRET_HASH"],
        },
    )
    assert result["AuthenticationResult"]["AccessToken"]
    assert result["AuthenticationResult"]["IdToken"]
    assert result["AuthenticationResult"]["RefreshToken"]


@mock_aws
def test_token_legitimacy():
    conn = boto3.client("cognito-idp", "us-west-2")

    path = "../../moto/cognitoidp/resources/jwks-public.json"
    with open(os.path.join(os.path.dirname(__file__), path)) as f:
        json_web_key = jwk.RSAKey.import_key(json.loads(f.read())["keys"][0])

    for auth_flow in ["ADMIN_NO_SRP_AUTH", "ADMIN_USER_PASSWORD_AUTH"]:
        outputs = authentication_flow(conn, auth_flow)
        id_token = outputs["id_token"]
        access_token = outputs["access_token"]
        client_id = outputs["client_id"]
        username = outputs["username"]
        issuer = (
            f"https://cognito-idp.us-west-2.amazonaws.com/{outputs['user_pool_id']}"
        )
        id_claims = jwt.decode(id_token, json_web_key, ["RS256"]).claims
        assert id_claims["iss"] == issuer
        assert id_claims["aud"] == client_id
        assert id_claims["token_use"] == "id"
        assert id_claims["cognito:username"] == username
        for k, v in outputs["additional_fields"].items():
            assert id_claims[k] == v
        access_claims = jwt.decode(access_token, json_web_key, ["RS256"]).claims
        assert access_claims["iss"] == issuer
        assert access_claims["client_id"] == client_id
        assert access_claims["token_use"] == "access"
        assert access_claims["username"] == username


@mock_aws
def test_change_password():
    conn = boto3.client("cognito-idp", "us-west-2")

    for auth_flow in ["ADMIN_NO_SRP_AUTH", "ADMIN_USER_PASSWORD_AUTH"]:
        outputs = authentication_flow(conn, auth_flow)

        # Take this opportunity to test change_password, which requires an access token.
        newer_password = "P2$Sword2"
        conn.change_password(
            AccessToken=outputs["access_token"],
            PreviousPassword=outputs["password"],
            ProposedPassword=newer_password,
        )

        # Log in again, which should succeed without a challenge because the user is no
        # longer in the force-new-password state.
        result = conn.admin_initiate_auth(
            UserPoolId=outputs["user_pool_id"],
            ClientId=outputs["client_id"],
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": outputs["username"],
                "PASSWORD": newer_password,
            },
        )

        assert result["AuthenticationResult"] is not None


@mock_aws
def test_change_password__using_custom_user_agent_header():
    # https://github.com/getmoto/moto/issues/3098
    # As the admin_initiate_auth-method is unauthenticated, we use the user-agent header to pass in the region
    # This test verifies this works, even if we pass in our own user-agent header
    from botocore.config import Config

    my_config = Config(user_agent_extra="more/info", signature_version="v4")
    conn = boto3.client("cognito-idp", "us-west-2", config=my_config)

    for auth_flow in ["ADMIN_NO_SRP_AUTH", "ADMIN_USER_PASSWORD_AUTH"]:
        outputs = authentication_flow(conn, auth_flow)

        # Take this opportunity to test change_password, which requires an access token.
        newer_password = "P2$Sword2"
        conn.change_password(
            AccessToken=outputs["access_token"],
            PreviousPassword=outputs["password"],
            ProposedPassword=newer_password,
        )

        # Log in again, which should succeed without a challenge because the user is no
        # longer in the force-new-password state.
        result = conn.admin_initiate_auth(
            UserPoolId=outputs["user_pool_id"],
            ClientId=outputs["client_id"],
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": outputs["username"],
                "PASSWORD": newer_password,
            },
        )

        assert result["AuthenticationResult"] is not None


@mock_aws
@set_initial_no_auth_action_count(2)
def test_forgot_password():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4())
    )["UserPoolClient"]["ClientId"]
    result = conn.forgot_password(ClientId=client_id, Username=str(uuid.uuid4()))
    assert result["CodeDeliveryDetails"]["Destination"] is not None
    assert result["CodeDeliveryDetails"]["DeliveryMedium"] == "EMAIL"
    assert result["CodeDeliveryDetails"]["AttributeName"] == "email"


@mock_aws
def test_forgot_password_nonexistent_client_id():
    conn = boto3.client("cognito-idp", "us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.forgot_password(ClientId=create_id(), Username=str(uuid.uuid4()))

    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Username/client id combination not found."


@mock_aws
def test_forgot_password_admin_only_recovery():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()),
        AccountRecoverySetting={
            "RecoveryMechanisms": [{"Name": "admin_only", "Priority": 1}]
        },
    )["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4())
    )["UserPoolClient"]["ClientId"]

    with pytest.raises(ClientError) as ex:
        conn.forgot_password(ClientId=client_id, Username=str(uuid.uuid4()))

    err = ex.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"
    assert err["Message"] == "Contact administrator to reset password."


@mock_aws
def test_forgot_password_user_with_all_recovery_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()),
        AccountRecoverySetting={
            "RecoveryMechanisms": [{"Name": "verified_email", "Priority": 1}]
        },
    )["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4())
    )["UserPoolClient"]["ClientId"]
    username = str(uuid.uuid4())
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[
            {"Name": "email", "Value": "test@m***"},
            {"Name": "phone_number", "Value": "555555555"},
        ],
    )

    result = conn.forgot_password(ClientId=client_id, Username=username)

    assert result["CodeDeliveryDetails"]["Destination"] == "t***@m***"
    assert result["CodeDeliveryDetails"]["DeliveryMedium"] == "EMAIL"
    assert result["CodeDeliveryDetails"]["AttributeName"] == "email"

    conn.update_user_pool(
        UserPoolId=user_pool_id,
        AccountRecoverySetting={
            "RecoveryMechanisms": [{"Name": "verified_phone_number", "Priority": 1}]
        },
    )

    result = conn.forgot_password(ClientId=client_id, Username=username)

    assert result["CodeDeliveryDetails"]["Destination"] == "555555555"
    assert result["CodeDeliveryDetails"]["DeliveryMedium"] == "SMS"
    assert result["CodeDeliveryDetails"]["AttributeName"] == "phone_number"


@mock_aws
def test_forgot_password_nonexistent_user_or_user_without_attributes():
    # Whether this fails against AWS or not depends on a setting
    # https://github.com/aws/aws-aspnet-cognito-identity-provider/issues/179#issuecomment-871051383
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()),
        AccountRecoverySetting={
            "RecoveryMechanisms": [{"Name": "verified_email", "Priority": 1}]
        },
    )["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4())
    )["UserPoolClient"]["ClientId"]
    user_without_attributes = str(uuid.uuid4())
    nonexistent_user = str(uuid.uuid4())

    conn.admin_create_user(UserPoolId=user_pool_id, Username=user_without_attributes)
    for user in user_without_attributes, nonexistent_user:
        result = conn.forgot_password(ClientId=client_id, Username=user)

        assert result["CodeDeliveryDetails"]["Destination"] == user + "@h***.com"
        assert result["CodeDeliveryDetails"]["DeliveryMedium"] == "EMAIL"
        assert result["CodeDeliveryDetails"]["AttributeName"] == "email"

    conn.update_user_pool(
        UserPoolId=user_pool_id,
        AccountRecoverySetting={
            "RecoveryMechanisms": [{"Name": "verified_phone_number", "Priority": 1}]
        },
    )

    for user in user_without_attributes, nonexistent_user:
        result = conn.forgot_password(ClientId=client_id, Username=user)

        assert result["CodeDeliveryDetails"]["Destination"] == "+*******9934"
        assert result["CodeDeliveryDetails"]["DeliveryMedium"] == "SMS"
        assert result["CodeDeliveryDetails"]["AttributeName"] == "phone_number"


@cognitoidp_aws_verified(recovery=[{"Name": "verified_email", "Priority": 1}])
@pytest.mark.aws_verified
def test_forgot_password_with_email_delivery_details(
    user_pool=None, user_pool_client=None
):
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = user_pool["UserPool"]["Id"]
    client_id = user_pool_client["UserPoolClient"]["ClientId"]
    user_without_attributes = str(uuid.uuid4())

    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=user_without_attributes,
        UserAttributes=[
            {"Name": "email", "Value": "test@test.com"},
            {"Name": "email_verified", "Value": "True"},
        ],
    )
    conn.admin_set_user_password(
        UserPoolId=user_pool_id,
        Username=user_without_attributes,
        Password="secretP2ss!",
        Permanent=True,
    )

    result = conn.forgot_password(ClientId=client_id, Username=user_without_attributes)
    assert result["CodeDeliveryDetails"]["Destination"] == "t***@t***"
    assert result["CodeDeliveryDetails"]["DeliveryMedium"] == "EMAIL"
    assert result["CodeDeliveryDetails"]["AttributeName"] == "email"


@mock_aws
def test_confirm_forgot_password_legacy():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4())
    )["UserPoolClient"]["ClientId"]
    conn.admin_create_user(
        UserPoolId=user_pool_id, Username=username, TemporaryPassword=str(uuid.uuid4())
    )

    # Random confirmation code - opt out of verification
    conn.forgot_password(ClientId=client_id, Username=username)
    res = conn.confirm_forgot_password(
        ClientId=client_id,
        Username=username,
        ConfirmationCode=str(uuid.uuid4()),
        Password=str(uuid.uuid4()),
    )

    assert res["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_confirm_forgot_password_opt_in_verification():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4())
    )["UserPoolClient"]["ClientId"]
    conn.admin_create_user(
        UserPoolId=user_pool_id, Username=username, TemporaryPassword=str(uuid.uuid4())
    )

    res = conn.forgot_password(ClientId=client_id, Username=username)

    confirmation_code = res["ResponseMetadata"]["HTTPHeaders"][
        "x-moto-forgot-password-confirmation-code"
    ]
    assert "moto-confirmation-code" in confirmation_code

    res = conn.confirm_forgot_password(
        ClientId=client_id,
        Username=username,
        ConfirmationCode=confirmation_code,
        Password=str(uuid.uuid4()),
    )

    assert res["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_confirm_forgot_password_opt_in_verification_invalid_confirmation_code():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4())
    )["UserPoolClient"]["ClientId"]
    conn.admin_create_user(
        UserPoolId=user_pool_id, Username=username, TemporaryPassword=str(uuid.uuid4())
    )

    with pytest.raises(ClientError) as ex:
        conn.confirm_forgot_password(
            ClientId=client_id,
            Username=username,
            ConfirmationCode="moto-confirmation-code:123invalid",
            Password=str(uuid.uuid4()),
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ExpiredCodeException"
    assert err["Message"] == "Invalid code provided, please request a code again."


@mock_aws
def test_admin_user_global_sign_out():
    conn = boto3.client("cognito-idp", "us-west-2")
    result = user_authentication_flow(conn)

    conn.admin_user_global_sign_out(
        UserPoolId=result["user_pool_id"], Username=result["username"]
    )

    with pytest.raises(ClientError) as ex:
        conn.initiate_auth(
            ClientId=result["client_id"],
            AuthFlow="REFRESH_TOKEN",
            AuthParameters={
                "REFRESH_TOKEN": result["refresh_token"],
                "SECRET_HASH": result["secret_hash"],
            },
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"
    assert err["Message"] == "Refresh Token has been revoked"


@mock_aws
def test_admin_user_global_sign_out_twice():
    conn = boto3.client("cognito-idp", "us-west-2")
    result = user_authentication_flow(conn)

    conn.admin_user_global_sign_out(
        UserPoolId=result["user_pool_id"], Username=result["username"]
    )

    conn.admin_user_global_sign_out(
        UserPoolId=result["user_pool_id"], Username=result["username"]
    )

    with pytest.raises(ClientError) as ex:
        conn.initiate_auth(
            ClientId=result["client_id"],
            AuthFlow="REFRESH_TOKEN",
            AuthParameters={
                "REFRESH_TOKEN": result["refresh_token"],
                "SECRET_HASH": result["secret_hash"],
            },
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"
    assert err["Message"] == "Refresh Token has been revoked"


@mock_aws
def test_admin_user_global_sign_out_unknown_userpool():
    conn = boto3.client("cognito-idp", "us-west-2")
    result = user_authentication_flow(conn)
    with pytest.raises(ClientError) as ex:
        conn.admin_user_global_sign_out(UserPoolId="n/a", Username=result["username"])
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_admin_user_global_sign_out_unknown_user():
    conn = boto3.client("cognito-idp", "us-west-2")
    result = user_authentication_flow(conn)
    with pytest.raises(ClientError) as ex:
        conn.admin_user_global_sign_out(
            UserPoolId=result["user_pool_id"], Username="n/a"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "UserNotFoundException"
    assert err["Message"] == "User does not exist."


@mock_aws
def test_global_sign_out():
    conn = boto3.client("cognito-idp", "us-west-2")
    result = user_authentication_flow(conn)

    conn.global_sign_out(AccessToken=result["access_token"])

    with pytest.raises(ClientError) as ex:
        conn.initiate_auth(
            ClientId=result["client_id"],
            AuthFlow="REFRESH_TOKEN",
            AuthParameters={
                "REFRESH_TOKEN": result["refresh_token"],
                "SECRET_HASH": result["secret_hash"],
            },
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"
    assert err["Message"] == "Refresh Token has been revoked"

    with pytest.raises(ClientError) as ex:
        conn.get_user(AccessToken=result["access_token"])

    err = ex.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"


@mock_aws
def test_global_sign_out_unknown_accesstoken():
    conn = boto3.client("cognito-idp", "us-east-2")
    with pytest.raises(ClientError) as ex:
        conn.global_sign_out(AccessToken="n/a")
    err = ex.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"


@mock_aws
def test_admin_update_user_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[
            {"Name": "family_name", "Value": "Doe"},
            {"Name": "given_name", "Value": "John"},
        ],
    )

    conn.admin_update_user_attributes(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[
            {"Name": "family_name", "Value": "Doe"},
            {"Name": "given_name", "Value": "Jane"},
        ],
    )

    user = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    attributes = user["UserAttributes"]
    for attr in attributes:
        val = attr["Value"]
        if attr["Name"] == "family_name":
            assert val == "Doe"
        elif attr["Name"] == "given_name":
            assert val == "Jane"


@mock_aws
def test_admin_delete_user_attributes():
    conn = boto3.client("cognito-idp", "us-east-1")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()),
        Schema=[
            {
                "Name": "foo",
                "AttributeDataType": "String",
                "Mutable": True,
                "Required": False,
            }
        ],
    )["UserPool"]["Id"]

    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[
            {"Name": "family_name", "Value": "Doe"},
            {"Name": "given_name", "Value": "John"},
            {"Name": "nickname", "Value": "Joe"},
            {"Name": "custom:foo", "Value": "bar"},
        ],
    )

    conn.admin_delete_user_attributes(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributeNames=["nickname", "custom:foo"],
    )

    user = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)

    assert len(user["UserAttributes"]) == 3  # family_name, given_name and sub
    assert {"Name": "family_name", "Value": "Doe"} in user["UserAttributes"]
    assert {"Name": "given_name", "Value": "John"} in user["UserAttributes"]
    assert {"Name": "nickname", "Value": "Joe"} not in user["UserAttributes"]
    assert {"Name": "custom:foo", "Value": "bar"} not in user["UserAttributes"]


@mock_aws
def test_admin_delete_user_attributes_non_existing_attribute():
    conn = boto3.client("cognito-idp", "us-east-1")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[
            {"Name": "family_name", "Value": "Doe"},
            {"Name": "given_name", "Value": "John"},
            {"Name": "nickname", "Value": "Joe"},
        ],
    )

    with pytest.raises(ClientError) as exc:
        conn.admin_delete_user_attributes(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributeNames=["nickname", "custom:foo"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "Invalid user attributes: user.custom:foo: Attribute does not exist in the schema.\n"
    )

    with pytest.raises(ClientError) as exc:
        conn.admin_delete_user_attributes(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributeNames=["nickname", "custom:foo", "custom:bar"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "Invalid user attributes: user.custom:foo: Attribute does not exist in the schema.\nuser.custom:bar: Attribute does not exist in the schema.\n"
    )


@mock_aws
def test_admin_delete_user_attributes_non_existing_user():
    conn = boto3.client("cognito-idp", "us-east-1")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    with pytest.raises(ClientError) as exc:
        conn.admin_delete_user_attributes(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributeNames=["nickname", "custom:foo"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotFoundException"
    assert err["Message"] == "User does not exist."


@mock_aws
def test_admin_delete_user_attributes_non_existing_pool():
    conn = boto3.client("cognito-idp", "us-east-1")

    user_pool_id = "us-east-1_aaaaaaaa"
    with pytest.raises(ClientError) as exc:
        conn.admin_delete_user_attributes(
            UserPoolId=user_pool_id,
            Username=str(uuid.uuid4()),
            UserAttributeNames=["nickname"],
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"User pool {user_pool_id} does not exist."


@mock_aws
def test_update_user_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")

    result = authentication_flow(conn, auth_flow="ADMIN_USER_PASSWORD_AUTH")
    access_token = result["access_token"]
    username = result["username"]
    user_pool_id = result["user_pool_id"]

    conn.update_user_attributes(
        AccessToken=access_token,
        UserAttributes=[
            {"Name": "family_name", "Value": "Doe"},
            {"Name": "given_name", "Value": "Jane"},
        ],
    )

    user = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    attributes = user["UserAttributes"]

    assert {"Name": "family_name", "Value": "Doe"} in attributes
    assert {"Name": "given_name", "Value": "Jane"} in attributes


@mock_aws
def test_update_user_attributes_unknown_accesstoken():
    conn = boto3.client("cognito-idp", "us-east-2")
    with pytest.raises(ClientError) as ex:
        conn.update_user_attributes(
            AccessToken="n/a", UserAttributes=[{"Name": "a", "Value": "b"}]
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"


@mock_aws
def test_create_resource_server():
    client = boto3.client("cognito-idp", "us-west-2")
    name = str(uuid.uuid4())
    res = client.create_user_pool(PoolName=name)

    user_pool_id = res["UserPool"]["Id"]
    identifier = "http://localhost.localdomain"
    name = "local server"
    scopes = [
        {"ScopeName": "app:write", "ScopeDescription": "write scope"},
        {"ScopeName": "app:read", "ScopeDescription": "read scope"},
    ]

    res = client.create_resource_server(
        UserPoolId=user_pool_id, Identifier=identifier, Name=name, Scopes=scopes
    )

    assert res["ResourceServer"]["UserPoolId"] == user_pool_id
    assert res["ResourceServer"]["Identifier"] == identifier
    assert res["ResourceServer"]["Name"] == name
    assert res["ResourceServer"]["Scopes"] == scopes

    with pytest.raises(ClientError) as ex:
        client.create_resource_server(
            UserPoolId=user_pool_id, Identifier=identifier, Name=name, Scopes=scopes
        )

    assert ex.value.operation_name == "CreateResourceServer"
    assert ex.value.response["Error"]["Code"] == "InvalidParameterException"
    assert (
        ex.value.response["Error"]["Message"]
        == f"{identifier} already exists in user pool {user_pool_id}."
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_create_resource_server_with_no_scopes():
    client = boto3.client("cognito-idp", "us-west-2")
    name = str(uuid.uuid4())
    res = client.create_user_pool(PoolName=name)

    user_pool_id = res["UserPool"]["Id"]
    identifier = "http://localhost.localdomain"
    name = "local server"

    res = client.create_resource_server(
        UserPoolId=user_pool_id, Identifier=identifier, Name=name
    )

    assert res["ResourceServer"]["UserPoolId"] == user_pool_id
    assert res["ResourceServer"]["Identifier"] == identifier
    assert res["ResourceServer"]["Name"] == name
    assert "Scopes" not in res["ResourceServer"]


@mock_aws
def test_describe_resource_server():
    # Create a user pool to attach a resource server to
    client = boto3.client("cognito-idp", "us-west-2")
    name = str(uuid.uuid4())
    user_pool = client.create_user_pool(PoolName=name)
    user_pool_id = user_pool["UserPool"]["Id"]

    server_id = "my_server"
    server_name = "new_remote_server"
    scopes = [
        {"ScopeName": "app:write", "ScopeDescription": "write scope"},
        {"ScopeName": "app:read", "ScopeDescription": "read scope"},
    ]

    # Create a new resource server
    new_resource_server = client.create_resource_server(
        UserPoolId=user_pool_id, Identifier=server_id, Name=server_name, Scopes=scopes
    )

    assert new_resource_server["ResourceServer"]["UserPoolId"] == user_pool_id
    assert new_resource_server["ResourceServer"]["Identifier"] == server_id
    assert new_resource_server["ResourceServer"]["Name"] == server_name
    assert new_resource_server["ResourceServer"]["Scopes"] == scopes

    # Describe the newly created resource server
    response = client.describe_resource_server(
        UserPoolId=user_pool_id, Identifier=server_id
    )

    # Assert all the values we expect are seen in the description.
    assert response["ResourceServer"]["UserPoolId"] == user_pool_id
    assert response["ResourceServer"]["Identifier"] == server_id
    assert response["ResourceServer"]["Name"] == server_name
    assert response["ResourceServer"]["Scopes"] == scopes

    # Make sure attempting to describe a non-existent server fails in
    # the expected manner
    fake_server_id = "non_existent_server"
    negative_response = None
    with pytest.raises(ClientError) as ex:
        negative_response = client.describe_resource_server(
            UserPoolId=user_pool_id, Identifier=fake_server_id
        )

    # Assert that error message content is what's expected for a failure.
    assert negative_response is None
    assert ex.value.operation_name == "DescribeResourceServer"
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        ex.value.response["Error"]["Message"]
        == f"Resource server {fake_server_id} does not exist."
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_list_resource_servers_empty_set():
    # Create a user pool to attach a resource server to
    client = boto3.client("cognito-idp", "us-west-2")
    name = str(uuid.uuid4())
    user_pool = client.create_user_pool(PoolName=name)
    user_pool_id = user_pool["UserPool"]["Id"]

    # Empty list, because we aren't creating any.
    all_resource_svrs = []

    max_return = 50
    servers = client.list_resource_servers(
        UserPoolId=user_pool_id, MaxResults=max_return
    )

    expected_keys = ["ResourceServers", "ResponseMetadata"]
    assert all(key in servers for key in expected_keys)
    assert servers["ResponseMetadata"].get("HTTPStatusCode")
    assert servers["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert servers.get("NextToken", False) is False
    assert len(servers["ResourceServers"]) == len(all_resource_svrs)
    assert len(servers["ResourceServers"]) == 0


@mock_aws
def test_list_resource_servers_single_page():
    # Create a user pool to attach a resource server to
    client = boto3.client("cognito-idp", "us-west-2")
    name = str(uuid.uuid4())
    user_pool = client.create_user_pool(PoolName=name)
    user_pool_id = user_pool["UserPool"]["Id"]
    create_num = 48

    all_resource_svrs = []
    for id_num in range(0, create_num, 1):
        server_id = f"my_server{id_num}"
        server_name = "new_remote_server{id_num}"
        scopes = [
            {
                "ScopeName": f"app:write{id_num}",
                "ScopeDescription": f"write scope{id_num}",
            },
            {
                "ScopeName": f"app:read{id_num}",
                "ScopeDescription": f"read scope{id_num}",
            },
        ]

        # Create a new resource server
        new_resource_server = client.create_resource_server(
            UserPoolId=user_pool_id,
            Identifier=server_id,
            Name=server_name,
            Scopes=scopes,
        )

        all_resource_svrs.append(new_resource_server)

    max_return = 50
    servers = client.list_resource_servers(
        UserPoolId=user_pool_id, MaxResults=max_return
    )

    expected_keys = ["ResourceServers", "ResponseMetadata"]
    assert all(key in servers for key in expected_keys)
    assert servers["ResponseMetadata"].get("HTTPStatusCode")
    assert servers["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert servers.get("NextToken", False) is False
    assert len(servers["ResourceServers"]) == create_num
    returned_servers = servers["ResourceServers"]

    for idx in range(0, create_num - 1, 1):
        for key in returned_servers[idx].keys():
            assert (
                returned_servers[idx][key]
                == all_resource_svrs[idx]["ResourceServer"][key]
            )


@mock_aws
def test_list_resource_servers_multi_page():
    # Create a user pool to attach a resource server to
    client = boto3.client("cognito-idp", "us-west-2")
    name = str(uuid.uuid4())
    user_pool = client.create_user_pool(PoolName=name)
    user_pool_id = user_pool["UserPool"]["Id"]
    create_num = 65

    all_resource_svrs = []
    for id_num in range(0, create_num, 1):
        server_id = f"my_server{id_num}"
        server_name = "new_remote_server{id_num}"
        scopes = [
            {
                "ScopeName": f"app:write{id_num}",
                "ScopeDescription": f"write scope{id_num}",
            },
            {
                "ScopeName": f"app:read{id_num}",
                "ScopeDescription": f"read scope{id_num}",
            },
        ]

        # Create a new resource server
        new_resource_server = client.create_resource_server(
            UserPoolId=user_pool_id,
            Identifier=server_id,
            Name=server_name,
            Scopes=scopes,
        )

        all_resource_svrs.append(new_resource_server)

    max_return = 50
    servers = client.list_resource_servers(
        UserPoolId=user_pool_id, MaxResults=max_return
    )

    expected_keys = ["ResourceServers", "NextToken", "ResponseMetadata"]
    assert all(key in servers for key in expected_keys)
    assert servers["ResponseMetadata"].get("HTTPStatusCode")
    assert servers["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert servers.get("NextToken", False)
    assert len(servers["ResourceServers"]) == max_return
    returned_servers = servers["ResourceServers"]

    for idx in range(0, max_return - 1, 1):
        for key in returned_servers[idx].keys():
            assert (
                returned_servers[idx][key]
                == all_resource_svrs[idx]["ResourceServer"][key]
            )

    next_page = client.list_resource_servers(
        UserPoolId=user_pool_id, MaxResults=max_return, NextToken=servers["NextToken"]
    )

    expected_keys = ["ResourceServers", "ResponseMetadata"]
    expected_returns = create_num - max_return
    assert all(key in next_page for key in expected_keys)
    assert next_page["ResponseMetadata"].get("HTTPStatusCode")
    assert next_page["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert next_page.get("NextToken", False) is False
    assert len(next_page["ResourceServers"]) == expected_returns
    returned_servers = next_page["ResourceServers"]

    # Check the second page of results
    # Each entry in the second page should be the offset of 'max_return + idx' in all_resource_svrs
    for idx in range(0, expected_returns, 1):
        for key in returned_servers[idx].keys():
            all_idx = idx + max_return
            assert (
                returned_servers[idx][key]
                == all_resource_svrs[all_idx]["ResourceServer"][key]
            )


@cognitoidp_aws_verified()
@pytest.mark.aws_verified
def test_sign_up(user_pool=None, user_pool_client=None):
    conn = boto3.client("cognito-idp", "us-west-2")
    client_id = user_pool_client["UserPoolClient"]["ClientId"]
    username = str(uuid.uuid4())
    password = "P2$Sword"
    result = conn.sign_up(ClientId=client_id, Username=username, Password=password)
    assert result["UserConfirmed"] is False
    assert result["UserSub"] is not None
    assert "CodeDeliveryDetails" not in result


@cognitoidp_aws_verified(recovery=[{"Name": "verified_email", "Priority": 1}])
@pytest.mark.aws_verified
def test_sign_up_with_unverified_email(user_pool=None, user_pool_client=None):
    conn = boto3.client("cognito-idp", "us-west-2")
    client_id = user_pool_client["UserPoolClient"]["ClientId"]
    username = str(uuid.uuid4())
    password = "P2$Sword"
    result = conn.sign_up(
        ClientId=client_id,
        Username=username,
        Password=password,
        UserAttributes=[{"Name": "email", "Value": "test@test.com"}],
    )
    assert result["UserConfirmed"] is False
    assert result["UserSub"] is not None
    assert "CodeDeliveryDetails" not in result


@cognitoidp_aws_verified(
    recovery=[{"Name": "verified_email", "Priority": 1}], verified_attributes=["email"]
)
@pytest.mark.aws_verified
def test_sign_up_with_verified_email(user_pool=None, user_pool_client=None):
    conn = boto3.client("cognito-idp", "us-west-2")
    client_id = user_pool_client["UserPoolClient"]["ClientId"]
    username = str(uuid.uuid4())
    password = "P2$Sword"
    result = conn.sign_up(
        ClientId=client_id,
        Username=username,
        Password=password,
        UserAttributes=[{"Name": "email", "Value": "test@test.com"}],
    )
    assert result["UserConfirmed"] is False
    assert result["UserSub"] is not None
    assert result["CodeDeliveryDetails"] == {
        "Destination": "t***@t***",
        "DeliveryMedium": "EMAIL",
        "AttributeName": "email",
    }


@cognitoidp_aws_verified(
    recovery=[{"Name": "verified_email", "Priority": 1}], verified_attributes=["email"]
)
@pytest.mark.aws_verified
def test_sign_up_with_verified_but_not_supplied_email(
    user_pool=None, user_pool_client=None
):
    conn = boto3.client("cognito-idp", "us-west-2")
    client_id = user_pool_client["UserPoolClient"]["ClientId"]
    username = str(uuid.uuid4())
    password = "P2$Sword"
    result = conn.sign_up(ClientId=client_id, Username=username, Password=password)
    assert result["UserConfirmed"] is False
    assert result["UserSub"] is not None
    assert "CodeDeliveryDetails" not in result


@mock_aws
@pytest.mark.parametrize("password", ["p2$$word", "P2$s"])
def test_sign_up_with_invalid_password(password):
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4())
    )["UserPoolClient"]["ClientId"]
    username = str(uuid.uuid4())

    with pytest.raises(ClientError) as exc:
        conn.sign_up(ClientId=client_id, Username=username, Password=password)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidPasswordException"


@mock_aws
def test_sign_up_with_username_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email", "phone_number"]
    )["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4())
    )["UserPoolClient"]["ClientId"]
    username = str(uuid.uuid4())
    password = "P2$Sword"
    with pytest.raises(ClientError) as err:
        # Attempt to add user again
        conn.sign_up(ClientId=client_id, Username=username, Password=password)
    assert err.value.response["Error"]["Code"] == "InvalidParameterException"

    username = "test@example.com"
    result = conn.sign_up(ClientId=client_id, Username=username, Password=password)

    assert result["UserConfirmed"] is False
    assert result["UserSub"] is not None
    username = "+123456789"
    result = conn.sign_up(ClientId=client_id, Username=username, Password=password)

    assert result["UserConfirmed"] is False
    assert result["UserSub"] is not None


@mock_aws
def test_sign_up_existing_user():
    conn = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4())
    )["UserPoolClient"]["ClientId"]
    username = str(uuid.uuid4())
    password = "P2$Sword"

    # Add initial user
    conn.sign_up(ClientId=client_id, Username=username, Password=password)

    with pytest.raises(ClientError) as err:
        # Attempt to add user again
        conn.sign_up(ClientId=client_id, Username=username, Password=password)

    assert err.value.response["Error"]["Code"] == "UsernameExistsException"


@mock_aws
def test_confirm_sign_up():
    conn = boto3.client("cognito-idp", "us-west-2")
    username = str(uuid.uuid4())
    password = "P2$Sword"
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=True
    )["UserPoolClient"]["ClientId"]
    _signup_and_confirm(client_id, conn, password, username)

    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert result["UserStatus"] == "CONFIRMED"


@set_initial_no_auth_action_count(0)
def _signup_and_confirm(client_id, conn, password, username):
    # Also verify Authentication works for these actions
    # There are no IAM policies, but they should be public - accessible by anyone
    conn.sign_up(ClientId=client_id, Username=username, Password=password)

    conn.confirm_sign_up(
        ClientId=client_id, Username=username, ConfirmationCode="123456"
    )


@mock_aws
def test_confirm_sign_up_with_username_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")
    username = "test@example.com"
    password = "P2$Sword"
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=True
    )["UserPoolClient"]["ClientId"]
    conn.sign_up(ClientId=client_id, Username=username, Password=password)

    conn.confirm_sign_up(
        ClientId=client_id, Username=username, ConfirmationCode="123456"
    )

    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert result["UserStatus"] == "CONFIRMED"


@mock_aws
def test_initiate_auth_USER_SRP_AUTH():
    conn = boto3.client("cognito-idp", "us-west-2")
    username = str(uuid.uuid4())
    password = "P2$Sword"
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=True
    )["UserPoolClient"]["ClientId"]
    conn.sign_up(ClientId=client_id, Username=username, Password=password)
    client_secret = conn.describe_user_pool_client(
        UserPoolId=user_pool_id, ClientId=client_id
    )["UserPoolClient"]["ClientSecret"]
    conn.confirm_sign_up(
        ClientId=client_id, Username=username, ConfirmationCode="123456"
    )

    key = bytes(str(client_secret).encode("latin-1"))
    msg = bytes(str(username + client_id).encode("latin-1"))
    new_digest = hmac.new(key, msg, hashlib.sha256).digest()
    secret_hash = base64.b64encode(new_digest).decode()

    result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_SRP_AUTH",
        AuthParameters={
            "USERNAME": username,
            "SRP_A": uuid.uuid4().hex,
            "SECRET_HASH": secret_hash,
        },
    )

    assert result["ChallengeName"] == "PASSWORD_VERIFIER"
    assert result["ChallengeParameters"]["USERNAME"] == username


@mock_aws
def test_initiate_auth_USER_SRP_AUTH_with_username_attributes():
    conn = boto3.client("cognito-idp", "us-west-2")
    username = "test@example.com"
    password = "P2$Sword"
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=True
    )["UserPoolClient"]["ClientId"]
    conn.sign_up(ClientId=client_id, Username=username, Password=password)
    client_secret = conn.describe_user_pool_client(
        UserPoolId=user_pool_id, ClientId=client_id
    )["UserPoolClient"]["ClientSecret"]
    conn.confirm_sign_up(
        ClientId=client_id, Username=username, ConfirmationCode="123456"
    )

    key = bytes(str(client_secret).encode("latin-1"))
    msg = bytes(str(username + client_id).encode("latin-1"))
    new_digest = hmac.new(key, msg, hashlib.sha256).digest()
    secret_hash = base64.b64encode(new_digest).decode()

    result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_SRP_AUTH",
        AuthParameters={
            "USERNAME": username,
            "SRP_A": uuid.uuid4().hex,
            "SECRET_HASH": secret_hash,
        },
    )

    assert result["ChallengeName"] == "PASSWORD_VERIFIER"


@pytest.mark.aws_verified
@cognitoidp_aws_verified(generate_secret=True)
def test_initiate_auth_REFRESH_TOKEN(user_pool=None, user_pool_client=None):
    conn = boto3.client("cognito-idp", "us-west-2")
    result = user_authentication_flow(
        conn, user_pool=user_pool, user_pool_client=user_pool_client, with_mfa=False
    )
    auth_result = conn.initiate_auth(
        ClientId=result["client_id"],
        AuthFlow="REFRESH_TOKEN",
        AuthParameters={
            "REFRESH_TOKEN": result["refresh_token"],
            "SECRET_HASH": result["secret_hash"],
        },
    )["AuthenticationResult"]
    access_token = auth_result["AccessToken"]
    id_token = auth_result["IdToken"]

    # Validate Access Token
    access_payload = get_jwt_payload(access_token)
    assert access_payload.claims["username"] == result["username"]
    assert access_payload.claims["client_id"] == result["client_id"]

    # Validate ID Token
    id_payload = get_jwt_payload(id_token)
    assert id_payload.claims["sub"] == access_payload.claims["sub"]
    assert id_payload.claims["cognito:username"] == result["username"]
    assert id_payload.claims["aud"] == result["client_id"]


def get_jwt_payload(access_token):
    old_validate_compact = jws.validate_compact

    def new_validate_compact(*args, **kwargs):
        return True

    jws.validate_compact = new_validate_compact
    try:
        payload = jwt.decode(access_token, key=None)
    finally:
        jws.validate_compact = old_validate_compact
    return payload


@pytest.mark.aws_verified
@cognitoidp_aws_verified(
    generate_secret=True, explicit_auth_flows=["USER_PASSWORD_AUTH"]
)
def test_initiate_auth_USER_PASSWORD_AUTH(user_pool=None, user_pool_client=None):
    conn = boto3.client("cognito-idp", "us-west-2")

    result = user_authentication_flow(
        conn, user_pool=user_pool, user_pool_client=user_pool_client, with_mfa=False
    )

    user_pool_id = result["user_pool_id"]
    client_id = result["client_id"]
    username = result["username"]
    password = result["password"]
    secret_hash = result["secret_hash"]

    # user_authentication_flow enables software token mfa so disable it
    conn.admin_set_user_mfa_preference(
        Username=username,
        UserPoolId=user_pool_id,
        SoftwareTokenMfaSettings={"Enabled": False, "PreferredMfa": False},
    )

    # ensure no mfa settings are set so no challenge is returned on initiate_auth
    # Moto returns empty values - AWS returs no values
    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert len(result.get("UserMFASettingList", [])) == 0
    assert result.get("PreferredMfaSetting", "") == ""

    auth_result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password,
            "SECRET_HASH": secret_hash,
        },
    )["AuthenticationResult"]

    assert auth_result["RefreshToken"] is not None
    assert auth_result["TokenType"] == "Bearer"

    # Validate Access Token
    access_payload = get_jwt_payload(auth_result["AccessToken"])
    assert access_payload.claims["username"] == username
    assert access_payload.claims["client_id"] == client_id
    assert "email" not in access_payload.claims

    # Validate ID Token
    id_payload = get_jwt_payload(auth_result["IdToken"])
    assert id_payload.claims["sub"] == access_payload.claims["sub"]
    assert id_payload.claims["cognito:username"] == username
    assert id_payload.claims["aud"] == client_id
    assert "email" not in id_payload.claims


@pytest.mark.aws_verified
@cognitoidp_aws_verified(
    generate_secret=True,
    explicit_auth_flows=["USER_PASSWORD_AUTH"],
    username_attributes=["email"],
)
def test_initiate_auth_USER_PASSWORD_AUTH_with_email(
    user_pool=None, user_pool_client=None
):
    conn = boto3.client("cognito-idp", "us-west-2")

    username = "test@moto.com"
    password = "SuperS3cret!"
    client_id = user_pool_client["UserPoolClient"]["ClientId"]
    client_secret = user_pool_client["UserPoolClient"]["ClientSecret"]
    user_pool_id = user_pool["UserPool"]["Id"]

    secret_hash = pycognito.aws_srp.AWSSRP.get_secret_hash(
        username=username, client_id=client_id, client_secret=client_secret
    )
    conn.sign_up(
        ClientId=client_id, Username=username, Password=password, SecretHash=secret_hash
    )

    client_secret = conn.describe_user_pool_client(
        UserPoolId=user_pool_id, ClientId=client_id
    )["UserPoolClient"]["ClientSecret"]

    conn.admin_confirm_sign_up(UserPoolId=user_pool_id, Username=username)
    auth_result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password,
            "SECRET_HASH": secret_hash,
        },
    )["AuthenticationResult"]

    # Validate Access Token
    access_payload = get_jwt_payload(auth_result["AccessToken"])
    assert access_payload.claims["username"] == access_payload.claims["sub"]
    assert access_payload.claims["client_id"] == client_id
    assert "email" not in access_payload.claims

    # Validate ID Token
    id_payload = get_jwt_payload(auth_result["IdToken"])
    assert id_payload.claims["sub"] == access_payload.claims["sub"]
    assert id_payload.claims["cognito:username"] == id_payload.claims["sub"]
    assert id_payload.claims["aud"] == client_id
    assert id_payload.claims["email"] == username


@mock_aws
def test_initiate_auth_USER_PASSWORD_AUTH_when_software_token_mfa_enabled():
    conn = boto3.client("cognito-idp", "us-west-2")

    result = user_authentication_flow(conn)

    user_pool_id = result["user_pool_id"]
    username = result["username"]
    password = result["password"]
    client_id = result["client_id"]
    secret_hash = result["secret_hash"]

    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert result["PreferredMfaSetting"] == "SOFTWARE_TOKEN_MFA"

    result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )

    assert result["ChallengeName"] == "SOFTWARE_TOKEN_MFA"
    assert result["ChallengeParameters"] == {}
    assert result["Session"] is not None

    result = conn.respond_to_auth_challenge(
        ClientId=client_id,
        ChallengeName="SOFTWARE_TOKEN_MFA",
        Session=result["Session"],
        ChallengeResponses={
            "SOFTWARE_TOKEN_MFA_CODE": "123456",
            "USERNAME": username,
            "SECRET_HASH": secret_hash,
        },
    )

    assert result["AuthenticationResult"]["IdToken"] != ""
    assert result["AuthenticationResult"]["AccessToken"] != ""
    assert result["AuthenticationResult"]["RefreshToken"] != ""
    assert result["AuthenticationResult"]["TokenType"] == "Bearer"


@mock_aws
def test_initiate_auth_USER_PASSWORD_AUTH_when_sms_mfa_enabled():
    conn = boto3.client("cognito-idp", "us-west-2")

    result = user_authentication_flow(conn)

    user_pool_id = result["user_pool_id"]
    username = result["username"]
    password = result["password"]
    client_id = result["client_id"]
    secret_hash = result["secret_hash"]

    conn.admin_set_user_mfa_preference(
        Username=username,
        UserPoolId=user_pool_id,
        SMSMfaSettings={"Enabled": True, "PreferredMfa": True},
    )

    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert result["PreferredMfaSetting"] == "SMS_MFA"

    result = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )

    assert result["ChallengeName"] == "SMS_MFA"
    assert result["ChallengeParameters"] == {}
    assert result["Session"] is not None

    result = conn.respond_to_auth_challenge(
        ClientId=client_id,
        ChallengeName="SMS_MFA",
        Session=result["Session"],
        ChallengeResponses={
            "SMS_MFA_CODE": "123456",
            "USERNAME": username,
            "SECRET_HASH": secret_hash,
        },
    )

    assert result["AuthenticationResult"]["IdToken"] != ""
    assert result["AuthenticationResult"]["AccessToken"] != ""
    assert result["AuthenticationResult"]["RefreshToken"] != ""
    assert result["AuthenticationResult"]["TokenType"] == "Bearer"


@mock_aws
def test_initiate_auth_invalid_auth_flow():
    conn = boto3.client("cognito-idp", "us-west-2")
    result = user_authentication_flow(conn)

    with pytest.raises(ClientError) as ex:
        user_authentication_flow(conn)

        conn.initiate_auth(
            ClientId=result["client_id"],
            AuthFlow="NO_SUCH_FLOW",
            AuthParameters={
                "USERNAME": result["username"],
                "PASSWORD": result["password"],
            },
        )

    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "1 validation error detected: Value 'NO_SUCH_FLOW' at 'authFlow' failed to satisfy constraint: Member must satisfy enum value set: ['ADMIN_NO_SRP_AUTH', 'ADMIN_USER_PASSWORD_AUTH', 'USER_SRP_AUTH', 'REFRESH_TOKEN_AUTH', 'REFRESH_TOKEN', 'CUSTOM_AUTH', 'USER_PASSWORD_AUTH']"
    )


@mock_aws
def test_initiate_auth_invalid_admin_auth_flow():
    """Pass an admin auth_flow to the regular initiate_auth"""
    conn = boto3.client("cognito-idp", "us-west-2")
    result = user_authentication_flow(conn)

    with pytest.raises(ClientError) as ex:
        user_authentication_flow(conn)

        conn.initiate_auth(
            ClientId=result["client_id"],
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": result["username"],
                "PASSWORD": result["password"],
            },
        )

    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert err["Message"] == "Initiate Auth method not supported"


@mock_aws
def test_initiate_auth_USER_PASSWORD_AUTH_with_FORCE_CHANGE_PASSWORD_status():
    # Test flow:
    # 1. Create user with FORCE_CHANGE_PASSWORD status
    # 2. Login with temporary password
    # 3. Check that the right challenge is received
    # 4. Respond to challenge with new password
    # 5. Check that the access tokens are received

    client = boto3.client("cognito-idp", "us-west-2")
    username = str(uuid.uuid4())

    # Create pool and client
    user_pool_id = client.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]

    client_id = client.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=True
    )["UserPoolClient"]["ClientId"]

    # Create user in status FORCE_CHANGE_PASSWORD
    temporary_password = "P2$Sword"
    client.admin_create_user(
        UserPoolId=user_pool_id, Username=username, TemporaryPassword=temporary_password
    )

    result = client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": temporary_password},
    )

    assert result["ChallengeName"] == "NEW_PASSWORD_REQUIRED"
    assert result["ChallengeParameters"]["USERNAME"] == username
    assert result["Session"] != ""
    assert result.get("AuthenticationResult") is None

    new_password = "P2$Sword2"
    result = client.respond_to_auth_challenge(
        ClientId=client_id,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        Session=result["Session"],
        ChallengeResponses={
            "NEW_PASSWORD": new_password,
            "USERNAME": result["ChallengeParameters"]["USERNAME"],
        },
    )

    assert result["AuthenticationResult"]["IdToken"] != ""
    assert result["AuthenticationResult"]["AccessToken"] != ""


@cognitoidp_aws_verified(explicit_auth_flows=["USER_PASSWORD_AUTH"], with_mfa="ON")
@pytest.mark.aws_verified
def test_initiate_mfa_auth_USER_PASSWORD_AUTH_with_FORCE_CHANGE_PASSWORD_status(
    user_pool=None, user_pool_client=None
):
    # Test flow:
    # 1. Create user with FORCE_CHANGE_PASSWORD status
    # 2. Configure MFA
    # 3. Login with temporary password
    # 4. Check that the right challenge is received
    # 5. Respond to challenge with new password
    # 6. Check that the MFA challenge is received
    # 7. Return the MFA challenge
    # 8. Check that the access tokens are received
    # 9. Login again

    client = boto3.client("cognito-idp", "us-west-2")
    username = str(uuid.uuid4())

    user_pool_id = user_pool["UserPool"]["Id"]
    client_id = user_pool_client["UserPoolClient"]["ClientId"]

    # Create user in status FORCE_CHANGE_PASSWORD
    temporary_password = "P2$Sword"
    client.admin_create_user(
        UserPoolId=user_pool_id, Username=username, TemporaryPassword=temporary_password
    )

    result = client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": temporary_password},
    )

    assert result["ChallengeName"] == "NEW_PASSWORD_REQUIRED"
    assert result.get("AuthenticationResult") is None

    new_password = "P2$Sword2"
    result = client.respond_to_auth_challenge(
        ClientId=client_id,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        Session=result["Session"],
        ChallengeResponses={
            "NEW_PASSWORD": new_password,
            "USERNAME": username,
        },
    )
    assert result["ChallengeName"] == "MFA_SETUP"
    assert result["Session"]

    assoc_response = client.associate_software_token(Session=result["Session"])

    secret_code = assoc_response["SecretCode"]
    totp = pyotp.TOTP(secret_code)
    user_code = totp.now()

    verify_response = client.verify_software_token(
        Session=assoc_response["Session"], UserCode=user_code
    )
    assert verify_response["Status"] == "SUCCESS"

    new_user_code = totp.now()
    if allow_aws_request():
        while user_code == new_user_code:
            new_user_code = totp.now()
            time.sleep(1)
    result = client.respond_to_auth_challenge(
        ClientId=client_id,
        Session=verify_response["Session"],
        ChallengeName=result["ChallengeName"],
        ChallengeResponses={
            "SOFTWARE_TOKEN_MFA_CODE": new_user_code,
            "USERNAME": username,
        },
    )
    assert result["ChallengeParameters"] == {}
    assert result["AuthenticationResult"]["AccessToken"]
    assert result["AuthenticationResult"]["RefreshToken"]
    assert result["AuthenticationResult"]["IdToken"]

    result = client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": new_password},
    )
    assert result["ChallengeName"] == "SOFTWARE_TOKEN_MFA"
    third_user_code = totp.now()
    if allow_aws_request():
        while third_user_code == new_user_code:
            third_user_code = totp.now()
            time.sleep(1)
    result = client.respond_to_auth_challenge(
        ClientId=client_id,
        Session=result["Session"],
        ChallengeName=result["ChallengeName"],
        ChallengeResponses={
            "SOFTWARE_TOKEN_MFA_CODE": third_user_code,
            "USERNAME": username,
        },
    )
    assert result["ChallengeParameters"] == {}
    assert result["AuthenticationResult"]["AccessToken"]
    assert result["AuthenticationResult"]["RefreshToken"]
    assert result["AuthenticationResult"]["IdToken"]


@mock_aws
def test_initiate_auth_USER_PASSWORD_AUTH_user_not_found():
    conn = boto3.client("cognito-idp", "us-west-2")
    result = user_authentication_flow(conn)
    with pytest.raises(ClientError) as ex:
        conn.initiate_auth(
            ClientId=result["client_id"],
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": "INVALIDUSER", "PASSWORD": result["password"]},
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "UserNotFoundException"


@mock_aws
def test_initiate_auth_USER_PASSWORD_AUTH_user_incorrect_password():
    conn = boto3.client("cognito-idp", "us-west-2")
    result = user_authentication_flow(conn)
    with pytest.raises(ClientError) as ex:
        conn.initiate_auth(
            ClientId=result["client_id"],
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": result["username"],
                "PASSWORD": "NotAuthorizedException",
            },
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"


@mock_aws
def test_initiate_auth_USER_PASSWORD_AUTH_unconfirmed_user():
    conn = boto3.client("cognito-idp", "us-west-2")
    username = str(uuid.uuid4())
    password = "P2$Sword"
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=True
    )["UserPoolClient"]["ClientId"]
    conn.sign_up(ClientId=client_id, Username=username, Password=password)

    with pytest.raises(ClientError) as ex:
        conn.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "UserNotConfirmedException"


@mock_aws
def test_initiate_auth_for_unconfirmed_user():
    conn = boto3.client("cognito-idp", "us-west-2")
    username = str(uuid.uuid4())
    password = "P2$Sword"
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=True
    )["UserPoolClient"]["ClientId"]
    conn.sign_up(ClientId=client_id, Username=username, Password=password)
    client_secret = conn.describe_user_pool_client(
        UserPoolId=user_pool_id, ClientId=client_id
    )["UserPoolClient"]["ClientSecret"]

    key = bytes(str(client_secret).encode("latin-1"))
    msg = bytes(str(username + client_id).encode("latin-1"))
    new_digest = hmac.new(key, msg, hashlib.sha256).digest()
    secret_hash = base64.b64encode(new_digest).decode()

    with pytest.raises(ClientError) as exc:
        conn.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_SRP_AUTH",
            AuthParameters={
                "USERNAME": username,
                "SRP_A": uuid.uuid4().hex,
                "SECRET_HASH": secret_hash,
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotConfirmedException"


@mock_aws
def test_initiate_auth_with_invalid_secret_hash():
    conn = boto3.client("cognito-idp", "us-west-2")
    username = str(uuid.uuid4())
    password = "P2$Sword"
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=True
    )["UserPoolClient"]["ClientId"]
    conn.sign_up(ClientId=client_id, Username=username, Password=password)
    conn.describe_user_pool_client(UserPoolId=user_pool_id, ClientId=client_id)
    conn.confirm_sign_up(
        ClientId=client_id, Username=username, ConfirmationCode="123456"
    )

    invalid_secret_hash = str(uuid.uuid4())

    with pytest.raises(ClientError) as exc:
        conn.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_SRP_AUTH",
            AuthParameters={
                "USERNAME": username,
                "SRP_A": uuid.uuid4().hex,
                "SECRET_HASH": invalid_secret_hash,
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"


@mock_aws
def test_setting_mfa():
    conn = boto3.client("cognito-idp", "us-west-2")

    for auth_flow in ["ADMIN_NO_SRP_AUTH", "ADMIN_USER_PASSWORD_AUTH"]:
        result = authentication_flow(conn, auth_flow)

        # Set MFA method
        conn.associate_software_token(AccessToken=result["access_token"])
        conn.verify_software_token(
            AccessToken=result["access_token"], UserCode="123456"
        )
        conn.set_user_mfa_preference(
            AccessToken=result["access_token"],
            SoftwareTokenMfaSettings={"Enabled": True, "PreferredMfa": True},
        )
        user = conn.admin_get_user(
            UserPoolId=result["user_pool_id"], Username=result["username"]
        )

        assert len(user["UserMFASettingList"]) == 1
        assert user["PreferredMfaSetting"] == "SOFTWARE_TOKEN_MFA"

        # Unset MFA method
        conn.set_user_mfa_preference(
            AccessToken=result["access_token"],
            SoftwareTokenMfaSettings={"Enabled": False, "PreferredMfa": False},
        )
        user = conn.admin_get_user(
            UserPoolId=result["user_pool_id"], Username=result["username"]
        )

        assert len(user["UserMFASettingList"]) == 0
        assert user["PreferredMfaSetting"] == ""


@mock_aws
def test_setting_mfa_when_token_not_verified():
    conn = boto3.client("cognito-idp", "us-west-2")

    for auth_flow in ["ADMIN_NO_SRP_AUTH", "ADMIN_USER_PASSWORD_AUTH"]:
        result = authentication_flow(conn, auth_flow)
        conn.associate_software_token(AccessToken=result["access_token"])

        with pytest.raises(ClientError) as exc:
            conn.set_user_mfa_preference(
                AccessToken=result["access_token"],
                SoftwareTokenMfaSettings={"Enabled": True, "PreferredMfa": True},
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "InvalidParameterException"


@mock_aws
def test_admin_setting_single_mfa():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    username = "test@example.com"
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    # Set MFA SMS method
    conn.admin_set_user_mfa_preference(
        Username=username,
        UserPoolId=user_pool_id,
        SMSMfaSettings={"Enabled": True, "PreferredMfa": True},
    )
    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert len(result["UserMFASettingList"]) == 1
    assert result["PreferredMfaSetting"] == "SMS_MFA"

    # Unset MFA SMS method
    conn.admin_set_user_mfa_preference(
        Username=username,
        UserPoolId=user_pool_id,
        SMSMfaSettings={"Enabled": False, "PreferredMfa": False},
    )
    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert len(result["UserMFASettingList"]) == 0
    assert result["PreferredMfaSetting"] == ""


@mock_aws
def test_admin_setting_mfa_totp_and_sms():
    conn = boto3.client("cognito-idp", "us-west-2")

    result = authentication_flow(conn, "ADMIN_NO_SRP_AUTH")
    access_token = result["access_token"]
    user_pool_id = result["user_pool_id"]
    username = result["username"]
    conn.associate_software_token(AccessToken=access_token)
    conn.verify_software_token(AccessToken=access_token, UserCode="123456")

    # Set MFA TOTP and SMS methods
    conn.admin_set_user_mfa_preference(
        Username=username,
        UserPoolId=user_pool_id,
        SoftwareTokenMfaSettings={"Enabled": True, "PreferredMfa": True},
        SMSMfaSettings={"Enabled": True, "PreferredMfa": False},
    )
    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert len(result["UserMFASettingList"]) == 2
    assert result["PreferredMfaSetting"] == "SOFTWARE_TOKEN_MFA"

    # Unset MFA TOTP and SMS methods
    conn.admin_set_user_mfa_preference(
        Username=username,
        UserPoolId=user_pool_id,
        SoftwareTokenMfaSettings={"Enabled": False, "PreferredMfa": False},
        SMSMfaSettings={"Enabled": False, "PreferredMfa": False},
    )
    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert len(result["UserMFASettingList"]) == 0
    assert result["PreferredMfaSetting"] == ""


@mock_aws
def test_admin_initiate_auth_when_token_totp_enabled():
    conn = boto3.client("cognito-idp", "us-west-2")

    result = authentication_flow(conn, "ADMIN_NO_SRP_AUTH")
    access_token = result["access_token"]
    user_pool_id = result["user_pool_id"]
    username = result["username"]
    client_id = result["client_id"]
    password = result["password"]
    conn.associate_software_token(AccessToken=access_token)
    conn.verify_software_token(AccessToken=access_token, UserCode="123456")

    # Set MFA TOTP and SMS methods
    conn.admin_set_user_mfa_preference(
        Username=username,
        UserPoolId=user_pool_id,
        SoftwareTokenMfaSettings={"Enabled": True, "PreferredMfa": True},
        SMSMfaSettings={"Enabled": True, "PreferredMfa": False},
    )
    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert len(result["UserMFASettingList"]) == 2
    assert result["PreferredMfaSetting"] == "SOFTWARE_TOKEN_MFA"

    # Initiate auth with TOTP
    result = conn.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password,
        },
    )

    assert result["ChallengeName"] == "SOFTWARE_TOKEN_MFA"
    assert result["Session"] != ""

    # Respond to challenge with TOTP
    result = conn.admin_respond_to_auth_challenge(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        ChallengeName="SOFTWARE_TOKEN_MFA",
        Session=result["Session"],
        ChallengeResponses={
            "SOFTWARE_TOKEN_MFA_CODE": "123456",
            "USERNAME": username,
        },
    )

    assert result["AuthenticationResult"]["IdToken"] != ""
    assert result["AuthenticationResult"]["AccessToken"] != ""
    assert result["AuthenticationResult"]["RefreshToken"] != ""
    assert result["AuthenticationResult"]["TokenType"] == "Bearer"


@mock_aws
def test_admin_initiate_auth_when_sms_mfa_enabled():
    conn = boto3.client("cognito-idp", "us-west-2")

    result = authentication_flow(conn, "ADMIN_NO_SRP_AUTH")
    user_pool_id = result["user_pool_id"]
    username = result["username"]
    client_id = result["client_id"]
    password = result["password"]

    # Set MFA SMS methods
    conn.admin_set_user_mfa_preference(
        Username=username,
        UserPoolId=user_pool_id,
        SMSMfaSettings={"Enabled": True, "PreferredMfa": True},
    )
    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert len(result["UserMFASettingList"]) == 1
    assert result["PreferredMfaSetting"] == "SMS_MFA"

    result = conn.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password,
        },
    )

    assert result["ChallengeName"] == "SMS_MFA"
    assert result["Session"] != ""

    result = conn.admin_respond_to_auth_challenge(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        ChallengeName="SMS_MFA",
        Session=result["Session"],
        ChallengeResponses={
            "SMS_MFA_CODE": "123456",
            "USERNAME": username,
        },
    )

    assert result["AuthenticationResult"]["IdToken"] != ""
    assert result["AuthenticationResult"]["AccessToken"] != ""
    assert result["AuthenticationResult"]["RefreshToken"] != ""
    assert result["AuthenticationResult"]["TokenType"] == "Bearer"


@mock_aws
def test_admin_setting_mfa_when_token_not_verified():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()), UsernameAttributes=["email"]
    )["UserPool"]["Id"]
    username = "test@example.com"
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)

    with pytest.raises(conn.exceptions.InvalidParameterException):
        conn.admin_set_user_mfa_preference(
            Username=username,
            UserPoolId=user_pool_id,
            SoftwareTokenMfaSettings={"Enabled": True, "PreferredMfa": True},
        )


@mock_aws
def test_respond_to_auth_challenge_with_invalid_secret_hash():
    conn = boto3.client("cognito-idp", "us-west-2")
    result = user_authentication_flow(conn)

    valid_secret_hash = result["secret_hash"]
    invalid_secret_hash = str(uuid.uuid4())

    challenge = conn.initiate_auth(
        ClientId=result["client_id"],
        AuthFlow="USER_SRP_AUTH",
        AuthParameters={
            "USERNAME": result["username"],
            "SRP_A": uuid.uuid4().hex,
            "SECRET_HASH": valid_secret_hash,
        },
    )

    challenge = conn.respond_to_auth_challenge(
        ClientId=result["client_id"],
        ChallengeName=challenge["ChallengeName"],
        ChallengeResponses={
            "PASSWORD_CLAIM_SIGNATURE": str(uuid.uuid4()),
            "PASSWORD_CLAIM_SECRET_BLOCK": challenge["Session"],
            "TIMESTAMP": str(uuid.uuid4()),
            "USERNAME": result["username"],
        },
    )

    with pytest.raises(ClientError) as exc:
        conn.respond_to_auth_challenge(
            ClientId=result["client_id"],
            Session=challenge["Session"],
            ChallengeName=challenge["ChallengeName"],
            ChallengeResponses={
                "SOFTWARE_TOKEN_MFA_CODE": "123456",
                "USERNAME": result["username"],
                "SECRET_HASH": invalid_secret_hash,
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"


@mock_aws
def test_admin_set_user_password():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    value = str(uuid.uuid4())
    password = "P2$$word"
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "thing", "Value": value}],
    )
    conn.admin_set_user_password(
        UserPoolId=user_pool_id, Username=username, Password=password, Permanent=True
    )
    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert result["Username"] == username
    assert len(result["UserAttributes"]) == 2

    def _verify_attribute(name, v):
        attr = [a for a in result["UserAttributes"] if a["Name"] == name]
        assert len(attr) == 1
        assert attr[0]["Value"] == v

    _verify_attribute("thing", value)


@mock_aws
@pytest.mark.parametrize("password", ["pa$$word", "Password", "p2ssword", "P2$S"])
def test_admin_set_invalid_user_password(password):
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "thing", "Value": value}],
    )
    with pytest.raises(ClientError) as exc:
        conn.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=password,
            Permanent=True,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidPasswordException"


@mock_aws
@pytest.mark.parametrize("password", ["password", "P2$$word"])
def test_admin_set_invalid_user_password__custom_policy_provided(password):
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(
        PoolName=str(uuid.uuid4()),
        Policies={
            "PasswordPolicy": {
                "MinimumLength": 12,
                "RequireUppercase": False,
                "RequireLowercase": False,
                "RequireNumbers": False,
                "RequireSymbols": False,
            }
        },
    )["UserPool"]["Id"]
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "thing", "Value": value}],
    )
    with pytest.raises(ClientError) as exc:
        conn.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=password,
            Permanent=True,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidPasswordException"

    # We can set a plain password, as long as it's 12 characters long
    conn.admin_set_user_password(
        UserPoolId=user_pool_id,
        Username=username,
        Password="longpassword",
        Permanent=True,
    )


@mock_aws
def test_change_password_with_invalid_token_raises_error():
    client = boto3.client("cognito-idp", "us-west-2")
    with pytest.raises(ClientError) as ex:
        client.change_password(
            AccessToken=str(uuid.uuid4()),
            PreviousPassword="previous_password",
            ProposedPassword="newer_password",
        )
    assert ex.value.response["Error"]["Code"] == "NotAuthorizedException"


@mock_aws
def test_confirm_forgot_password_with_non_existent_client_id_raises_error():
    client = boto3.client("cognito-idp", "us-west-2")
    with pytest.raises(ClientError) as ex:
        client.confirm_forgot_password(
            ClientId="non-existent-client-id",
            Username="not-existent-username",
            ConfirmationCode=str(uuid.uuid4()),
            Password=str(uuid.uuid4()),
        )
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_admin_reset_password_and_change_password():
    client = boto3.client("cognito-idp", "us-west-2")
    username = str(uuid.uuid4())
    temporary_pass = str(uuid.uuid4())
    # Create pool and client
    user_pool_id = client.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = client.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=True
    )["UserPoolClient"]["ClientId"]
    # Create CONFIRMED user with verified email
    client.admin_create_user(
        UserPoolId=user_pool_id, Username=username, TemporaryPassword=temporary_pass
    )
    client.confirm_sign_up(
        ClientId=client_id, Username=username, ConfirmationCode="123456"
    )
    client.admin_update_user_attributes(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "email_verified", "Value": "true"}],
    )

    # User should be in RESET_REQUIRED state after reset
    client.admin_reset_user_password(UserPoolId=user_pool_id, Username=username)
    result = client.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert result["UserStatus"] == "RESET_REQUIRED"

    # Return to CONFIRMED status after NEW_PASSWORD_REQUIRED auth challenge
    auth_result = client.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": temporary_pass},
    )
    password = "Admin123!"
    auth_result = client.respond_to_auth_challenge(
        Session=auth_result["Session"],
        ClientId=client_id,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        ChallengeResponses={"USERNAME": username, "NEW_PASSWORD": password},
    )
    result = client.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert result["UserStatus"] == "CONFIRMED"

    # Return to CONFIRMED after user-initated password change
    client.admin_reset_user_password(UserPoolId=user_pool_id, Username=username)
    client.change_password(
        AccessToken=auth_result["AuthenticationResult"]["AccessToken"],
        PreviousPassword=password,
        ProposedPassword="Admin1234!",
    )
    result = client.admin_get_user(UserPoolId=user_pool_id, Username=username)
    assert result["UserStatus"] == "CONFIRMED"


@mock_aws
def test_admin_initiate_auth__use_access_token():
    client = boto3.client("cognito-idp", "us-west-2")
    un = str(uuid.uuid4())
    pw = str(uuid.uuid4())
    # Create pool and client
    user_pool_id = client.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = client.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=True
    )["UserPoolClient"]["ClientId"]
    client.admin_create_user(UserPoolId=user_pool_id, Username=un, TemporaryPassword=pw)
    client.confirm_sign_up(ClientId=client_id, Username=un, ConfirmationCode="123456")

    # Initiate once, to get a refresh token
    auth_result = client.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={"USERNAME": un, "PASSWORD": pw},
    )
    refresh_token = auth_result["AuthenticationResult"]["RefreshToken"]

    # Initiate Auth using a Refresh Token
    auth_result = client.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="REFRESH_TOKEN",
        AuthParameters={"REFRESH_TOKEN": refresh_token},
    )
    access_token = auth_result["AuthenticationResult"]["AccessToken"]

    # Verify the AccessToken of this authentication works
    client.global_sign_out(AccessToken=access_token)


@mock_aws
def test_admin_reset_password_disabled_user():
    client = boto3.client("cognito-idp", "us-west-2")
    username = str(uuid.uuid4())
    # Create pool
    user_pool_id = client.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    # Create disabled user
    client.admin_create_user(
        UserPoolId=user_pool_id, Username=username, TemporaryPassword=str(uuid.uuid4())
    )
    client.admin_disable_user(UserPoolId=user_pool_id, Username=username)

    with pytest.raises(ClientError) as ex:
        client.admin_reset_user_password(UserPoolId=user_pool_id, Username=username)
    err = ex.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"
    assert err["Message"] == "User is disabled"


@mock_aws
def test_admin_reset_password_unconfirmed_user():
    client = boto3.client("cognito-idp", "us-west-2")
    username = str(uuid.uuid4())
    # Create pool
    user_pool_id = client.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    # Create user in status FORCE_CHANGE_PASSWORD
    client.admin_create_user(
        UserPoolId=user_pool_id, Username=username, TemporaryPassword=str(uuid.uuid4())
    )

    with pytest.raises(ClientError) as ex:
        client.admin_reset_user_password(UserPoolId=user_pool_id, Username=username)
    err = ex.value.response["Error"]
    assert err["Code"] == "NotAuthorizedException"
    assert err["Message"] == "User password cannot be reset in the current state."


@mock_aws
def test_admin_reset_password_no_verified_notification_channel():
    client = boto3.client("cognito-idp", "us-west-2")
    username = str(uuid.uuid4())
    # Create pool and client
    user_pool_id = client.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = client.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=True
    )["UserPoolClient"]["ClientId"]
    # Create CONFIRMED user without verified email or phone
    client.admin_create_user(
        UserPoolId=user_pool_id, Username=username, TemporaryPassword=str(uuid.uuid4())
    )
    client.confirm_sign_up(
        ClientId=client_id, Username=username, ConfirmationCode="123456"
    )

    with pytest.raises(ClientError) as ex:
        client.admin_reset_user_password(UserPoolId=user_pool_id, Username=username)
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "Cannot reset password for the user as there is no registered/verified email or phone_number"
    )


@mock_aws
def test_admin_reset_password_multiple_invocations():
    client = boto3.client("cognito-idp", "us-west-2")
    username = str(uuid.uuid4())
    # Create pool and client
    user_pool_id = client.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = client.create_user_pool_client(
        UserPoolId=user_pool_id, ClientName=str(uuid.uuid4()), GenerateSecret=True
    )["UserPoolClient"]["ClientId"]
    # Create CONFIRMED user with verified email
    client.admin_create_user(
        UserPoolId=user_pool_id, Username=username, TemporaryPassword=str(uuid.uuid4())
    )
    client.confirm_sign_up(
        ClientId=client_id, Username=username, ConfirmationCode="123456"
    )
    client.admin_update_user_attributes(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "email_verified", "Value": "true"}],
    )

    for _ in range(3):
        client.admin_reset_user_password(UserPoolId=user_pool_id, Username=username)
        user = client.admin_get_user(UserPoolId=user_pool_id, Username=username)
        assert user["UserStatus"] == "RESET_REQUIRED"


@mock_aws
def test_login_denied_if_account_disabled():
    """Make sure a disabled account is denied login"""
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    temporary_password = "P2$Sword"
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    user_attribute_name = str(uuid.uuid4())
    user_attribute_value = str(uuid.uuid4())
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=str(uuid.uuid4()),
        ReadAttributes=[user_attribute_name],
    )["UserPoolClient"]["ClientId"]

    # Create a user and disable the account
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        TemporaryPassword=temporary_password,
        UserAttributes=[{"Name": user_attribute_name, "Value": user_attribute_value}],
    )
    conn.admin_disable_user(
        UserPoolId=user_pool_id,
        Username=username,
    )

    # User should not be able to login into a disabled account
    with pytest.raises(conn.exceptions.NotAuthorizedException) as ex:
        conn.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": temporary_password},
        )

    assert ex.value.response["Error"]["Code"] == "NotAuthorizedException"
    assert ex.value.response["Error"]["Message"] == "User is disabled."
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400

    # Using admin login should yield the same result
    with pytest.raises(conn.exceptions.NotAuthorizedException) as ex:
        conn.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": temporary_password},
        )

    assert ex.value.response["Error"]["Code"] == "NotAuthorizedException"
    assert ex.value.response["Error"]["Message"] == "User is disabled."
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
# Also validate that we don't need IAM policies, as this operation should be publicly accessible
@set_initial_no_auth_action_count(0)
def test_initiate_auth_with_invalid_user_pool():
    conn = boto3.client("cognito-idp", "us-west-2")
    with pytest.raises(ClientError) as exc:
        conn.initiate_auth(
            ClientId="unknown",
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": "user", "PASSWORD": "pass"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_idtoken_contains_kid_header():
    # https://github.com/getmoto/moto/issues/3078
    # Setup
    cognito = boto3.client("cognito-idp", "us-west-2")
    user_pool_id = cognito.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"][
        "Id"
    ]
    client = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ExplicitAuthFlows=[
            "ALLOW_ADMIN_USER_PASSWORD_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
            "ALLOW_ADMIN_NO_SRP_AUTH",
        ],
        AllowedOAuthFlows=["code", "implicit"],
        ClientName=str(uuid.uuid4()),
        CallbackURLs=["https://example.com"],
    )
    client_id = client["UserPoolClient"]["ClientId"]
    username = str(uuid.uuid4())
    temporary_password = "1TemporaryP@ssword"
    cognito.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        TemporaryPassword=temporary_password,
    )
    result = cognito.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": temporary_password},
    )

    # A newly created user is forced to set a new password
    # This sets a new password and logs the user in (creates tokens)
    password = "1F@kePassword"
    result = cognito.respond_to_auth_challenge(
        Session=result["Session"],
        ClientId=client_id,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        ChallengeResponses={"USERNAME": username, "NEW_PASSWORD": password},
    )
    #
    id_token = result["AuthenticationResult"]["IdToken"]

    # Verify the KID header is present in the token, and corresponds to the KID supplied by the public JWT
    verify_kid_header(id_token)


def verify_kid_header(token):
    """Verifies the kid-header is corresponds with the public key"""
    if isinstance(token, str):
        token = token.encode("ascii")
    sig = jws.extract_compact(token)
    kid = sig.headers()["kid"]

    key_index = -1
    keys = fetch_public_keys()
    for i in range(len(keys)):
        if kid == keys[i]["kid"]:
            key_index = i
            break
    if key_index == -1:
        raise Exception("Public key (kid) not found in jwks.json")


def fetch_public_keys():
    if settings.TEST_DECORATOR_MODE:
        keys_url = "https://cognito-idp.us-west-2.amazonaws.com/someuserpoolid/.well-known/jwks.json"
    else:
        keys_url = "http://localhost:5000/someuserpoolid/.well-known/jwks.json"
    headers = {
        "Authorization": "AWS4-HMAC-SHA256 Credential=abcd/20010101/us-east-1/cognito-idp/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=...",
    }
    response = requests.get(keys_url, headers=headers).json()
    return response["keys"]
