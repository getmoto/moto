from typing import Any, Optional

from moto.utilities.tagging_service import TaggingService
from moto.utilities.utils import filter_resources

from ..exceptions import InvalidInputError
from ..utils import (
    convert_tag_spec,
    random_traffic_mirror_filter_id,
    random_traffic_mirror_target_id,
)
from .core import TaggedEC2Resource


class TrafficMirrorFilter(TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend: Any,
        description: Optional[str],
        tag_specifications: Optional[list[dict[str, Any]]],
        dry_run: Optional[bool],
        client_token: Optional[str],
    ):
        self.ec2_backend = ec2_backend
        self.id = random_traffic_mirror_filter_id()

        self.description = description
        self.dry_run = dry_run
        self.client_token = client_token

        self.tags = []
        if tag_specifications:
            tag_spec = convert_tag_spec(tag_specifications)
            self.add_tags(tag_spec.get("traffic-mirror-filter", {}))
            self.tags = self.get_tags()

    @property
    def owner_id(self) -> str:
        return self.ec2_backend.account_id

    @property
    def arn(self) -> str:
        return f"arn:{self.ec2_backend.partition}:ec2:{self.ec2_backend.region_name}:{self.ec2_backend.account_id}:traffic-mirror-filter/{self.id}"

    def to_dict(self) -> dict[str, Any]:
        traffic_mirror_filter = {
            "TrafficMirrorFilterId": self.id,
            "IngressFilterRules": [],
            "EgressFilterRules": [],
            "NetworkServices": [],
            "Description": self.description,
            "Tags": self.tags or [],
        }

        return traffic_mirror_filter


class TrafficMirrorTarget(TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend: Any,
        network_interface_id: Optional[str],
        network_load_balancer_arn: Optional[str],
        description: Optional[str],
        tag_specifications: Optional[list[dict[str, Any]]],
        dry_run: Optional[bool],
        client_token: Optional[str],
        gateway_load_balancer_endpoint_id: Optional[str],
    ):
        self.ec2_backend = ec2_backend
        self.id = random_traffic_mirror_target_id()
        self.type = self._determine_traffic_mirror_target_type(
            {
                "NetworkInterfaceId": network_interface_id,
                "NetworkLoadBalancerArn": network_load_balancer_arn,
                "GatewayLoadBalancerEndpointId": gateway_load_balancer_endpoint_id,
            }
        )

        self.network_interface_id = network_interface_id
        self.network_load_balancer_arn = network_load_balancer_arn
        self.description = description
        self.dry_run = dry_run
        self.client_token = client_token
        self.gateway_load_balancer_endpoint_id = gateway_load_balancer_endpoint_id

        self.tags = []
        if tag_specifications:
            tag_spec = convert_tag_spec(tag_specifications)
            self.add_tags(tag_spec.get("traffic-mirror-target", {}))
            self.tags = self.get_tags()

    @property
    def owner_id(self) -> str:
        return self.ec2_backend.account_id

    @property
    def arn(self) -> str:
        return f"arn:{self.ec2_backend.partition}:ec2:{self.ec2_backend.region_name}:{self.ec2_backend.account_id}:traffic-mirror-target/{self.id}"

    def to_dict(self) -> dict[str, Any]:
        traffic_mirror_target = {
            "TrafficMirrorTargetId": self.id,
            "NetworkInterfaceId": self.network_interface_id,
            "NetworkLoadBalancerArn": self.network_load_balancer_arn,
            "Type": self.type,
            "Description": self.description,
            "OwnerId": self.owner_id,
            "Tags": self.tags or [],
            "GatewayLoadBalancerEndpointId": self.gateway_load_balancer_endpoint_id,
        }

        return traffic_mirror_target

    @staticmethod
    def _determine_traffic_mirror_target_type(
        values: dict[str, Optional[str]],
    ) -> Optional[str]:
        target_fields = {
            "NetworkInterfaceId": "network-interface",
            "NetworkLoadBalancerArn": "network-load-balancer",
            "GatewayLoadBalancerEndpointId": "gateway-load-balancer-endpoint",
        }

        present = [field for field, val in values.items() if val]

        if len(present) == 1:
            return target_fields[present[0]]

        raise InvalidInputError(
            "Invalid number of inputs. Only 1 of NetworkInterfaceId, "
            "NetworkLoadBalancerArn or GatewayLoadBalancerEndpointId required."
        )


class TrafficMirrorsBackend:
    def __init__(self) -> None:
        self.traffic_mirror_filters: dict[str, TrafficMirrorFilter] = {}
        self.traffic_mirror_targets: dict[str, TrafficMirrorTarget] = {}
        self.tagger = TaggingService()

    def create_traffic_mirror_filter(
        self,
        description: Optional[str],
        tag_specifications: Optional[list[dict[str, Any]]],
        dry_run: Optional[bool],
        client_token: Optional[str],
    ) -> TrafficMirrorFilter:
        mirror_filter = TrafficMirrorFilter(
            self, description, tag_specifications, dry_run, client_token
        )
        self.traffic_mirror_filters[mirror_filter.id] = mirror_filter

        return mirror_filter

    def create_traffic_mirror_target(
        self,
        network_interface_id: Optional[str],
        network_load_balancer_arn: Optional[str],
        description: Optional[str],
        tag_specifications: Optional[list[dict[str, Any]]],
        dry_run: Optional[bool],
        client_token: Optional[str],
        gateway_load_balancer_endpoint_id: Optional[str],
    ) -> TrafficMirrorTarget:
        mirror_target = TrafficMirrorTarget(
            self,
            network_interface_id,
            network_load_balancer_arn,
            description,
            tag_specifications,
            dry_run,
            client_token,
            gateway_load_balancer_endpoint_id,
        )

        self.traffic_mirror_targets[mirror_target.id] = mirror_target
        return mirror_target

    def describe_traffic_mirror_filters(
        self,
        traffic_mirror_filter_ids: Optional[list[str]],
        filters: Optional[list[Any]],
    ) -> list[TrafficMirrorFilter]:
        traffic_mirror_filters = list(self.traffic_mirror_filters.values())

        if traffic_mirror_filter_ids:
            traffic_mirror_filters = [
                item
                for item in traffic_mirror_filters
                if item.id in traffic_mirror_filter_ids
            ]

        attr_pairs = (
            ("traffic-mirror-filter-id", "id"),
            ("description", "description"),
        )

        result = traffic_mirror_filters
        if filters:
            result = filter_resources(traffic_mirror_filters, filters, attr_pairs)

        return result

    def describe_traffic_mirror_targets(
        self,
        traffic_mirror_target_ids: Optional[list[str]],
        filters: Optional[list[Any]],
    ) -> list[TrafficMirrorTarget]:
        traffic_mirror_targets = list(self.traffic_mirror_targets.values())

        if traffic_mirror_target_ids:
            traffic_mirror_targets = [
                item
                for item in traffic_mirror_targets
                if item.id in traffic_mirror_target_ids
            ]

        attr_pairs = (
            ("traffic-mirror-target-id", "id"),
            ("description", "description"),
            ("network-load-balancer-arn", "network_load_balancer_arn"),
            ("owner-id", "owner_id"),
            ("network-interface-id", "network_interface_id"),
        )

        result = traffic_mirror_targets
        if filters:
            result = filter_resources(traffic_mirror_targets, filters, attr_pairs)

        return result
