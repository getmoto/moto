import weakref
from collections import defaultdict
from moto.core import CloudFormationModel
from ..exceptions import (
    InvalidVPCPeeringConnectionIdError,
    InvalidVPCPeeringConnectionStateTransitionError,
    OperationNotPermitted2,
    OperationNotPermitted3,
)
from .core import TaggedEC2Resource
from ..utils import random_vpc_peering_connection_id


class PeeringConnectionStatus(object):
    def __init__(self, code="initiating-request", message=""):
        self.code = code
        self.message = message

    def deleted(self):
        self.code = "deleted"
        self.message = "Deleted by {deleter ID}"

    def initiating(self):
        self.code = "initiating-request"
        self.message = "Initiating Request to {accepter ID}"

    def pending(self):
        self.code = "pending-acceptance"
        self.message = "Pending Acceptance by {accepter ID}"

    def accept(self):
        self.code = "active"
        self.message = "Active"

    def reject(self):
        self.code = "rejected"
        self.message = "Inactive"


class VPCPeeringConnection(TaggedEC2Resource, CloudFormationModel):
    DEFAULT_OPTIONS = {
        "AllowEgressFromLocalClassicLinkToRemoteVpc": "false",
        "AllowEgressFromLocalVpcToRemoteClassicLink": "false",
        "AllowDnsResolutionFromRemoteVpc": "false",
    }

    def __init__(self, backend, vpc_pcx_id, vpc, peer_vpc, tags=None):
        self.id = vpc_pcx_id
        self.ec2_backend = backend
        self.vpc = vpc
        self.peer_vpc = peer_vpc
        self.requester_options = self.DEFAULT_OPTIONS.copy()
        self.accepter_options = self.DEFAULT_OPTIONS.copy()
        self.add_tags(tags or {})
        self._status = PeeringConnectionStatus()

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-vpcpeeringconnection.html
        return "AWS::EC2::VPCPeeringConnection"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        from ..models import ec2_backends

        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[account_id][region_name]
        vpc = ec2_backend.get_vpc(properties["VpcId"])
        peer_vpc = ec2_backend.get_vpc(properties["PeerVpcId"])

        vpc_pcx = ec2_backend.create_vpc_peering_connection(vpc, peer_vpc)

        return vpc_pcx

    @property
    def physical_resource_id(self):
        return self.id


class VPCPeeringConnectionBackend:
    # for cross region vpc reference
    vpc_pcx_refs = defaultdict(set)

    def __init__(self):
        self.vpc_pcxs = {}
        self.vpc_pcx_refs[self.__class__].add(weakref.ref(self))

    @classmethod
    def get_vpc_pcx_refs(cls):
        for inst_ref in cls.vpc_pcx_refs[cls]:
            inst = inst_ref()
            if inst is not None:
                yield inst

    def create_vpc_peering_connection(self, vpc, peer_vpc, tags=None):
        vpc_pcx_id = random_vpc_peering_connection_id()
        vpc_pcx = VPCPeeringConnection(self, vpc_pcx_id, vpc, peer_vpc, tags)
        vpc_pcx._status.pending()
        self.vpc_pcxs[vpc_pcx_id] = vpc_pcx
        # insert cross region peering info
        if vpc.ec2_backend.region_name != peer_vpc.ec2_backend.region_name:
            for vpc_pcx_cx in peer_vpc.ec2_backend.get_vpc_pcx_refs():
                if vpc_pcx_cx.region_name == peer_vpc.ec2_backend.region_name:
                    vpc_pcx_cx.vpc_pcxs[vpc_pcx_id] = vpc_pcx
        return vpc_pcx

    def describe_vpc_peering_connections(self, vpc_peering_ids=None):
        all_pcxs = self.vpc_pcxs.copy().values()
        if vpc_peering_ids:
            return [pcx for pcx in all_pcxs if pcx.id in vpc_peering_ids]
        return all_pcxs

    def get_vpc_peering_connection(self, vpc_pcx_id):
        if vpc_pcx_id not in self.vpc_pcxs:
            raise InvalidVPCPeeringConnectionIdError(vpc_pcx_id)
        return self.vpc_pcxs.get(vpc_pcx_id)

    def delete_vpc_peering_connection(self, vpc_pcx_id):
        deleted = self.get_vpc_peering_connection(vpc_pcx_id)
        deleted._status.deleted()
        return deleted

    def accept_vpc_peering_connection(self, vpc_pcx_id):
        vpc_pcx = self.get_vpc_peering_connection(vpc_pcx_id)
        # if cross region need accepter from another region
        pcx_req_region = vpc_pcx.vpc.ec2_backend.region_name
        pcx_acp_region = vpc_pcx.peer_vpc.ec2_backend.region_name
        if pcx_req_region != pcx_acp_region and self.region_name == pcx_req_region:
            raise OperationNotPermitted2(self.region_name, vpc_pcx.id, pcx_acp_region)
        if vpc_pcx._status.code != "pending-acceptance":
            raise InvalidVPCPeeringConnectionStateTransitionError(vpc_pcx.id)
        vpc_pcx._status.accept()
        return vpc_pcx

    def reject_vpc_peering_connection(self, vpc_pcx_id):
        vpc_pcx = self.get_vpc_peering_connection(vpc_pcx_id)
        # if cross region need accepter from another region
        pcx_req_region = vpc_pcx.vpc.ec2_backend.region_name
        pcx_acp_region = vpc_pcx.peer_vpc.ec2_backend.region_name
        if pcx_req_region != pcx_acp_region and self.region_name == pcx_req_region:
            raise OperationNotPermitted3(self.region_name, vpc_pcx.id, pcx_acp_region)
        if vpc_pcx._status.code != "pending-acceptance":
            raise InvalidVPCPeeringConnectionStateTransitionError(vpc_pcx.id)
        vpc_pcx._status.reject()
        return vpc_pcx

    def modify_vpc_peering_connection_options(
        self, vpc_pcx_id, accepter_options=None, requester_options=None
    ):
        vpc_pcx = self.get_vpc_peering_connection(vpc_pcx_id)
        if not vpc_pcx:
            raise InvalidVPCPeeringConnectionIdError(vpc_pcx_id)
        # TODO: check if actual vpc has this options enabled
        if accepter_options:
            vpc_pcx.accepter_options.update(accepter_options)
        if requester_options:
            vpc_pcx.requester_options.update(requester_options)
