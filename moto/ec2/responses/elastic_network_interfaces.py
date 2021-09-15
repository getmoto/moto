from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring, add_tag_specification


class ElasticNetworkInterfaces(BaseResponse):
    def create_network_interface(self):
        subnet_id = self._get_param("SubnetId")
        private_ip_address = self._get_param("PrivateIpAddress")
        private_ip_addresses = self._get_multi_param("PrivateIpAddresses")
        groups = self._get_multi_param("SecurityGroupId")
        subnet = self.ec2_backend.get_subnet(subnet_id)
        description = self._get_param("Description")
        tags = self._get_multi_param("TagSpecification")
        tags = add_tag_specification(tags)

        if self.is_not_dryrun("CreateNetworkInterface"):
            eni = self.ec2_backend.create_network_interface(
                subnet,
                private_ip_address,
                private_ip_addresses,
                groups,
                description,
                tags,
            )
            template = self.response_template(CREATE_NETWORK_INTERFACE_RESPONSE)
            return template.render(eni=eni)

    def delete_network_interface(self):
        eni_id = self._get_param("NetworkInterfaceId")
        if self.is_not_dryrun("DeleteNetworkInterface"):
            self.ec2_backend.delete_network_interface(eni_id)
            template = self.response_template(DELETE_NETWORK_INTERFACE_RESPONSE)
            return template.render()

    def describe_network_interface_attribute(self):
        raise NotImplementedError(
            "ElasticNetworkInterfaces(AmazonVPC).describe_network_interface_attribute is not yet implemented"
        )

    def describe_network_interfaces(self):
        eni_ids = self._get_multi_param("NetworkInterfaceId")
        filters = filters_from_querystring(self.querystring)
        enis = self.ec2_backend.get_all_network_interfaces(eni_ids, filters)
        template = self.response_template(DESCRIBE_NETWORK_INTERFACES_RESPONSE)
        return template.render(enis=enis)

    def attach_network_interface(self):
        eni_id = self._get_param("NetworkInterfaceId")
        instance_id = self._get_param("InstanceId")
        device_index = self._get_param("DeviceIndex")
        if self.is_not_dryrun("AttachNetworkInterface"):
            attachment_id = self.ec2_backend.attach_network_interface(
                eni_id, instance_id, device_index
            )
            template = self.response_template(ATTACH_NETWORK_INTERFACE_RESPONSE)
            return template.render(attachment_id=attachment_id)

    def detach_network_interface(self):
        attachment_id = self._get_param("AttachmentId")
        if self.is_not_dryrun("DetachNetworkInterface"):
            self.ec2_backend.detach_network_interface(attachment_id)
            template = self.response_template(DETACH_NETWORK_INTERFACE_RESPONSE)
            return template.render()

    def modify_network_interface_attribute(self):
        eni_id = self._get_param("NetworkInterfaceId")
        group_ids = self._get_multi_param("SecurityGroupId")
        source_dest_check = self._get_param("SourceDestCheck")
        if self.is_not_dryrun("ModifyNetworkInterface"):
            self.ec2_backend.modify_network_interface_attribute(
                eni_id, group_ids, source_dest_check
            )
            return MODIFY_NETWORK_INTERFACE_ATTRIBUTE_RESPONSE

    def reset_network_interface_attribute(self):
        if self.is_not_dryrun("ResetNetworkInterface"):
            raise NotImplementedError(
                "ElasticNetworkInterfaces(AmazonVPC).reset_network_interface_attribute is not yet implemented"
            )


CREATE_NETWORK_INTERFACE_RESPONSE = """
<CreateNetworkInterfaceResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>2c6021ec-d705-445a-9780-420d0c7ab793</requestId>
    <networkInterface>
        <association></association>
        <attachment></attachment>
        <networkInterfaceId>{{ eni.id }}</networkInterfaceId>
        <subnetId>{{ eni.subnet.id }}</subnetId>
        <vpcId>{{ eni.subnet.vpc_id }}</vpcId>
        <availabilityZone>{{ eni.subnet.availability_zone }}</availabilityZone>
        {% if eni.description %}
        <description>{{ eni.description }}</description>
        {% endif %}
        <ownerId>{{ eni.owner_id }}</ownerId>
        <requesterId>AIDARCSPW2WNREUEN7XFM</requesterId>
        <requesterManaged>False</requesterManaged>
        <status>{{ eni.status }}</status>
        <macAddress>{{ eni.mac_address }}</macAddress>
        {% if eni.private_ip_address %}
          <privateIpAddress>{{ eni.private_ip_address }}</privateIpAddress>
        {% endif %}
        <sourceDestCheck>{{ eni.source_dest_check }}</sourceDestCheck>
        <groupSet>
        {% for group in eni.group_set %}
            <item>
                <groupId>{{ group.id }}</groupId>
                <groupName>{{ group.name }}</groupName>
             </item>
         {% endfor %}
         </groupSet>
        {% if eni.association %}
        <association>
            <publicIp>{{ eni.public_ip }}</publicIp>
            <ipOwnerId>{{ eni.owner_id }}</ipOwnerId>
            <allocationId>{{ eni.association.allocationId }}</allocationId>
            <associationId>{{ eni.association.associationId }}</associationId>
            <natEnabled>true</natEnabled>
        </association>
        {% endif %}
        <tagSet>
          {% for tag in eni.get_tags() %}
              <item>
                  <key>{{ tag.key }}</key>
                  <value>{{ tag.value }}</value>
              </item>
          {% endfor %}
        </tagSet>
        <privateIpAddressesSet>
          {% for address in eni.private_ip_addresses %}
          <item>
            <privateIpAddress>{{ address.PrivateIpAddress }}</privateIpAddress>
            {% if address.privateDnsName %}
            <privateDnsName>{{ address.privateDnsName }}</privateDnsName>
            {% endif %}
            <primary>{{ address.Primary }}</primary>
          </item>
          {% endfor %}
        </privateIpAddressesSet>
        <ipv6AddressesSet/>
        <interfaceType>{{ eni.interface_type }}</interfaceType>
    </networkInterface>
</CreateNetworkInterfaceResponse>
"""

