import uuid
from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError
from dateutil.tz import tzlocal

from moto import mock_aws

DEFAULT_REGION = "us-east-1"


@pytest.fixture
def mock_uuid4(monkeypatch):
    monkeypatch.setattr(
        uuid, "uuid4", lambda: uuid.UUID("11111111-1111-1111-1111-111111111111")
    )
    monkeypatch.setattr(
        "moto.moto_api._internal.moto_random.MotoRandom.uuid4",
        lambda _: uuid.UUID("11111111-1111-1111-1111-111111111111"),
    )


@pytest.fixture
@mock_aws
def client():
    return boto3.client("bedrock-agentcore", region_name=DEFAULT_REGION)


def _mk_event(
    client,
    *,
    memory_id="mem-12345678",
    actor_id="actor-12345678",
    session_id="sess-12345678",
    when: datetime = datetime(2026, 3, 11),
    text="moto is amazing!",
    client_token=None,
    branch=None,
    metadata=None,
):
    """Helper for creating events."""
    kwargs = {
        "memoryId": memory_id,
        "actorId": actor_id,
        "sessionId": session_id,
        "payload": [{"conversational": {"content": {"text": text}, "role": "USER"}}],
        "eventTimestamp": when,
    }

    if branch is not None:
        kwargs["branch"] = branch
    if metadata is not None:
        kwargs["metadata"] = metadata
    if client_token is not None:
        kwargs["clientToken"] = client_token

    return client.create_event(**kwargs)["event"]


@mock_aws
def test_create_event(client, mock_uuid4):
    event = _mk_event(client)

    assert event["actorId"] == "actor-12345678"
    assert event["sessionId"] == "sess-12345678"
    assert event["eventId"] == "11111111-1111-1111-1111-111111111111"

    # According to the documentation about client token:
    # A unique, case-sensitive identifier to ensure that the operation completes no more than one time.
    # If this token matches a previous request,
    # AgentCore ignores the request, but does not return an error.
    new_event = _mk_event(
        client,
        memory_id="mem-other-12345678",
        client_token="11111111-1111-1111-1111-111111111111",
    )

    # Using the same client token the request must be
    # ignored but return the same event
    assert event == new_event


@mock_aws
def test_get_event(client, mock_uuid4):
    _mk_event(client)

    event = client.get_event(
        eventId="11111111-1111-1111-1111-111111111111",
        memoryId="mem-12345678",
        actorId="actor-12345678",
        sessionId="sess-12345678",
    )["event"]

    assert event == {
        "memoryId": "mem-12345678",
        "actorId": "actor-12345678",
        "sessionId": "sess-12345678",
        "eventId": "11111111-1111-1111-1111-111111111111",
        "eventTimestamp": datetime(2026, 3, 10, 21, 0, tzinfo=tzlocal()),
        "payload": [
            {
                "conversational": {
                    "content": {"text": "moto is amazing!"},
                    "role": "USER",
                }
            }
        ],
    }


@mock_aws
def test_list_events(client):
    _mk_event(client, text="Moto is amazing 1")
    _mk_event(client, text="Moto is amazing 2")
    _mk_event(client, text="Moto is amazing 3")

    response = client.list_events(
        memoryId="mem-12345678",
        actorId="actor-12345678",
        sessionId="sess-12345678",
    )

    assert len(response["events"]) == 3
    assert all("payload" in r for r in response["events"])

    # Exclude payload
    response = client.list_events(
        memoryId="mem-12345678",
        actorId="actor-12345678",
        sessionId="sess-12345678",
        includePayloads=False,
    )
    assert len(response["events"]) == 3
    assert all("payload" not in r for r in response["events"])

    # Now use pagination
    response = client.list_events(
        memoryId="mem-12345678",
        actorId="actor-12345678",
        sessionId="sess-12345678",
        maxResults=2,
    )
    assert len(response["events"]) == 2
    # Use the token
    response = client.list_events(
        memoryId="mem-12345678",
        actorId="actor-12345678",
        sessionId="sess-12345678",
        maxResults=2,
        nextToken=response["nextToken"],
    )
    assert len(response["events"]) == 1


@mock_aws
def test_list_events_with_filter(client):
    # Create events with different metadata and branches
    _mk_event(
        client,
        text="Moto is amazing 1",
        branch={"name": "alpha"},
        metadata={"topic": {"stringValue": "fun"}},
    )
    _mk_event(
        client,
        text="Moto is amazing 2",
        branch={"name": "beta"},
        metadata={"topic": {"stringValue": "boring"}},
    )
    _mk_event(
        client,
        text="Moto is amazing 3",
        branch={"name": "alpha"},
        metadata={"topic": {"stringValue": "fun"}},
    )

    response = client.list_events(
        memoryId="mem-12345678",
        actorId="actor-12345678",
        sessionId="sess-12345678",
        includePayloads=True,
        filter={
            "branch": {
                "name": "alpha",
                "includeParentBranches": False,
            },
            "eventMetadata": [
                {
                    "left": {
                        "metadataKey": "topic",
                    },
                    "operator": "EQUALS_TO",
                    "right": {
                        "metadataValue": {
                            "stringValue": "fun",
                        }
                    },
                }
            ],
        },
    )

    assert len(response["events"]) == 2
    texts = [
        e["payload"][0]["conversational"]["content"]["text"] for e in response["events"]
    ]
    assert "Moto is amazing 1" in texts
    assert "Moto is amazing 3" in texts


@mock_aws
def test_delete_event(client, mock_uuid4):
    _mk_event(client)
    response = client.delete_event(
        eventId="11111111-1111-1111-1111-111111111111",
        memoryId="mem-12345678",
        actorId="actor-12345678",
        sessionId="sess-12345678",
    )

    assert response["eventId"] == "11111111-1111-1111-1111-111111111111"

    response = client.list_events(
        memoryId="mem-12345678", actorId="actor-12345678", sessionId="sess-12345678"
    )

    assert response["events"] == []


@mock_aws
@pytest.mark.parametrize("method", ["get_event", "delete_event"])
@pytest.mark.parametrize(
    "wrong_params",
    [
        {"eventId": "wrong-id-12345678"},
        {"memoryId": "wrong-mem-12345678"},
        {"actorId": "wrong-actor-12345678"},
        {"sessionId": "wrong-sess-12345678"},
    ],
)
def test_get_or_delete_event_not_found(client, mock_uuid4, wrong_params, method):
    client.create_event(
        memoryId="mem-12345678",
        actorId="actor-12345678",
        sessionId="sess-12345678",
        payload=[{"conversational": {"content": {"text": "moto!"}, "role": "USER"}}],
        eventTimestamp=datetime(2026, 3, 11),
    )

    params = {
        "eventId": "11111111-1111-1111-1111-111111111111",
        "memoryId": "mem-12345678",
        "actorId": "actor-12345678",
        "sessionId": "sess-12345678",
    }

    params.update(wrong_params)

    with pytest.raises(ClientError) as e:
        method = getattr(client, method)
        method(**params)

    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"
