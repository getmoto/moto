from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend


def process_rules_from_querystring(querystring):

    name = None
    group_id = None

    try:
        name = querystring.get('GroupName')[0]
    except:
        group_id = querystring.get('GroupId')[0]

    ip_protocol = querystring.get('IpPermissions.1.IpProtocol')[0]
    from_port = querystring.get('IpPermissions.1.FromPort')[0]
    to_port = querystring.get('IpPermissions.1.ToPort')[0]
    ip_ranges = []
    for key, value in querystring.iteritems():
        if 'IpPermissions.1.IpRanges' in key:
            ip_ranges.append(value[0])

    source_groups = []
    source_group_ids = []

    for key, value in querystring.iteritems():
        if 'IpPermissions.1.Groups.1.GroupId' in key:
            source_group_ids.append(value[0])
        elif 'IpPermissions.1.Groups' in key:
            source_groups.append(value[0])

    return (name, group_id, ip_protocol, from_port, to_port, ip_ranges, source_groups, source_group_ids)


class SecurityGroups(BaseResponse):
    def authorize_security_group_egress(self):
        raise NotImplementedError('SecurityGroups.authorize_security_group_egress is not yet implemented')

    def authorize_security_group_ingress(self):
        ec2_backend.authorize_security_group_ingress(*process_rules_from_querystring(self.querystring))
        return AUTHORIZE_SECURITY_GROUP_INGRESS_REPONSE

    def create_security_group(self):
        name = self.querystring.get('GroupName')[0]
        description = self.querystring.get('GroupDescription', [None])[0]
        vpc_id = self.querystring.get("VpcId", [None])[0]
        group = ec2_backend.create_security_group(name, description, vpc_id=vpc_id)
        template = Template(CREATE_SECURITY_GROUP_RESPONSE)
        return template.render(group=group)

    def delete_security_group(self):
        # TODO this should raise an error if there are instances in the group. See http://docs.aws.amazon.com/AWSEC2/latest/APIReference/ApiReference-query-DeleteSecurityGroup.html

        name = self.querystring.get('GroupName')
        sg_id = self.querystring.get('GroupId')

        if name:
            group = ec2_backend.delete_security_group(name[0])
        elif sg_id:
            group = ec2_backend.delete_security_group(group_id=sg_id[0])

        return DELETE_GROUP_RESPONSE

    def describe_security_groups(self):
        groups = ec2_backend.describe_security_groups()
        template = Template(DESCRIBE_SECURITY_GROUPS_RESPONSE)
        return template.render(groups=groups)

    def revoke_security_group_egress(self):
        raise NotImplementedError('SecurityGroups.revoke_security_group_egress is not yet implemented')

    def revoke_security_group_ingress(self):
        ec2_backend.revoke_security_group_ingress(*process_rules_from_querystring(self.querystring))
        return REVOKE_SECURITY_GROUP_INGRESS_REPONSE


CREATE_SECURITY_GROUP_RESPONSE = """<CreateSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
   <groupId>{{ group.id }}</groupId>
</CreateSecurityGroupResponse>"""

DELETE_GROUP_RESPONSE = """<DeleteSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DeleteSecurityGroupResponse>"""

DESCRIBE_SECURITY_GROUPS_RESPONSE = """<DescribeSecurityGroupsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <securityGroupInfo>
      {% for group in groups %}
          <item>
             <ownerId>111122223333</ownerId>
             <groupId>{{ group.id }}</groupId>
             <groupName>{{ group.name }}</groupName>
             <groupDescription>{{ group.description }}</groupDescription>
             {% if group.vpc_id %}
             <vpcId>{{ group.vpc_id }}</vpcId>
             {% endif %}
             <ipPermissions>
               {% for rule in group.ingress_rules %}
                    <item>
                       <ipProtocol>{{ rule.ip_protocol }}</ipProtocol>
                       <fromPort>{{ rule.from_port }}</fromPort>
                       <toPort>{{ rule.to_port }}</toPort>
                       <groups>
                          {% for source_group in rule.source_groups %}
                              <item>
                                 <userId>111122223333</userId>
                                 <groupId>{{ source_group.id }}</groupId>
                                 <groupName>{{ source_group.name }}</groupName>
                              </item>
                          {% endfor %}
                       </groups>
                       <ipRanges>
                          {% for ip_range in rule.ip_ranges %}
                              <item>
                                 <cidrIp>{{ ip_range }}</cidrIp>
                              </item>
                          {% endfor %}
                       </ipRanges>
                    </item>
                {% endfor %}
             </ipPermissions>
             <ipPermissionsEgress/>
          </item>
      {% endfor %}
   </securityGroupInfo>
</DescribeSecurityGroupsResponse>"""

AUTHORIZE_SECURITY_GROUP_INGRESS_REPONSE = """<AuthorizeSecurityGroupIngressResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</AuthorizeSecurityGroupIngressResponse>"""

REVOKE_SECURITY_GROUP_INGRESS_REPONSE = """<RevokeSecurityGroupIngressResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</RevokeSecurityGroupIngressResponse>"""