DESCRIBE_NETWORK_INTERFACES_RESPONSE = """<DescribeNetworkInterfacesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>ddb0aaf1-8b65-4f0a-94fa-654b18b8a204</requestId>
    <networkInterfaceSet>
    {% for eni in enis %}
        <item>
          <networkInterfaceId>{{ eni.id }}</networkInterfaceId>
          <subnetId>{{ eni.subnet.id }}</subnetId>
          <vpcId>{{ eni.subnet.vpc_id }}</vpcId>
          <availabilityZone>{{ eni.subnet.availability_zone }}</availabilityZone>
          {% if eni.description %}
          <description>{{ eni.description }}</description>
          {% endif %}
          <ownerId>{{ eni.owner_id }}</ownerId>
          <requesterId>AIDARCSPW2WNREUEN7XFM</requesterId>
          <requesterManaged>False</requesterManaged>
          <status>{{ eni.status }}</status>
          <macAddress>{{ eni.mac_address }}</macAddress>
          {% if eni.private_ip_address %}
            <privateIpAddress>{{ eni.private_ip_address }}</privateIpAddress>
          {% endif %}
          <sourceDestCheck>{{ eni.source_dest_check }}</sourceDestCheck>
          <groupSet>
          {% for group in eni.group_set %}
              <item>
                  <groupId>{{ group.id }}</groupId>
                  <groupName>{{ group.name }}</groupName>
              </item>
          {% endfor %}
          </groupSet>
          {% if eni.association %}
          <association>
            <publicIp>{{ eni.public_ip }}</publicIp>
            <ipOwnerId>{{ eni.owner_id }}</ipOwnerId>
            <allocationId>{{ eni.association.allocationId }}</allocationId>
            <associationId>{{ eni.association.associationId }}</associationId>
            <natEnabled>true</natEnabled>
          </association>
          {% endif %}
          <tagSet>
            {% for tag in eni.get_tags() %}
                <item>
                    <key>{{ tag.key }}</key>
                    <value>{{ tag.value }}</value>
                </item>
            {% endfor %}
          </tagSet>
          <privateIpAddressesSet>
            {% for address in eni.private_ip_addresses %}
            <item>
              <privateIpAddress>{{ address.PrivateIpAddress }}</privateIpAddress>
              {% if address.privateDnsName %}
              <privateDnsName>{{ address.privateDnsName }}</privateDnsName>
              {% endif %}
              <primary>{{ address.Primary }}</primary>
            </item>
            {% endfor %}
          </privateIpAddressesSet>
          <ipv6AddressesSet/>
          <interfaceType>{{ eni.interface_type }}</interfaceType>
        </item>
    {% endfor %}
    </networkInterfaceSet>
</DescribeNetworkInterfacesResponse>"""

ATTACH_NETWORK_INTERFACE_RESPONSE = """<AttachNetworkInterfaceResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <attachmentId>{{ attachment_id }}</attachmentId>
</AttachNetworkInterfaceResponse>"""

DETACH_NETWORK_INTERFACE_RESPONSE = """<DetachNetworkInterfaceResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DetachNetworkInterfaceResponse>"""

MODIFY_NETWORK_INTERFACE_ATTRIBUTE_RESPONSE = """<ModifyNetworkInterfaceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</ModifyNetworkInterfaceAttributeResponse>"""

DELETE_NETWORK_INTERFACE_RESPONSE = """
<DeleteNetworkInterfaceResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>34b5b3b4-d0c5-49b9-b5e2-a468ef6adcd8</requestId>
    <return>true</return>
</DeleteNetworkInterfaceResponse>"""
