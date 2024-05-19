import json
import os
import re
from datetime import datetime
from unittest import SkipTest, mock

import boto3
import pytest
from botocore.exceptions import ClientError
from dateutil.tz import tzutc

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

region = "us-east-1"
simple_definition = (
    '{"Comment": "An example of the Amazon States Language using a choice state.",'
    '"StartAt": "DefaultState",'
    '"States": '
    '{"DefaultState": {"Type": "Fail","Error": "DefaultStateError","Cause": "No Matches!"}}}'
)
account_id = None


@mock_aws
def test_state_machine_creation_succeeds():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    #
    response = client.create_state_machine(
        name=name, definition=str(simple_definition), roleArn=_get_default_role()
    )
    #
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert isinstance(response["creationDate"], datetime)
    assert response["stateMachineArn"] == (
        "arn:aws:states:" + region + ":" + ACCOUNT_ID + ":stateMachine:" + name
    )


@mock_aws
def test_state_machine_creation_fails_with_invalid_names():
    client = boto3.client("stepfunctions", region_name=region)
    invalid_names = [
        "with space",
        "with<bracket",
        "with>bracket",
        "with{bracket",
        "with}bracket",
        "with[bracket",
        "with]bracket",
        "with?wildcard",
        "with*wildcard",
        'special"char',
        "special#char",
        "special%char",
        "special\\char",
        "special^char",
        "special|char",
        "special~char",
        "special`char",
        "special$char",
        "special&char",
        "special,char",
        "special;char",
        "special:char",
        "special/char",
        "uni\u0000code",
        "uni\u0001code",
        "uni\u0002code",
        "uni\u0003code",
        "uni\u0004code",
        "uni\u0005code",
        "uni\u0006code",
        "uni\u0007code",
        "uni\u0008code",
        "uni\u0009code",
        "uni\u000acode",
        "uni\u000bcode",
        "uni\u000ccode",
        "uni\u000dcode",
        "uni\u000ecode",
        "uni\u000fcode",
        "uni\u0010code",
        "uni\u0011code",
        "uni\u0012code",
        "uni\u0013code",
        "uni\u0014code",
        "uni\u0015code",
        "uni\u0016code",
        "uni\u0017code",
        "uni\u0018code",
        "uni\u0019code",
        "uni\u001acode",
        "uni\u001bcode",
        "uni\u001ccode",
        "uni\u001dcode",
        "uni\u001ecode",
        "uni\u001fcode",
        "uni\u007fcode",
        "uni\u0080code",
        "uni\u0081code",
        "uni\u0082code",
        "uni\u0083code",
        "uni\u0084code",
        "uni\u0085code",
        "uni\u0086code",
        "uni\u0087code",
        "uni\u0088code",
        "uni\u0089code",
        "uni\u008acode",
        "uni\u008bcode",
        "uni\u008ccode",
        "uni\u008dcode",
        "uni\u008ecode",
        "uni\u008fcode",
        "uni\u0090code",
        "uni\u0091code",
        "uni\u0092code",
        "uni\u0093code",
        "uni\u0094code",
        "uni\u0095code",
        "uni\u0096code",
        "uni\u0097code",
        "uni\u0098code",
        "uni\u0099code",
        "uni\u009acode",
        "uni\u009bcode",
        "uni\u009ccode",
        "uni\u009dcode",
        "uni\u009ecode",
        "uni\u009fcode",
    ]
    #

    for invalid_name in invalid_names:
        with pytest.raises(ClientError):
            client.create_state_machine(
                name=invalid_name,
                definition=str(simple_definition),
                roleArn=_get_default_role(),
            )


@mock_aws
def test_state_machine_creation_requires_valid_role_arn():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    #
    with pytest.raises(ClientError):
        client.create_state_machine(
            name=name,
            definition=str(simple_definition),
            roleArn="arn:aws:iam::1234:role/unknown_role",
        )


