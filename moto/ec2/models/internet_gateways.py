from moto.core import CloudFormationModel
from .core import TaggedEC2Resource

from ..exceptions import (
    InvalidVPCIdError,
    GatewayNotAttachedError,
    DependencyViolationError,
    InvalidInternetGatewayIdError,
    InvalidGatewayIDError,
    ResourceAlreadyAssociatedError,
)
from .vpn_gateway import VPCGatewayAttachment
from ..utils import (
    filter_internet_gateways,
    random_egress_only_internet_gateway_id,
    random_internet_gateway_id,
)


class EgressOnlyInternetGateway(TaggedEC2Resource):
    def __init__(self, ec2_backend, vpc_id, tags=None):
        self.id = random_egress_only_internet_gateway_id()
        self.ec2_backend = ec2_backend
        self.vpc_id = vpc_id
        self.state = "attached"
        self.add_tags(tags or {})

    @property
    def physical_resource_id(self):
        return self.id


class EgressOnlyInternetGatewayBackend:
    def __init__(self):
        self.egress_only_internet_gateway_backend = {}

    def create_egress_only_internet_gateway(self, vpc_id, tags=None):
        vpc = self.get_vpc(vpc_id)
        if not vpc:
            raise InvalidVPCIdError(vpc_id)
        egress_only_igw = EgressOnlyInternetGateway(self, vpc_id, tags)
        self.egress_only_internet_gateway_backend[egress_only_igw.id] = egress_only_igw
        return egress_only_igw

    def describe_egress_only_internet_gateways(self, ids=None):
        """
        The Filters-argument is not yet supported
        """
        egress_only_igws = list(self.egress_only_internet_gateway_backend.values())

        if ids:
            egress_only_igws = [
                egress_only_igw
                for egress_only_igw in egress_only_igws
                if egress_only_igw.id in ids
            ]
        return egress_only_igws

    def delete_egress_only_internet_gateway(self, gateway_id):
        egress_only_igw = self.egress_only_internet_gateway_backend.get(gateway_id)
        if not egress_only_igw:
            raise InvalidGatewayIDError(gateway_id)
        if egress_only_igw:
            self.egress_only_internet_gateway_backend.pop(gateway_id)

    def get_egress_only_igw(self, gateway_id):
        egress_only_igw = self.egress_only_internet_gateway_backend.get(
            gateway_id, None
        )
        if not egress_only_igw:
            raise InvalidGatewayIDError(gateway_id)
        return egress_only_igw


class InternetGateway(TaggedEC2Resource, CloudFormationModel):
    def __init__(self, ec2_backend):
        self.ec2_backend = ec2_backend
        self.id = random_internet_gateway_id()
        self.vpc = None

    @property
    def owner_id(self):
        return self.ec2_backend.account_id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-internetgateway.html
        return "AWS::EC2::InternetGateway"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        from ..models import ec2_backends

        ec2_backend = ec2_backends[account_id][region_name]
        return ec2_backend.create_internet_gateway()

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def attachment_state(self):
        if self.vpc:
            return "available"
        else:
            return "detached"


class InternetGatewayBackend:
    def __init__(self):
        self.internet_gateways = {}

    def create_internet_gateway(self, tags=None):
        igw = InternetGateway(self)
        for tag in tags or []:
            igw.add_tag(tag.get("Key"), tag.get("Value"))
        self.internet_gateways[igw.id] = igw
        return igw

    def describe_internet_gateways(self, internet_gateway_ids=None, filters=None):
        igws = []
        if internet_gateway_ids is None:
            igws = self.internet_gateways.values()
        else:
            for igw_id in internet_gateway_ids:
                if igw_id in self.internet_gateways:
                    igws.append(self.internet_gateways[igw_id])
                else:
                    raise InvalidInternetGatewayIdError(igw_id)
        if filters is not None:
            igws = filter_internet_gateways(igws, filters)
        return igws

    def delete_internet_gateway(self, internet_gateway_id):
        igw = self.get_internet_gateway(internet_gateway_id)
        if igw.vpc:
            raise DependencyViolationError(
                f"{internet_gateway_id} is being utilized by {igw.vpc.id}"
            )
        self.internet_gateways.pop(internet_gateway_id)
        return True

    def detach_internet_gateway(self, internet_gateway_id, vpc_id):
        igw = self.get_internet_gateway(internet_gateway_id)
        if not igw.vpc or igw.vpc.id != vpc_id:
            raise GatewayNotAttachedError(internet_gateway_id, vpc_id)
        igw.vpc = None
        return True

    def attach_internet_gateway(self, internet_gateway_id, vpc_id):
        igw = self.get_internet_gateway(internet_gateway_id)
        if igw.vpc:
            raise ResourceAlreadyAssociatedError(internet_gateway_id)
        vpc = self.get_vpc(vpc_id)
        igw.vpc = vpc
        return VPCGatewayAttachment(gateway_id=internet_gateway_id, vpc_id=vpc_id)

    def get_internet_gateway(self, internet_gateway_id):
        igw_ids = [internet_gateway_id]
        return self.describe_internet_gateways(internet_gateway_ids=igw_ids)[0]
