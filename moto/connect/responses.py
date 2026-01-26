"""Handles incoming connect requests, invokes methods, returns responses."""

import json
from typing import Any, Optional
from urllib.parse import unquote

from moto.core.responses import BaseResponse

from .models import ConnectBackend, connect_backends


class ConnectResponse(BaseResponse):
    """Handler for Connect requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="connect")

    @property
    def connect_backend(self) -> ConnectBackend:
        """Return backend instance specific for this region."""
        return connect_backends[self.current_account][self.region]

    def _get_instance_id(self) -> str:
        """Extract instance_id from request path params."""
        instance_id = self._get_param("InstanceId")
        return unquote(instance_id) if instance_id else ""

    def _get_param_case_insensitive(
        self, name: str, default: Optional[str] = None
    ) -> Optional[str]:
        value = self._get_param(name)
        if value is not None:
            return value
        if name and name[0].islower():
            alt_name = name[0].upper() + name[1:]
        elif name:
            alt_name = name[0].lower() + name[1:]
        else:
            return default
        value = self._get_param(alt_name)
        if value is not None:
            return value
        return default

    def _get_int_param_case_insensitive(
        self, name: str, default: Optional[int] = None
    ) -> Optional[int]:
        value = self._get_param_case_insensitive(name)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def associate_analytics_data_set(self) -> str:
        instance_id = self._get_instance_id()
        params = json.loads(self.body) if self.body else {}
        if "DataSetId" not in params:
            raise ValueError("DataSetId is required")
        data_set_id = str(params["DataSetId"])
        target_account_id = params.get("TargetAccountId")

        result = self.connect_backend.associate_analytics_data_set(
            instance_id=instance_id,
            data_set_id=data_set_id,
            target_account_id=target_account_id,
        )

        return json.dumps(result)

    def disassociate_analytics_data_set(self) -> str:
        instance_id = self._get_instance_id()
        params = json.loads(self.body) if self.body else {}
        if "DataSetId" not in params:
            raise ValueError("DataSetId is required")
        data_set_id = str(params["DataSetId"])

        self.connect_backend.disassociate_analytics_data_set(
            instance_id=instance_id,
            data_set_id=data_set_id,
        )

        return "{}"

    def list_analytics_data_associations(self) -> str:
        instance_id = self._get_instance_id()
        data_set_id = self._get_param_case_insensitive("DataSetId")
        max_results = self._get_int_param_case_insensitive("maxResults")
        next_token = self._get_param_case_insensitive("nextToken")

        results, token = self.connect_backend.list_analytics_data_associations(
            instance_id=instance_id,
            data_set_id=data_set_id,
            max_results=max_results,
            next_token=next_token,
        )

        response: dict[str, Any] = {"Results": results}
        if token:
            response["NextToken"] = token

        return json.dumps(response)

    def analytics_data_association(self) -> str:
        """Route analytics data association requests based on HTTP method."""
        if self.method == "PUT":
            return self.associate_analytics_data_set()
        elif self.method == "POST":
            return self.disassociate_analytics_data_set()
        else:
            return self.list_analytics_data_associations()

    def create_instance(self) -> str:
        params = json.loads(self.body) if self.body else {}
        if "IdentityManagementType" not in params:
            raise ValueError("IdentityManagementType is required")
        identity_management_type = str(params["IdentityManagementType"])
        instance_alias = params.get("InstanceAlias")
        inbound_calls_enabled = params.get("InboundCallsEnabled", False)
        outbound_calls_enabled = params.get("OutboundCallsEnabled", False)
        tags = params.get("Tags")

        result = self.connect_backend.create_instance(
            identity_management_type=identity_management_type,
            instance_alias=instance_alias,
            inbound_calls_enabled=inbound_calls_enabled,
            outbound_calls_enabled=outbound_calls_enabled,
            tags=tags,
        )

        return json.dumps(result)

    def describe_instance(self) -> str:
        instance_id = self._get_instance_id()

        instance = self.connect_backend.describe_instance(instance_id=instance_id)

        return json.dumps({"Instance": instance})

    def list_instances(self) -> str:
        max_results = self._get_int_param_case_insensitive("maxResults")
        next_token = self._get_param_case_insensitive("nextToken")

        results, token = self.connect_backend.list_instances(
            max_results=max_results,
            next_token=next_token,
        )

        response: dict[str, Any] = {"InstanceSummaryList": results}
        if token:
            response["NextToken"] = token

        return json.dumps(response)

    def delete_instance(self) -> str:
        instance_id = self._get_instance_id()

        self.connect_backend.delete_instance(instance_id=instance_id)

        return "{}"
