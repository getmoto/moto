"""Handles incoming bedrockagentcore requests, invokes methods, returns responses."""

from moto.core.responses import ActionResult, BaseResponse

from .models import BedrockAgentCoreBackend, bedrockagentcore_backends


class BedrockAgentCoreResponse(BaseResponse):
    """Handler for BedrockAgentCore requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="bedrock-agentcore")
        self.automated_parameter_parsing = True

    @property
    def backend(self) -> BedrockAgentCoreBackend:
        return bedrockagentcore_backends[self.current_account][self.region]

    def create_event(self) -> ActionResult:
        params = self._get_params()
        event = self.backend.create_event(
            memory_id=params["memoryId"],
            actor_id=params.get("actorId"),
            session_id=params.get("sessionId"),
            event_timestamp=params.get("eventTimestamp"),
            payload=params.get("payload"),
            branch=params.get("branch"),
            metadata=params.get("metadata"),
        )
        return ActionResult({"event": event.to_dict()})

    def get_event(self) -> ActionResult:
        params = self._get_params()
        event = self.backend.get_event(
            memory_id=params["memoryId"],
            actor_id=params["actorId"],
            session_id=params["sessionId"],
            event_id=params["eventId"],
        )
        return ActionResult({"event": event.to_dict()})

    def list_events(self) -> ActionResult:
        params = self._get_params()
        include_payloads = params.get("includePayloads", False)
        events = self.backend.list_events(
            memory_id=params["memoryId"],
            actor_id=params["actorId"],
            session_id=params["sessionId"],
            max_results=params.get("maxResults"),
        )
        return ActionResult(
            {
                "events": [e.to_dict(include_payload=include_payloads) for e in events],
                "nextToken": None,
            }
        )

    def delete_event(self) -> ActionResult:
        params = self._get_params()
        event_id = self.backend.delete_event(
            memory_id=params["memoryId"],
            actor_id=params["actorId"],
            session_id=params["sessionId"],
            event_id=params["eventId"],
        )
        return ActionResult({"eventId": event_id})
