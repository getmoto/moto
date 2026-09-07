from moto.core.responses import ActionResult

from ._base_response import EC2BaseResponse


class TrafficMirrors(EC2BaseResponse):
    def create_traffic_mirror_filter(self) -> ActionResult:
        description = self._get_param("Description")
        tag_specifications = self._get_param("TagSpecifications")
        client_token = self._get_param("ClientToken")

        mirror_filter = self.ec2_backend.create_traffic_mirror_filter(
            description=description,
            tag_specifications=tag_specifications,
            client_token=client_token,
        )

        return ActionResult(
            {
                "TrafficMirrorFilter": mirror_filter.to_dict(),
                "ClientToken": mirror_filter.client_token,
            }
        )

    def create_traffic_mirror_target(self) -> ActionResult:
        network_interface_id = self._get_param("NetworkInterfaceId")
        network_load_balancer_arn = self._get_param("NetworkLoadBalancerArn")
        description = self._get_param("Description")
        tag_specifications = self._get_param("TagSpecifications")
        client_token = self._get_param("ClientToken")
        gateway_load_balancer_endpoint_id = self._get_param(
            "GatewayLoadBalancerEndpointId"
        )

        mirror_target = self.ec2_backend.create_traffic_mirror_target(
            network_interface_id=network_interface_id,
            network_load_balancer_arn=network_load_balancer_arn,
            description=description,
            tag_specifications=tag_specifications,
            client_token=client_token,
            gateway_load_balancer_endpoint_id=gateway_load_balancer_endpoint_id,
        )

        return ActionResult(
            {
                "TrafficMirrorTarget": mirror_target.to_dict(),
                "ClientToken": mirror_target.client_token,
            }
        )

    def describe_traffic_mirror_filters(self) -> ActionResult:
        traffic_mirror_filter_ids = self._get_param("TrafficMirrorFilterIds")
        filters = self._filters_from_querystring()

        mirror_filters = self.ec2_backend.describe_traffic_mirror_filters(
            traffic_mirror_filter_ids=traffic_mirror_filter_ids, filters=filters
        )

        return ActionResult({"TrafficMirrorFilters": mirror_filters})

    def describe_traffic_mirror_targets(self) -> ActionResult:
        traffic_mirror_target_ids = self._get_param("TrafficMirrorTargetIds")
        filters = self._filters_from_querystring()

        mirror_targets = self.ec2_backend.describe_traffic_mirror_targets(
            traffic_mirror_target_ids=traffic_mirror_target_ids, filters=filters
        )

        return ActionResult({"TrafficMirrorTargets": mirror_targets})

    def create_traffic_mirror_session(self) -> ActionResult:
        network_interface_id = self._get_param("NetworkInterfaceId")
        traffic_mirror_target_id = self._get_param("TrafficMirrorTargetId")
        traffic_mirror_filter_id = self._get_param("TrafficMirrorFilterId")
        session_number = self._get_int_param("SessionNumber")
        packet_length = self._get_int_param("PacketLength")
        virtual_network_id = self._get_int_param("VirtualNetworkId")
        description = self._get_param("Description")
        tag_specifications = self._get_param("TagSpecifications")
        client_token = self._get_param("ClientToken")

        mirror_session = self.ec2_backend.create_traffic_mirror_session(
            network_interface_id=network_interface_id,
            traffic_mirror_target_id=traffic_mirror_target_id,
            traffic_mirror_filter_id=traffic_mirror_filter_id,
            session_number=session_number,
            packet_length=packet_length,
            virtual_network_id=virtual_network_id,
            description=description,
            tag_specifications=tag_specifications,
            client_token=client_token,
        )

        return ActionResult(
            {
                "TrafficMirrorSession": mirror_session.to_dict(),
                "ClientToken": mirror_session.client_token,
            }
        )

    def describe_traffic_mirror_sessions(self) -> ActionResult:
        traffic_mirror_session_ids = self._get_param("TrafficMirrorSessionIds")
        filters = self._filters_from_querystring()

        mirror_sessions = self.ec2_backend.describe_traffic_mirror_sessions(
            traffic_mirror_session_ids=traffic_mirror_session_ids, filters=filters
        )

        return ActionResult({"TrafficMirrorSessions": mirror_sessions})

    def delete_traffic_mirror_session(self) -> ActionResult:
        traffic_mirror_session_id = self._get_param("TrafficMirrorSessionId")

        session_id = self.ec2_backend.delete_traffic_mirror_session(
            traffic_mirror_session_id=traffic_mirror_session_id
        )

        return ActionResult({"TrafficMirrorSessionId": session_id})

    def modify_traffic_mirror_session(self) -> ActionResult:
        traffic_mirror_session_id = self._get_param("TrafficMirrorSessionId")
        traffic_mirror_target_id = self._get_param("TrafficMirrorTargetId")
        traffic_mirror_filter_id = self._get_param("TrafficMirrorFilterId")
        packet_length = self._get_int_param("PacketLength")
        session_number = self._get_int_param("SessionNumber")
        virtual_network_id = self._get_int_param("VirtualNetworkId")
        description = self._get_param("Description")

        mirror_session = self.ec2_backend.modify_traffic_mirror_session(
            traffic_mirror_session_id=traffic_mirror_session_id,
            traffic_mirror_target_id=traffic_mirror_target_id,
            traffic_mirror_filter_id=traffic_mirror_filter_id,
            packet_length=packet_length,
            session_number=session_number,
            virtual_network_id=virtual_network_id,
            description=description,
        )

        return ActionResult({"TrafficMirrorSession": mirror_session.to_dict()})
