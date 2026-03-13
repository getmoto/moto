import json
import re
from re import Match
from typing import cast

from moto.core.responses import BaseResponse

from .models import BedrockAgentCoreBackend, bedrockagentcore_backends

MEMORY_PATH_RE = re.compile(r"/memories/(?P<memory_id>[A-Za-z0-9\-_]+)/events")

GET_METHOD_RE = re.compile(
    r"/memories/(?P<memory_id>[^/]+)"
    r"/actor/(?P<actor_id>[^/]+)"
    r"/sessions/(?P<session_id>[^/]+)"
    r"/events/(?P<event_id>[^/]+)"
)

LIST_METHOD_RE = re.compile(
    r"/memories/(?P<memory_id>[^/]+)"
    r"/actor/(?P<actor_id>[^/]+)"
    r"/sessions/(?P<session_id>[^/]+)"
)


class BedrockAgentCoreResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="bedrock-agentcore")

    @property
    def backend(self) -> BedrockAgentCoreBackend:
        return bedrockagentcore_backends[self.current_account][self.region]

    def create_event(self) -> str:
        # Memory is not part of the body
        match = cast(Match[str], MEMORY_PATH_RE.match(self.path))
        memory_id = match.group("memory_id")
        params = json.loads(self.body)
        event = self.backend.create_event(
            memory_id=memory_id,
            actor_id=params.get("actorId"),
            session_id=params.get("sessionId"),
            event_timestamp=params.get("eventTimestamp"),
            payload=params.get("payload"),
            branch=params.get("branch"),
            client_token=params.get("clientToken"),
            metadata=params.get("metadata"),
        )
        return json.dumps({"event": event.to_dict()})

    def get_event(self) -> str:
        # Memory, event, actor and session are not part of the body
        match = cast(Match[str], GET_METHOD_RE.match(self.path))
        memory_id = match.group("memory_id")
        actor_id = match.group("actor_id")
        session_id = match.group("session_id")
        event_id = match.group("event_id")
        event = self.backend.get_event(
            event_id=event_id,
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
        )
        return json.dumps({"event": event.to_dict()})

    def list_events(self) -> str:
        # Memory, actor and session are not part of the body
        match = cast(Match[str], LIST_METHOD_RE.match(self.path))
        memory_id = match.group("memory_id")
        actor_id = match.group("actor_id")
        session_id = match.group("session_id")
        params = json.loads(self.body)
        events, next_token = self.backend.list_events(
            memory_id=memory_id,
            session_id=session_id,
            actor_id=actor_id,
            filter=params.get("filter"),
            max_results=params.get("maxResults"),
            next_token=params.get("nextToken"),
            includePayloads=params.get("includePayloads", True),
        )
        return json.dumps(
            {
                "events": [
                    e.to_dict(include_payloads=params.get("includePayloads", True))
                    for e in events
                ],
                "nextToken": next_token,
            }
        )

    def delete_event(self) -> str:
        # Memory, event, actor and session are not part of the body
        match = cast(Match[str], GET_METHOD_RE.match(self.path))
        memory_id = match.group("memory_id")
        actor_id = match.group("actor_id")
        session_id = match.group("session_id")
        event_id = match.group("event_id")
        result = self.backend.delete_event(
            memory_id=memory_id,
            session_id=session_id,
            event_id=event_id,
            actor_id=actor_id,
        )
        return json.dumps({"eventId": result})
