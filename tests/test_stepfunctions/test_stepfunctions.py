from __future__ import unicode_literals

import boto3
import json
import os
import sure  # noqa
from datetime import datetime
from dateutil.tz import tzutc
from botocore.exceptions import ClientError
import pytest

from moto import mock_sts, mock_stepfunctions
from moto.core import ACCOUNT_ID

from unittest import SkipTest, mock

region = "us-east-1"
simple_definition = (
    '{"Comment": "An example of the Amazon States Language using a choice state.",'
    '"StartAt": "DefaultState",'
    '"States": '
    '{"DefaultState": {"Type": "Fail","Error": "DefaultStateError","Cause": "No Matches!"}}}'
)
account_id = None


@mock_stepfunctions
@mock_sts
def test_state_machine_creation_succeeds():
    client = boto3.client("stepfunctions", region_name=region)
    name = "example_step_function"
    #
    response = client.create_state_machine(
        name=name, definition=str(simple_definition), roleArn=_get_default_role()
    )
    #
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["creationDate"].should.be.a(datetime)
    response["stateMachineArn"].should.equal(
        "arn:aws:states:" + region + ":" + ACCOUNT_ID + ":stateMachine:" + name
    )


@mock_stepfunctions
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
        "uni\u000Acode",
        "uni\u000Bcode",
        "uni\u000Ccode",
        "uni\u000Dcode",
        "uni\u000Ecode",
        "uni\u000Fcode",
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
        "uni\u001Acode",
        "uni\u001Bcode",
        "uni\u001Ccode",
        "uni\u001Dcode",
        "uni\u001Ecode",
        "uni\u001Fcode",
        "uni\u007Fcode",
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
        "uni\u008Acode",
        "uni\u008Bcode",
        "uni\u008Ccode",
        "uni\u008Dcode",
        "uni\u008Ecode",
        "uni\u008Fcode",
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
        "uni\u009Acode",
        "uni\u009Bcode",
        "uni\u009Ccode",
        "uni\u009Dcode",
        "uni\u009Ecode",
        "uni\u009Fcode",
    ]
    #

    for invalid_name in invalid_names:
        with pytest.raises(ClientError):
            client.create_state_machine(
                name=invalid_name,
                definition=str(simple_definition),
                roleArn=_get_default_role(),
            )


@mock_stepfunctions
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


@mock_stepfunctions
@mock_sts
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
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    resp["updateDate"].should.be.a(datetime)

    desc = client.describe_state_machine(stateMachineArn=state_machine_arn)
    desc["definition"].should.equal(updated_definition)
    desc["roleArn"].should.equal(updated_role)


@mock_stepfunctions
def test_state_machine_list_returns_empty_list_by_default():
    client = boto3.client("stepfunctions", region_name=region)
    #
    list = client.list_state_machines()
    list["stateMachines"].should.be.empty


