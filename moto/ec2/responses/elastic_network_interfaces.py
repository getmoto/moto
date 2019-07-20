from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring


class ElasticNetworkInterfaces(BaseResponse):

    def create_network_interface(self):
        subnet_id = self._get_param('SubnetId')
        private_ip_address = self._get_param('PrivateIpAddress')
        groups = self._get_multi_param('SecurityGroupId')
        subnet = self.ec2_backend.get_subnet(subnet_id)
        description = self._get_param('Description')
        if self.is_not_dryrun('CreateNetworkInterface'):
            eni = self.ec2_backend.create_network_interface(
                subnet, private_ip_address, groups, description)
            template = self.response_template(
                CREATE_NETWORK_INTERFACE_RESPONSE)
            return template.render(eni=eni)

    def delete_network_interface(self):
        eni_id = self._get_param('NetworkInterfaceId')
        if self.is_not_dryrun('DeleteNetworkInterface'):
            self.ec2_backend.delete_network_interface(eni_id)
            template = self.response_template(
                DELETE_NETWORK_INTERFACE_RESPONSE)
            return template.render()

    def describe_network_interface_attribute(self):
        raise NotImplementedError(
            'ElasticNetworkInterfaces(AmazonVPC).describe_network_interface_attribute is not yet implemented')

    def describe_network_interfaces(self):
        eni_ids = self._get_multi_param('NetworkInterfaceId')
        filters = filters_from_querystring(self.querystring)
        enis = self.ec2_backend.get_all_network_interfaces(eni_ids, filters)
        template = self.response_template(DESCRIBE_NETWORK_INTERFACES_RESPONSE)
        return template.render(enis=enis)

    def attach_network_interface(self):
        eni_id = self._get_param('NetworkInterfaceId')
        instance_id = self._get_param('InstanceId')
        device_index = self._get_param('DeviceIndex')
        if self.is_not_dryrun('AttachNetworkInterface'):
            attachment_id = self.ec2_backend.attach_network_interface(
                eni_id, instance_id, device_index)
            template = self.response_template(
                ATTACH_NETWORK_INTERFACE_RESPONSE)
            return template.render(attachment_id=attachment_id)

    def detach_network_interface(self):
        attachment_id = self._get_param('AttachmentId')
        if self.is_not_dryrun('DetachNetworkInterface'):
            self.ec2_backend.detach_network_interface(attachment_id)
            template = self.response_template(
                DETACH_NETWORK_INTERFACE_RESPONSE)
            return template.render()

    def modify_network_interface_attribute(self):
        # Currently supports modifying one and only one security group
        eni_id = self._get_param('NetworkInterfaceId')
        group_id = self._get_param('SecurityGroupId.1')
        if self.is_not_dryrun('ModifyNetworkInterface'):
            self.ec2_backend.modify_network_interface_attribute(
                eni_id, group_id)
            return MODIFY_NETWORK_INTERFACE_ATTRIBUTE_RESPONSE

    def reset_network_interface_attribute(self):
        if self.is_not_dryrun('ResetNetworkInterface'):
            raise NotImplementedError(
                'ElasticNetworkInterfaces(AmazonVPC).reset_network_interface_attribute is not yet implemented')


CREATE_NETWORK_INTERFACE_RESPONSE = """
<CreateNetworkInterfaceResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>2c6021ec-d705-445a-9780-420d0c7ab793</requestId>
    <networkInterface>
        <networkInterfaceId>{{ eni.id }}</networkInterfaceId>
        <subnetId>{{ eni.subnet.id }}</subnetId>
        <vpcId>{{ eni.subnet.vpc_id }}</vpcId>
        <availabilityZone>us-west-2a</availabilityZone>
        {% if eni.description %}
        <description>{{ eni.description }}</description>
        {% else %}
        <description/>
        {% endif %}
        <ownerId>498654062920</ownerId>
        <requesterManaged>false</requesterManaged>
        <status>pending</status>
        <macAddress>02:07:a9:b6:12:51</macAddress>
        {% if eni.private_ip_address %}
          <privateIpAddress>{{ eni.private_ip_address }}</privateIpAddress>
        {% endif %}
        {% if eni.instance %}
          <sourceDestCheck>{{ eni.instance.source_dest_check }}</sourceDestCheck>
        {% endif %}
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

DESCRIBE_NETWORK_INTERFACES_RESPONSE = """<DescribeNetworkInterfacesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>ddb0aaf1-8b65-4f0a-94fa-654b18b8a204</requestId>
    <networkInterfaceSet>
    {% for eni in enis %}
        <item>
           <networkInterfaceId>{{ eni.id }}</networkInterfaceId>
           <subnetId>{{ eni.subnet.id }}</subnetId>
           <vpcId>{{ eni.subnet.vpc_id }}</vpcId>
           <availabilityZone>us-west-2a</availabilityZone>
           <description>{{ eni.description }}</description>
           <ownerId>190610284047</ownerId>
           <requesterManaged>false</requesterManaged>
           {% if eni.attachment_id %}
             <status>in-use</status>
           {% else %}
             <status>available</status>
           {% endif %}
           <macAddress>0e:a3:a7:7b:95:a7</macAddress>
           {% if eni.private_ip_address %}
             <privateIpAddress>{{ eni.private_ip_address }}</privateIpAddress>
           {% endif %}
           <privateDnsName>ip-10-0-0-134.us-west-2.compute.internal</privateDnsName>
           {% if eni.instance %}
             <sourceDestCheck>{{ eni.instance.source_dest_check }}</sourceDestCheck>
           {% endif %}
           <groupSet>
           {% for group in eni.group_set %}
               <item>
                   <groupId>{{ group.id }}</groupId>
                   <groupName>{{ group.name }}</groupName>
                </item>
            {% endfor %}
            </groupSet>
            <tagSet>
              {% for tag in eni.get_tags() %}
                <item>
                  <key>{{ tag.key }}</key>
                  <value>{{ tag.value }}</value>
                </item>
              {% endfor %}
            </tagSet>
            {% if eni.instance %}
               <attachment>
                  <attachmentId>{{ eni.attachment_id }}</attachmentId>
                  <instanceId>{{ eni.instance.id }}</instanceId>
                  <instanceOwnerId>190610284047</instanceOwnerId>
                  <deviceIndex>{{ eni.device_index }}</deviceIndex>
                  <status>attached</status>
                  <attachTime>2013-10-04T17:38:53.000Z</attachTime>
                  <deleteOnTermination>true</deleteOnTermination>
               </attachment>
            {% endif %}
            <association>
                <publicIp>{{ eni.public_ip }}</publicIp>
                <publicDnsName>ec2-54-200-86-47.us-west-2.compute.amazonaws.com</publicDnsName>
                <ipOwnerId>amazon</ipOwnerId>
            </association>
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
