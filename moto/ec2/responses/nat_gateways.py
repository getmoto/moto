from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring


class NatGateways(BaseResponse):

    def create_nat_gateway(self):
        subnet_id = self._get_param('SubnetId')
        allocation_id = self._get_param('AllocationId')
        nat_gateway = self.ec2_backend.create_nat_gateway(
            subnet_id=subnet_id, allocation_id=allocation_id)
        template = self.response_template(CREATE_NAT_GATEWAY)
        return template.render(nat_gateway=nat_gateway)

    def delete_nat_gateway(self):
        nat_gateway_id = self._get_param('NatGatewayId')
        nat_gateway = self.ec2_backend.delete_nat_gateway(nat_gateway_id)
        template = self.response_template(DELETE_NAT_GATEWAY_RESPONSE)
        return template.render(nat_gateway=nat_gateway)

    def describe_nat_gateways(self):
        filters = filters_from_querystring(self.querystring)
        nat_gateways = self.ec2_backend.get_all_nat_gateways(filters)
        template = self.response_template(DESCRIBE_NAT_GATEWAYS_RESPONSE)
        return template.render(nat_gateways=nat_gateways)


DESCRIBE_NAT_GATEWAYS_RESPONSE = """<DescribeNatGatewaysResponse xmlns="http://ec2.amazonaws.com/doc/2015-10-01/">
    <requestId>bfed02c6-dae9-47c0-86a2-example</requestId>
    <natGatewaySet>
    {% for nat_gateway in nat_gateways %}
         <item>
            <subnetId>{{ nat_gateway.subnet_id }}</subnetId>
            <natGatewayAddressSet>
                <item>
                    <networkInterfaceId>{{ nat_gateway.network_interface_id }}</networkInterfaceId>
                    <publicIp>{{ nat_gateway.public_ip }}</publicIp>
                    <allocationId>{{ nat_gateway.allocation_id }}</allocationId>
                    <privateIp>{{ nat_gateway.private_ip }}</privateIp>
                </item>
            </natGatewayAddressSet>
            <createTime>{{ nat_gateway.create_time }}</createTime>
            <vpcId>{{ nat_gateway.vpc_id }}</vpcId>
            <natGatewayId>{{ nat_gateway.id }}</natGatewayId>
            <state>{{ nat_gateway.state }}</state>
        </item>
    {% endfor %}
    </natGatewaySet>
</DescribeNatGatewaysResponse>
"""

CREATE_NAT_GATEWAY = """<CreateNatGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2015-10-01/">
    <requestId>1b74dc5c-bcda-403f-867d-example</requestId>
    <natGateway>
        <subnetId>{{ nat_gateway.subnet_id }}</subnetId>
        <natGatewayAddressSet>
            <item>
                <allocationId>{{ nat_gateway.allocation_id }}</allocationId>
            </item>
        </natGatewayAddressSet>
        <createTime>{{ nat_gateway.create_time }}</createTime>
        <vpcId>{{ nat_gateway.vpc_id }}</vpcId>
        <natGatewayId>{{ nat_gateway.id }}</natGatewayId>
        <state>{{ nat_gateway.state }}</state>
    </natGateway>
</CreateNatGatewayResponse>
"""


DELETE_NAT_GATEWAY_RESPONSE = """<DeleteNatGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2015-10-01/">
    <requestId>741fc8ab-6ebe-452b-b92b-example</requestId>
    <natGatewayId>{{ nat_gateway.id }}</natGatewayId>
</DeleteNatGatewayResponse>"""
