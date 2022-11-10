from collections import OrderedDict

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict
from moto.mediaconnect.exceptions import NotFoundException
from moto.moto_api._internal import mock_random as random


class Flow(BaseModel):
    def __init__(self, **kwargs):
        self.availability_zone = kwargs.get("availability_zone")
        self.entitlements = kwargs.get("entitlements", [])
        self.name = kwargs.get("name")
        self.outputs = kwargs.get("outputs", [])
        self.source = kwargs.get("source", {})
        self.source_failover_config = kwargs.get("source_failover_config", {})
        self.sources = kwargs.get("sources", [])
        self.vpc_interfaces = kwargs.get("vpc_interfaces", [])
        self.status = "STANDBY"  # one of 'STANDBY'|'ACTIVE'|'UPDATING'|'DELETING'|'STARTING'|'STOPPING'|'ERROR'
        self._previous_status = None
        self.description = None
        self.flow_arn = None
        self.egress_ip = None
        if self.source and not self.sources:
            self.sources = [
                self.source,
            ]

    def to_dict(self, include=None):
        data = {
            "availabilityZone": self.availability_zone,
            "description": self.description,
            "egressIp": self.egress_ip,
            "entitlements": self.entitlements,
            "flowArn": self.flow_arn,
            "name": self.name,
            "outputs": self.outputs,
            "source": self.source,
            "sourceFailoverConfig": self.source_failover_config,
            "sources": self.sources,
            "status": self.status,
            "vpcInterfaces": self.vpc_interfaces,
        }
        if include:
            new_data = {k: v for k, v in data.items() if k in include}
            if "sourceType" in include:
                new_data["sourceType"] = "OWNED"
            return new_data
        return data

    def resolve_transient_states(self):
        if self.status in ["STARTING"]:
            self.status = "ACTIVE"
        if self.status in ["STOPPING"]:
            self.status = "STANDBY"
        if self.status in ["UPDATING"]:
            self.status = self._previous_status
            self._previous_status = None


class Resource(BaseModel):
    def __init__(self, **kwargs):
        self.resource_arn = kwargs.get("resource_arn")
        self.tags = OrderedDict()

    def to_dict(self):
        data = {
            "resourceArn": self.resource_arn,
            "tags": self.tags,
        }
        return data


class MediaConnectBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self._flows = OrderedDict()
        self._resources = OrderedDict()

    def _add_source_details(self, source, flow_id, ingest_ip="127.0.0.1"):
        if source:
            source["sourceArn"] = (
                f"arn:aws:mediaconnect:{self.region_name}:{self.account_id}:source"
                f":{flow_id}:{source['name']}"
            )
            if not source.get("entitlementArn"):
                source["ingestIp"] = ingest_ip

    def _add_entitlement_details(self, entitlement, entitlement_id):
        if entitlement:
            entitlement["entitlementArn"] = (
                f"arn:aws:mediaconnect:{self.region_name}"
                f":{self.account_id}:entitlement:{entitlement_id}"
                f":{entitlement['name']}"
            )

    def _create_flow_add_details(self, flow):
        flow_id = random.uuid4().hex

        flow.description = "A Moto test flow"
        flow.egress_ip = "127.0.0.1"
        flow.flow_arn = f"arn:aws:mediaconnect:{self.region_name}:{self.account_id}:flow:{flow_id}:{flow.name}"

        for index, _source in enumerate(flow.sources):
            self._add_source_details(_source, flow_id, f"127.0.0.{index}")

        for index, output in enumerate(flow.outputs or []):
            if output.get("protocol") in ["srt-listener", "zixi-pull"]:
                output["listenerAddress"] = f"{index}.0.0.0"
            output_id = random.uuid4().hex
            arn = (
                f"arn:aws:mediaconnect:{self.region_name}"
                f":{self.account_id}:output:{output_id}:{output['name']}"
            )
            output["outputArn"] = arn

        for _, entitlement in enumerate(flow.entitlements):
            entitlement_id = random.uuid4().hex
            self._add_entitlement_details(entitlement, entitlement_id)

    def create_flow(
        self,
        availability_zone,
        entitlements,
        name,
        outputs,
        source,
        source_failover_config,
        sources,
        vpc_interfaces,
    ):
        flow = Flow(
            availability_zone=availability_zone,
            entitlements=entitlements,
            name=name,
            outputs=outputs,
            source=source,
            source_failover_config=source_failover_config,
            sources=sources,
            vpc_interfaces=vpc_interfaces,
        )
        self._create_flow_add_details(flow)
        self._flows[flow.flow_arn] = flow
        return flow

    def list_flows(self, max_results, next_token):
        flows = list(self._flows.values())
        if max_results is not None:
            flows = flows[:max_results]
        response_flows = [
            fl.to_dict(
                include=[
                    "availabilityZone",
                    "description",
                    "flowArn",
                    "name",
                    "sourceType",
                    "status",
                ]
            )
            for fl in flows
        ]
        return response_flows, next_token

    def describe_flow(self, flow_arn=None):
        messages = {}
        if flow_arn in self._flows:
            flow = self._flows[flow_arn]
            flow.resolve_transient_states()
        else:
            raise NotFoundException(message="Flow not found.")
        return flow.to_dict(), messages

    def delete_flow(self, flow_arn):
        if flow_arn in self._flows:
            flow = self._flows[flow_arn]
            del self._flows[flow_arn]
        else:
            raise NotFoundException(message="Flow not found.")
        return flow_arn, flow.status

    def start_flow(self, flow_arn):
        if flow_arn in self._flows:
            flow = self._flows[flow_arn]
            flow.status = "STARTING"
        else:
            raise NotFoundException(message="Flow not found.")
        return flow_arn, flow.status

    def stop_flow(self, flow_arn):
        if flow_arn in self._flows:
            flow = self._flows[flow_arn]
            flow.status = "STOPPING"
        else:
            raise NotFoundException(message="Flow not found.")
        return flow_arn, flow.status

    def tag_resource(self, resource_arn, tags):
        if resource_arn in self._resources:
            resource = self._resources[resource_arn]
        else:
            resource = Resource(resource_arn=resource_arn)
        resource.tags.update(tags)
        self._resources[resource_arn] = resource
        return None

    def list_tags_for_resource(self, resource_arn):
        if resource_arn in self._resources:
            resource = self._resources[resource_arn]
        else:
            raise NotFoundException(message="Resource not found.")
        return resource.tags

    def add_flow_vpc_interfaces(self, flow_arn, vpc_interfaces):
        if flow_arn in self._flows:
            flow = self._flows[flow_arn]
            flow.vpc_interfaces = vpc_interfaces
        else:
            raise NotFoundException(
                message="flow with arn={} not found".format(flow_arn)
            )
        return flow_arn, flow.vpc_interfaces

    def add_flow_outputs(self, flow_arn, outputs):
        if flow_arn in self._flows:
            flow = self._flows[flow_arn]
            flow.outputs = outputs
        else:
            raise NotFoundException(
                message="flow with arn={} not found".format(flow_arn)
            )
        return flow_arn, flow.outputs

    def remove_flow_vpc_interface(self, flow_arn, vpc_interface_name):
        if flow_arn in self._flows:
            flow = self._flows[flow_arn]
            flow.vpc_interfaces = [
                vpc_interface
                for vpc_interface in self._flows[flow_arn].vpc_interfaces
                if vpc_interface["name"] != vpc_interface_name
            ]
        else:
            raise NotFoundException(
                message="flow with arn={} not found".format(flow_arn)
            )
        return flow_arn, vpc_interface_name

    def remove_flow_output(self, flow_arn, output_name):
        if flow_arn in self._flows:
            flow = self._flows[flow_arn]
            flow.outputs = [
                output
                for output in self._flows[flow_arn].outputs
                if output["name"] != output_name
            ]
        else:
            raise NotFoundException(
                message="flow with arn={} not found".format(flow_arn)
            )
        return flow_arn, output_name

    def update_flow_output(
        self,
        flow_arn,
        output_arn,
        cidr_allow_list,
        description,
        destination,
        encryption,
        max_latency,
        media_stream_output_configuration,
        min_latency,
        port,
        protocol,
        remote_id,
        sender_control_port,
        sender_ip_address,
        smoothing_latency,
        stream_id,
        vpc_interface_attachment,
    ):
        if flow_arn not in self._flows:
            raise NotFoundException(
                message="flow with arn={} not found".format(flow_arn)
            )
        flow = self._flows[flow_arn]
        for output in flow.outputs:
            if output["outputArn"] == output_arn:
                output["cidrAllowList"] = cidr_allow_list
                output["description"] = description
                output["destination"] = destination
                output["encryption"] = encryption
                output["maxLatency"] = max_latency
                output[
                    "mediaStreamOutputConfiguration"
                ] = media_stream_output_configuration
                output["minLatency"] = min_latency
                output["port"] = port
                output["protocol"] = protocol
                output["remoteId"] = remote_id
                output["senderControlPort"] = sender_control_port
                output["senderIpAddress"] = sender_ip_address
                output["smoothingLatency"] = smoothing_latency
                output["streamId"] = stream_id
                output["vpcInterfaceAttachment"] = vpc_interface_attachment
                return flow_arn, output
        raise NotFoundException(
            message="output with arn={} not found".format(output_arn)
        )

    def add_flow_sources(self, flow_arn, sources):
        if flow_arn not in self._flows:
            raise NotFoundException(
                message="flow with arn={} not found".format(flow_arn)
            )
        flow = self._flows[flow_arn]
        for source in sources:
            source_id = random.uuid4().hex
            name = source["name"]
            arn = f"arn:aws:mediaconnect:{self.region_name}:{self.account_id}:source:{source_id}:{name}"
            source["sourceArn"] = arn
        flow.sources = sources
        return flow_arn, sources

    def update_flow_source(
        self,
        flow_arn,
        source_arn,
        decryption,
        description,
        entitlement_arn,
        ingest_port,
        max_bitrate,
        max_latency,
        max_sync_buffer,
        media_stream_source_configurations,
        min_latency,
        protocol,
        sender_control_port,
        sender_ip_address,
        stream_id,
        vpc_interface_name,
        whitelist_cidr,
    ):
        if flow_arn not in self._flows:
            raise NotFoundException(
                message="flow with arn={} not found".format(flow_arn)
            )
        flow = self._flows[flow_arn]
        source = next(
            iter(
                [source for source in flow.sources if source["sourceArn"] == source_arn]
            ),
            {},
        )
        if source:
            source["decryption"] = decryption
            source["description"] = description
            source["entitlementArn"] = entitlement_arn
            source["ingestPort"] = ingest_port
            source["maxBitrate"] = max_bitrate
            source["maxLatency"] = max_latency
            source["maxSyncBuffer"] = max_sync_buffer
            source[
                "mediaStreamSourceConfigurations"
            ] = media_stream_source_configurations
            source["minLatency"] = min_latency
            source["protocol"] = protocol
            source["senderControlPort"] = sender_control_port
            source["senderIpAddress"] = sender_ip_address
            source["streamId"] = stream_id
            source["vpcInterfaceName"] = vpc_interface_name
            source["whitelistCidr"] = whitelist_cidr
        return flow_arn, source

    def grant_flow_entitlements(
        self,
        flow_arn,
        entitlements,
    ):
        if flow_arn not in self._flows:
            raise NotFoundException(
                message="flow with arn={} not found".format(flow_arn)
            )
        flow = self._flows[flow_arn]
        for entitlement in entitlements:
            entitlement_id = random.uuid4().hex
            name = entitlement["name"]
            arn = f"arn:aws:mediaconnect:{self.region_name}:{self.account_id}:entitlement:{entitlement_id}:{name}"
            entitlement["entitlementArn"] = arn

        flow.entitlements += entitlements
        return flow_arn, entitlements

    def revoke_flow_entitlement(self, flow_arn, entitlement_arn):
        if flow_arn not in self._flows:
            raise NotFoundException(
                message="flow with arn={} not found".format(flow_arn)
            )
        flow = self._flows[flow_arn]
        for entitlement in flow.entitlements:
            if entitlement_arn == entitlement["entitlementArn"]:
                flow.entitlements.remove(entitlement)
                return flow_arn, entitlement_arn
        raise NotFoundException(
            message="entitlement with arn={} not found".format(entitlement_arn)
        )

    def update_flow_entitlement(
        self,
        flow_arn,
        entitlement_arn,
        description,
        encryption,
        entitlement_status,
        name,
        subscribers,
    ):
        if flow_arn not in self._flows:
            raise NotFoundException(
                message="flow with arn={} not found".format(flow_arn)
            )
        flow = self._flows[flow_arn]
        for entitlement in flow.entitlements:
            if entitlement_arn == entitlement["entitlementArn"]:
                entitlement["description"] = description
                entitlement["encryption"] = encryption
                entitlement["entitlementStatus"] = entitlement_status
                entitlement["name"] = name
                entitlement["subscribers"] = subscribers
                return flow_arn, entitlement
        raise NotFoundException(
            message="entitlement with arn={} not found".format(entitlement_arn)
        )

        # add methods from here


mediaconnect_backends = BackendDict(MediaConnectBackend, "mediaconnect")
