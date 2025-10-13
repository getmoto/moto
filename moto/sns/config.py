"""AWS Config integration for SNS resources."""

import json
from typing import Any, Dict, List, Optional, Tuple

from moto.core.common_models import ConfigQueryModel
from moto.sns import sns_backends
from moto.sns.models import SNSBackend


class SNSConfigQuery(ConfigQueryModel[SNSBackend]):
    """Config query model for SNS topics."""

    def list_config_service_resources(
        self,
        account_id: str,
        partition: str,
        resource_ids: Optional[List[str]],
        resource_name: Optional[str],
        limit: int,
        next_token: Optional[str],
        backend_region: Optional[str] = None,
        resource_region: Optional[str] = None,
        aggregator: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        if resource_ids and resource_name:
            match_found = False
            for resource_id in resource_ids:
                topic_name = resource_id.split(":")[-1]
                if topic_name == resource_name:
                    match_found = True
                    break
            if not match_found:
                return [], None

        region = resource_region or backend_region or "us-east-1"
        backend = self.backends[account_id][region]

        topics, new_token = backend.list_config_service_resources(
            resource_ids=resource_ids,
            resource_name=resource_name,
            limit=limit,
            next_token=next_token,
        )

        return topics, new_token

    def get_config_resource(
        self,
        account_id: str,
        partition: str,
        resource_id: str,
        resource_name: Optional[str] = None,
        backend_region: Optional[str] = None,
        resource_region: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        region = resource_region or backend_region or "us-east-1"
        backend = self.backends[account_id][region]

        config_data = backend.get_config_resource(resource_id)

        if not config_data:
            return None

        if resource_name and config_data.get("resourceName") != resource_name:
            return None

        if "configuration" in config_data and not isinstance(
            config_data["configuration"], str
        ):
            config_data["configuration"] = json.dumps(config_data["configuration"])

        if "supplementaryConfiguration" in config_data:
            for field, value in config_data["supplementaryConfiguration"].items():
                if not isinstance(value, str):
                    config_data["supplementaryConfiguration"][field] = json.dumps(value)

        return config_data


sns_config_query = SNSConfigQuery(sns_backends)
