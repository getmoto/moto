import random
import boto3
import json

from moto.events import mock_events
from botocore.exceptions import ClientError
from nose.tools import assert_raises

RULES = [
    {'Name': 'test1', 'ScheduleExpression': 'rate(5 minutes)'},
    {'Name': 'test2', 'ScheduleExpression': 'rate(1 minute)'},
    {'Name': 'test3', 'EventPattern': '{"source": ["test-source"]}'}
]

TARGETS = {
    'test-target-1': {
        'Id': 'test-target-1',
        'Arn': 'arn:aws:lambda:us-west-2:111111111111:function:test-function-1',
        'Rules': ['test1', 'test2']
    },
    'test-target-2': {
        'Id': 'test-target-2',
        'Arn': 'arn:aws:lambda:us-west-2:111111111111:function:test-function-2',
        'Rules': ['test1', 'test3']
    },
    'test-target-3': {
        'Id': 'test-target-3',
        'Arn': 'arn:aws:lambda:us-west-2:111111111111:function:test-function-3',
        'Rules': ['test1', 'test2']
    },
    'test-target-4': {
        'Id': 'test-target-4',
        'Arn': 'arn:aws:lambda:us-west-2:111111111111:function:test-function-4',
        'Rules': ['test1', 'test3']
    },
    'test-target-5': {
        'Id': 'test-target-5',
        'Arn': 'arn:aws:lambda:us-west-2:111111111111:function:test-function-5',
        'Rules': ['test1', 'test2']
    },
    'test-target-6': {
        'Id': 'test-target-6',
        'Arn': 'arn:aws:lambda:us-west-2:111111111111:function:test-function-6',
        'Rules': ['test1', 'test3']
    }
}


def get_random_rule():
    return RULES[random.randint(0, len(RULES) - 1)]


def generate_environment():
    client = boto3.client('events', 'us-west-2')

    for rule in RULES:
        client.put_rule(
            Name=rule['Name'],
            ScheduleExpression=rule.get('ScheduleExpression', ''),
            EventPattern=rule.get('EventPattern', '')
        )

        targets = []
        for target in TARGETS:
            if rule['Name'] in TARGETS[target].get('Rules'):
                targets.append({'Id': target, 'Arn': TARGETS[target]['Arn']})

        client.put_targets(Rule=rule['Name'], Targets=targets)

    return client


@mock_events
def test_list_rules():
    client = generate_environment()
    response = client.list_rules()

    assert(response is not None)
    assert(len(response['Rules']) > 0)


@mock_events
def test_describe_rule():
    rule_name = get_random_rule()['Name']
    client = generate_environment()
    response = client.describe_rule(Name=rule_name)

    assert(response is not None)
    assert(response.get('Name') == rule_name)
    assert(response.get('Arn') is not None)


@mock_events
def test_enable_disable_rule():
    rule_name = get_random_rule()['Name']
    client = generate_environment()

    # Rules should start out enabled in these tests.
    rule = client.describe_rule(Name=rule_name)
    assert(rule['State'] == 'ENABLED')

    client.disable_rule(Name=rule_name)
    rule = client.describe_rule(Name=rule_name)
    assert(rule['State'] == 'DISABLED')

    client.enable_rule(Name=rule_name)
    rule = client.describe_rule(Name=rule_name)
    assert(rule['State'] == 'ENABLED')

    # Test invalid name
    try:
        client.enable_rule(Name='junk')

    except ClientError as ce:
        assert ce.response['Error']['Code'] == 'ResourceNotFoundException'


@mock_events
def test_list_rule_names_by_target():
    test_1_target = TARGETS['test-target-1']
    test_2_target = TARGETS['test-target-2']
    client = generate_environment()

    rules = client.list_rule_names_by_target(TargetArn=test_1_target['Arn'])
    assert(len(rules['RuleNames']) == len(test_1_target['Rules']))
    for rule in rules['RuleNames']:
        assert(rule in test_1_target['Rules'])

    rules = client.list_rule_names_by_target(TargetArn=test_2_target['Arn'])
    assert(len(rules['RuleNames']) == len(test_2_target['Rules']))
    for rule in rules['RuleNames']:
        assert(rule in test_2_target['Rules'])


@mock_events
def test_list_rules():
    client = generate_environment()

    rules = client.list_rules()
    assert(len(rules['Rules']) == len(RULES))


@mock_events
def test_delete_rule():
    client = generate_environment()

    client.delete_rule(Name=RULES[0]['Name'])
    rules = client.list_rules()
    assert(len(rules['Rules']) == len(RULES) - 1)


@mock_events
def test_list_targets_by_rule():
    rule_name = get_random_rule()['Name']
    client = generate_environment()
    targets = client.list_targets_by_rule(Rule=rule_name)

    expected_targets = []
    for target in TARGETS:
        if rule_name in TARGETS[target].get('Rules'):
            expected_targets.append(target)

    assert(len(targets['Targets']) == len(expected_targets))


@mock_events
def test_remove_targets():
    rule_name = get_random_rule()['Name']
    client = generate_environment()

    targets = client.list_targets_by_rule(Rule=rule_name)['Targets']
    targets_before = len(targets)
    assert(targets_before > 0)

    client.remove_targets(Rule=rule_name, Ids=[targets[0]['Id']])

    targets = client.list_targets_by_rule(Rule=rule_name)['Targets']
    targets_after = len(targets)
    assert(targets_before - 1 == targets_after)


@mock_events
def test_permissions():
    client = boto3.client('events', 'eu-central-1')

    client.put_permission(Action='events:PutEvents', Principal='111111111111', StatementId='Account1')
    client.put_permission(Action='events:PutEvents', Principal='222222222222', StatementId='Account2')

    resp = client.describe_event_bus()
    resp_policy = json.loads(resp['Policy'])
    assert len(resp_policy['Statement']) == 2

    client.remove_permission(StatementId='Account2')

    resp = client.describe_event_bus()
    resp_policy = json.loads(resp['Policy'])
    assert len(resp_policy['Statement']) == 1
    assert resp_policy['Statement'][0]['Sid'] == 'Account1'


@mock_events
def test_put_events():
    client = boto3.client('events', 'eu-central-1')

    event = {
        "Source": "com.mycompany.myapp",
        "Detail": '{"key1": "value3", "key2": "value4"}',
        "Resources": ["resource1", "resource2"],
        "DetailType": "myDetailType"
    }

    client.put_events(Entries=[event])
    # Boto3 would error if it didn't return 200 OK

    with assert_raises(ClientError):
        client.put_events(Entries=[event]*20)