@mock_stepfunctions
@mock_sts
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
    list = client.list_state_machines()
    #
    list["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    list["stateMachines"].should.have.length_of(2)
    list["stateMachines"][0]["creationDate"].should.be.a(datetime)
    list["stateMachines"][0]["creationDate"].should.equal(machine1["creationDate"])
    list["stateMachines"][0]["name"].should.equal("name1")
    list["stateMachines"][0]["stateMachineArn"].should.equal(
        machine1["stateMachineArn"]
    )
    list["stateMachines"][1]["creationDate"].should.be.a(datetime)
    list["stateMachines"][1]["creationDate"].should.equal(machine2["creationDate"])
    list["stateMachines"][1]["name"].should.equal("name2")
    list["stateMachines"][1]["stateMachineArn"].should.equal(
        machine2["stateMachineArn"]
    )


@mock_stepfunctions
def test_state_machine_list_pagination():
    client = boto3.client("stepfunctions", region_name=region)
    for i in range(25):
        machine_name = "StateMachine-{}".format(i)
        client.create_state_machine(
            name=machine_name,
            definition=str(simple_definition),
            roleArn=_get_default_role(),
        )

    resp = client.list_state_machines()
    resp.should_not.have.key("nextToken")
    resp["stateMachines"].should.have.length_of(25)

    paginator = client.get_paginator("list_state_machines")
    page_iterator = paginator.paginate(maxResults=5)
    for page in page_iterator:
        page["stateMachines"].should.have.length_of(5)
    page["stateMachines"][-1]["name"].should.contain("24")


@mock_stepfunctions
@mock_sts
def test_state_machine_creation_is_idempotent_by_name():
    client = boto3.client("stepfunctions", region_name=region)
    #
    client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    sm_list = client.list_state_machines()
    sm_list["stateMachines"].should.have.length_of(1)
    #
    client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    sm_list = client.list_state_machines()
    sm_list["stateMachines"].should.have.length_of(1)
    #
    client.create_state_machine(
        name="diff_name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    sm_list = client.list_state_machines()
    sm_list["stateMachines"].should.have.length_of(2)


@mock_stepfunctions
@mock_sts
def test_state_machine_creation_can_be_described():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    desc = client.describe_state_machine(stateMachineArn=sm["stateMachineArn"])
    desc["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    desc["creationDate"].should.equal(sm["creationDate"])
    desc["definition"].should.equal(str(simple_definition))
    desc["name"].should.equal("name")
    desc["roleArn"].should.equal(_get_default_role())
    desc["stateMachineArn"].should.equal(sm["stateMachineArn"])
    desc["status"].should.equal("ACTIVE")


@mock_stepfunctions
@mock_sts
def test_state_machine_throws_error_when_describing_unknown_machine():
    client = boto3.client("stepfunctions", region_name=region)
    #
    with pytest.raises(ClientError):
        unknown_state_machine = (
            "arn:aws:states:"
            + region
            + ":"
            + _get_account_id()
            + ":stateMachine:unknown"
        )
        client.describe_state_machine(stateMachineArn=unknown_state_machine)


@mock_stepfunctions
@mock_sts
def test_state_machine_throws_error_when_describing_bad_arn():
    client = boto3.client("stepfunctions", region_name=region)
    #
    with pytest.raises(ClientError):
        client.describe_state_machine(stateMachineArn="bad")


@mock_stepfunctions
@mock_sts
def test_state_machine_throws_error_when_describing_machine_in_different_account():
    client = boto3.client("stepfunctions", region_name=region)
    #
    with pytest.raises(ClientError):
        unknown_state_machine = (
            "arn:aws:states:" + region + ":000000000000:stateMachine:unknown"
        )
        client.describe_state_machine(stateMachineArn=unknown_state_machine)


@mock_stepfunctions
@mock_sts
def test_state_machine_can_be_deleted():
    client = boto3.client("stepfunctions", region_name=region)
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    #
    response = client.delete_state_machine(stateMachineArn=sm["stateMachineArn"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    #
    sm_list = client.list_state_machines()
    sm_list["stateMachines"].should.have.length_of(0)


@mock_stepfunctions
@mock_sts
def test_state_machine_can_deleted_nonexisting_machine():
    client = boto3.client("stepfunctions", region_name=region)
    #
    unknown_state_machine = (
        "arn:aws:states:" + region + ":" + ACCOUNT_ID + ":stateMachine:unknown"
    )
    response = client.delete_state_machine(stateMachineArn=unknown_state_machine)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    #
    sm_list = client.list_state_machines()
    sm_list["stateMachines"].should.have.length_of(0)


@mock_stepfunctions
def test_state_machine_tagging_non_existent_resource_fails():
    client = boto3.client("stepfunctions", region_name=region)
    non_existent_arn = "arn:aws:states:{region}:{account}:stateMachine:non-existent".format(
        region=region, account=ACCOUNT_ID
    )
    with pytest.raises(ClientError) as ex:
        client.tag_resource(resourceArn=non_existent_arn, tags=[])
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFound")
    ex.value.response["Error"]["Message"].should.contain(non_existent_arn)


@mock_stepfunctions
def test_state_machine_untagging_non_existent_resource_fails():
    client = boto3.client("stepfunctions", region_name=region)
    non_existent_arn = "arn:aws:states:{region}:{account}:stateMachine:non-existent".format(
        region=region, account=ACCOUNT_ID
    )
    with pytest.raises(ClientError) as ex:
        client.untag_resource(resourceArn=non_existent_arn, tagKeys=[])
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFound")
    ex.value.response["Error"]["Message"].should.contain(non_existent_arn)


@mock_stepfunctions
@mock_sts
def test_state_machine_tagging():
    client = boto3.client("stepfunctions", region_name=region)
    tags = [
        {"key": "tag_key1", "value": "tag_value1"},
        {"key": "tag_key2", "value": "tag_value2"},
    ]
    machine = client.create_state_machine(
        name="test", definition=str(simple_definition), roleArn=_get_default_role(),
    )
    client.tag_resource(resourceArn=machine["stateMachineArn"], tags=tags)
    resp = client.list_tags_for_resource(resourceArn=machine["stateMachineArn"])
    resp["tags"].should.equal(tags)

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
    resp["tags"].should.equal(tags_expected)


@mock_stepfunctions
@mock_sts
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
    resp["tags"].should.equal(tags)
    tags_to_delete = ["tag_key1", "tag_key2"]
    client.untag_resource(
        resourceArn=machine["stateMachineArn"], tagKeys=tags_to_delete
    )
    resp = client.list_tags_for_resource(resourceArn=machine["stateMachineArn"])
    expected_tags = [tag for tag in tags if tag["key"] not in tags_to_delete]
    resp["tags"].should.equal(expected_tags)


@mock_stepfunctions
@mock_sts
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
    tags.should.have.length_of(1)
    tags[0].should.equal({"key": "tag_key", "value": "tag_value"})


@mock_stepfunctions
@mock_sts
def test_state_machine_list_tags_for_machine_without_tags():
    client = boto3.client("stepfunctions", region_name=region)
    #
    machine = client.create_state_machine(
        name="name1", definition=str(simple_definition), roleArn=_get_default_role()
    )
    response = client.list_tags_for_resource(resourceArn=machine["stateMachineArn"])
    tags = response["tags"]
    tags.should.have.length_of(0)


@mock_stepfunctions
@mock_sts
def test_state_machine_list_tags_for_nonexisting_machine():
    client = boto3.client("stepfunctions", region_name=region)
    #
    non_existing_state_machine = (
        "arn:aws:states:" + region + ":" + _get_account_id() + ":stateMachine:unknown"
    )
    response = client.list_tags_for_resource(resourceArn=non_existing_state_machine)
    tags = response["tags"]
    tags.should.have.length_of(0)


@mock_stepfunctions
@mock_sts
def test_state_machine_start_execution():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    execution = client.start_execution(stateMachineArn=sm["stateMachineArn"])
    #
    execution["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    uuid_regex = "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
    expected_exec_name = (
        "arn:aws:states:"
        + region
        + ":"
        + _get_account_id()
        + ":execution:name:"
        + uuid_regex
    )
    execution["executionArn"].should.match(expected_exec_name)
    execution["startDate"].should.be.a(datetime)


@mock_stepfunctions
@mock_sts
def test_state_machine_start_execution_bad_arn_raises_exception():
    client = boto3.client("stepfunctions", region_name=region)
    #
    with pytest.raises(ClientError):
        client.start_execution(stateMachineArn="bad")


@mock_stepfunctions
@mock_sts
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
    execution["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    expected_exec_name = (
        "arn:aws:states:"
        + region
        + ":"
        + _get_account_id()
        + ":execution:name:execution_name"
    )
    execution["executionArn"].should.equal(expected_exec_name)
    execution["startDate"].should.be.a(datetime)


@mock_stepfunctions
@mock_sts
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
    ex.value.response["Error"]["Message"].should.equal(
        "Execution Already Exists: '" + execution_one["executionArn"] + "'"
    )


@mock_stepfunctions
@mock_sts
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
    execution["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    uuid_regex = "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
    expected_exec_name = (
        "arn:aws:states:"
        + region
        + ":"
        + _get_account_id()
        + ":execution:name:"
        + uuid_regex
    )
    execution["executionArn"].should.match(expected_exec_name)
    execution["startDate"].should.be.a(datetime)


@mock_stepfunctions
@mock_sts
def test_state_machine_start_execution_with_invalid_input():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    with pytest.raises(ClientError):
        _ = client.start_execution(stateMachineArn=sm["stateMachineArn"], input="")
    with pytest.raises(ClientError):
        _ = client.start_execution(stateMachineArn=sm["stateMachineArn"], input="{")


@mock_stepfunctions
@mock_sts
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
    executions["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    executions["executions"].should.have.length_of(1)
    executions["executions"][0]["executionArn"].should.equal(execution_arn)
    executions["executions"][0]["name"].should.equal(execution_name)
    executions["executions"][0]["startDate"].should.equal(execution["startDate"])
    executions["executions"][0]["stateMachineArn"].should.equal(sm["stateMachineArn"])
    executions["executions"][0]["status"].should.equal("RUNNING")
    executions["executions"][0].shouldnt.have("stopDate")


@mock_stepfunctions
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
    resp["executions"].should.have.length_of(20)

    resp = client.list_executions(
        stateMachineArn=sm["stateMachineArn"], statusFilter="ABORTED"
    )
    resp["executions"].should.have.length_of(5)
    all([e["status"] == "ABORTED" for e in resp["executions"]]).should.be.true


@mock_stepfunctions
def test_state_machine_list_executions_with_pagination():
    client = boto3.client("stepfunctions", region_name=region)
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    for _ in range(100):
        client.start_execution(stateMachineArn=sm["stateMachineArn"])

    resp = client.list_executions(stateMachineArn=sm["stateMachineArn"])
    resp.should_not.have.key("nextToken")
    resp["executions"].should.have.length_of(100)

    paginator = client.get_paginator("list_executions")
    page_iterator = paginator.paginate(
        stateMachineArn=sm["stateMachineArn"], maxResults=25
    )
    for page in page_iterator:
        page["executions"].should.have.length_of(25)

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
    ex.value.response["Error"]["Code"].should.equal("InvalidToken")
    ex.value.response["Error"]["Message"].should.contain(
        "Input inconsistent with page token"
    )

    with pytest.raises(ClientError) as ex:
        client.list_executions(
            stateMachineArn=sm["stateMachineArn"], nextToken="invalid"
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidToken")


@mock_stepfunctions
@mock_sts
def test_state_machine_list_executions_when_none_exist():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    executions = client.list_executions(stateMachineArn=sm["stateMachineArn"])
    #
    executions["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    executions["executions"].should.have.length_of(0)


@mock_stepfunctions
@mock_sts
def test_state_machine_describe_execution_with_no_input():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    execution = client.start_execution(stateMachineArn=sm["stateMachineArn"])
    description = client.describe_execution(executionArn=execution["executionArn"])
    #
    description["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    description["executionArn"].should.equal(execution["executionArn"])
    description["input"].should.equal("{}")
    description["name"].shouldnt.be.empty
    description["startDate"].should.equal(execution["startDate"])
    description["stateMachineArn"].should.equal(sm["stateMachineArn"])
    description["status"].should.equal("RUNNING")
    description.shouldnt.have("stopDate")


@mock_stepfunctions
@mock_sts
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
    description["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    description["executionArn"].should.equal(execution["executionArn"])
    description["input"].should.equal(execution_input)
    description["name"].shouldnt.be.empty
    description["startDate"].should.equal(execution["startDate"])
    description["stateMachineArn"].should.equal(sm["stateMachineArn"])
    description["status"].should.equal("RUNNING")
    description.shouldnt.have("stopDate")


@mock_stepfunctions
@mock_sts
def test_execution_throws_error_when_describing_unknown_execution():
    client = boto3.client("stepfunctions", region_name=region)
    #
    with pytest.raises(ClientError):
        unknown_execution = (
            "arn:aws:states:" + region + ":" + _get_account_id() + ":execution:unknown"
        )
        client.describe_execution(executionArn=unknown_execution)


@mock_stepfunctions
@mock_sts
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
    desc["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    desc["definition"].should.equal(str(simple_definition))
    desc["name"].should.equal("name")
    desc["roleArn"].should.equal(_get_default_role())
    desc["stateMachineArn"].should.equal(sm["stateMachineArn"])


@mock_stepfunctions
@mock_sts
def test_state_machine_throws_error_when_describing_unknown_execution():
    client = boto3.client("stepfunctions", region_name=region)
    #
    with pytest.raises(ClientError):
        unknown_execution = (
            "arn:aws:states:" + region + ":" + _get_account_id() + ":execution:unknown"
        )
        client.describe_state_machine_for_execution(executionArn=unknown_execution)


@mock_stepfunctions
@mock_sts
def test_state_machine_stop_execution():
    client = boto3.client("stepfunctions", region_name=region)
    #
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    start = client.start_execution(stateMachineArn=sm["stateMachineArn"])
    stop = client.stop_execution(executionArn=start["executionArn"])
    #
    stop["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    stop["stopDate"].should.be.a(datetime)


@mock_stepfunctions
@mock_sts
def test_state_machine_stop_raises_error_when_unknown_execution():
    client = boto3.client("stepfunctions", region_name=region)
    client.create_state_machine(
        name="test-state-machine",
        definition=str(simple_definition),
        roleArn=_get_default_role(),
    )
    with pytest.raises(ClientError) as ex:
        unknown_execution = (
            "arn:aws:states:"
            + region
            + ":"
            + _get_account_id()
            + ":execution:test-state-machine:unknown"
        )
        client.stop_execution(executionArn=unknown_execution)
    ex.value.response["Error"]["Code"].should.equal("ExecutionDoesNotExist")
    ex.value.response["Error"]["Message"].should.contain("Execution Does Not Exist:")


@mock_stepfunctions
@mock_sts
def test_state_machine_describe_execution_after_stoppage():
    client = boto3.client("stepfunctions", region_name=region)
    sm = client.create_state_machine(
        name="name", definition=str(simple_definition), roleArn=_get_default_role()
    )
    execution = client.start_execution(stateMachineArn=sm["stateMachineArn"])
    client.stop_execution(executionArn=execution["executionArn"])
    description = client.describe_execution(executionArn=execution["executionArn"])
    #
    description["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    description["status"].should.equal("ABORTED")
    description["stopDate"].should.be.a(datetime)


@mock_stepfunctions
@mock_sts
def test_state_machine_get_execution_history_throws_error_with_unknown_execution():
    client = boto3.client("stepfunctions", region_name=region)
    client.create_state_machine(
        name="test-state-machine",
        definition=str(simple_definition),
        roleArn=_get_default_role(),
    )
    with pytest.raises(ClientError) as ex:
        unknown_execution = (
            "arn:aws:states:"
            + region
            + ":"
            + _get_account_id()
            + ":execution:test-state-machine:unknown"
        )
        client.get_execution_history(executionArn=unknown_execution)
    ex.value.response["Error"]["Code"].should.equal("ExecutionDoesNotExist")
    ex.value.response["Error"]["Message"].should.contain("Execution Does Not Exist:")


@mock_stepfunctions
@mock_sts
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
    execution_history["events"].should.have.length_of(4)
    execution_history["events"].should.equal(expected_events)


@mock_stepfunctions
@mock_sts
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
    execution_history["events"].should.have.length_of(3)
    execution_history["events"].should.equal(expected_events)


def _get_account_id():
    global account_id
    if account_id:
        return account_id
    sts = boto3.client("sts", region_name=region)
    identity = sts.get_caller_identity()
    account_id = identity["Account"]
    return account_id


def _get_default_role():
    return "arn:aws:iam::" + _get_account_id() + ":role/unknown_sf_role"
