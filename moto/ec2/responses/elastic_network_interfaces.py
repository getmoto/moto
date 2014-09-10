from __future__ import unicode_literals
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend
from moto.ec2.utils import sequence_from_querystring, resource_ids_from_querystring, filters_from_querystring


class ElasticNetworkInterfaces(BaseResponse):
    def attach_network_interface(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).attach_network_interface is not yet implemented')

    def create_network_interface(self):
        subnet_id = self.querystring.get('SubnetId')[0]
        private_ip_address = self.querystring.get('PrivateIpAddress', [None])[0]
        groups = sequence_from_querystring('SecurityGroupId', self.querystring)
        subnet = ec2_backend.get_subnet(subnet_id)
        eni = ec2_backend.create_network_interface(subnet, private_ip_address, groups)
        template = Template(CREATE_NETWORK_INTERFACE_RESPONSE)
        return template.render(eni=eni)

    def delete_network_interface(self):
        eni_id = self.querystring.get('NetworkInterfaceId')[0]
        eni = ec2_backend.delete_network_interface(eni_id)
        template = Template(DELETE_NETWORK_INTERFACE_RESPONSE)
        return template.render()

    def describe_network_interface_attribute(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).describe_network_interface_attribute is not yet implemented')

    def describe_network_interfaces(self):
        #Partially implemented. Supports only network-interface-id and group-id filters
        filters = filters_from_querystring(self.querystring)
        enis = ec2_backend.describe_network_interfaces(filters)
        template = Template(DESCRIBE_NETWORK_INTERFACES_RESPONSE)
        return template.render(enis=enis)

    def detach_network_interface(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).detach_network_interface is not yet implemented')

    def modify_network_interface_attribute(self):
        #Currently supports modifying one and only one security group
        eni_id = self.querystring.get('NetworkInterfaceId')[0]
        group_id = self.querystring.get('SecurityGroupId.1')[0]
        ec2_backend.modify_network_interface_attribute(eni_id, group_id)
        return MODIFY_NETWORK_INTERFACE_ATTRIBUTE_RESPONSE

    def reset_network_interface_attribute(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).reset_network_interface_attribute is not yet implemented')

CREATE_NETWORK_INTERFACE_RESPONSE = """
<CreateNetworkInterfaceResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
    <requestId>2c6021ec-d705-445a-9780-420d0c7ab793</requestId>
    <networkInterface>
        <networkInterfaceId>{{ eni.id }}</networkInterfaceId>
        <subnetId>{{ eni.subnet.id }}</subnetId>
        <vpcId>{{ eni.subnet.vpc_id }}</vpcId>
        <availabilityZone>us-west-2a</availabilityZone>
        <description/>
        <ownerId>498654062920</ownerId>
        <requesterManaged>false</requesterManaged>
        <status>pending</status>
        <macAddress>02:07:a9:b6:12:51</macAddress>
        {% if eni.private_ip_address %}
          <privateIpAddress>{{ eni.private_ip_address }}</privateIpAddress>
        {% endif %}
        <sourceDestCheck>true</sourceDestCheck>
        <groupSet>
        {% for group in eni.group_set %}
            <item>
                <groupId>{{ group.id }}</groupId>
                <groupName>{{ group.name }}</groupName>
             </item>
         {% endfor %}
         </groupSet>
        <tagSet/>
        {% if eni.private_ip_address %}
          <privateIpAddressesSet>
              <item>
                  <privateIpAddress>{{ eni.private_ip_address }}</privateIpAddress>
                  <primary>true</primary>
              </item>
          </privateIpAddressesSet>
        {% else %}
          <privateIpAddressesSet/>
        {% endif %}
    </networkInterface>
</CreateNetworkInterfaceResponse>
"""

DESCRIBE_NETWORK_INTERFACES_RESPONSE = """<DescribeNetworkInterfacesResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
    <requestId>ddb0aaf1-8b65-4f0a-94fa-654b18b8a204</requestId>
    <networkInterfaceSet>
    {% for eni in enis %}
        <item>
           <networkInterfaceId>{{ eni.id }}</networkInterfaceId>
           <subnetId>{{ eni.subnet.id }}</subnetId>
           <vpcId>vpc-9367a6f8</vpcId>
           <availabilityZone>us-west-2a</availabilityZone>
           <description>Primary network interface</description>
           <ownerId>190610284047</ownerId>
           <requesterManaged>false</requesterManaged>
           <status>in-use</status>
           <macAddress>0e:a3:a7:7b:95:a7</macAddress>
           {% if eni.private_ip_address %}
             <privateIpAddress>{{ eni.private_ip_address }}</privateIpAddress>
           {% endif %}
           <privateDnsName>ip-10-0-0-134.us-west-2.compute.internal</privateDnsName>
           <sourceDestCheck>true</sourceDestCheck>
           <groupSet>
           {% for group in eni.group_set %}
               <item>
                   <groupId>{{ group.id }}</groupId>
                   <groupName>{{ group.name }}</groupName>
                </item>
            {% endfor %}
            </groupSet>
            {% for attachment in eni.attachments %}
            <attachment>
                <attachmentId>{{ attachment['attachmentId'] }}</attachmentId>
                <instanceId>{{ attachment['instanceId'] }}</instanceId>
                <instanceOwnerId>190610284047</instanceOwnerId>
                <deviceIndex>{{ attachment['deviceIndex'] }}</deviceIndex>
                <status>attached</status>
                <attachTime>2013-10-04T17:38:53.000Z</attachTime>
                <deleteOnTermination>true</deleteOnTermination>
            </attachment>
            {% endfor %}
            <association>
                <publicIp>{{ eni.public_ip }}</publicIp>
                <publicDnsName>ec2-54-200-86-47.us-west-2.compute.amazonaws.com</publicDnsName>
                <ipOwnerId>amazon</ipOwnerId>
            </association>
            <tagSet/>
            {% if eni.private_ip_address %}
              <privateIpAddressesSet>
                  <item>
                      <privateIpAddress>{{ eni.private_ip_address }}</privateIpAddress>
                      <privateDnsName>ip-10-0-0-134.us-west-2.compute.internal</privateDnsName>
                      <primary>true</primary>
                      {% if eni.public_ip %}
                        <association>
                            <publicIp>{{ eni.public_ip }}</publicIp>
                            <publicDnsName>ec2-54-200-86-47.us-west-2.compute.amazonaws.com</publicDnsName>
                            <ipOwnerId>amazon</ipOwnerId>
                        </association>
                      {% endif %}
                  </item>
              </privateIpAddressesSet>
            {% else %}
              <privateIpAddressesSet/>
            {% endif %}
        </item>
    {% endfor %}
    </networkInterfaceSet>
</DescribeNetworkInterfacesResponse>"""

MODIFY_NETWORK_INTERFACE_ATTRIBUTE_RESPONSE = """<ModifyNetworkInterfaceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</ModifyNetworkInterfaceAttributeResponse>"""

DELETE_NETWORK_INTERFACE_RESPONSE = """
<DeleteNetworkInterfaceResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
    <requestId>34b5b3b4-d0c5-49b9-b5e2-a468ef6adcd8</requestId>
    <return>true</return>
</DeleteNetworkInterfaceResponse>"""
