"""Unit tests for fis-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_experiment_template():
    client = boto3.client("fis", region_name="ap-southeast-1")
    resp = client.create_experiment_template(
        clientToken="token-123",
        description="my template",
        stopConditions=[{"source": "none"}],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": [
                    "arn:aws:ec2:ap-southeast-1:123456789012:instance/i-123"
                ],
                "selectionMode": "ALL",
            }
        },
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "parameters": {},
                "targets": {"Instances": "t1"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
        tags={"env": "test"},
    )

    tmpl = resp["experimentTemplate"]
    assert tmpl["id"]
    assert tmpl["arn"].endswith(f"experiment-template/{tmpl['id']}")
    assert tmpl["description"] == "my template"
    assert tmpl["roleArn"] == "arn:aws:iam::123456789012:role/FISRole"
    assert tmpl["targets"]["t1"]["selectionMode"] == "ALL"
    assert tmpl["actions"]["a1"]["actionId"] == "aws:ec2:stop-instances"
    assert tmpl["stopConditions"][0]["source"] == "none"
    assert tmpl["tags"]["env"] == "test"


@mock_aws
def test_delete_experiment_template():
    client = boto3.client("fis", region_name="eu-west-1")
    created = client.create_experiment_template(
        clientToken="token-del",
        description="to delete",
        stopConditions=[{"source": "none"}],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": ["arn:aws:ec2:eu-west-1:123456789012:instance/i-abc"],
                "selectionMode": "ALL",
            }
        },
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "parameters": {},
                "targets": {"Instances": "t1"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
    )
    template_id = created["experimentTemplate"]["id"]
    resp = client.delete_experiment_template(id=template_id)
    assert resp["experimentTemplate"]["id"] == template_id


@mock_aws
def test_tag_resource():
    client = boto3.client("fis", region_name="eu-west-1")
    created = client.create_experiment_template(
        clientToken="token-tag",
        description="tag me",
        stopConditions=[{"source": "none"}],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": ["arn:aws:ec2:eu-west-1:123456789012:instance/i-def"],
                "selectionMode": "ALL",
            }
        },
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "parameters": {},
                "targets": {"Instances": "t1"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
    )
    arn = created["experimentTemplate"]["arn"]
    client.tag_resource(resourceArn=arn, tags={"k1": "v1", "k2": "v2"})
    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert tags["k1"] == "v1"
    assert tags["k2"] == "v2"


@mock_aws
def test_untag_resource():
    client = boto3.client("fis", region_name="us-east-2")
    created = client.create_experiment_template(
        clientToken="token-untag",
        description="untag me",
        stopConditions=[{"source": "none"}],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": ["arn:aws:ec2:us-east-2:123456789012:instance/i-ghi"],
                "selectionMode": "ALL",
            }
        },
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "parameters": {},
                "targets": {"Instances": "t1"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
    )
    arn = created["experimentTemplate"]["arn"]
    client.tag_resource(resourceArn=arn, tags={"k1": "v1", "k2": "v2"})
    client.untag_resource(resourceArn=arn, tagKeys=["k1"])
    tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
    assert "k1" not in tags
    assert tags["k2"] == "v2"


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("fis", region_name="us-east-2")
    created = client.create_experiment_template(
        clientToken="token-list",
        description="list tags",
        stopConditions=[{"source": "none"}],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": ["arn:aws:ec2:us-east-2:123456789012:instance/i-jkl"],
                "selectionMode": "ALL",
            }
        },
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "parameters": {},
                "targets": {"Instances": "t1"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
    )
    arn = created["experimentTemplate"]["arn"]
    client.tag_resource(resourceArn=arn, tags={"env": "test"})
    resp = client.list_tags_for_resource(resourceArn=arn)
    assert resp["tags"]["env"] == "test"


def _create_template(client, region, description="tmpl", **kwargs):
    return client.create_experiment_template(
        description=description,
        stopConditions=[{"source": "none"}],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": [f"arn:aws:ec2:{region}:123456789012:instance/i-123"],
                "selectionMode": "ALL",
            }
        },
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "parameters": {},
                "targets": {"Instances": "t1"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
        **kwargs,
    )["experimentTemplate"]


@mock_aws
def test_list_experiment_templates_empty():
    client = boto3.client("fis", region_name="ap-southeast-1")
    resp = client.list_experiment_templates()

    assert resp["experimentTemplates"] == []
    assert "nextToken" not in resp


@mock_aws
def test_list_experiment_templates():
    client = boto3.client("fis", region_name="ap-southeast-1")
    created = _create_template(
        client,
        "ap-southeast-1",
        description="my template",
        clientToken="token-list-tmpl",
        tags={"env": "test"},
    )

    resp = client.list_experiment_templates()

    assert "nextToken" not in resp
    templates = resp["experimentTemplates"]
    assert len(templates) == 1

    summary = templates[0]
    assert summary["id"] == created["id"]
    assert summary["arn"] == created["arn"]
    assert summary["description"] == "my template"
    assert summary["tags"] == {"env": "test"}
    assert summary["creationTime"] == created["creationTime"]
    assert summary["lastUpdateTime"] == created["lastUpdateTime"]
    # The summary shape does not include the full template details
    assert "targets" not in summary
    assert "actions" not in summary
    assert "stopConditions" not in summary
    assert "roleArn" not in summary


@mock_aws
def test_list_experiment_templates_is_region_specific():
    client = boto3.client("fis", region_name="eu-west-1")
    _create_template(client, "eu-west-1", clientToken="token-eu")

    other_client = boto3.client("fis", region_name="us-east-2")
    assert other_client.list_experiment_templates()["experimentTemplates"] == []
    assert len(client.list_experiment_templates()["experimentTemplates"]) == 1


@mock_aws
def test_list_experiment_templates_excludes_deleted():
    client = boto3.client("fis", region_name="us-east-2")
    keep = _create_template(client, "us-east-2", clientToken="token-keep")
    remove = _create_template(client, "us-east-2", clientToken="token-remove")

    client.delete_experiment_template(id=remove["id"])

    ids = [t["id"] for t in client.list_experiment_templates()["experimentTemplates"]]
    assert ids == [keep["id"]]


@mock_aws
def test_list_experiment_templates_paginated():
    client = boto3.client("fis", region_name="us-east-1")
    for idx in range(5):
        _create_template(client, "us-east-1", clientToken=f"token-{idx}")

    page1 = client.list_experiment_templates(maxResults=2)
    assert len(page1["experimentTemplates"]) == 2
    assert page1["nextToken"]

    page2 = client.list_experiment_templates(maxResults=2, nextToken=page1["nextToken"])
    assert len(page2["experimentTemplates"]) == 2
    assert page2["nextToken"]

    page3 = client.list_experiment_templates(maxResults=2, nextToken=page2["nextToken"])
    assert len(page3["experimentTemplates"]) == 1
    assert "nextToken" not in page3

    seen = [
        tmpl["id"]
        for page in (page1, page2, page3)
        for tmpl in page["experimentTemplates"]
    ]
    assert len(set(seen)) == 5


@mock_aws
def test_get_experiment_template():
    client = boto3.client("fis", region_name="ap-southeast-1")
    created = client.create_experiment_template(
        clientToken="token-get",
        description="get me",
        stopConditions=[
            {
                "source": "aws:cloudwatch:alarm",
                "value": "arn:aws:cloudwatch:ap-southeast-1:123456789012:alarm:my-alarm",
            }
        ],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceTags": {"env": "prod"},
                "filters": [
                    {"path": "State.Name", "values": ["running"]},
                ],
                "selectionMode": "COUNT(1)",
                "parameters": {},
            }
        },
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "description": "stop them",
                "parameters": {"startInstancesAfterDuration": "PT1M"},
                "targets": {"Instances": "t1"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
        tags={"env": "test"},
        logConfiguration={
            "cloudWatchLogsConfiguration": {
                "logGroupArn": "arn:aws:logs:ap-southeast-1:123456789012:log-group:fis:*"
            },
            "logSchemaVersion": 2,
        },
        experimentOptions={
            "accountTargeting": "single-account",
            "emptyTargetResolutionMode": "fail",
        },
    )["experimentTemplate"]

    resp = client.get_experiment_template(id=created["id"])
    tmpl = resp["experimentTemplate"]

    assert tmpl["id"] == created["id"]
    assert tmpl["arn"] == created["arn"]
    assert tmpl["description"] == "get me"
    assert tmpl["roleArn"] == "arn:aws:iam::123456789012:role/FISRole"
    assert tmpl["creationTime"] == created["creationTime"]
    assert tmpl["lastUpdateTime"] == created["lastUpdateTime"]
    assert tmpl["tags"] == {"env": "test"}

    target = tmpl["targets"]["t1"]
    assert target["resourceType"] == "aws:ec2:instance"
    assert target["resourceTags"] == {"env": "prod"}
    assert target["filters"] == [{"path": "State.Name", "values": ["running"]}]
    assert target["selectionMode"] == "COUNT(1)"

    action = tmpl["actions"]["a1"]
    assert action["actionId"] == "aws:ec2:stop-instances"
    assert action["description"] == "stop them"
    assert action["parameters"] == {"startInstancesAfterDuration": "PT1M"}
    assert action["targets"] == {"Instances": "t1"}

    assert tmpl["stopConditions"][0]["source"] == "aws:cloudwatch:alarm"
    assert tmpl["logConfiguration"]["logSchemaVersion"] == 2
    assert tmpl["experimentOptions"]["accountTargeting"] == "single-account"
    assert tmpl["targetAccountConfigurationsCount"] == 0


@mock_aws
def test_get_experiment_template_reflects_tag_changes():
    client = boto3.client("fis", region_name="eu-west-1")
    created = _create_template(client, "eu-west-1", clientToken="token-get-tags")

    assert (
        client.get_experiment_template(id=created["id"])["experimentTemplate"]["tags"]
        == {}
    )

    client.tag_resource(resourceArn=created["arn"], tags={"k1": "v1"})
    tmpl = client.get_experiment_template(id=created["id"])["experimentTemplate"]
    assert tmpl["tags"] == {"k1": "v1"}


@mock_aws
def test_get_experiment_template_unknown_id():
    client = boto3.client("fis", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.get_experiment_template(id="unknown-template")

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment template unknown-template does not exist"


@mock_aws
def test_get_experiment_template_after_delete():
    client = boto3.client("fis", region_name="us-east-2")
    created = _create_template(client, "us-east-2", clientToken="token-get-deleted")
    client.delete_experiment_template(id=created["id"])

    with pytest.raises(ClientError) as exc:
        client.get_experiment_template(id=created["id"])

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_start_experiment():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(
        client, "us-east-2", description="run me", clientToken="token-tmpl-start"
    )

    resp = client.start_experiment(
        clientToken="token-start",
        experimentTemplateId=template["id"],
        tags={"env": "test"},
    )
    experiment = resp["experiment"]

    assert experiment["id"]
    assert experiment["arn"].endswith(f"experiment/{experiment['id']}")
    assert ":us-east-2:123456789012:experiment/" in experiment["arn"]
    assert experiment["experimentTemplateId"] == template["id"]
    assert experiment["roleArn"] == template["roleArn"]
    assert experiment["state"]["status"] == "pending"
    assert experiment["state"]["reason"]
    assert experiment["tags"] == {"env": "test"}
    assert experiment["creationTime"] == experiment["startTime"]
    assert "endTime" not in experiment
    assert experiment["targetAccountConfigurationsCount"] == 0

    # The experiment inherits the template configuration
    assert experiment["targets"] == template["targets"]
    assert experiment["stopConditions"] == template["stopConditions"]

    action = experiment["actions"]["a1"]
    assert action["actionId"] == "aws:ec2:stop-instances"
    assert action["targets"] == {"Instances": "t1"}
    assert action["state"]["status"] == "pending"
    assert "startTime" not in action
    assert "endTime" not in action


@mock_aws
def test_start_experiment_default_experiment_options():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-tmpl-opts-def")

    experiment = client.start_experiment(
        clientToken="token-opts-def", experimentTemplateId=template["id"]
    )["experiment"]

    assert experiment["experimentOptions"] == {
        "accountTargeting": "single-account",
        "emptyTargetResolutionMode": "fail",
        "actionsMode": "run-all",
    }


@mock_aws
def test_start_experiment_experiment_options():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(
        client,
        "us-east-2",
        clientToken="token-tmpl-opts",
        experimentOptions={
            "accountTargeting": "multi-account",
            "emptyTargetResolutionMode": "skip",
        },
    )

    experiment = client.start_experiment(
        clientToken="token-opts",
        experimentTemplateId=template["id"],
        experimentOptions={"actionsMode": "skip-all"},
    )["experiment"]

    # accountTargeting/emptyTargetResolutionMode come from the template,
    # actionsMode comes from the StartExperiment request.
    assert experiment["experimentOptions"] == {
        "accountTargeting": "multi-account",
        "emptyTargetResolutionMode": "skip",
        "actionsMode": "skip-all",
    }


@mock_aws
def test_start_experiment_is_idempotent_per_client_token():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-tmpl-idem")

    first = client.start_experiment(
        clientToken="token-idem", experimentTemplateId=template["id"]
    )["experiment"]
    second = client.start_experiment(
        clientToken="token-idem", experimentTemplateId=template["id"]
    )["experiment"]

    assert first["id"] == second["id"]


@mock_aws
def test_start_experiment_copies_template_config():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-tmpl-copy")
    experiment = client.start_experiment(
        clientToken="token-copy", experimentTemplateId=template["id"]
    )["experiment"]

    # Deleting the template does not affect the already-started experiment
    client.delete_experiment_template(id=template["id"])
    assert experiment["targets"]["t1"]["resourceType"] == "aws:ec2:instance"


@mock_aws
def test_start_experiment_tags_are_separate_from_the_template():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(
        client, "eu-west-1", clientToken="token-tmpl-tags", tags={"on": "template"}
    )
    experiment = client.start_experiment(
        clientToken="token-exp-tags",
        experimentTemplateId=template["id"],
        tags={"on": "experiment"},
    )["experiment"]

    assert client.list_tags_for_resource(resourceArn=experiment["arn"])["tags"] == {
        "on": "experiment"
    }
    assert client.list_tags_for_resource(resourceArn=template["arn"])["tags"] == {
        "on": "template"
    }


@mock_aws
def test_start_experiment_unknown_template():
    client = boto3.client("fis", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.start_experiment(
            clientToken="token-unknown", experimentTemplateId="unknown-template"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment template unknown-template does not exist"


@mock_aws
def test_get_experiment():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-tmpl-get-exp")
    started = client.start_experiment(
        clientToken="token-get-exp",
        experimentTemplateId=template["id"],
        tags={"env": "test"},
    )["experiment"]

    experiment = client.get_experiment(id=started["id"])["experiment"]

    assert experiment["id"] == started["id"]
    assert experiment["arn"] == started["arn"]
    assert experiment["experimentTemplateId"] == template["id"]
    assert experiment["roleArn"] == template["roleArn"]
    assert experiment["tags"] == {"env": "test"}
    assert experiment["creationTime"] == started["creationTime"]
    assert experiment["startTime"] == started["startTime"]
    assert experiment["targets"] == started["targets"]
    assert experiment["stopConditions"] == started["stopConditions"]
    assert experiment["experimentOptions"] == started["experimentOptions"]
    assert experiment["targetAccountConfigurationsCount"] == 0


@mock_aws
def test_get_experiment_advances_state():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-tmpl-advance")
    started = client.start_experiment(
        clientToken="token-advance", experimentTemplateId=template["id"]
    )["experiment"]

    # StartExperiment itself does not advance the experiment
    assert started["state"]["status"] == "pending"

    statuses = [
        client.get_experiment(id=started["id"])["experiment"]["state"]["status"]
        for _ in range(4)
    ]
    assert statuses == ["initiating", "running", "completed", "completed"]


@mock_aws
def test_get_experiment_sets_end_time_once_completed():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-tmpl-end")
    started = client.start_experiment(
        clientToken="token-end", experimentTemplateId=template["id"]
    )["experiment"]

    assert "endTime" not in started

    # pending -> initiating -> running: still no endTime
    for _ in range(2):
        assert "endTime" not in client.get_experiment(id=started["id"])["experiment"]

    completed = client.get_experiment(id=started["id"])["experiment"]
    assert completed["state"]["status"] == "completed"
    assert completed["endTime"] >= completed["startTime"]

    # The endTime is stable once set
    again = client.get_experiment(id=started["id"])["experiment"]
    assert again["endTime"] == completed["endTime"]


@mock_aws
def test_get_experiment_action_state_follows_the_experiment():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-tmpl-actions")
    started = client.start_experiment(
        clientToken="token-actions", experimentTemplateId=template["id"]
    )["experiment"]

    assert started["actions"]["a1"]["state"]["status"] == "pending"
    assert "startTime" not in started["actions"]["a1"]

    initiating = client.get_experiment(id=started["id"])["experiment"]["actions"]["a1"]
    assert initiating["state"]["status"] == "pending"

    running = client.get_experiment(id=started["id"])["experiment"]["actions"]["a1"]
    assert running["state"]["status"] == "running"
    assert running["startTime"] == started["startTime"]
    assert "endTime" not in running

    completed = client.get_experiment(id=started["id"])["experiment"]["actions"]["a1"]
    assert completed["state"]["status"] == "completed"
    assert completed["endTime"]


@mock_aws
def test_get_experiment_state_transition_is_configurable():
    from moto.moto_api import state_manager

    state_manager.set_transition(
        "fis::experiment", transition={"progression": "immediate"}
    )
    try:
        client = boto3.client("fis", region_name="us-east-2")
        template = _create_template(
            client, "us-east-2", clientToken="token-tmpl-immediate"
        )
        started = client.start_experiment(
            clientToken="token-immediate", experimentTemplateId=template["id"]
        )["experiment"]

        experiment = client.get_experiment(id=started["id"])["experiment"]
        assert experiment["state"]["status"] == "completed"
    finally:
        state_manager.unset_transition("fis::experiment")


@mock_aws
def test_get_experiment_reflects_tag_changes():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-tmpl-exp-tags")
    started = client.start_experiment(
        clientToken="token-exp-get-tags", experimentTemplateId=template["id"]
    )["experiment"]

    assert client.get_experiment(id=started["id"])["experiment"]["tags"] == {}

    client.tag_resource(resourceArn=started["arn"], tags={"k1": "v1"})
    assert client.get_experiment(id=started["id"])["experiment"]["tags"] == {"k1": "v1"}


@mock_aws
def test_get_experiment_unknown_id():
    client = boto3.client("fis", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.get_experiment(id="unknown-experiment")

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment unknown-experiment does not exist"


@mock_aws
def test_get_experiment_does_not_accept_a_template_id():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-tmpl-notexp")

    with pytest.raises(ClientError) as exc:
        client.get_experiment(id=template["id"])

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_experiments_empty():
    client = boto3.client("fis", region_name="ap-southeast-1")
    resp = client.list_experiments()

    assert resp["experiments"] == []
    assert "nextToken" not in resp


@mock_aws
def test_list_experiments():
    client = boto3.client("fis", region_name="ap-southeast-1")
    template = _create_template(
        client, "ap-southeast-1", clientToken="token-tmpl-list-exp"
    )
    started = client.start_experiment(
        clientToken="token-list-exp",
        experimentTemplateId=template["id"],
        tags={"env": "test"},
    )["experiment"]

    resp = client.list_experiments()

    assert "nextToken" not in resp
    assert len(resp["experiments"]) == 1

    summary = resp["experiments"][0]
    assert summary["id"] == started["id"]
    assert summary["arn"] == started["arn"]
    assert summary["experimentTemplateId"] == template["id"]
    assert summary["state"]["status"] == "pending"
    assert summary["creationTime"] == started["creationTime"]
    assert summary["tags"] == {"env": "test"}
    assert summary["experimentOptions"] == started["experimentOptions"]
    # The summary shape does not include the full experiment details
    assert "targets" not in summary
    assert "actions" not in summary
    assert "stopConditions" not in summary
    assert "roleArn" not in summary
    assert "startTime" not in summary


@mock_aws
def test_list_experiments_does_not_advance_state():
    client = boto3.client("fis", region_name="ap-southeast-1")
    template = _create_template(
        client, "ap-southeast-1", clientToken="token-tmpl-noadvance"
    )
    started = client.start_experiment(
        clientToken="token-noadvance", experimentTemplateId=template["id"]
    )["experiment"]

    for _ in range(5):
        assert (
            client.list_experiments()["experiments"][0]["state"]["status"] == "pending"
        )

    # Only get_experiment advances the experiment
    assert (
        client.get_experiment(id=started["id"])["experiment"]["state"]["status"]
        == "initiating"
    )
    assert (
        client.list_experiments()["experiments"][0]["state"]["status"] == "initiating"
    )


@mock_aws
def test_list_experiments_filtered_by_experiment_template_id():
    client = boto3.client("fis", region_name="us-east-2")
    template1 = _create_template(client, "us-east-2", clientToken="token-tmpl-f1")
    template2 = _create_template(client, "us-east-2", clientToken="token-tmpl-f2")

    exp1 = client.start_experiment(
        clientToken="token-f1", experimentTemplateId=template1["id"]
    )["experiment"]
    exp2a = client.start_experiment(
        clientToken="token-f2a", experimentTemplateId=template2["id"]
    )["experiment"]
    exp2b = client.start_experiment(
        clientToken="token-f2b", experimentTemplateId=template2["id"]
    )["experiment"]

    assert len(client.list_experiments()["experiments"]) == 3

    only1 = client.list_experiments(experimentTemplateId=template1["id"])["experiments"]
    assert [e["id"] for e in only1] == [exp1["id"]]

    only2 = client.list_experiments(experimentTemplateId=template2["id"])["experiments"]
    assert sorted(e["id"] for e in only2) == sorted([exp2a["id"], exp2b["id"]])


@mock_aws
def test_list_experiments_filtered_by_unknown_template_id():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-tmpl-unknown")
    client.start_experiment(
        clientToken="token-unknown-filter", experimentTemplateId=template["id"]
    )

    resp = client.list_experiments(experimentTemplateId="does-not-exist")

    assert resp["experiments"] == []
    assert "nextToken" not in resp


@mock_aws
def test_list_experiments_is_region_specific():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(
        client, "eu-west-1", clientToken="token-tmpl-exp-region"
    )
    client.start_experiment(
        clientToken="token-exp-region", experimentTemplateId=template["id"]
    )

    other_client = boto3.client("fis", region_name="us-east-2")
    assert other_client.list_experiments()["experiments"] == []
    assert len(client.list_experiments()["experiments"]) == 1


@mock_aws
def test_list_experiments_paginated():
    client = boto3.client("fis", region_name="us-east-1")
    template = _create_template(client, "us-east-1", clientToken="token-tmpl-exp-page")
    for idx in range(5):
        client.start_experiment(
            clientToken=f"token-exp-page-{idx}", experimentTemplateId=template["id"]
        )

    page1 = client.list_experiments(maxResults=2)
    assert len(page1["experiments"]) == 2
    assert page1["nextToken"]

    page2 = client.list_experiments(maxResults=2, nextToken=page1["nextToken"])
    assert len(page2["experiments"]) == 2
    assert page2["nextToken"]

    page3 = client.list_experiments(maxResults=2, nextToken=page2["nextToken"])
    assert len(page3["experiments"]) == 1
    assert "nextToken" not in page3

    seen = [exp["id"] for page in (page1, page2, page3) for exp in page["experiments"]]
    assert len(set(seen)) == 5


@mock_aws
def test_list_experiments_paginated_with_filter():
    client = boto3.client("fis", region_name="us-east-1")
    template1 = _create_template(client, "us-east-1", clientToken="token-tmpl-pf1")
    template2 = _create_template(client, "us-east-1", clientToken="token-tmpl-pf2")
    for idx in range(3):
        client.start_experiment(
            clientToken=f"token-pf1-{idx}", experimentTemplateId=template1["id"]
        )
        client.start_experiment(
            clientToken=f"token-pf2-{idx}", experimentTemplateId=template2["id"]
        )

    page1 = client.list_experiments(experimentTemplateId=template1["id"], maxResults=2)
    assert len(page1["experiments"]) == 2

    page2 = client.list_experiments(
        experimentTemplateId=template1["id"],
        maxResults=2,
        nextToken=page1["nextToken"],
    )
    assert len(page2["experiments"]) == 1
    assert "nextToken" not in page2

    assert all(
        exp["experimentTemplateId"] == template1["id"]
        for page in (page1, page2)
        for exp in page["experiments"]
    )


@mock_aws
def test_stop_experiment():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-tmpl-stop")
    started = client.start_experiment(
        clientToken="token-stop",
        experimentTemplateId=template["id"],
        tags={"env": "test"},
    )["experiment"]

    experiment = client.stop_experiment(id=started["id"])["experiment"]

    assert experiment["id"] == started["id"]
    assert experiment["arn"] == started["arn"]
    assert experiment["experimentTemplateId"] == template["id"]
    assert experiment["state"]["status"] == "stopping"
    assert experiment["tags"] == {"env": "test"}
    assert experiment["creationTime"] == started["creationTime"]
    assert experiment["startTime"] == started["startTime"]
    # Still stopping, so the experiment has not ended yet
    assert "endTime" not in experiment


@mock_aws
def test_stop_experiment_then_transitions_to_stopped():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-tmpl-stopped")
    started = client.start_experiment(
        clientToken="token-stopped", experimentTemplateId=template["id"]
    )["experiment"]

    # Advance the experiment into a running state first
    client.get_experiment(id=started["id"])
    running = client.get_experiment(id=started["id"])["experiment"]
    assert running["state"]["status"] == "running"

    assert (
        client.stop_experiment(id=started["id"])["experiment"]["state"]["status"]
        == "stopping"
    )

    stopped = client.get_experiment(id=started["id"])["experiment"]
    assert stopped["state"]["status"] == "stopped"
    assert stopped["endTime"] >= stopped["startTime"]

    # "stopped" is terminal - it never becomes "completed"
    for _ in range(3):
        assert (
            client.get_experiment(id=started["id"])["experiment"]["state"]["status"]
            == "stopped"
        )


@mock_aws
def test_stop_experiment_stops_the_actions():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-tmpl-stopact")
    started = client.start_experiment(
        clientToken="token-stopact", experimentTemplateId=template["id"]
    )["experiment"]

    client.get_experiment(id=started["id"])
    client.get_experiment(id=started["id"])

    stopping = client.stop_experiment(id=started["id"])["experiment"]
    assert stopping["actions"]["a1"]["state"]["status"] == "stopping"

    stopped = client.get_experiment(id=started["id"])["experiment"]["actions"]["a1"]
    assert stopped["state"]["status"] == "stopped"
    assert stopped["endTime"]


@mock_aws
def test_stop_experiment_is_visible_in_list_experiments():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-tmpl-stoplist")
    started = client.start_experiment(
        clientToken="token-stoplist", experimentTemplateId=template["id"]
    )["experiment"]

    client.stop_experiment(id=started["id"])

    summary = client.list_experiments()["experiments"][0]
    assert summary["id"] == started["id"]
    assert summary["state"]["status"] == "stopping"


@mock_aws
def test_stop_experiment_on_a_completed_experiment_is_a_noop():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-tmpl-stopdone")
    started = client.start_experiment(
        clientToken="token-stopdone", experimentTemplateId=template["id"]
    )["experiment"]

    for _ in range(3):
        completed = client.get_experiment(id=started["id"])["experiment"]
    assert completed["state"]["status"] == "completed"

    stopped = client.stop_experiment(id=started["id"])["experiment"]
    assert stopped["state"]["status"] == "completed"
    assert stopped["endTime"] == completed["endTime"]


@mock_aws
def test_stop_experiment_is_idempotent():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-tmpl-stoptwice")
    started = client.start_experiment(
        clientToken="token-stoptwice", experimentTemplateId=template["id"]
    )["experiment"]

    client.stop_experiment(id=started["id"])
    assert (
        client.stop_experiment(id=started["id"])["experiment"]["state"]["status"]
        == "stopping"
    )


@mock_aws
def test_stop_experiment_unknown_id():
    client = boto3.client("fis", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.stop_experiment(id="unknown-experiment")

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment unknown-experiment does not exist"


@mock_aws
def test_create_target_account_configuration():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-create-tac")

    config = client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
        description="target account",
    )["targetAccountConfiguration"]

    assert config["accountId"] == "111122223333"
    assert config["roleArn"] == "arn:aws:iam::111122223333:role/FISTargetRole"
    assert config["description"] == "target account"


@mock_aws
def test_create_target_account_configuration_without_description():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-create-nodesc")

    config = client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="444455556666",
        roleArn="arn:aws:iam::444455556666:role/FISTargetRole",
    )["targetAccountConfiguration"]

    assert config["accountId"] == "444455556666"
    assert "description" not in config


@mock_aws
def test_create_target_account_configuration_with_client_token():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-create-ct")

    config = client.create_target_account_configuration(
        clientToken="token-tac-create",
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
    )["targetAccountConfiguration"]

    assert config["accountId"] == "111122223333"


@mock_aws
def test_create_target_account_configuration_updates_the_template_count():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-create-count")

    assert template["targetAccountConfigurationsCount"] == 0

    for idx, account_id in enumerate(["111122223333", "444455556666"], start=1):
        client.create_target_account_configuration(
            experimentTemplateId=template["id"],
            accountId=account_id,
            roleArn=f"arn:aws:iam::{account_id}:role/FISTargetRole",
        )
        tmpl = client.get_experiment_template(id=template["id"])["experimentTemplate"]
        assert tmpl["targetAccountConfigurationsCount"] == idx


@mock_aws
def test_create_target_account_configuration_is_readable():
    client = boto3.client("fis", region_name="ap-southeast-1")
    template = _create_template(
        client, "ap-southeast-1", clientToken="token-create-read"
    )

    created = client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
        description="target account",
    )["targetAccountConfiguration"]

    assert (
        client.get_target_account_configuration(
            experimentTemplateId=template["id"], accountId="111122223333"
        )["targetAccountConfiguration"]
        == created
    )
    assert client.list_target_account_configurations(
        experimentTemplateId=template["id"]
    )["targetAccountConfigurations"] == [created]


@mock_aws
def test_create_target_account_configuration_is_used_by_later_experiments():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-create-exp")
    experiment_before = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
    )
    experiment_after = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    assert experiment_before["targetAccountConfigurationsCount"] == 0
    assert experiment_after["targetAccountConfigurationsCount"] == 1
    assert (
        client.get_experiment_target_account_configuration(
            experimentId=experiment_after["id"], accountId="111122223333"
        )["targetAccountConfiguration"]["accountId"]
        == "111122223333"
    )


@mock_aws
def test_create_target_account_configuration_is_per_template():
    client = boto3.client("fis", region_name="us-east-2")
    first = _create_template(client, "us-east-2", clientToken="token-create-tmpl-a")
    second = _create_template(client, "us-east-2", clientToken="token-create-tmpl-b")

    client.create_target_account_configuration(
        experimentTemplateId=first["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
    )

    assert (
        client.list_target_account_configurations(experimentTemplateId=second["id"])[
            "targetAccountConfigurations"
        ]
        == []
    )


@mock_aws
def test_create_target_account_configuration_unknown_template():
    client = boto3.client("fis", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.create_target_account_configuration(
            experimentTemplateId="unknown-template",
            accountId="111122223333",
            roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment template unknown-template does not exist"


@mock_aws
def test_create_target_account_configuration_after_template_delete():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-create-deleted")
    client.delete_experiment_template(id=template["id"])

    with pytest.raises(ClientError) as exc:
        client.create_target_account_configuration(
            experimentTemplateId=template["id"],
            accountId="111122223333",
            roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
        )

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_update_experiment_template():
    client = boto3.client("fis", region_name="ap-southeast-1")
    created = _create_template(
        client,
        "ap-southeast-1",
        description="before",
        clientToken="token-tmpl-update",
        tags={"env": "test"},
    )

    tmpl = client.update_experiment_template(
        id=created["id"],
        description="after",
        stopConditions=[
            {
                "source": "aws:cloudwatch:alarm",
                "value": "arn:aws:cloudwatch:ap-southeast-1:123456789012:alarm:my-alarm",
            }
        ],
        targets={
            "t2": {
                "resourceType": "aws:ecs:cluster",
                "resourceTags": {"env": "prod"},
                "filters": [{"path": "State.Name", "values": ["running"]}],
                "selectionMode": "COUNT(1)",
            }
        },
        actions={
            "a2": {
                "actionId": "aws:ecs:stop-task",
                "description": "stop the task",
                "parameters": {},
                "targets": {"Clusters": "t2"},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/OtherFISRole",
        logConfiguration={
            "s3Configuration": {"bucketName": "my-bucket", "prefix": "fis/"},
            "logSchemaVersion": 2,
        },
        experimentOptions={"emptyTargetResolutionMode": "skip"},
        experimentReportConfiguration={
            "outputs": {
                "s3Configuration": {"bucketName": "report-bucket", "prefix": "reports/"}
            },
            "preExperimentDuration": "PT1M",
            "postExperimentDuration": "PT5M",
        },
    )["experimentTemplate"]

    # The identity of the template does not change
    assert tmpl["id"] == created["id"]
    assert tmpl["arn"] == created["arn"]
    assert tmpl["creationTime"] == created["creationTime"]
    assert tmpl["tags"] == {"env": "test"}

    assert tmpl["description"] == "after"
    assert tmpl["roleArn"] == "arn:aws:iam::123456789012:role/OtherFISRole"
    assert tmpl["stopConditions"][0]["source"] == "aws:cloudwatch:alarm"
    assert list(tmpl["targets"]) == ["t2"]
    assert tmpl["targets"]["t2"]["resourceType"] == "aws:ecs:cluster"
    assert list(tmpl["actions"]) == ["a2"]
    assert tmpl["actions"]["a2"]["actionId"] == "aws:ecs:stop-task"
    assert tmpl["logConfiguration"]["s3Configuration"]["bucketName"] == "my-bucket"
    assert tmpl["experimentOptions"]["emptyTargetResolutionMode"] == "skip"
    assert tmpl["experimentReportConfiguration"]["preExperimentDuration"] == "PT1M"

    # The changes are persisted
    assert (
        client.get_experiment_template(id=created["id"])["experimentTemplate"] == tmpl
    )


@mock_aws
def test_update_experiment_template_only_updates_supplied_parameters():
    client = boto3.client("fis", region_name="eu-west-1")
    created = _create_template(
        client,
        "eu-west-1",
        description="original",
        clientToken="token-tmpl-partial",
    )

    tmpl = client.update_experiment_template(id=created["id"], description="updated")[
        "experimentTemplate"
    ]

    assert tmpl["description"] == "updated"
    assert tmpl["targets"] == created["targets"]
    assert tmpl["actions"] == created["actions"]
    assert tmpl["stopConditions"] == created["stopConditions"]
    assert tmpl["roleArn"] == created["roleArn"]


@mock_aws
def test_update_experiment_template_updates_last_update_time():
    client = boto3.client("fis", region_name="us-east-2")
    created = _create_template(client, "us-east-2", clientToken="token-tmpl-lut")

    tmpl = client.update_experiment_template(id=created["id"], description="touched")[
        "experimentTemplate"
    ]

    assert tmpl["creationTime"] == created["creationTime"]
    assert tmpl["lastUpdateTime"] >= created["lastUpdateTime"]

    summary = client.list_experiment_templates()["experimentTemplates"][0]
    assert summary["description"] == "touched"
    assert summary["lastUpdateTime"] == tmpl["lastUpdateTime"]


@mock_aws
def test_update_experiment_template_keeps_account_targeting():
    client = boto3.client("fis", region_name="us-east-2")
    created = _create_template(
        client,
        "us-east-2",
        clientToken="token-tmpl-opts-update",
        experimentOptions={
            "accountTargeting": "multi-account",
            "emptyTargetResolutionMode": "fail",
        },
    )

    tmpl = client.update_experiment_template(
        id=created["id"],
        experimentOptions={"emptyTargetResolutionMode": "skip"},
    )["experimentTemplate"]

    # Only emptyTargetResolutionMode can be updated
    assert tmpl["experimentOptions"] == {
        "accountTargeting": "multi-account",
        "emptyTargetResolutionMode": "skip",
    }


@mock_aws
def test_update_experiment_template_does_not_affect_running_experiments():
    client = boto3.client("fis", region_name="eu-west-1")
    created = _create_template(
        client, "eu-west-1", description="before", clientToken="token-tmpl-exp-update"
    )
    started = client.start_experiment(
        clientToken="token-exp-update", experimentTemplateId=created["id"]
    )["experiment"]

    client.update_experiment_template(
        id=created["id"],
        targets={
            "t9": {
                "resourceType": "aws:ecs:cluster",
                "resourceTags": {"env": "prod"},
                "selectionMode": "ALL",
            }
        },
    )

    experiment = client.get_experiment(id=started["id"])["experiment"]
    assert experiment["targets"] == created["targets"]


@mock_aws
def test_update_experiment_template_unknown_id():
    client = boto3.client("fis", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.update_experiment_template(id="unknown-template", description="nope")

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment template unknown-template does not exist"


@mock_aws
def test_update_experiment_template_after_delete():
    client = boto3.client("fis", region_name="us-east-2")
    created = _create_template(client, "us-east-2", clientToken="token-tmpl-upd-del")
    client.delete_experiment_template(id=created["id"])

    with pytest.raises(ClientError) as exc:
        client.update_experiment_template(id=created["id"], description="nope")

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_action():
    client = boto3.client("fis", region_name="eu-west-1")
    resp = client.get_action()

    raise Exception("NotYetImplemented")


@mock_aws
def test_list_actions():
    client = boto3.client("fis", region_name="ap-southeast-1")
    resp = client.list_actions()

    raise Exception("NotYetImplemented")


def _start_experiment_with_target_account(
    client, region, account_id="111122223333", description="target account", **kwargs
):
    template = _create_template(client, region, **kwargs)
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId=account_id,
        roleArn=f"arn:aws:iam::{account_id}:role/FISTargetRole",
        description=description,
    )
    return client.start_experiment(experimentTemplateId=template["id"])["experiment"]


@mock_aws
def test_get_experiment_target_account_configuration():
    client = boto3.client("fis", region_name="ap-southeast-1")
    experiment = _start_experiment_with_target_account(
        client, "ap-southeast-1", clientToken="token-exp-tac"
    )

    config = client.get_experiment_target_account_configuration(
        experimentId=experiment["id"], accountId="111122223333"
    )["targetAccountConfiguration"]

    assert config["accountId"] == "111122223333"
    assert config["roleArn"] == "arn:aws:iam::111122223333:role/FISTargetRole"
    assert config["description"] == "target account"


@mock_aws
def test_get_experiment_target_account_configuration_without_description():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-no-desc")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="444455556666",
        roleArn="arn:aws:iam::444455556666:role/FISTargetRole",
    )
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    config = client.get_experiment_target_account_configuration(
        experimentId=experiment["id"], accountId="444455556666"
    )["targetAccountConfiguration"]

    assert config["accountId"] == "444455556666"
    assert "description" not in config


@mock_aws
def test_get_experiment_target_account_configuration_counts_on_the_experiment():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-count")
    for account_id in ["111122223333", "444455556666"]:
        client.create_target_account_configuration(
            experimentTemplateId=template["id"],
            accountId=account_id,
            roleArn=f"arn:aws:iam::{account_id}:role/FISTargetRole",
        )
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    assert experiment["targetAccountConfigurationsCount"] == 2
    for account_id in ["111122223333", "444455556666"]:
        config = client.get_experiment_target_account_configuration(
            experimentId=experiment["id"], accountId=account_id
        )["targetAccountConfiguration"]
        assert config["accountId"] == account_id


@mock_aws
def test_get_experiment_target_account_configuration_is_a_snapshot():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-snapshot")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
        description="original",
    )
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    # Adding a target account to the template afterwards does not change the
    # configuration the experiment was started with.
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="777788889999",
        roleArn="arn:aws:iam::777788889999:role/FISTargetRole",
    )

    config = client.get_experiment_target_account_configuration(
        experimentId=experiment["id"], accountId="111122223333"
    )["targetAccountConfiguration"]
    assert config["description"] == "original"

    with pytest.raises(ClientError) as exc:
        client.get_experiment_target_account_configuration(
            experimentId=experiment["id"], accountId="777788889999"
        )

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_experiment_target_account_configuration_unknown_account():
    client = boto3.client("fis", region_name="eu-west-1")
    experiment = _start_experiment_with_target_account(
        client, "eu-west-1", clientToken="token-unknown-account"
    )

    with pytest.raises(ClientError) as exc:
        client.get_experiment_target_account_configuration(
            experimentId=experiment["id"], accountId="999999999999"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "Target account configuration for account 999999999999 does not exist"
    )


@mock_aws
def test_get_experiment_target_account_configuration_unknown_experiment():
    client = boto3.client("fis", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.get_experiment_target_account_configuration(
            experimentId="unknown-experiment", accountId="111122223333"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment unknown-experiment does not exist"


@mock_aws
def test_get_experiment_target_account_configuration_on_experiment_without_accounts():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-no-accounts")
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    assert experiment["targetAccountConfigurationsCount"] == 0

    with pytest.raises(ClientError) as exc:
        client.get_experiment_target_account_configuration(
            experimentId=experiment["id"], accountId="111122223333"
        )

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_update_target_account_configuration():
    client = boto3.client("fis", region_name="ap-southeast-1")
    template = _create_template(client, "ap-southeast-1", clientToken="token-upd-tac")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
        description="original",
    )

    config = client.update_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/UpdatedRole",
        description="updated",
    )["targetAccountConfiguration"]

    assert config["accountId"] == "111122223333"
    assert config["roleArn"] == "arn:aws:iam::111122223333:role/UpdatedRole"
    assert config["description"] == "updated"


@mock_aws
def test_update_target_account_configuration_only_updates_supplied_parameters():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-upd-partial")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
        description="original",
    )

    config = client.update_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        description="only the description",
    )["targetAccountConfiguration"]

    assert config["roleArn"] == "arn:aws:iam::111122223333:role/FISTargetRole"
    assert config["description"] == "only the description"

    config = client.update_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/UpdatedRole",
    )["targetAccountConfiguration"]

    assert config["roleArn"] == "arn:aws:iam::111122223333:role/UpdatedRole"
    assert config["description"] == "only the description"


@mock_aws
def test_update_target_account_configuration_only_updates_one_account():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-upd-one")
    for account_id in ["111122223333", "444455556666"]:
        client.create_target_account_configuration(
            experimentTemplateId=template["id"],
            accountId=account_id,
            roleArn=f"arn:aws:iam::{account_id}:role/FISTargetRole",
            description="original",
        )

    client.update_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        description="updated",
    )
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    assert experiment["targetAccountConfigurationsCount"] == 2
    untouched = client.get_experiment_target_account_configuration(
        experimentId=experiment["id"], accountId="444455556666"
    )["targetAccountConfiguration"]
    assert untouched["description"] == "original"


@mock_aws
def test_update_target_account_configuration_does_not_affect_running_experiments():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-upd-running")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
        description="original",
    )
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    client.update_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/UpdatedRole",
        description="updated",
    )

    running = client.get_experiment_target_account_configuration(
        experimentId=experiment["id"], accountId="111122223333"
    )["targetAccountConfiguration"]
    assert running["roleArn"] == "arn:aws:iam::111122223333:role/FISTargetRole"
    assert running["description"] == "original"

    # Experiments started after the update do pick it up.
    later = client.start_experiment(experimentTemplateId=template["id"])["experiment"]
    later_config = client.get_experiment_target_account_configuration(
        experimentId=later["id"], accountId="111122223333"
    )["targetAccountConfiguration"]
    assert later_config["roleArn"] == "arn:aws:iam::111122223333:role/UpdatedRole"
    assert later_config["description"] == "updated"


@mock_aws
def test_update_target_account_configuration_unknown_account():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-upd-unknown")

    with pytest.raises(ClientError) as exc:
        client.update_target_account_configuration(
            experimentTemplateId=template["id"],
            accountId="999999999999",
            description="nope",
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "Target account configuration for account 999999999999 does not exist"
    )


@mock_aws
def test_update_target_account_configuration_unknown_template():
    client = boto3.client("fis", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.update_target_account_configuration(
            experimentTemplateId="unknown-template",
            accountId="111122223333",
            description="nope",
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment template unknown-template does not exist"


@mock_aws
def test_delete_target_account_configuration():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-del-tac")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
        description="to be deleted",
    )

    config = client.delete_target_account_configuration(
        experimentTemplateId=template["id"], accountId="111122223333"
    )["targetAccountConfiguration"]

    assert config["accountId"] == "111122223333"
    assert config["roleArn"] == "arn:aws:iam::111122223333:role/FISTargetRole"
    assert config["description"] == "to be deleted"

    tmpl = client.get_experiment_template(id=template["id"])["experimentTemplate"]
    assert tmpl["targetAccountConfigurationsCount"] == 0


@mock_aws
def test_delete_target_account_configuration_only_deletes_one_account():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-del-one")
    for account_id in ["111122223333", "444455556666"]:
        client.create_target_account_configuration(
            experimentTemplateId=template["id"],
            accountId=account_id,
            roleArn=f"arn:aws:iam::{account_id}:role/FISTargetRole",
        )

    client.delete_target_account_configuration(
        experimentTemplateId=template["id"], accountId="111122223333"
    )

    tmpl = client.get_experiment_template(id=template["id"])["experimentTemplate"]
    assert tmpl["targetAccountConfigurationsCount"] == 1

    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]
    kept = client.get_experiment_target_account_configuration(
        experimentId=experiment["id"], accountId="444455556666"
    )["targetAccountConfiguration"]
    assert kept["accountId"] == "444455556666"


@mock_aws
def test_delete_target_account_configuration_does_not_affect_running_experiments():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-del-running")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
        description="original",
    )
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    client.delete_target_account_configuration(
        experimentTemplateId=template["id"], accountId="111122223333"
    )

    running = client.get_experiment_target_account_configuration(
        experimentId=experiment["id"], accountId="111122223333"
    )["targetAccountConfiguration"]
    assert running["description"] == "original"
    assert experiment["targetAccountConfigurationsCount"] == 1


@mock_aws
def test_delete_target_account_configuration_is_not_idempotent():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-del-twice")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
    )

    client.delete_target_account_configuration(
        experimentTemplateId=template["id"], accountId="111122223333"
    )

    with pytest.raises(ClientError) as exc:
        client.delete_target_account_configuration(
            experimentTemplateId=template["id"], accountId="111122223333"
        )

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_delete_target_account_configuration_unknown_account():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-del-unknown")

    with pytest.raises(ClientError) as exc:
        client.delete_target_account_configuration(
            experimentTemplateId=template["id"], accountId="999999999999"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "Target account configuration for account 999999999999 does not exist"
    )


@mock_aws
def test_delete_target_account_configuration_unknown_template():
    client = boto3.client("fis", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.delete_target_account_configuration(
            experimentTemplateId="unknown-template", accountId="111122223333"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment template unknown-template does not exist"


@mock_aws
def test_get_target_account_configuration():
    client = boto3.client("fis", region_name="ap-southeast-1")
    template = _create_template(client, "ap-southeast-1", clientToken="token-get-tac")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
        description="target account",
    )

    config = client.get_target_account_configuration(
        experimentTemplateId=template["id"], accountId="111122223333"
    )["targetAccountConfiguration"]

    assert config["accountId"] == "111122223333"
    assert config["roleArn"] == "arn:aws:iam::111122223333:role/FISTargetRole"
    assert config["description"] == "target account"


@mock_aws
def test_get_target_account_configuration_without_description():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-get-tac-nodesc")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="444455556666",
        roleArn="arn:aws:iam::444455556666:role/FISTargetRole",
    )

    config = client.get_target_account_configuration(
        experimentTemplateId=template["id"], accountId="444455556666"
    )["targetAccountConfiguration"]

    assert config["accountId"] == "444455556666"
    assert "description" not in config


@mock_aws
def test_get_target_account_configuration_reflects_updates():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-get-tac-upd")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
        description="original",
    )

    client.update_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        description="updated",
    )

    config = client.get_target_account_configuration(
        experimentTemplateId=template["id"], accountId="111122223333"
    )["targetAccountConfiguration"]
    assert config["description"] == "updated"


@mock_aws
def test_get_target_account_configuration_after_delete():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-get-tac-del")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
    )
    client.delete_target_account_configuration(
        experimentTemplateId=template["id"], accountId="111122223333"
    )

    with pytest.raises(ClientError) as exc:
        client.get_target_account_configuration(
            experimentTemplateId=template["id"], accountId="111122223333"
        )

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_target_account_configuration_is_per_template():
    client = boto3.client("fis", region_name="eu-west-1")
    with_account = _create_template(client, "eu-west-1", clientToken="token-tac-a")
    without_account = _create_template(client, "eu-west-1", clientToken="token-tac-b")
    client.create_target_account_configuration(
        experimentTemplateId=with_account["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
    )

    with pytest.raises(ClientError) as exc:
        client.get_target_account_configuration(
            experimentTemplateId=without_account["id"], accountId="111122223333"
        )

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_target_account_configuration_unknown_account():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(
        client, "us-east-2", clientToken="token-get-tac-unknown"
    )

    with pytest.raises(ClientError) as exc:
        client.get_target_account_configuration(
            experimentTemplateId=template["id"], accountId="999999999999"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "Target account configuration for account 999999999999 does not exist"
    )


@mock_aws
def test_get_target_account_configuration_unknown_template():
    client = boto3.client("fis", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.get_target_account_configuration(
            experimentTemplateId="unknown-template", accountId="111122223333"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment template unknown-template does not exist"


@mock_aws
def test_get_target_resource_type():
    client = boto3.client("fis", region_name="eu-west-1")
    resp = client.get_target_resource_type()

    raise Exception("NotYetImplemented")


@mock_aws
def _start_experiment_with_targets(client, targets, client_token):
    template = client.create_experiment_template(
        clientToken=client_token,
        description="resolved targets",
        stopConditions=[{"source": "none"}],
        targets=targets,
        actions={
            "a1": {
                "actionId": "aws:ec2:stop-instances",
                "targets": {"Instances": list(targets)[0]},
            }
        },
        roleArn="arn:aws:iam::123456789012:role/FISRole",
    )["experimentTemplate"]
    return client.start_experiment(experimentTemplateId=template["id"])["experiment"]


@mock_aws
def test_list_experiment_resolved_targets():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-resolved")
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    resp = client.list_experiment_resolved_targets(experimentId=experiment["id"])

    assert "nextToken" not in resp
    assert resp["resolvedTargets"] == [
        {
            "resourceType": "aws:ec2:instance",
            "targetName": "t1",
            "targetInformation": {
                "arn": "arn:aws:ec2:eu-west-1:123456789012:instance/i-123"
            },
        }
    ]


@mock_aws
def test_list_experiment_resolved_targets_one_per_resource():
    client = boto3.client("fis", region_name="us-east-2")
    experiment = _start_experiment_with_targets(
        client,
        {
            "instances": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": [
                    "arn:aws:ec2:us-east-2:123456789012:instance/i-111",
                    "arn:aws:ec2:us-east-2:123456789012:instance/i-222",
                ],
                "selectionMode": "ALL",
            }
        },
        client_token="token-resolved-multi",
    )

    targets = client.list_experiment_resolved_targets(experimentId=experiment["id"])[
        "resolvedTargets"
    ]

    assert len(targets) == 2
    assert {t["targetInformation"]["arn"] for t in targets} == {
        "arn:aws:ec2:us-east-2:123456789012:instance/i-111",
        "arn:aws:ec2:us-east-2:123456789012:instance/i-222",
    }
    assert {t["targetName"] for t in targets} == {"instances"}


@mock_aws
def test_list_experiment_resolved_targets_filtered_by_target_name():
    client = boto3.client("fis", region_name="us-east-2")
    experiment = _start_experiment_with_targets(
        client,
        {
            "instances": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": ["arn:aws:ec2:us-east-2:123456789012:instance/i-111"],
                "selectionMode": "ALL",
            },
            "clusters": {
                "resourceType": "aws:rds:cluster",
                "resourceArns": ["arn:aws:rds:us-east-2:123456789012:cluster:db-1"],
                "selectionMode": "ALL",
            },
        },
        client_token="token-resolved-filter",
    )

    assert (
        len(
            client.list_experiment_resolved_targets(experimentId=experiment["id"])[
                "resolvedTargets"
            ]
        )
        == 2
    )

    targets = client.list_experiment_resolved_targets(
        experimentId=experiment["id"], targetName="clusters"
    )["resolvedTargets"]

    assert len(targets) == 1
    assert targets[0]["targetName"] == "clusters"
    assert targets[0]["resourceType"] == "aws:rds:cluster"


@mock_aws
def test_list_experiment_resolved_targets_unknown_target_name():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(
        client, "eu-west-1", clientToken="token-resolved-noname"
    )
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    resp = client.list_experiment_resolved_targets(
        experimentId=experiment["id"], targetName="does-not-exist"
    )

    assert resp["resolvedTargets"] == []


@mock_aws
def test_list_experiment_resolved_targets_for_targets_selected_by_tag():
    client = boto3.client("fis", region_name="eu-west-1")
    experiment = _start_experiment_with_targets(
        client,
        {
            "instances": {
                "resourceType": "aws:ec2:instance",
                "resourceTags": {"env": "test"},
                "selectionMode": "ALL",
            }
        },
        client_token="token-resolved-tags",
    )

    # Targets that select their resources by tag are not resolved by moto.
    assert (
        client.list_experiment_resolved_targets(experimentId=experiment["id"])[
            "resolvedTargets"
        ]
        == []
    )


@mock_aws
def test_list_experiment_resolved_targets_paginated():
    client = boto3.client("fis", region_name="us-east-1")
    experiment = _start_experiment_with_targets(
        client,
        {
            "instances": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": [
                    f"arn:aws:ec2:us-east-1:123456789012:instance/i-{idx}"
                    for idx in range(5)
                ],
                "selectionMode": "ALL",
            }
        },
        client_token="token-resolved-page",
    )

    page1 = client.list_experiment_resolved_targets(
        experimentId=experiment["id"], maxResults=2
    )
    assert len(page1["resolvedTargets"]) == 2
    assert page1["nextToken"]

    page2 = client.list_experiment_resolved_targets(
        experimentId=experiment["id"], maxResults=2, nextToken=page1["nextToken"]
    )
    assert len(page2["resolvedTargets"]) == 2
    assert page2["nextToken"]

    page3 = client.list_experiment_resolved_targets(
        experimentId=experiment["id"], maxResults=2, nextToken=page2["nextToken"]
    )
    assert len(page3["resolvedTargets"]) == 1
    assert "nextToken" not in page3

    seen = [
        target["targetInformation"]["arn"]
        for page in (page1, page2, page3)
        for target in page["resolvedTargets"]
    ]
    assert len(set(seen)) == 5


@mock_aws
def test_list_experiment_resolved_targets_is_a_snapshot():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-resolved-snap")
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    client.update_experiment_template(
        id=template["id"],
        targets={
            "t1": {
                "resourceType": "aws:ec2:instance",
                "resourceArns": [
                    "arn:aws:ec2:us-east-2:123456789012:instance/i-999",
                ],
                "selectionMode": "ALL",
            }
        },
    )

    targets = client.list_experiment_resolved_targets(experimentId=experiment["id"])[
        "resolvedTargets"
    ]
    assert targets[0]["targetInformation"]["arn"].endswith("i-123")


@mock_aws
def test_list_experiment_resolved_targets_unknown_experiment():
    client = boto3.client("fis", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.list_experiment_resolved_targets(experimentId="unknown-experiment")

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment unknown-experiment does not exist"


@mock_aws
def test_list_experiment_target_account_configurations():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-list-exp-tac")
    for account_id in ["111122223333", "444455556666"]:
        client.create_target_account_configuration(
            experimentTemplateId=template["id"],
            accountId=account_id,
            roleArn=f"arn:aws:iam::{account_id}:role/FISTargetRole",
            description=f"account {account_id}",
        )
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    resp = client.list_experiment_target_account_configurations(
        experimentId=experiment["id"]
    )

    assert "nextToken" not in resp
    configurations = resp["targetAccountConfigurations"]
    assert len(configurations) == 2
    assert {c["accountId"] for c in configurations} == {
        "111122223333",
        "444455556666",
    }
    by_account = {c["accountId"]: c for c in configurations}
    assert (
        by_account["111122223333"]["roleArn"]
        == "arn:aws:iam::111122223333:role/FISTargetRole"
    )
    assert by_account["111122223333"]["description"] == "account 111122223333"


@mock_aws
def test_list_experiment_target_account_configurations_empty():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-list-exp-empty")
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    resp = client.list_experiment_target_account_configurations(
        experimentId=experiment["id"]
    )

    assert resp["targetAccountConfigurations"] == []
    assert "nextToken" not in resp


@mock_aws
def test_list_experiment_target_account_configurations_without_description():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(
        client, "eu-west-1", clientToken="token-list-exp-nodesc"
    )
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
    )
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    configurations = client.list_experiment_target_account_configurations(
        experimentId=experiment["id"]
    )["targetAccountConfigurations"]

    assert len(configurations) == 1
    assert "description" not in configurations[0]


@mock_aws
def test_list_experiment_target_account_configurations_matches_get():
    client = boto3.client("fis", region_name="ap-southeast-1")
    experiment = _start_experiment_with_target_account(
        client, "ap-southeast-1", clientToken="token-list-exp-match"
    )

    for summary in client.list_experiment_target_account_configurations(
        experimentId=experiment["id"]
    )["targetAccountConfigurations"]:
        config = client.get_experiment_target_account_configuration(
            experimentId=experiment["id"], accountId=summary["accountId"]
        )["targetAccountConfiguration"]
        assert summary == config


@mock_aws
def test_list_experiment_target_account_configurations_is_a_snapshot():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-list-exp-snap")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
    )
    experiment = client.start_experiment(experimentTemplateId=template["id"])[
        "experiment"
    ]

    client.delete_target_account_configuration(
        experimentTemplateId=template["id"], accountId="111122223333"
    )
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="777788889999",
        roleArn="arn:aws:iam::777788889999:role/FISTargetRole",
    )

    configurations = client.list_experiment_target_account_configurations(
        experimentId=experiment["id"]
    )["targetAccountConfigurations"]

    assert [c["accountId"] for c in configurations] == ["111122223333"]


@mock_aws
def test_list_experiment_target_account_configurations_is_experiment_specific():
    client = boto3.client("fis", region_name="eu-west-1")
    with_accounts = _start_experiment_with_target_account(
        client, "eu-west-1", clientToken="token-list-exp-a"
    )
    other_template = _create_template(
        client, "eu-west-1", clientToken="token-list-exp-b"
    )
    without_accounts = client.start_experiment(
        experimentTemplateId=other_template["id"]
    )["experiment"]

    assert (
        len(
            client.list_experiment_target_account_configurations(
                experimentId=with_accounts["id"]
            )["targetAccountConfigurations"]
        )
        == 1
    )
    assert (
        client.list_experiment_target_account_configurations(
            experimentId=without_accounts["id"]
        )["targetAccountConfigurations"]
        == []
    )


@mock_aws
def test_list_experiment_target_account_configurations_unknown_experiment():
    client = boto3.client("fis", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.list_experiment_target_account_configurations(
            experimentId="unknown-experiment"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment unknown-experiment does not exist"


@mock_aws
def test_list_target_resource_types():
    client = boto3.client("fis", region_name="ap-southeast-1")
    resp = client.list_target_resource_types()

    raise Exception("NotYetImplemented")


@mock_aws
def test_list_target_account_configurations():
    client = boto3.client("fis", region_name="ap-southeast-1")
    template = _create_template(client, "ap-southeast-1", clientToken="token-list-tac")
    for account_id in ["111122223333", "444455556666"]:
        client.create_target_account_configuration(
            experimentTemplateId=template["id"],
            accountId=account_id,
            roleArn=f"arn:aws:iam::{account_id}:role/FISTargetRole",
            description=f"account {account_id}",
        )

    resp = client.list_target_account_configurations(
        experimentTemplateId=template["id"]
    )

    assert "nextToken" not in resp
    configurations = resp["targetAccountConfigurations"]
    assert len(configurations) == 2
    by_account = {c["accountId"]: c for c in configurations}
    assert set(by_account) == {"111122223333", "444455556666"}
    assert (
        by_account["444455556666"]["roleArn"]
        == "arn:aws:iam::444455556666:role/FISTargetRole"
    )
    assert by_account["444455556666"]["description"] == "account 444455556666"


@mock_aws
def test_list_target_account_configurations_empty():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-list-tac-empty")

    resp = client.list_target_account_configurations(
        experimentTemplateId=template["id"]
    )

    assert resp["targetAccountConfigurations"] == []
    assert "nextToken" not in resp


@mock_aws
def test_list_target_account_configurations_matches_get():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-list-tac-match")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
    )

    for summary in client.list_target_account_configurations(
        experimentTemplateId=template["id"]
    )["targetAccountConfigurations"]:
        config = client.get_target_account_configuration(
            experimentTemplateId=template["id"], accountId=summary["accountId"]
        )["targetAccountConfiguration"]
        assert summary == config
        assert "description" not in summary


@mock_aws
def test_list_target_account_configurations_reflects_updates_and_deletes():
    client = boto3.client("fis", region_name="us-east-2")
    template = _create_template(client, "us-east-2", clientToken="token-list-tac-upd")
    for account_id in ["111122223333", "444455556666"]:
        client.create_target_account_configuration(
            experimentTemplateId=template["id"],
            accountId=account_id,
            roleArn=f"arn:aws:iam::{account_id}:role/FISTargetRole",
            description="original",
        )

    client.update_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        description="updated",
    )
    client.delete_target_account_configuration(
        experimentTemplateId=template["id"], accountId="444455556666"
    )

    configurations = client.list_target_account_configurations(
        experimentTemplateId=template["id"]
    )["targetAccountConfigurations"]

    assert len(configurations) == 1
    assert configurations[0]["accountId"] == "111122223333"
    assert configurations[0]["description"] == "updated"


@mock_aws
def test_list_target_account_configurations_is_per_template():
    client = boto3.client("fis", region_name="eu-west-1")
    with_accounts = _create_template(
        client, "eu-west-1", clientToken="token-list-tac-a"
    )
    without_accounts = _create_template(
        client, "eu-west-1", clientToken="token-list-tac-b"
    )
    client.create_target_account_configuration(
        experimentTemplateId=with_accounts["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
    )

    assert (
        len(
            client.list_target_account_configurations(
                experimentTemplateId=with_accounts["id"]
            )["targetAccountConfigurations"]
        )
        == 1
    )
    assert (
        client.list_target_account_configurations(
            experimentTemplateId=without_accounts["id"]
        )["targetAccountConfigurations"]
        == []
    )


@mock_aws
def test_list_target_account_configurations_paginated():
    client = boto3.client("fis", region_name="us-east-1")
    template = _create_template(client, "us-east-1", clientToken="token-list-tac-page")
    account_ids = [f"11112222{idx:04d}" for idx in range(5)]
    for account_id in account_ids:
        client.create_target_account_configuration(
            experimentTemplateId=template["id"],
            accountId=account_id,
            roleArn=f"arn:aws:iam::{account_id}:role/FISTargetRole",
        )

    page1 = client.list_target_account_configurations(
        experimentTemplateId=template["id"], maxResults=2
    )
    assert len(page1["targetAccountConfigurations"]) == 2
    assert page1["nextToken"]

    page2 = client.list_target_account_configurations(
        experimentTemplateId=template["id"],
        maxResults=2,
        nextToken=page1["nextToken"],
    )
    assert len(page2["targetAccountConfigurations"]) == 2
    assert page2["nextToken"]

    page3 = client.list_target_account_configurations(
        experimentTemplateId=template["id"],
        maxResults=2,
        nextToken=page2["nextToken"],
    )
    assert len(page3["targetAccountConfigurations"]) == 1
    assert "nextToken" not in page3

    seen = [
        configuration["accountId"]
        for page in (page1, page2, page3)
        for configuration in page["targetAccountConfigurations"]
    ]
    assert set(seen) == set(account_ids)


@mock_aws
def test_list_target_account_configurations_unknown_template():
    client = boto3.client("fis", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.list_target_account_configurations(
            experimentTemplateId="unknown-template"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Experiment template unknown-template does not exist"


@mock_aws
def test_list_target_account_configurations_after_template_delete():
    client = boto3.client("fis", region_name="eu-west-1")
    template = _create_template(client, "eu-west-1", clientToken="token-list-tac-del")
    client.create_target_account_configuration(
        experimentTemplateId=template["id"],
        accountId="111122223333",
        roleArn="arn:aws:iam::111122223333:role/FISTargetRole",
    )
    client.delete_experiment_template(id=template["id"])

    with pytest.raises(ClientError) as exc:
        client.list_target_account_configurations(experimentTemplateId=template["id"])

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
