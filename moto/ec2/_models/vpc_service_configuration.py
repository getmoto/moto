from moto.core.models import CloudFormationModel
from moto.core.utils import get_random_hex
from .core import TaggedEC2Resource
from ..exceptions import UnknownVpcEndpointService


class VPCServiceConfiguration(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self, load_balancer, region, acceptance_required, private_dns_name, ec2_backend
    ):
        self.id = f"vpce-svc-{get_random_hex(length=17)}"
        self.service_name = f"com.amazonaws.vpce.{region}.{self.id}"
        self.service_state = "Available"

        self.availability_zones = [s.availability_zone for s in load_balancer.subnets]

        if load_balancer.loadbalancer_type == "network":
            self.service_type = "Interface"
            self.gateway_load_balancer_arns = None
            self.network_load_balancer_arns = load_balancer.arn
        else:
            self.service_type = "Gateway"
            self.gateway_load_balancer_arns = load_balancer.arn
            self.network_load_balancer_arns = None

        self.acceptance_required = acceptance_required
        self.manages_vpc_endpoints = False
        self.private_dns_name = private_dns_name
        self.endpoint_dns_name = f"{self.id}.{region}.vpce.amazonaws.com"

        self.principals = []
        self.ec2_backend = ec2_backend


class VPCServiceConfigurationBackend(object):
    def __init__(self):
        self.configurations = {}
        super().__init__()

    @property
    def elbv2_backend(self):
        from moto.elbv2.models import elbv2_backends

        return elbv2_backends[self.region_name]

    def create_vpc_endpoint_service_configuration(
        self, lb_arns, acceptance_required, private_dns_name, tags
    ):
        lbs = self.elbv2_backend.describe_load_balancers(arns=lb_arns, names=None)
        config = VPCServiceConfiguration(
            load_balancer=lbs[0],
            region=self.region_name,
            acceptance_required=acceptance_required,
            private_dns_name=private_dns_name,
            ec2_backend=self,
        )
        for tag in tags or []:
            tag_key = tag.get("Key")
            tag_value = tag.get("Value")
            config.add_tag(tag_key, tag_value)

        self.configurations[config.id] = config
        return config

    def describe_vpc_endpoint_service_configurations(self, service_ids):
        """
        The Filters, MaxResults, NextToken parameters are not yet implemented
        """
        if service_ids:
            found_configs = []
            for service_id in service_ids:
                if service_id in self.configurations:
                    found_configs.append(self.configurations[service_id])
                else:
                    raise UnknownVpcEndpointService(service_id)
            return found_configs
        return self.configurations.values()

    def delete_vpc_endpoint_service_configurations(self, service_ids):
        missing = [s for s in service_ids if s not in self.configurations]
        for s in service_ids:
            self.configurations.pop(s, None)
        return missing

    def describe_vpc_endpoint_service_permissions(self, service_id):
        """
        The Filters, MaxResults, NextToken parameters are not yet implemented
        """
        config = self.describe_vpc_endpoint_service_configurations([service_id])[0]
        return config.principals

    def modify_vpc_endpoint_service_permissions(
        self, service_id, add_principals, remove_principals
    ):
        config = self.describe_vpc_endpoint_service_configurations([service_id])[0]
        config.principals += add_principals
        config.principals = [p for p in config.principals if p not in remove_principals]
        config.principals = list(set(config.principals))

    def modify_vpc_endpoint_service_configuration(
        self, service_id, acceptance_required, private_dns_name
    ):
        """
        The following parameters are not yet implemented: RemovePrivateDnsName, AddNetworkLoadBalancerArns, RemoveNetworkLoadBalancerArns, AddGatewayLoadBalancerArns, RemoveGatewayLoadBalancerArns
        """
        config = self.describe_vpc_endpoint_service_configurations([service_id])[0]
        config.acceptance_required = (
            config.acceptance_required
            if acceptance_required is None
            else acceptance_required
        )
        config.private_dns_name = (
            config.private_dns_name if private_dns_name is None else private_dns_name
        )
