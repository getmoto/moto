"""Unit tests for bedrock-agentcore-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

TEST_REGION = "us-east-1"
MEMORY_ID = "mtest12345-abcdefghij"


def _create_client():
    return boto3.client("bedrock-agentcore", region_name=TEST_REGION)


def _payload(text="hello"):
    return [{"conversational": {"content": {"text": text}, "role": "USER"}}]


@mock_aws
def test_create_event():
    client = _create_client()

    resp = client.create_event(
        memoryId=MEMORY_ID,
        actorId="actor-1",
        sessionId="session-1",
        eventTimestamp="2026-01-01T00:00:00Z",
        payload=_payload(),
    )

    event = resp["event"]
    assert event["memoryId"] == MEMORY_ID
    assert event["actorId"] == "actor-1"
    assert event["sessionId"] == "session-1"
    assert "eventId" in event
    assert event["payload"] == _payload()
    assert event["branch"] == {"name": "main"}


@mock_aws
def test_create_event_with_metadata_and_branch():
    client = _create_client()

    resp = client.create_event(
        memoryId=MEMORY_ID,
        actorId="actor-1",
        sessionId="session-1",
        eventTimestamp="2026-01-01T00:00:00Z",
        payload=_payload(),
        branch={"name": "feature-branch"},
        metadata={"source": {"stringValue": "unit-test"}},
    )

    event = resp["event"]
    assert event["branch"] == {"name": "feature-branch"}
    assert event["metadata"] == {"source": {"stringValue": "unit-test"}}


@mock_aws
def test_create_event_errors():
    client = _create_client()

    with pytest.raises(ClientError) as exc:
        client.create_event(
            memoryId=MEMORY_ID,
            actorId="actor-1",
            eventTimestamp="2026-01-01T00:00:00Z",
            payload=_payload(),
        )
    assert exc.value.response["Error"]["Code"] == "ValidationException"

    with pytest.raises(ClientError) as exc:
        client.create_event(
            memoryId=MEMORY_ID,
            actorId="actor-1",
            sessionId="session-1",
            eventTimestamp="2026-01-01T00:00:00Z",
            payload=[],
        )
    assert exc.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_get_event():
    client = _create_client()
    created = client.create_event(
        memoryId=MEMORY_ID,
        actorId="actor-1",
        sessionId="session-1",
        eventTimestamp="2026-01-01T00:00:00Z",
        payload=_payload(),
    )["event"]

    resp = client.get_event(
        memoryId=MEMORY_ID,
        actorId="actor-1",
        sessionId="session-1",
        eventId=created["eventId"],
    )

    assert resp["event"]["eventId"] == created["eventId"]
    assert resp["event"]["payload"] == _payload()


@mock_aws
def test_get_event_not_found():
    client = _create_client()

    with pytest.raises(ClientError) as exc:
        client.get_event(
            memoryId=MEMORY_ID,
            actorId="actor-1",
            sessionId="session-1",
            eventId="not-a-real-event",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_events():
    client = _create_client()
    for text in ("first", "second", "third"):
        client.create_event(
            memoryId=MEMORY_ID,
            actorId="actor-1",
            sessionId="session-1",
            eventTimestamp="2026-01-01T00:00:00Z",
            payload=_payload(text),
        )

    resp = client.list_events(
        memoryId=MEMORY_ID, actorId="actor-1", sessionId="session-1"
    )

    assert len(resp["events"]) == 3
    # payloads are not included by default
    assert "payload" not in resp["events"][0]


@mock_aws
def test_list_events_include_payloads():
    client = _create_client()
    client.create_event(
        memoryId=MEMORY_ID,
        actorId="actor-1",
        sessionId="session-1",
        eventTimestamp="2026-01-01T00:00:00Z",
        payload=_payload(),
    )

    resp = client.list_events(
        memoryId=MEMORY_ID,
        actorId="actor-1",
        sessionId="session-1",
        includePayloads=True,
    )

    assert resp["events"][0]["payload"] == _payload()


@mock_aws
def test_list_events_max_results():
    client = _create_client()
    for _ in range(3):
        client.create_event(
            memoryId=MEMORY_ID,
            actorId="actor-1",
            sessionId="session-1",
            eventTimestamp="2026-01-01T00:00:00Z",
            payload=_payload(),
        )

    resp = client.list_events(
        memoryId=MEMORY_ID, actorId="actor-1", sessionId="session-1", maxResults=2
    )

    assert len(resp["events"]) == 2


@mock_aws
def test_list_events_scoped_to_session():
    client = _create_client()
    client.create_event(
        memoryId=MEMORY_ID,
        actorId="actor-1",
        sessionId="session-1",
        eventTimestamp="2026-01-01T00:00:00Z",
        payload=_payload(),
    )
    client.create_event(
        memoryId=MEMORY_ID,
        actorId="actor-1",
        sessionId="session-2",
        eventTimestamp="2026-01-01T00:00:00Z",
        payload=_payload(),
    )

    resp = client.list_events(
        memoryId=MEMORY_ID, actorId="actor-1", sessionId="session-1"
    )

    assert len(resp["events"]) == 1


@mock_aws
def test_delete_event():
    client = _create_client()
    created = client.create_event(
        memoryId=MEMORY_ID,
        actorId="actor-1",
        sessionId="session-1",
        eventTimestamp="2026-01-01T00:00:00Z",
        payload=_payload(),
    )["event"]

    resp = client.delete_event(
        memoryId=MEMORY_ID,
        actorId="actor-1",
        sessionId="session-1",
        eventId=created["eventId"],
    )

    assert resp["eventId"] == created["eventId"]

    with pytest.raises(ClientError) as exc:
        client.get_event(
            memoryId=MEMORY_ID,
            actorId="actor-1",
            sessionId="session-1",
            eventId=created["eventId"],
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_delete_event_not_found():
    client = _create_client()

    with pytest.raises(ClientError) as exc:
        client.delete_event(
            memoryId=MEMORY_ID,
            actorId="actor-1",
            sessionId="session-1",
            eventId="not-a-real-event",
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
