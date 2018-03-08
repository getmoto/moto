from __future__ import unicode_literals
from boto.ec2.elb.attributes import (
    ConnectionSettingAttribute,
    ConnectionDrainingAttribute,
    AccessLogAttribute,
    CrossZoneLoadBalancingAttribute,
)
from boto.ec2.elb.policies import (
    AppCookieStickinessPolicy,
    OtherPolicy,
)

from moto.core.responses import BaseResponse
from .models import elb_backends
from .exceptions import DuplicateTagKeysError, LoadBalancerNotFoundError


class ELBResponse(BaseResponse):

    @property
    def elb_backend(self):
        return elb_backends[self.region]

    def create_load_balancer(self):
        load_balancer_name = self._get_param('LoadBalancerName')
        availability_zones = self._get_multi_param("AvailabilityZones.member")
        ports = self._get_list_prefix("Listeners.member")
        scheme = self._get_param('Scheme')
        subnets = self._get_multi_param("Subnets.member")
        security_groups = self._get_multi_param("SecurityGroups.member")

        load_balancer = self.elb_backend.create_load_balancer(
            name=load_balancer_name,
            zones=availability_zones,
            ports=ports,
            scheme=scheme,
            subnets=subnets,
            security_groups=security_groups,
        )
        self._add_tags(load_balancer)
        template = self.response_template(CREATE_LOAD_BALANCER_TEMPLATE)
        return template.render(load_balancer=load_balancer)

    def create_load_balancer_listeners(self):
        load_balancer_name = self._get_param('LoadBalancerName')
        ports = self._get_list_prefix("Listeners.member")

        self.elb_backend.create_load_balancer_listeners(
            name=load_balancer_name, ports=ports)

        template = self.response_template(
            CREATE_LOAD_BALANCER_LISTENERS_TEMPLATE)
        return template.render()

    def describe_load_balancers(self):
        names = self._get_multi_param("LoadBalancerNames.member")
        all_load_balancers = list(self.elb_backend.describe_load_balancers(names))
        marker = self._get_param('Marker')
        all_names = [balancer.name for balancer in all_load_balancers]
        if marker:
            start = all_names.index(marker) + 1
        else:
            start = 0
        page_size = self._get_int_param('PageSize', 50)  # the default is 400, but using 50 to make testing easier
        load_balancers_resp = all_load_balancers[start:start + page_size]
        next_marker = None
        if len(all_load_balancers) > start + page_size:
            next_marker = load_balancers_resp[-1].name

        template = self.response_template(DESCRIBE_LOAD_BALANCERS_TEMPLATE)
        return template.render(load_balancers=load_balancers_resp, marker=next_marker)

    def delete_load_balancer_listeners(self):
        load_balancer_name = self._get_param('LoadBalancerName')
        ports = self._get_multi_param("LoadBalancerPorts.member")
        ports = [int(port) for port in ports]

        self.elb_backend.delete_load_balancer_listeners(
            load_balancer_name, ports)
        template = self.response_template(DELETE_LOAD_BALANCER_LISTENERS)
        return template.render()

    def delete_load_balancer(self):
        load_balancer_name = self._get_param('LoadBalancerName')
        self.elb_backend.delete_load_balancer(load_balancer_name)
        template = self.response_template(DELETE_LOAD_BALANCER_TEMPLATE)
        return template.render()

    def apply_security_groups_to_load_balancer(self):
        load_balancer_name = self._get_param('LoadBalancerName')
        security_group_ids = self._get_multi_param("SecurityGroups.member")
        self.elb_backend.apply_security_groups_to_load_balancer(load_balancer_name, security_group_ids)
        template = self.response_template(APPLY_SECURITY_GROUPS_TEMPLATE)
        return template.render(security_group_ids=security_group_ids)

    def configure_health_check(self):
        check = self.elb_backend.configure_health_check(
            load_balancer_name=self._get_param('LoadBalancerName'),
            timeout=self._get_param('HealthCheck.Timeout'),
            healthy_threshold=self._get_param('HealthCheck.HealthyThreshold'),
            unhealthy_threshold=self._get_param(
                'HealthCheck.UnhealthyThreshold'),
            interval=self._get_param('HealthCheck.Interval'),
            target=self._get_param('HealthCheck.Target'),
        )
        template = self.response_template(CONFIGURE_HEALTH_CHECK_TEMPLATE)
        return template.render(check=check)

    def register_instances_with_load_balancer(self):
        load_balancer_name = self._get_param('LoadBalancerName')
        instance_ids = [list(param.values())[0] for param in self._get_list_prefix('Instances.member')]
        template = self.response_template(REGISTER_INSTANCES_TEMPLATE)
        load_balancer = self.elb_backend.register_instances(
            load_balancer_name, instance_ids)
        return template.render(load_balancer=load_balancer)

    def set_load_balancer_listener_ssl_certificate(self):
        load_balancer_name = self._get_param('LoadBalancerName')
        ssl_certificate_id = self.querystring['SSLCertificateId'][0]
        lb_port = self.querystring['LoadBalancerPort'][0]

        self.elb_backend.set_load_balancer_listener_sslcertificate(
            load_balancer_name, lb_port, ssl_certificate_id)

        template = self.response_template(SET_LOAD_BALANCER_SSL_CERTIFICATE)
        return template.render()

    def deregister_instances_from_load_balancer(self):
        load_balancer_name = self._get_param('LoadBalancerName')
        instance_ids = [list(param.values())[0] for param in self._get_list_prefix('Instances.member')]
        template = self.response_template(DEREGISTER_INSTANCES_TEMPLATE)
        load_balancer = self.elb_backend.deregister_instances(
            load_balancer_name, instance_ids)
        return template.render(load_balancer=load_balancer)

    def describe_load_balancer_attributes(self):
        load_balancer_name = self._get_param('LoadBalancerName')
        load_balancer = self.elb_backend.get_load_balancer(load_balancer_name)
        template = self.response_template(DESCRIBE_ATTRIBUTES_TEMPLATE)
        return template.render(attributes=load_balancer.attributes)

    def modify_load_balancer_attributes(self):
        load_balancer_name = self._get_param('LoadBalancerName')
        load_balancer = self.elb_backend.get_load_balancer(load_balancer_name)

        cross_zone = self._get_dict_param(
            "LoadBalancerAttributes.CrossZoneLoadBalancing.")
        if cross_zone:
            attribute = CrossZoneLoadBalancingAttribute()
            attribute.enabled = cross_zone["enabled"] == "true"
            self.elb_backend.set_cross_zone_load_balancing_attribute(
                load_balancer_name, attribute)

        access_log = self._get_dict_param("LoadBalancerAttributes.AccessLog.")
        if access_log:
            attribute = AccessLogAttribute()
            attribute.enabled = access_log["enabled"] == "true"
            attribute.s3_bucket_name = access_log['s3_bucket_name']
            attribute.s3_bucket_prefix = access_log['s3_bucket_prefix']
            attribute.emit_interval = access_log["emit_interval"]
            self.elb_backend.set_access_log_attribute(
                load_balancer_name, attribute)

        connection_draining = self._get_dict_param(
            "LoadBalancerAttributes.ConnectionDraining.")
        if connection_draining:
            attribute = ConnectionDrainingAttribute()
            attribute.enabled = connection_draining["enabled"] == "true"
            attribute.timeout = connection_draining.get("timeout", 300)
            self.elb_backend.set_connection_draining_attribute(load_balancer_name, attribute)

        connection_settings = self._get_dict_param(
            "LoadBalancerAttributes.ConnectionSettings.")
        if connection_settings:
            attribute = ConnectionSettingAttribute()
            attribute.idle_timeout = connection_settings["idle_timeout"]
            self.elb_backend.set_connection_settings_attribute(
                load_balancer_name, attribute)

        template = self.response_template(MODIFY_ATTRIBUTES_TEMPLATE)
        return template.render(load_balancer=load_balancer, attributes=load_balancer.attributes)

    def create_load_balancer_policy(self):
        load_balancer_name = self._get_param('LoadBalancerName')

        other_policy = OtherPolicy()
        policy_name = self._get_param("PolicyName")
        other_policy.policy_name = policy_name

        self.elb_backend.create_lb_other_policy(
            load_balancer_name, other_policy)

        template = self.response_template(CREATE_LOAD_BALANCER_POLICY_TEMPLATE)
        return template.render()

    def create_app_cookie_stickiness_policy(self):
        load_balancer_name = self._get_param('LoadBalancerName')

        policy = AppCookieStickinessPolicy()
        policy.policy_name = self._get_param("PolicyName")
        policy.cookie_name = self._get_param("CookieName")

        self.elb_backend.create_app_cookie_stickiness_policy(
            load_balancer_name, policy)

        template = self.response_template(CREATE_LOAD_BALANCER_POLICY_TEMPLATE)
        return template.render()

    def create_lb_cookie_stickiness_policy(self):
        load_balancer_name = self._get_param('LoadBalancerName')

        policy = AppCookieStickinessPolicy()
        policy.policy_name = self._get_param("PolicyName")
        cookie_expirations = self._get_param("CookieExpirationPeriod")
        if cookie_expirations:
            policy.cookie_expiration_period = int(cookie_expirations)
        else:
            policy.cookie_expiration_period = None

        self.elb_backend.create_lb_cookie_stickiness_policy(
            load_balancer_name, policy)

        template = self.response_template(CREATE_LOAD_BALANCER_POLICY_TEMPLATE)
        return template.render()

    def set_load_balancer_policies_of_listener(self):
        load_balancer_name = self._get_param('LoadBalancerName')
        load_balancer = self.elb_backend.get_load_balancer(load_balancer_name)
        load_balancer_port = int(self._get_param('LoadBalancerPort'))

        mb_listener = [l for l in load_balancer.listeners if int(
            l.load_balancer_port) == load_balancer_port]
        if mb_listener:
            policies = self._get_multi_param("PolicyNames.member")
            self.elb_backend.set_load_balancer_policies_of_listener(
                load_balancer_name, load_balancer_port, policies)
        # else: explode?

        template = self.response_template(
            SET_LOAD_BALANCER_POLICIES_OF_LISTENER_TEMPLATE)
        return template.render()

    def set_load_balancer_policies_for_backend_server(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        load_balancer = self.elb_backend.get_load_balancer(load_balancer_name)
        instance_port = int(self.querystring.get('InstancePort')[0])

        mb_backend = [b for b in load_balancer.backends if int(
            b.instance_port) == instance_port]
        if mb_backend:
            policies = self._get_multi_param('PolicyNames.member')
            self.elb_backend.set_load_balancer_policies_of_backend_server(
                load_balancer_name, instance_port, policies)
        # else: explode?

        template = self.response_template(
            SET_LOAD_BALANCER_POLICIES_FOR_BACKEND_SERVER_TEMPLATE)
        return template.render()

    def describe_instance_health(self):
        load_balancer_name = self._get_param('LoadBalancerName')
        instance_ids = [list(param.values())[0] for param in self._get_list_prefix('Instances.member')]
        if len(instance_ids) == 0:
            instance_ids = self.elb_backend.get_load_balancer(
                load_balancer_name).instance_ids
        template = self.response_template(DESCRIBE_INSTANCE_HEALTH_TEMPLATE)
        return template.render(instance_ids=instance_ids)

    def add_tags(self):

        for key, value in self.querystring.items():
            if "LoadBalancerNames.member" in key:
                load_balancer_name = value[0]
                elb = self.elb_backend.get_load_balancer(load_balancer_name)
                if not elb:
                    raise LoadBalancerNotFoundError(load_balancer_name)

                self._add_tags(elb)

        template = self.response_template(ADD_TAGS_TEMPLATE)
        return template.render()

    def remove_tags(self):
        for key, value in self.querystring.items():
            if "LoadBalancerNames.member" in key:
                number = key.split('.')[2]
                load_balancer_name = self._get_param(
                    'LoadBalancerNames.member.{0}'.format(number))
                elb = self.elb_backend.get_load_balancer(load_balancer_name)
                if not elb:
                    raise LoadBalancerNotFoundError(load_balancer_name)

                key = 'Tag.member.{0}.Key'.format(number)
                for t_key, t_val in self.querystring.items():
                    if t_key.startswith('Tags.member.'):
                        if t_key.split('.')[3] == 'Key':
                            elb.remove_tag(t_val[0])

        template = self.response_template(REMOVE_TAGS_TEMPLATE)
        return template.render()

    def describe_tags(self):
        elbs = []
        for key, value in self.querystring.items():
            if "LoadBalancerNames.member" in key:
                number = key.split('.')[2]
                load_balancer_name = self._get_param(
                    'LoadBalancerNames.member.{0}'.format(number))
                elb = self.elb_backend.get_load_balancer(load_balancer_name)
                if not elb:
                    raise LoadBalancerNotFoundError(load_balancer_name)
                elbs.append(elb)

        template = self.response_template(DESCRIBE_TAGS_TEMPLATE)
        return template.render(load_balancers=elbs)

    def _add_tags(self, elb):
        tag_values = []
        tag_keys = []

        for t_key, t_val in sorted(self.querystring.items()):
            if t_key.startswith('Tags.member.'):
                if t_key.split('.')[3] == 'Key':
                    tag_keys.extend(t_val)
                elif t_key.split('.')[3] == 'Value':
                    tag_values.extend(t_val)

        counts = {}
        for i in tag_keys:
            counts[i] = tag_keys.count(i)

        counts = sorted(counts.items(), key=lambda i: i[1], reverse=True)

        if counts and counts[0][1] > 1:
            # We have dupes...
            raise DuplicateTagKeysError(counts[0])

        for tag_key, tag_value in zip(tag_keys, tag_values):
            elb.add_tag(tag_key, tag_value)


ADD_TAGS_TEMPLATE = """<AddTagsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <AddTagsResult/>
  <ResponseMetadata>
    <RequestId>360e81f7-1100-11e4-b6ed-0f30EXAMPLE</RequestId>
  </ResponseMetadata>
</AddTagsResponse>"""

REMOVE_TAGS_TEMPLATE = """<RemoveTagsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <RemoveTagsResult/>
  <ResponseMetadata>
    <RequestId>360e81f7-1100-11e4-b6ed-0f30EXAMPLE</RequestId>
  </ResponseMetadata>
</RemoveTagsResponse>"""

DESCRIBE_TAGS_TEMPLATE = """<DescribeTagsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DescribeTagsResult>
    <TagDescriptions>
      {% for elb in load_balancers %}
      <member>
        <LoadBalancerName>{{ elb.name }}</LoadBalancerName>
        <Tags>
          {% for key, value in elb.tags.items() %}
          <member>
            <Value>{{ value }}</Value>
            <Key>{{ key }}</Key>
          </member>
          {% endfor %}
        </Tags>
      </member>
      {% endfor %}
    </TagDescriptions>
  </DescribeTagsResult>
  <ResponseMetadata>
    <RequestId>360e81f7-1100-11e4-b6ed-0f30EXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeTagsResponse>"""


CREATE_LOAD_BALANCER_TEMPLATE = """<CreateLoadBalancerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <CreateLoadBalancerResult>
    <DNSName>{{ load_balancer.dns_name }}</DNSName>
  </CreateLoadBalancerResult>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
</CreateLoadBalancerResponse>"""

CREATE_LOAD_BALANCER_LISTENERS_TEMPLATE = """<CreateLoadBalancerListenersResponse xmlns="http://elasticloadbalancing.amazon aws.com/doc/2012-06-01/">
  <CreateLoadBalancerListenersResult/>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
</CreateLoadBalancerListenersResponse>"""

DELETE_LOAD_BALANCER_TEMPLATE = """<DeleteLoadBalancerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DeleteLoadBalancerResult/>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
</DeleteLoadBalancerResponse>"""

DESCRIBE_LOAD_BALANCERS_TEMPLATE = """<DescribeLoadBalancersResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DescribeLoadBalancersResult>
    <LoadBalancerDescriptions>
      {% for load_balancer in load_balancers %}
        <member>
          <SecurityGroups>
            {% for security_group_id in load_balancer.security_groups %}
            <member>{{ security_group_id }}</member>
            {% endfor %}
          </SecurityGroups>
          <LoadBalancerName>{{ load_balancer.name }}</LoadBalancerName>
          <CreatedTime>{{ load_balancer.created_time }}</CreatedTime>
          <HealthCheck>
            {% if load_balancer.health_check %}
              <Interval>{{ load_balancer.health_check.interval }}</Interval>
              <Target>{{ load_balancer.health_check.target }}</Target>
              <HealthyThreshold>{{ load_balancer.health_check.healthy_threshold }}</HealthyThreshold>
              <Timeout>{{ load_balancer.health_check.timeout }}</Timeout>
              <UnhealthyThreshold>{{ load_balancer.health_check.unhealthy_threshold }}</UnhealthyThreshold>
            {% endif %}
          </HealthCheck>
          {% if load_balancer.vpc_id %}
          <VPCId>{{ load_balancer.vpc_id }}</VPCId>
          {% else %}
          <VPCId />
          {% endif %}
          <ListenerDescriptions>
            {% for listener in load_balancer.listeners %}
              <member>
                <PolicyNames>
                  {% for policy_name in listener.policy_names %}
                    <member>{{ policy_name }}</member>
                  {% endfor %}
                </PolicyNames>
                <Listener>
                  <Protocol>{{ listener.protocol }}</Protocol>
                  <LoadBalancerPort>{{ listener.load_balancer_port }}</LoadBalancerPort>
                  <InstanceProtocol>{{ listener.protocol }}</InstanceProtocol>
                  <InstancePort>{{ listener.instance_port }}</InstancePort>
                  <SSLCertificateId>{{ listener.ssl_certificate_id }}</SSLCertificateId>
                </Listener>
              </member>
            {% endfor %}
          </ListenerDescriptions>
          <Instances>
            {% for instance_id in load_balancer.instance_ids %}
              <member>
                <InstanceId>{{ instance_id }}</InstanceId>
              </member>
            {% endfor %}
          </Instances>
          <Policies>
            <AppCookieStickinessPolicies>
            {% if load_balancer.policies.app_cookie_stickiness_policies %}
                {% for policy in load_balancer.policies.app_cookie_stickiness_policies %}
                    <member>
                        <CookieName>{{ policy.cookie_name }}</CookieName>
                        <PolicyName>{{ policy.policy_name }}</PolicyName>
                    </member>
                {% endfor %}
            {% endif %}
            </AppCookieStickinessPolicies>
            <LBCookieStickinessPolicies>
            {% if load_balancer.policies.lb_cookie_stickiness_policies %}
                {% for policy in load_balancer.policies.lb_cookie_stickiness_policies %}
                    <member>
                        {% if policy.cookie_expiration_period %}
                        <CookieExpirationPeriod>{{ policy.cookie_expiration_period }}</CookieExpirationPeriod>
                        {% endif %}
                        <PolicyName>{{ policy.policy_name }}</PolicyName>
                    </member>
                {% endfor %}
            {% endif %}
            </LBCookieStickinessPolicies>
            <OtherPolicies>
            {% if load_balancer.policies.other_policies %}
                {% for policy in load_balancer.policies.other_policies %}
                    <member>{{ policy.policy_name }}</member>
                {% endfor %}
            {% endif %}
            </OtherPolicies>
          </Policies>
          <AvailabilityZones>
            {% for zone in load_balancer.zones %}
              <member>{{ zone }}</member>
            {% endfor %}
          </AvailabilityZones>
          <CanonicalHostedZoneName>{{ load_balancer.dns_name }}</CanonicalHostedZoneName>
          <CanonicalHostedZoneNameID>Z3ZONEID</CanonicalHostedZoneNameID>
          <Scheme>{{ load_balancer.scheme }}</Scheme>
          <DNSName>{{ load_balancer.dns_name }}</DNSName>
          <BackendServerDescriptions>
          {% for backend in load_balancer.backends %}
            {% if backend.policy_names %}
            <member>
                <InstancePort>{{ backend.instance_port }}</InstancePort>
                <PolicyNames>
                    {% for policy in backend.policy_names %}
                    <member>{{ policy }}</member>
                    {% endfor %}
                </PolicyNames>
            </member>
            {% endif %}
          {% endfor %}
          </BackendServerDescriptions>
          <Subnets>
          {% for subnet in load_balancer.subnets %}
              <member>{{ subnet }}</member>
          {% endfor %}
          </Subnets>
        </member>
      {% endfor %}
    </LoadBalancerDescriptions>
    {% if marker %}
    <NextMarker>{{ marker }}</NextMarker>
    {% endif %}
  </DescribeLoadBalancersResult>
  <ResponseMetadata>
    <RequestId>f9880f01-7852-629d-a6c3-3ae2-666a409287e6dc0c</RequestId>
  </ResponseMetadata>
</DescribeLoadBalancersResponse>"""

APPLY_SECURITY_GROUPS_TEMPLATE = """<ApplySecurityGroupsToLoadBalancerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <ApplySecurityGroupsToLoadBalancerResult>
    <SecurityGroups>
      {% for security_group_id in security_group_ids %}
      <member>{{ security_group_id }}</member>
      {% endfor %}
    </SecurityGroups>
  </ApplySecurityGroupsToLoadBalancerResult>
  <ResponseMetadata>
    <RequestId>f9880f01-7852-629d-a6c3-3ae2-666a409287e6dc0c</RequestId>
  </ResponseMetadata>
</ApplySecurityGroupsToLoadBalancerResponse>"""

CONFIGURE_HEALTH_CHECK_TEMPLATE = """<ConfigureHealthCheckResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <ConfigureHealthCheckResult>
    <HealthCheck>
      <Interval>{{ check.interval }}</Interval>
      <Target>{{ check.target }}</Target>
      <HealthyThreshold>{{ check.healthy_threshold }}</HealthyThreshold>
      <Timeout>{{ check.timeout }}</Timeout>
      <UnhealthyThreshold>{{ check.unhealthy_threshold }}</UnhealthyThreshold>
    </HealthCheck>
  </ConfigureHealthCheckResult>
  <ResponseMetadata>
    <RequestId>f9880f01-7852-629d-a6c3-3ae2-666a409287e6dc0c</RequestId>
  </ResponseMetadata>
</ConfigureHealthCheckResponse>"""

REGISTER_INSTANCES_TEMPLATE = """<RegisterInstancesWithLoadBalancerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <RegisterInstancesWithLoadBalancerResult>
    <Instances>
      {% for instance_id in load_balancer.instance_ids %}
        <member>
          <InstanceId>{{ instance_id }}</InstanceId>
        </member>
      {% endfor %}
    </Instances>
  </RegisterInstancesWithLoadBalancerResult>
  <ResponseMetadata>
    <RequestId>f9880f01-7852-629d-a6c3-3ae2-666a409287e6dc0c</RequestId>
  </ResponseMetadata>
</RegisterInstancesWithLoadBalancerResponse>"""

DEREGISTER_INSTANCES_TEMPLATE = """<DeregisterInstancesFromLoadBalancerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DeregisterInstancesFromLoadBalancerResult>
    <Instances>
      {% for instance_id in load_balancer.instance_ids %}
        <member>
          <InstanceId>{{ instance_id }}</InstanceId>
        </member>
      {% endfor %}
    </Instances>
  </DeregisterInstancesFromLoadBalancerResult>
  <ResponseMetadata>
    <RequestId>f9880f01-7852-629d-a6c3-3ae2-666a409287e6dc0c</RequestId>
  </ResponseMetadata>
</DeregisterInstancesFromLoadBalancerResponse>"""

SET_LOAD_BALANCER_SSL_CERTIFICATE = """<SetLoadBalancerListenerSSLCertificateResponse xmlns="http://elasticloadbalan cing.amazonaws.com/doc/2012-06-01/">
 <SetLoadBalancerListenerSSLCertificateResult/>
<ResponseMetadata>
    <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
</ResponseMetadata>
</SetLoadBalancerListenerSSLCertificateResponse>"""


DELETE_LOAD_BALANCER_LISTENERS = """<DeleteLoadBalancerListenersResponse xmlns="http://elasticloadbalan cing.amazonaws.com/doc/2012-06-01/">
 <DeleteLoadBalancerListenersResult/>
<ResponseMetadata>
    <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
</ResponseMetadata>
</DeleteLoadBalancerListenersResponse>"""

DESCRIBE_ATTRIBUTES_TEMPLATE = """<DescribeLoadBalancerAttributesResponse  xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DescribeLoadBalancerAttributesResult>
    <LoadBalancerAttributes>
      <AccessLog>
        <Enabled>{{ attributes.access_log.enabled }}</Enabled>
        {% if attributes.access_log.enabled %}
        <S3BucketName>{{ attributes.access_log.s3_bucket_name }}</S3BucketName>
        <S3BucketPrefix>{{ attributes.access_log.s3_bucket_prefix }}</S3BucketPrefix>
        <EmitInterval>{{ attributes.access_log.emit_interval }}</EmitInterval>
        {% endif %}
      </AccessLog>
      <ConnectionSettings>
        <IdleTimeout>{{ attributes.connecting_settings.idle_timeout }}</IdleTimeout>
      </ConnectionSettings>
      <CrossZoneLoadBalancing>
        <Enabled>{{ attributes.cross_zone_load_balancing.enabled }}</Enabled>
      </CrossZoneLoadBalancing>
      <ConnectionDraining>
        {% if attributes.connection_draining.enabled %}
        <Enabled>true</Enabled>
        <Timeout>{{ attributes.connection_draining.timeout }}</Timeout>
        {% else %}
        <Enabled>false</Enabled>
        {% endif %}
      </ConnectionDraining>
    </LoadBalancerAttributes>
  </DescribeLoadBalancerAttributesResult>
  <ResponseMetadata>
    <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeLoadBalancerAttributesResponse>
"""

MODIFY_ATTRIBUTES_TEMPLATE = """<ModifyLoadBalancerAttributesResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <ModifyLoadBalancerAttributesResult>
  <LoadBalancerName>{{ load_balancer.name }}</LoadBalancerName>
    <LoadBalancerAttributes>
      <AccessLog>
        <Enabled>{{ attributes.access_log.enabled }}</Enabled>
        {% if attributes.access_log.enabled %}
        <S3BucketName>{{ attributes.access_log.s3_bucket_name }}</S3BucketName>
        <S3BucketPrefix>{{ attributes.access_log.s3_bucket_prefix }}</S3BucketPrefix>
        <EmitInterval>{{ attributes.access_log.emit_interval }}</EmitInterval>
        {% endif %}
      </AccessLog>
      <ConnectionSettings>
        <IdleTimeout>{{ attributes.connecting_settings.idle_timeout }}</IdleTimeout>
      </ConnectionSettings>
      <CrossZoneLoadBalancing>
        <Enabled>{{ attributes.cross_zone_load_balancing.enabled }}</Enabled>
      </CrossZoneLoadBalancing>
      <ConnectionDraining>
        {% if attributes.connection_draining.enabled %}
        <Enabled>true</Enabled>
        <Timeout>{{ attributes.connection_draining.timeout }}</Timeout>
        {% else %}
        <Enabled>false</Enabled>
        {% endif %}
      </ConnectionDraining>
    </LoadBalancerAttributes>
  </ModifyLoadBalancerAttributesResult>
  <ResponseMetadata>
    <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
  </ResponseMetadata>
</ModifyLoadBalancerAttributesResponse>
"""

CREATE_LOAD_BALANCER_POLICY_TEMPLATE = """<CreateLoadBalancerPolicyResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <CreateLoadBalancerPolicyResult/>
  <ResponseMetadata>
      <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
  </ResponseMetadata>
</CreateLoadBalancerPolicyResponse>
"""

SET_LOAD_BALANCER_POLICIES_OF_LISTENER_TEMPLATE = """<SetLoadBalancerPoliciesOfListenerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
    <SetLoadBalancerPoliciesOfListenerResult/>
    <ResponseMetadata>
        <RequestId>07b1ecbc-1100-11e3-acaf-dd7edEXAMPLE</RequestId>
    </ResponseMetadata>
</SetLoadBalancerPoliciesOfListenerResponse>
"""

SET_LOAD_BALANCER_POLICIES_FOR_BACKEND_SERVER_TEMPLATE = """<SetLoadBalancerPoliciesForBackendServerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
    <SetLoadBalancerPoliciesForBackendServerResult/>
    <ResponseMetadata>
        <RequestId>0eb9b381-dde0-11e2-8d78-6ddbaEXAMPLE</RequestId>
    </ResponseMetadata>
</SetLoadBalancerPoliciesForBackendServerResponse>
"""

DESCRIBE_INSTANCE_HEALTH_TEMPLATE = """<DescribeInstanceHealthResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DescribeInstanceHealthResult>
    <InstanceStates>
      {% for instance_id in instance_ids %}
      <member>
        <Description>N/A</Description>
        <InstanceId>{{ instance_id }}</InstanceId>
        <State>InService</State>
        <ReasonCode>N/A</ReasonCode>
      </member>
      {% endfor %}
    </InstanceStates>
  </DescribeInstanceHealthResult>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeInstanceHealthResponse>"""
