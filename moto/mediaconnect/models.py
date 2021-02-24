from __future__ import unicode_literals

from collections import OrderedDict
from uuid import uuid4

from boto3 import Session
from moto.core import BaseBackend, BaseModel
from moto.mediaconnect.exceptions import NotFoundException


class Flow(BaseModel):
    def __init__(self, *args, **kwargs):
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
    def __init__(self, *args, **kwargs):
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
        super(MediaConnectBackend, self).__init__()
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

    # add methods from here


mediaconnect_backends = {}
for region in Session().get_available_regions("mediaconnect"):
    mediaconnect_backends[region] = MediaConnectBackend()
for region in Session().get_available_regions(
    "mediaconnect", partition_name="aws-us-gov"
):
    mediaconnect_backends[region] = MediaConnectBackend()
for region in Session().get_available_regions("mediaconnect", partition_name="aws-cn"):
    mediaconnect_backends[region] = MediaConnectBackend()