@mock_aws
def test_update_state_machine():
    client = boto3.client("stepfunctions", region_name=region)

    resp = client.create_state_machine(
        name="test", definition=str(simple_definition), roleArn=_get_default_role()
    )
    state_machine_arn = resp["stateMachineArn"]

    updated_role = _get_default_role() + "-updated"
    updated_definition = str(simple_definition).replace(
        "DefaultState", "DefaultStateUpdated"
    )
    resp = client.update_state_machine(
        stateMachineArn=state_machine_arn,
        definition=updated_definition,
        roleArn=updated_role,
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert isinstance(resp["updateDate"], datetime)

    desc = client.describe_state_machine(stateMachineArn=state_machine_arn)
    assert desc["definition"] == updated_definition
    assert desc["roleArn"] == updated_role


@mock_aws
def test_state_machine_list_returns_empty_list_by_default():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm_list = client.list_state_machines()
    assert sm_list["stateMachines"] == []


@mock_aws
def test_state_machine_list_returns_created_state_machines():
    client = boto3.client("stepfunctions", region_name=region)
    #
    machine1 = client.create_state_machine(
        name="name1",
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        tags=[{"key": "tag_key", "value": "tag_value"}],
    )
    machine2 = client.create_state_machine(
        name="name2", definition=str(simple_definition), roleArn=_get_default_role()
    )
    sm_list = client.list_state_machines()
    #
    assert sm_list["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(sm_list["stateMachines"]) == 2
    assert isinstance(sm_list["stateMachines"][0]["creationDate"], datetime)
    assert sm_list["stateMachines"][0]["creationDate"] == machine1["creationDate"]
    assert sm_list["stateMachines"][0]["name"] == "name1"
    assert sm_list["stateMachines"][0]["stateMachineArn"] == machine1["stateMachineArn"]
    assert isinstance(sm_list["stateMachines"][1]["creationDate"], datetime)
    assert sm_list["stateMachines"][1]["creationDate"] == machine2["creationDate"]
    assert sm_list["stateMachines"][1]["name"] == "name2"
    assert sm_list["stateMachines"][1]["stateMachineArn"] == machine2["stateMachineArn"]


@mock_aws
def test_state_machine_list_pagination():
    client = boto3.client("stepfunctions", region_name=region)
    for i in range(25):
        machine_name = f"StateMachine-{i}"
        client.create_state_machine(
            name=machine_name,
            definition=str(simple_definition),
            roleArn=_get_default_role(),
        )

    resp = client.list_state_machines()
    assert "nextToken" not in resp
    assert len(resp["stateMachines"]) == 25

    paginator = client.get_paginator("list_state_machines")
    page_iterator = paginator.paginate(maxResults=5)
    page_list = list(page_iterator)
    for page in page_list:
        assert len(page["stateMachines"]) == 5
    assert "24" in page_list[-1]["stateMachines"][-1]["name"]


@mock_aws
def test_state_machine_creation_is_idempotent_by_name():
    client = boto3.client("stepfunctions", region_name=region)
    #
    client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    sm_list = client.list_state_machines()
    assert len(sm_list["stateMachines"]) == 1
    #
    client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    sm_list = client.list_state_machines()
    assert len(sm_list["stateMachines"]) == 1
    #
    client.create_state_machine(
        name="diff_name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    sm_list = client.list_state_machines()
    assert len(sm_list["stateMachines"]) == 2


@mock_aws
def test_state_machine_creation_can_be_described():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    desc = client.describe_state_machine(stateMachineArn=sm["stateMachineArn"])
    assert desc["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert desc["creationDate"] == sm["creationDate"]
    assert desc["definition"] == str(simple_definition)
    assert desc["name"] == "name"
    assert desc["roleArn"] == _get_default_role()
    assert desc["stateMachineArn"] == sm["stateMachineArn"]
    assert desc["status"] == "ACTIVE"


@mock_aws
def test_state_machine_throws_error_when_describing_unknown_machine():
    client = boto3.client("stepfunctions", region_name=region)
    #
    with pytest.raises(ClientError):
        unknown_state_machine = (
            f"arn:aws:states:{region}:{ACCOUNT_ID}:stateMachine:unknown"
        )
        client.describe_state_machine(stateMachineArn=unknown_state_machine)


@mock_aws
def test_state_machine_throws_error_when_describing_bad_arn():
    client = boto3.client("stepfunctions", region_name=region)
    #
    with pytest.raises(ClientError):
        client.describe_state_machine(stateMachineArn="bad")


@mock_aws
def test_state_machine_throws_error_when_describing_machine_in_different_account():
    client = boto3.client("stepfunctions", region_name=region)
    #
    with pytest.raises(ClientError):
        unknown_state_machine = (
            "arn:aws:states:" + region + ":000000000000:stateMachine:unknown"
        )
        client.describe_state_machine(stateMachineArn=unknown_state_machine)


@mock_aws
def test_state_machine_can_be_deleted():
    client = boto3.client("stepfunctions", region_name=region)
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    #
    response = client.delete_state_machine(stateMachineArn=sm["stateMachineArn"])
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    #
    sm_list = client.list_state_machines()
    assert len(sm_list["stateMachines"]) == 0


@mock_aws
def test_state_machine_can_deleted_nonexisting_machine():
    client = boto3.client("stepfunctions", region_name=region)
    #
    unknown_state_machine = (
        "arn:aws:states:" + region + ":" + ACCOUNT_ID + ":stateMachine:unknown"
    )
    response = client.delete_state_machine(stateMachineArn=unknown_state_machine)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    #
    sm_list = client.list_state_machines()
    assert len(sm_list["stateMachines"]) == 0


@mock_aws
def test_state_machine_tagging_non_existent_resource_fails():
    client = boto3.client("stepfunctions", region_name=region)
    non_existent_arn = f"arn:aws:states:{region}:{ACCOUNT_ID}:stateMachine:non-existent"
    with pytest.raises(ClientError) as ex:
        client.tag_resource(resourceArn=non_existent_arn, tags=[])
    assert ex.value.response["Error"]["Code"] == "ResourceNotFound"
    assert non_existent_arn in ex.value.response["Error"]["Message"]


@mock_aws
def test_state_machine_untagging_non_existent_resource_fails():
    client = boto3.client("stepfunctions", region_name=region)
    non_existent_arn = f"arn:aws:states:{region}:{ACCOUNT_ID}:stateMachine:non-existent"
    with pytest.raises(ClientError) as ex:
        client.untag_resource(resourceArn=non_existent_arn, tagKeys=[])
    assert ex.value.response["Error"]["Code"] == "ResourceNotFound"
    assert non_existent_arn in ex.value.response["Error"]["Message"]


@mock_aws
def test_state_machine_tagging():
    client = boto3.client("stepfunctions", region_name=region)
    tags = [
        {"key": "tag_key1", "value": "tag_value1"},
        {"key": "tag_key2", "value": "tag_value2"},
    ]
    machine = client.create_state_machine(
        name="test", definition=str(simple_definition), roleArn=_get_default_role()
    )
    client.tag_resource(resourceArn=machine["stateMachineArn"], tags=tags)
    resp = client.list_tags_for_resource(resourceArn=machine["stateMachineArn"])
    assert resp["tags"] == tags

    tags_update = [
        {"key": "tag_key1", "value": "tag_value1_new"},
        {"key": "tag_key3", "value": "tag_value3"},
    ]
    client.tag_resource(resourceArn=machine["stateMachineArn"], tags=tags_update)
    resp = client.list_tags_for_resource(resourceArn=machine["stateMachineArn"])
    tags_expected = [
        tags_update[0],
        tags[1],
        tags_update[1],
    ]
    assert resp["tags"] == tags_expected


@mock_aws
def test_state_machine_untagging():
    client = boto3.client("stepfunctions", region_name=region)
    tags = [
        {"key": "tag_key1", "value": "tag_value1"},
        {"key": "tag_key2", "value": "tag_value2"},
        {"key": "tag_key3", "value": "tag_value3"},
    ]
    machine = client.create_state_machine(
        name="test",
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        tags=tags,
    )
    resp = client.list_tags_for_resource(resourceArn=machine["stateMachineArn"])
    assert resp["tags"] == tags
    tags_to_delete = ["tag_key1", "tag_key2"]
    client.untag_resource(
        resourceArn=machine["stateMachineArn"], tagKeys=tags_to_delete
    )
    resp = client.list_tags_for_resource(resourceArn=machine["stateMachineArn"])
    expected_tags = [tag for tag in tags if tag["key"] not in tags_to_delete]
    assert resp["tags"] == expected_tags


@mock_aws
def test_state_machine_list_tags_for_created_machine():
    client = boto3.client("stepfunctions", region_name=region)
    #
    machine = client.create_state_machine(
        name="name1",
        definition=str(simple_definition),
        roleArn=_get_default_role(),
        tags=[{"key": "tag_key", "value": "tag_value"}],
    )
    response = client.list_tags_for_resource(resourceArn=machine["stateMachineArn"])
    tags = response["tags"]
    assert len(tags) == 1
    assert tags[0] == {"key": "tag_key", "value": "tag_value"}


@mock_aws
def test_state_machine_list_tags_for_machine_without_tags():
    client = boto3.client("stepfunctions", region_name=region)
    #
    machine = client.create_state_machine(
        name="name1", definition=str(simple_definition), roleArn=_get_default_role()
    )
    response = client.list_tags_for_resource(resourceArn=machine["stateMachineArn"])
    tags = response["tags"]
    assert len(tags) == 0


@mock_aws
def test_state_machine_list_tags_for_nonexisting_machine():
    client = boto3.client("stepfunctions", region_name=region)
    #
    non_existing_state_machine = (
        f"arn:aws:states:{region}:{ACCOUNT_ID}:stateMachine:unknown"
    )
    response = client.list_tags_for_resource(resourceArn=non_existing_state_machine)
    tags = response["tags"]
    assert len(tags) == 0


@mock_aws
def test_state_machine_start_execution():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    execution = client.start_execution(stateMachineArn=sm["stateMachineArn"])
    #
    assert execution["ResponseMetadata"]["HTTPStatusCode"] == 200
    uuid_regex = "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
    expected_exec_name = (
        f"arn:aws:states:{region}:{ACCOUNT_ID}:execution:name:{uuid_regex}"
    )
    assert re.match(expected_exec_name, execution["executionArn"])
    assert isinstance(execution["startDate"], datetime)


@mock_aws
def test_state_machine_start_execution_bad_arn_raises_exception():
    client = boto3.client("stepfunctions", region_name=region)
    #
    with pytest.raises(ClientError):
        client.start_execution(stateMachineArn="bad")


@mock_aws
def test_state_machine_start_execution_with_custom_name():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    execution = client.start_execution(
        stateMachineArn=sm["stateMachineArn"], name="execution_name"
    )
    #
    assert execution["ResponseMetadata"]["HTTPStatusCode"] == 200
    expected_exec_name = (
        f"arn:aws:states:{region}:{ACCOUNT_ID}:execution:name:execution_name"
    )
    assert execution["executionArn"] == expected_exec_name
    assert isinstance(execution["startDate"], datetime)


@mock_aws
def test_state_machine_start_execution_fails_on_duplicate_execution_name():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    execution_one = client.start_execution(
        stateMachineArn=sm["stateMachineArn"], name="execution_name"
    )
    #
    with pytest.raises(ClientError) as ex:
        _ = client.start_execution(
            stateMachineArn=sm["stateMachineArn"], name="execution_name"
        )
    assert ex.value.response["Error"]["Message"] == (
        "Execution Already Exists: '" + execution_one["executionArn"] + "'"
    )


@mock_aws
def test_state_machine_start_execution_with_custom_input():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    execution_input = json.dumps({"input_key": "input_value"})
    execution = client.start_execution(
        stateMachineArn=sm["stateMachineArn"], input=execution_input
    )
    #
    assert execution["ResponseMetadata"]["HTTPStatusCode"] == 200
    uuid_regex = "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
    expected_exec_name = (
        f"arn:aws:states:{region}:{ACCOUNT_ID}:execution:name:{uuid_regex}"
    )
    assert re.match(expected_exec_name, execution["executionArn"])
    assert isinstance(execution["startDate"], datetime)


@mock_aws
def test_state_machine_start_execution_with_invalid_input():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    with pytest.raises(ClientError):
        client.start_execution(stateMachineArn=sm["stateMachineArn"], input="")
    with pytest.raises(ClientError):
        client.start_execution(stateMachineArn=sm["stateMachineArn"], input="{")


@mock_aws
def test_state_machine_list_executions():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    execution = client.start_execution(stateMachineArn=sm["stateMachineArn"])
    execution_arn = execution["executionArn"]
    execution_name = execution_arn[execution_arn.rindex(":") + 1 :]
    executions = client.list_executions(stateMachineArn=sm["stateMachineArn"])
    #
    assert executions["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(executions["executions"]) == 1
    assert executions["executions"][0]["executionArn"] == execution_arn
    assert executions["executions"][0]["name"] == execution_name
    assert executions["executions"][0]["startDate"] == execution["startDate"]
    assert executions["executions"][0]["stateMachineArn"] == sm["stateMachineArn"]
    assert executions["executions"][0]["status"] == "RUNNING"
    assert "stopDate" not in executions["executions"][0]


@mock_aws
def test_state_machine_list_executions_with_filter():
    client = boto3.client("stepfunctions", region_name=region)
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    for i in range(20):
        execution = client.start_execution(stateMachineArn=sm["stateMachineArn"])
        if not i % 4:
            client.stop_execution(executionArn=execution["executionArn"])

    resp = client.list_executions(stateMachineArn=sm["stateMachineArn"])
    assert len(resp["executions"]) == 20

    resp = client.list_executions(
        stateMachineArn=sm["stateMachineArn"], statusFilter="ABORTED"
    )
    assert len(resp["executions"]) == 5
    assert all(e["status"] == "ABORTED" for e in resp["executions"]) is True


@mock_aws
def test_state_machine_list_executions_with_pagination():
    client = boto3.client("stepfunctions", region_name=region)
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    for _ in range(100):
        client.start_execution(stateMachineArn=sm["stateMachineArn"])

    resp = client.list_executions(stateMachineArn=sm["stateMachineArn"])
    assert "nextToken" not in resp
    assert len(resp["executions"]) == 100

    paginator = client.get_paginator("list_executions")
    page_iterator = paginator.paginate(
        stateMachineArn=sm["stateMachineArn"], maxResults=25
    )
    for page in page_iterator:
        assert len(page["executions"]) == 25

    with pytest.raises(ClientError) as ex:
        resp = client.list_executions(
            stateMachineArn=sm["stateMachineArn"], maxResults=10
        )
        client.list_executions(
            stateMachineArn=sm["stateMachineArn"],
            maxResults=10,
            statusFilter="ABORTED",
            nextToken=resp["nextToken"],
        )
    assert ex.value.response["Error"]["Code"] == "InvalidToken"
    assert "Input inconsistent with page token" in ex.value.response["Error"]["Message"]

    with pytest.raises(ClientError) as ex:
        client.list_executions(
            stateMachineArn=sm["stateMachineArn"], nextToken="invalid"
        )
    assert ex.value.response["Error"]["Code"] == "InvalidToken"


@mock_aws
def test_state_machine_list_executions_when_none_exist():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    executions = client.list_executions(stateMachineArn=sm["stateMachineArn"])
    #
    assert executions["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(executions["executions"]) == 0


@mock_aws
def test_state_machine_describe_execution_with_no_input():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    execution = client.start_execution(stateMachineArn=sm["stateMachineArn"])
    description = client.describe_execution(executionArn=execution["executionArn"])
    #
    assert description["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert description["executionArn"] == execution["executionArn"]
    assert description["input"] == "{}"
    assert re.match("[-0-9a-z]+", description["name"])
    assert description["startDate"] == execution["startDate"]
    assert description["stateMachineArn"] == sm["stateMachineArn"]
    assert description["status"] == "RUNNING"
    assert "stopDate" not in description


@mock_aws
def test_state_machine_describe_execution_with_custom_input():
    client = boto3.client("stepfunctions", region_name=region)
    #
    execution_input = json.dumps({"input_key": "input_val"})
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    execution = client.start_execution(
        stateMachineArn=sm["stateMachineArn"], input=execution_input
    )
    description = client.describe_execution(executionArn=execution["executionArn"])
    #
    assert description["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert description["executionArn"] == execution["executionArn"]
    assert description["input"] == execution_input
    assert re.match("[-a-z0-9]+", description["name"])
    assert description["startDate"] == execution["startDate"]
    assert description["stateMachineArn"] == sm["stateMachineArn"]
    assert description["status"] == "RUNNING"
    assert "stopDate" not in description


@mock_aws
def test_execution_throws_error_when_describing_unknown_execution():
    client = boto3.client("stepfunctions", region_name=region)
    #
    with pytest.raises(ClientError):
        unknown_execution = f"arn:aws:states:{region}:{ACCOUNT_ID}:execution:unknown"
        client.describe_execution(executionArn=unknown_execution)


@mock_aws
def test_state_machine_can_be_described_by_execution():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    execution = client.start_execution(stateMachineArn=sm["stateMachineArn"])
    desc = client.describe_state_machine_for_execution(
        executionArn=execution["executionArn"]
    )
    assert desc["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert desc["definition"] == str(simple_definition)
    assert desc["name"] == "name"
    assert desc["roleArn"] == _get_default_role()
    assert desc["stateMachineArn"] == sm["stateMachineArn"]


@mock_aws
def test_state_machine_throws_error_when_describing_unknown_execution():
    client = boto3.client("stepfunctions", region_name=region)
    #
    with pytest.raises(ClientError):
        unknown_execution = f"arn:aws:states:{region}:{ACCOUNT_ID}:execution:unknown"
        client.describe_state_machine_for_execution(executionArn=unknown_execution)


@mock_aws
def test_state_machine_stop_execution():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm_arn = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )["stateMachineArn"]
    start = client.start_execution(stateMachineArn=sm_arn)
    stop = client.stop_execution(executionArn=start["executionArn"])
    #
    assert stop["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert isinstance(stop["stopDate"], datetime)

    description = client.describe_execution(executionArn=start["executionArn"])
    assert description["status"] == "ABORTED"
    assert isinstance(description["stopDate"], datetime)

    execution = client.list_executions(stateMachineArn=sm_arn)["executions"][0]
    assert isinstance(execution["stopDate"], datetime)


@mock_aws
def test_state_machine_stop_raises_error_when_unknown_execution():
    client = boto3.client("stepfunctions", region_name=region)
    client.create_state_machine(
        name="test-state-machine",
        definition=str(simple_definition),
        roleArn=_get_default_role(),
    )
    with pytest.raises(ClientError) as ex:
        unknown_execution = (
            f"arn:aws:states:{region}:{ACCOUNT_ID}:execution:test-state-machine:unknown"
        )
        client.stop_execution(executionArn=unknown_execution)
    assert ex.value.response["Error"]["Code"] == "ExecutionDoesNotExist"
    assert "Execution Does Not Exist:" in ex.value.response["Error"]["Message"]


@mock_aws
def test_state_machine_get_execution_history_throws_error_with_unknown_execution():
    client = boto3.client("stepfunctions", region_name=region)
    client.create_state_machine(
        name="test-state-machine",
        definition=str(simple_definition),
        roleArn=_get_default_role(),
    )
    with pytest.raises(ClientError) as ex:
        unknown_execution = (
            f"arn:aws:states:{region}:{ACCOUNT_ID}:execution:test-state-machine:unknown"
        )
        client.get_execution_history(executionArn=unknown_execution)
    assert ex.value.response["Error"]["Code"] == "ExecutionDoesNotExist"
    assert "Execution Does Not Exist:" in ex.value.response["Error"]["Message"]


@mock_aws
def test_state_machine_get_execution_history_contains_expected_success_events_when_started():
    expected_events = [
        {
            "timestamp": datetime(2020, 1, 1, 0, 0, 0, tzinfo=tzutc()),
            "type": "ExecutionStarted",
            "id": 1,
            "previousEventId": 0,
            "executionStartedEventDetails": {
                "input": "{}",
                "inputDetails": {"truncated": False},
                "roleArn": _get_default_role(),
            },
        },
        {
            "timestamp": datetime(2020, 1, 1, 0, 0, 10, tzinfo=tzutc()),
            "type": "PassStateEntered",
            "id": 2,
            "previousEventId": 0,
            "stateEnteredEventDetails": {
                "name": "A State",
                "input": "{}",
                "inputDetails": {"truncated": False},
            },
        },
        {
            "timestamp": datetime(2020, 1, 1, 0, 0, 10, tzinfo=tzutc()),
            "type": "PassStateExited",
            "id": 3,
            "previousEventId": 2,
            "stateExitedEventDetails": {
                "name": "A State",
                "output": "An output",
                "outputDetails": {"truncated": False},
            },
        },
        {
            "timestamp": datetime(2020, 1, 1, 0, 0, 20, tzinfo=tzutc()),
            "type": "ExecutionSucceeded",
            "id": 4,
            "previousEventId": 3,
            "executionSucceededEventDetails": {
                "output": "An output",
                "outputDetails": {"truncated": False},
            },
        },
    ]

    client = boto3.client("stepfunctions", region_name=region)
    sm = client.create_state_machine(
        name="test-state-machine",
        definition=simple_definition,
        roleArn=_get_default_role(),
    )
    execution = client.start_execution(stateMachineArn=sm["stateMachineArn"])
    execution_history = client.get_execution_history(
        executionArn=execution["executionArn"]
    )
    assert len(execution_history["events"]) == 4
    assert execution_history["events"] == expected_events


@mock.patch.dict("os.environ", {"MOTO_ENABLE_ISO_REGIONS": "true"})
@pytest.mark.parametrize(
    "test_region", ["us-west-2", "cn-northwest-1", "us-isob-east-1"]
)
@mock_aws
def test_stepfunction_regions(test_region):
    client = boto3.client("stepfunctions", region_name=test_region)
    resp = client.list_state_machines()
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    if test_region == "us-west-2":
        assert (
            response["stateMachineArn"]
            == f"arn:aws:states:{test_region}:{ACCOUNT_ID}:stateMachine:name"
        )
    if test_region == "cn-northwest-1":
        assert (
            response["stateMachineArn"]
            == f"arn:aws-cn:states:{test_region}:{ACCOUNT_ID}:stateMachine:name"
        )
    if test_region == "us-isob-east-1":
        assert (
            response["stateMachineArn"]
            == f"arn:aws-iso-b:states:{test_region}:{ACCOUNT_ID}:stateMachine:name"
        )


@mock_aws
@mock.patch.dict(os.environ, {"SF_EXECUTION_HISTORY_TYPE": "FAILURE"})
def test_state_machine_get_execution_history_contains_expected_failure_events_when_started():
    if os.environ.get("TEST_SERVER_MODE", "false").lower() == "true":
        raise SkipTest("Cant pass environment variable in server mode")
    expected_events = [
        {
            "timestamp": datetime(2020, 1, 1, 0, 0, 0, tzinfo=tzutc()),
            "type": "ExecutionStarted",
            "id": 1,
            "previousEventId": 0,
            "executionStartedEventDetails": {
                "input": "{}",
                "inputDetails": {"truncated": False},
                "roleArn": _get_default_role(),
            },
        },
        {
            "timestamp": datetime(2020, 1, 1, 0, 0, 10, tzinfo=tzutc()),
            "type": "FailStateEntered",
            "id": 2,
            "previousEventId": 0,
            "stateEnteredEventDetails": {
                "name": "A State",
                "input": "{}",
                "inputDetails": {"truncated": False},
            },
        },
        {
            "timestamp": datetime(2020, 1, 1, 0, 0, 10, tzinfo=tzutc()),
            "type": "ExecutionFailed",
            "id": 3,
            "previousEventId": 2,
            "executionFailedEventDetails": {
                "error": "AnError",
                "cause": "An error occurred!",
            },
        },
    ]

    client = boto3.client("stepfunctions", region_name=region)
    sm = client.create_state_machine(
        name="test-state-machine",
        definition=simple_definition,
        roleArn=_get_default_role(),
    )
    execution = client.start_execution(stateMachineArn=sm["stateMachineArn"])
    execution_history = client.get_execution_history(
        executionArn=execution["executionArn"]
    )
    assert len(execution_history["events"]) == 3
    assert execution_history["events"] == expected_events

    exc = client.describe_execution(executionArn=execution["executionArn"])
    assert exc["status"] == "FAILED"

    exc = client.list_executions(stateMachineArn=sm["stateMachineArn"])["executions"][0]
    assert exc["status"] == "FAILED"


@mock_aws
def test_state_machine_name_limits():
    # Setup
    client = boto3.client("stepfunctions", region_name=region)
    long_name = "t" * 81

    # Execute
    with pytest.raises(ClientError) as exc:
        client.create_state_machine(
            name=long_name,
            definition=simple_definition,
            roleArn=_get_default_role(),
        )

    # Verify
    assert exc.value.response["Error"]["Code"] == "ValidationException"
    assert exc.value.response["Error"]["Message"] == (
        f"1 validation error detected: Value '{long_name}' at 'name' "
        "failed to satisfy constraint: "
        "Member must have length less than or equal to 80"
    )


@mock_aws
def test_state_machine_execution_name_limits():
    # Setup
    client = boto3.client("stepfunctions", region_name=region)
    machine_name = "test_name"
    long_name = "t" * 81
    resp = client.create_state_machine(
        name=machine_name,
        definition=simple_definition,
        roleArn=_get_default_role(),
    )

    # Execute
    with pytest.raises(ClientError) as exc:
        client.start_execution(name=long_name, stateMachineArn=resp["stateMachineArn"])

    # Verify
    assert exc.value.response["Error"]["Code"] == "ValidationException"
    assert exc.value.response["Error"]["Message"] == (
        f"1 validation error detected: Value '{long_name}' at 'name' "
        "failed to satisfy constraint: "
        "Member must have length less than or equal to 80"
    )


def _get_default_role():
    return "arn:aws:iam::" + ACCOUNT_ID + ":role/unknown_sf_role"
