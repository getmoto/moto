from collections import OrderedDict
from uuid import uuid4

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict
from moto.mediaconnect.exceptions import NotFoundException


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
    def __init__(self, region_name=None):
        super().__init__()
        self.region_name = region_name
        self._flows = OrderedDict()
        self._resources = OrderedDict()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

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
        if isinstance(source, dict) and source.get("name"):
            source["sourceArn"] = "arn:aws:mediaconnect:source:{}".format(
                source["name"]
            )
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
        flow.description = "A Moto test flow"
        flow.egress_ip = "127.0.0.1"
        flow_id = uuid4().hex
        flow.flow_arn = "arn:aws:mediaconnect:flow:{}".format(flow_id)
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

    # add methods from here


mediaconnect_backends = BackendDict(MediaConnectBackend, "mediaconnect")
