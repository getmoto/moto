from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring, \
    network_acl_ids_from_querystring


class NetworkACLs(BaseResponse):

    def create_network_acl(self):
        vpc_id = self.querystring.get('VpcId')[0]
        network_acl = self.ec2_backend.create_network_acl(vpc_id)
        template = self.response_template(CREATE_NETWORK_ACL_RESPONSE)
        return template.render(network_acl=network_acl)

    def create_network_acl_entry(self):
        network_acl_id = self.querystring.get('NetworkAclId')[0]
        rule_number = self.querystring.get('RuleNumber')[0]
        protocol = self.querystring.get('Protocol')[0]
        rule_action = self.querystring.get('RuleAction')[0]
        egress = self.querystring.get('Egress')[0]
        cidr_block = self.querystring.get('CidrBlock')[0]
        icmp_code = self.querystring.get('Icmp.Code', [None])[0]
        icmp_type = self.querystring.get('Icmp.Type', [None])[0]
        port_range_from = self.querystring.get('PortRange.From')[0]
        port_range_to = self.querystring.get('PortRange.To')[0]

        network_acl_entry = self.ec2_backend.create_network_acl_entry(
            network_acl_id, rule_number, protocol, rule_action,
            egress, cidr_block, icmp_code, icmp_type,
            port_range_from, port_range_to)

        template = self.response_template(CREATE_NETWORK_ACL_ENTRY_RESPONSE)
        return template.render(network_acl_entry=network_acl_entry)

    def delete_network_acl(self):
        network_acl_id = self.querystring.get('NetworkAclId')[0]
        self.ec2_backend.delete_network_acl(network_acl_id)
        template = self.response_template(DELETE_NETWORK_ACL_ASSOCIATION)
        return template.render()

    def delete_network_acl_entry(self):
        network_acl_id = self.querystring.get('NetworkAclId')[0]
        rule_number = self.querystring.get('RuleNumber')[0]
        egress = self.querystring.get('Egress')[0]
        self.ec2_backend.delete_network_acl_entry(network_acl_id, rule_number, egress)
        template = self.response_template(DELETE_NETWORK_ACL_ENTRY_RESPONSE)
        return template.render()

    def replace_network_acl_entry(self):
        network_acl_id = self.querystring.get('NetworkAclId')[0]
        rule_number = self.querystring.get('RuleNumber')[0]
        protocol = self.querystring.get('Protocol')[0]
        rule_action = self.querystring.get('RuleAction')[0]
        egress = self.querystring.get('Egress')[0]
        cidr_block = self.querystring.get('CidrBlock')[0]
        icmp_code = self.querystring.get('Icmp.Code', [None])[0]
        icmp_type = self.querystring.get('Icmp.Type', [None])[0]
        port_range_from = self.querystring.get('PortRange.From')[0]
        port_range_to = self.querystring.get('PortRange.To')[0]

        self.ec2_backend.replace_network_acl_entry(
            network_acl_id, rule_number, protocol, rule_action,
            egress, cidr_block, icmp_code, icmp_type,
            port_range_from, port_range_to)

        template = self.response_template(REPLACE_NETWORK_ACL_ENTRY_RESPONSE)
        return template.render()

    def describe_network_acls(self):
        network_acl_ids = network_acl_ids_from_querystring(self.querystring)
        filters = filters_from_querystring(self.querystring)
        network_acls = self.ec2_backend.get_all_network_acls(
            network_acl_ids, filters)
        template = self.response_template(DESCRIBE_NETWORK_ACL_RESPONSE)
        return template.render(network_acls=network_acls)

    def replace_network_acl_association(self):
        association_id = self.querystring.get('AssociationId')[0]
        network_acl_id = self.querystring.get('NetworkAclId')[0]

        association = self.ec2_backend.replace_network_acl_association(
            association_id,
            network_acl_id
        )
        template = self.response_template(REPLACE_NETWORK_ACL_ASSOCIATION)
        return template.render(association=association)


CREATE_NETWORK_ACL_RESPONSE = """
<CreateNetworkAclResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <networkAcl>
      <networkAclId>{{ network_acl.id }}</networkAclId>
      <vpcId>{{ network_acl.vpc_id }}</vpcId>
      <default>false</default>
      <entrySet/>
      <associationSet/>
      <tagSet>
      {% for tag in network_acl.get_tags() %}
        <item>
          <resourceId>{{ tag.resource_id }}</resourceId>
          <resourceType>{{ tag.resource_type }}</resourceType>
          <key>{{ tag.key }}</key>
          <value>{{ tag.value }}</value>
        </item>
      {% endfor %}
      </tagSet>
   </networkAcl>
</CreateNetworkAclResponse>
"""

DESCRIBE_NETWORK_ACL_RESPONSE = """
<DescribeNetworkAclsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <networkAclSet>
   {% for network_acl in network_acls %}
   <item>
     <networkAclId>{{ network_acl.id }}</networkAclId>
     <vpcId>{{ network_acl.vpc_id }}</vpcId>
     <default>{{ network_acl.default }}</default>
     <entrySet>
       {% for entry in network_acl.network_acl_entries %}
         <item>
           <ruleNumber>{{ entry.rule_number }}</ruleNumber>
           <protocol>{{ entry.protocol }}</protocol>
           <ruleAction>{{ entry.rule_action }}</ruleAction>
           <egress>{{ entry.egress.lower() }}</egress>
           <cidrBlock>{{ entry.cidr_block }}</cidrBlock>
           {% if entry.port_range_from or entry.port_range_to %}
             <portRange>
               <from>{{ entry.port_range_from }}</from>
               <to>{{ entry.port_range_to }}</to>
             </portRange>
           {% endif %}
         </item>
       {% endfor %}
     </entrySet>
     <associationSet>
       {% for association in network_acl.associations.values() %}
         <item>
           <networkAclAssociationId>{{ association.id }}</networkAclAssociationId>
           <networkAclId>{{ association.network_acl_id }}</networkAclId>
           <subnetId>{{ association.subnet_id }}</subnetId>
         </item>
       {% endfor %}
     </associationSet>
     <tagSet>
      {% for tag in network_acl.get_tags() %}
        <item>
          <resourceId>{{ tag.resource_id }}</resourceId>
          <resourceType>{{ tag.resource_type }}</resourceType>
          <key>{{ tag.key }}</key>
          <value>{{ tag.value }}</value>
        </item>
      {% endfor %}
     </tagSet>
   </item>
   {% endfor %}
 </networkAclSet>
</DescribeNetworkAclsResponse>
"""

CREATE_NETWORK_ACL_ENTRY_RESPONSE = """
<CreateNetworkAclEntryResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</CreateNetworkAclEntryResponse>
"""

REPLACE_NETWORK_ACL_ENTRY_RESPONSE = """
<ReplaceNetworkAclEntryResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</ReplaceNetworkAclEntryResponse>
"""

REPLACE_NETWORK_ACL_ASSOCIATION = """
<ReplaceNetworkAclAssociationResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <newAssociationId>{{ association.new_association_id }}</newAssociationId>
</ReplaceNetworkAclAssociationResponse>
"""

DELETE_NETWORK_ACL_ASSOCIATION = """
<DeleteNetworkAclResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</DeleteNetworkAclResponse>
"""

DELETE_NETWORK_ACL_ENTRY_RESPONSE = """
<DeleteNetworkAclEntryResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</DeleteNetworkAclEntryResponse>
"""
