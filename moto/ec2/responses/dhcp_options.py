from jinja2 import Template
from moto.core.responses import BaseResponse
from moto.ec2.utils import (
    dhcp_configuration_from_querystring,
    sequence_from_querystring)
from moto.ec2.models import ec2_backend


class DHCPOptions(BaseResponse):
    def associate_dhcp_options(self):
        dhcp_opt_id = self.querystring.get("DhcpOptionsId", [None])[0]
        vpc_id = self.querystring.get("VpcId", [None])[0]

        dhcp_opt = ec2_backend.describe_dhcp_options([dhcp_opt_id])[0]
        vpc = ec2_backend.get_vpc(vpc_id)

        ec2_backend.associate_dhcp_options(dhcp_opt, vpc)

        template = Template(ASSOCIATE_DHCP_OPTIONS_RESPONSE)
        return template.render()

    def create_dhcp_options(self):
        dhcp_config = dhcp_configuration_from_querystring(self.querystring)

        # TODO validate we only got the options we know about

        domain_name_servers = dhcp_config.get("domain-name-servers", None)
        domain_name = dhcp_config.get("domain-name", None)
        ntp_servers = dhcp_config.get("ntp-servers", None)
        netbios_name_servers = dhcp_config.get("netbios-name-servers", None)
        netbios_node_type = dhcp_config.get("netbios-node-type", None)

        dhcp_options_set = ec2_backend.create_dhcp_options(
            domain_name_servers=domain_name_servers,
            domain_name=domain_name,
            ntp_servers=ntp_servers,
            netbios_name_servers=netbios_name_servers,
            netbios_node_type=netbios_node_type
        )

        template = Template(CREATE_DHCP_OPTIONS_RESPONSE)
        return template.render(dhcp_options_set=dhcp_options_set)

    def delete_dhcp_options(self):
        dhcp_opt_id = self.querystring.get("DhcpOptionsId", [None])[0]
        delete_status = ec2_backend.delete_dhcp_options_set(dhcp_opt_id)
        template = Template(DELETE_DHCP_OPTIONS_RESPONSE)
        return template.render(delete_status=delete_status)

    def describe_dhcp_options(self):
        if "Filter.1.Name" in self.querystring:
            raise NotImplementedError("Filtering not supported in describe_dhcp_options.")
        elif "DhcpOptionsId.1" in self.querystring:
            dhcp_opt_ids = sequence_from_querystring("DhcpOptionsId", self.querystring)
            dhcp_opt = ec2_backend.describe_dhcp_options(dhcp_opt_ids)
        else:
            dhcp_opt = ec2_backend.describe_dhcp_options()
        template = Template(DESCRIBE_DHCP_OPTIONS_RESPONSE)
        return template.render(dhcp_options=dhcp_opt)


CREATE_DHCP_OPTIONS_RESPONSE = u"""
<CreateDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <dhcpOptions>
      <dhcpOptionsId>{{ dhcp_options_set.id }}</dhcpOptionsId>
      <dhcpConfigurationSet>
      {% for key, values in dhcp_options_set.options.iteritems() %}
        {{ values }}
        {% if values %}
        <item>
          <key>{{key}}</key>
          <valueSet>
            {% for value in values %}
            <item>
              <value>{{ value }}</value>
            </item>
            {% endfor %}
          </valueSet>
        </item>
        {% endif %}
      {% endfor %}
      </dhcpConfigurationSet>
      <tagSet>
        {% for tag in dhcp_options_set.get_tags() %}
          <item>
            <resourceId>{{ tag.resource_id }}</resourceId>
            <resourceType>{{ tag.resource_type }}</resourceType>
            <key>{{ tag.key }}</key>
            <value>{{ tag.value }}</value>
          </item>
        {% endfor %}
      </tagSet>
  </dhcpOptions>
</CreateDhcpOptionsResponse>
"""

DELETE_DHCP_OPTIONS_RESPONSE = u"""
<DeleteDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>{{delete_status}}</return>
</DeleteDhcpOptionsResponse>
"""

DESCRIBE_DHCP_OPTIONS_RESPONSE = u"""
<DescribeDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <item>
    {% for dhcp_options_set in dhcp_options %}
    <dhcpOptions>
      <dhcpOptionsId>{{ dhcp_options_set.id }}</dhcpOptionsId>
      <dhcpConfigurationSet>
      {% for key, values in dhcp_options_set.options.iteritems() %}
        {{ values }}
        {% if values %}
        <item>
          <key>{{key}}</key>
          <valueSet>
            {% for value in values %}
            <item>
              <value>{{ value }}</value>
            </item>
            {% endfor %}
          </valueSet>
        </item>
        {% endif %}
      {% endfor %}
      </dhcpConfigurationSet>
      <tagSet>
        {% for tag in dhcp_options_set.get_tags() %}
          <item>
            <resourceId>{{ tag.resource_id }}</resourceId>
            <resourceType>{{ tag.resource_type }}</resourceType>
            <key>{{ tag.key }}</key>
            <value>{{ tag.value }}</value>
          </item>
        {% endfor %}
      </tagSet>
    </dhcpOptions>
    {% endfor %}
  </item>
</DescribeDhcpOptionsResponse>
"""

ASSOCIATE_DHCP_OPTIONS_RESPONSE = u"""
<AssociateDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
<requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
<return>true</return>
</AssociateDhcpOptionsResponse>
"""
