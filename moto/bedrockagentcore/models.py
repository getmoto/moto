"""BedrockAgentCoreBackend class with methods for supported APIs."""

from typing import Any, Optional

from moto.bedrockagentcore.exceptions import (
    ResourceNotFoundException,
    ValidationException,
)
from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.utils import unix_time
from moto.moto_api._internal import mock_random
from moto.utilities.paginator import paginate


class Event(BaseModel):
    def __init__(
        self,
        memory_id: str,
        actor_id: str,
        region_name: str,
        account_id: str,
        session_id: str,
        event_timestamp: float,
        payload: list[dict[str, Any]],
        branch: Optional[dict[str, str]],
        client_token: Optional[str],
        metadata: Optional[dict[str, dict[str, str]]],
    ) -> None:
        self.region_name = region_name
        self.account_id = account_id
        self.event_id: str = str(mock_random.uuid4())
        self.memory_id = memory_id
        self.actor_id = actor_id
        self.session_id = session_id
        self.event_timestamp = event_timestamp
        self.created_at = unix_time()
        self.updated_at = unix_time()
        self.payload = payload
        self.branch = branch
        self.client_token = client_token
        self.metadata = metadata

    def to_dict(self, include_payloads: bool = True) -> dict[str, Any]:
        _dict = {
            "eventId": self.event_id,
            "memoryId": self.memory_id,
            "actorId": self.actor_id,
            "sessionId": self.session_id,
            "eventTimestamp": int(self.event_timestamp),
            "branch": self.branch or None,
            "clientToken": self.client_token,
            "metadata": self.metadata or None,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if include_payloads:
            _dict["payload"] = self.payload
        return _dict


class BedrockAgentCoreBackend(BaseBackend):
    """Implementation of BedrockAgentCoreBackend APIs.

    See: https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-agentcore.html

    """

    PAGINATION_MODEL = {
        "list_events": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "event_id",
        }
    }

    def __init__(self, region_name: str, account_id: str):
        # TODO: Actually we're not validating that the memory
        # exists as an AWS resources. This can be implemented
        # once this work is done: https://github.com/getmoto/moto/pull/9776
        super().__init__(region_name, account_id)
        self.events: dict[str, Event] = {}
        self.events_by_memory: dict[str, list[str]] = {}
        self.client_tokens: dict[str, str] = {}

    def create_event(
        self,
        memory_id: str,
        actor_id: str,
        session_id: str,
        event_timestamp: float,
        payload: list[dict[str, Any]],
        branch: Optional[dict[str, str]],
        client_token: Optional[str],
        metadata: Optional[dict[str, dict[str, str]]],
    ) -> Event:
        """Create an event and return the Event model"""
        existing_id = self.client_tokens.get(client_token)

        if existing_id:
            # AWS doc: If this token matches a previous request, AgentCore
            # ignores the request, but does not return an error.
            return self.events[existing_id]

        event = Event(
            memory_id=memory_id,
            actor_id=actor_id,
            region_name=self.region_name,
            account_id=self.account_id,
            session_id=session_id,
            event_timestamp=event_timestamp,
            payload=payload,
            branch=branch,
            client_token=client_token,
            metadata=metadata,
        )

        self.events[event.event_id] = event
        self.events_by_memory.setdefault(memory_id, []).append(event.event_id)
        self.client_tokens[event.client_token] = event.event_id
        return event

    def get_event(
        self, event_id: str, memory_id: str, actor_id: str, session_id: str
    ) -> Event:
        """
        Return a single event by its event_id.
        Raises ResourceNotFoundException if it does not exist.
        """
        event = self.events.get(event_id)
        if (
            not event
            or event.memory_id != memory_id
            or event.session_id != session_id
            or event.actor_id != actor_id
        ):
            raise ResourceNotFoundException(f"Event '{event_id}' not found")
        return event

    def _match_branch_filter(
        self, event: Event, branch_filter: Optional[dict[str, Any]]
    ) -> bool:
        """
        branch_filter:
          {
            "name": <required string>,
            "includeParentBranches": <bool>
          }
        Minimal impl: exact match on name.
        NOTE: We don't model parent branches yet; includeParentBranches is accepted but ignored.
        """
        if not branch_filter:
            return True

        name = branch_filter.get("name")
        if not isinstance(name, str) or not name:
            raise ValidationException(
                "filter.branch.name is required and must be a non-empty string"
            )

        ev_name = None
        if isinstance(event.branch, dict):
            ev_name = event.branch.get("name")

        return ev_name == name

    def _match_metadata_filters(
        self, event: Event, meta_filters: Optional[list[dict[str, Any]]]
    ) -> bool:
        """
        meta_filters is a list of expressions:
          {
            "left": { "metadataKey": "k" },
            "operator": "EQUALS_TO" | "EXISTS" | "NOT_EXISTS",
            "right": { "metadataValue": { "stringValue": "v" } }   # only for EQUALS_TO
          }
        All expressions are AND'ed.
        """
        if not meta_filters:
            return True

        ev_meta = event.metadata or {}

        for idx, expr in enumerate(meta_filters):
            if not isinstance(expr, dict):
                raise ValidationException(
                    f"filter.eventMetadata[{idx}] must be an object"
                )

            left = expr.get("left", {})
            operator = expr.get("operator")
            right = expr.get("right", {})

            key = left.get("metadataKey")
            if not isinstance(key, str) or not key:
                raise ValidationException(
                    f"filter.eventMetadata[{idx}].left.metadataKey is required"
                )

            operator = (operator or "").upper()
            if operator not in ("EQUALS_TO", "EXISTS", "NOT_EXISTS"):
                raise ValidationException(
                    f"filter.eventMetadata[{idx}].operator must be one of EQUALS_TO|EXISTS|NOT_EXISTS"
                )

            present = key in ev_meta

            if operator == "EXISTS":
                if not present:
                    return False
                continue

            if operator == "NOT_EXISTS":
                if present:
                    return False
                continue

            if not present:
                return False
            ev_val_wrapper = ev_meta.get(key) or {}
            ev_val = ev_val_wrapper.get("stringValue")

            right_val_wrapper = (right or {}).get("metadataValue") or {}
            right_val = right_val_wrapper.get("stringValue")

            if right_val is None:
                raise ValidationException(
                    f"filter.eventMetadata[{idx}].right.metadataValue.stringValue is required for EQUALS_TO"
                )

            if ev_val != right_val:
                return False

        return True

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_events(
        self,
        memory_id: str,
        session_id: str,
        actor_id: str,
        filter: Optional[dict[str, Any]] = None,
        includePayloads: bool = True,
    ) -> list[Event]:
        ids = list(self.events_by_memory.get(memory_id, []))
        items = [self.events[eid] for eid in ids]
        items = [
            e for e in items if e.session_id == session_id and e.actor_id == actor_id
        ]
        f_branch = None
        f_event_meta = None
        if filter:
            if "branch" in filter:
                f_branch = filter.get("branch")
            if "eventMetadata" in filter:
                f_event_meta = filter.get("eventMetadata")
                if not isinstance(f_event_meta, list):
                    raise ValidationException("filter.eventMetadata must be a list")

        filtered: list[Event] = []
        for event in items:
            if not self._match_branch_filter(event, f_branch):
                continue
            if not self._match_metadata_filters(event, f_event_meta):
                continue
            filtered.append(event)

        filtered.sort(key=lambda e: e.event_timestamp)
        return filtered

    def delete_event(
        self,
        memory_id: str,
        session_id: str,
        event_id: str,
        actor_id: str,
    ) -> str:
        event = self.events.get(event_id)
        if (
            not event
            or event.memory_id != memory_id
            or event.session_id != session_id
            or event.actor_id != actor_id
        ):
            raise ResourceNotFoundException(f"Event '{event_id}' not found")

        self.events.pop(event_id, None)

        mem_list = self.events_by_memory.get(event.memory_id, [])
        mem_list.remove(event_id)

        if not mem_list:
            self.events_by_memory.pop(event.memory_id, None)

        tokens_to_remove = [
            t for t, eid in self.client_tokens.items() if eid == event_id
        ]
        for t in tokens_to_remove:
            self.client_tokens.pop(t, None)

        return event_id


bedrockagentcore_backends = BackendDict(BedrockAgentCoreBackend, "bedrock")
