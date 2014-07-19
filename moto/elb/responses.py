from jinja2 import Template

from moto.core.responses import BaseResponse
from .models import elb_backend


class ELBResponse(BaseResponse):

    def create_load_balancer(self):
        """
        u'Scheme': [u'internet-facing'],
        """
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        availability_zones = [value[0] for key, value in self.querystring.items() if "AvailabilityZones.member" in key]
        ports = []
        port_index = 1
        while True:
            try:
                protocol = self.querystring['Listeners.member.{0}.Protocol'.format(port_index)][0]
            except KeyError:
                break
            lb_port = self.querystring['Listeners.member.{0}.LoadBalancerPort'.format(port_index)][0]
            instance_port = self.querystring['Listeners.member.{0}.InstancePort'.format(port_index)][0]
            ssl_certificate_id = self.querystring.get('Listeners.member.{0}.SSLCertificateId'.format(port_index)[0], None)
            ports.append([protocol, lb_port, instance_port, ssl_certificate_id])
            port_index += 1

        elb_backend.create_load_balancer(
            name=load_balancer_name,
            zones=availability_zones,
            ports=ports,
        )
        template = Template(CREATE_LOAD_BALANCER_TEMPLATE)
        return template.render()

    def create_load_balancer_listeners(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        ports = []
        port_index = 1
        while True:
            try:
                protocol = self.querystring['Listeners.member.{0}.Protocol'.format(port_index)][0]
            except KeyError:
                break
            lb_port = self.querystring['Listeners.member.{0}.LoadBalancerPort'.format(port_index)][0]
            instance_port = self.querystring['Listeners.member.{0}.InstancePort'.format(port_index)][0]
            ssl_certificate_id = self.querystring.get('Listeners.member.{0}.SSLCertificateId'.format(port_index)[0], None)
            ports.append([protocol, lb_port, instance_port, ssl_certificate_id])
            port_index += 1

        elb_backend.create_load_balancer_listeners(name=load_balancer_name, ports=ports)

        template = Template(CREATE_LOAD_BALANCER_LISTENERS_TEMPLATE)
        return template.render()

    def describe_load_balancers(self):
        names = [value[0] for key, value in self.querystring.items() if "LoadBalancerNames.member" in key]
        load_balancers = elb_backend.describe_load_balancers(names)
        template = Template(DESCRIBE_LOAD_BALANCERS_TEMPLATE)
        return template.render(load_balancers=load_balancers)

    def delete_load_balancer_listeners(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        ports = []
        port_index = 1
        while True:
            try:
                port = self.querystring['LoadBalancerPorts.member.{0}'.format(port_index)][0]
            except KeyError:
                break

            port_index += 1
            ports.append(int(port))

        elb_backend.delete_load_balancer_listeners(load_balancer_name, ports)
        template = Template(DELETE_LOAD_BALANCER_LISTENERS)
        return template.render()

    def delete_load_balancer(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        elb_backend.delete_load_balancer(load_balancer_name)
        template = Template(DELETE_LOAD_BALANCER_TEMPLATE)
        return template.render()

    def configure_health_check(self):
        check = elb_backend.configure_health_check(
            load_balancer_name=self.querystring.get('LoadBalancerName')[0],
            timeout=self.querystring.get('HealthCheck.Timeout')[0],
            healthy_threshold=self.querystring.get('HealthCheck.HealthyThreshold')[0],
            unhealthy_threshold=self.querystring.get('HealthCheck.UnhealthyThreshold')[0],
            interval=self.querystring.get('HealthCheck.Interval')[0],
            target=self.querystring.get('HealthCheck.Target')[0],
        )
        template = Template(CONFIGURE_HEALTH_CHECK_TEMPLATE)
        return template.render(check=check)

    def register_instances_with_load_balancer(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        instance_ids = [value[0] for key, value in self.querystring.items() if "Instances.member" in key]
        template = Template(REGISTER_INSTANCES_TEMPLATE)
        load_balancer = elb_backend.register_instances(load_balancer_name, instance_ids)
        return template.render(load_balancer=load_balancer)

    def set_load_balancer_listener_sslcertificate(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        ssl_certificate_id = self.querystring['SSLCertificateId'][0]
        lb_port = self.querystring['LoadBalancerPort'][0]

        elb_backend.set_load_balancer_listener_sslcertificate(load_balancer_name, lb_port, ssl_certificate_id)

        template = Template(SET_LOAD_BALANCER_SSL_CERTIFICATE)
        return template.render()

    def deregister_instances_from_load_balancer(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        instance_ids = [value[0] for key, value in self.querystring.items() if "Instances.member" in key]
        template = Template(DEREGISTER_INSTANCES_TEMPLATE)
        load_balancer = elb_backend.deregister_instances(load_balancer_name, instance_ids)
        return template.render(load_balancer=load_balancer)

CREATE_LOAD_BALANCER_TEMPLATE = """<CreateLoadBalancerResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
    <DNSName>tests.us-east-1.elb.amazonaws.com</DNSName>
</CreateLoadBalancerResult>"""

CREATE_LOAD_BALANCER_LISTENERS_TEMPLATE = """<CreateLoadBalancerListenersResponse xmlns="http://elasticloadbalancing.amazon aws.com/doc/2012-06-01/">
  <CreateLoadBalancerListenersResult/>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
</CreateLoadBalancerListenersResponse>"""

DELETE_LOAD_BALANCER_TEMPLATE = """<DeleteLoadBalancerResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
</DeleteLoadBalancerResult>"""

DESCRIBE_LOAD_BALANCERS_TEMPLATE = """<DescribeLoadBalancersResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DescribeLoadBalancersResult>
    <LoadBalancerDescriptions>
      {% for load_balancer in load_balancers %}
        <member>
          <SecurityGroups>
          </SecurityGroups>
          <LoadBalancerName>{{ load_balancer.name }}</LoadBalancerName>
          <CreatedTime>2013-01-01T00:00:00.19000Z</CreatedTime>
          <HealthCheck>
            {% if load_balancer.health_check %}
              <Interval>{{ load_balancer.health_check.interval }}</Interval>
              <Target>{{ load_balancer.health_check.target }}</Target>
              <HealthyThreshold>{{ load_balancer.health_check.healthy_threshold }}</HealthyThreshold>
              <Timeout>{{ load_balancer.health_check.timeout }}</Timeout>
              <UnhealthyThreshold>{{ load_balancer.health_check.unhealthy_threshold }}</UnhealthyThreshold>
            {% endif %}
          </HealthCheck>
          <VPCId>vpc-56e10e3d</VPCId>
          <ListenerDescriptions>
            {% for listener in load_balancer.listeners %}
              <member>
                <PolicyNames>
                  <member>AWSConsolePolicy-1</member>
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
            <AppCookieStickinessPolicies/>
            <OtherPolicies/>
            <LBCookieStickinessPolicies>
              <member>
                <PolicyName>AWSConsolePolicy-1</PolicyName>
                <CookieExpirationPeriod>30</CookieExpirationPeriod>
              </member>
            </LBCookieStickinessPolicies>
          </Policies>
          <AvailabilityZones>
            {% for zone in load_balancer.zones %}
              <member>{{ zone }}</member>
            {% endfor %}
          </AvailabilityZones>
          <CanonicalHostedZoneName>tests.us-east-1.elb.amazonaws.com</CanonicalHostedZoneName>
          <CanonicalHostedZoneNameID>Z3ZONEID</CanonicalHostedZoneNameID>
          <Scheme>internet-facing</Scheme>
          <DNSName>tests.us-east-1.elb.amazonaws.com</DNSName>
          <BackendServerDescriptions/>
          <Subnets>
          </Subnets>
        </member>
      {% endfor %}
    </LoadBalancerDescriptions>
  </DescribeLoadBalancersResult>
  <ResponseMetadata>
    <RequestId>f9880f01-7852-629d-a6c3-3ae2-666a409287e6dc0c</RequestId>
  </ResponseMetadata>
</DescribeLoadBalancersResponse>"""

CONFIGURE_HEALTH_CHECK_TEMPLATE = """<ConfigureHealthCheckResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <HealthCheck>
    <Interval>{{ check.interval }}</Interval>
    <Target>{{ check.target }}</Target>
    <HealthyThreshold>{{ check.healthy_threshold }}</HealthyThreshold>
    <Timeout>{{ check.timeout }}</Timeout>
    <UnhealthyThreshold>{{ check.unhealthy_threshold }}</UnhealthyThreshold>
  </HealthCheck>
</ConfigureHealthCheckResult>"""

REGISTER_INSTANCES_TEMPLATE = """<RegisterInstancesWithLoadBalancerResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <Instances>
    {% for instance_id in load_balancer.instance_ids %}
      <member>
        <InstanceId>{{ instance_id }}</InstanceId>
      </member>
    {% endfor %}
  </Instances>
</RegisterInstancesWithLoadBalancerResult>"""

DEREGISTER_INSTANCES_TEMPLATE = """<DeregisterInstancesWithLoadBalancerResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <Instances>
    {% for instance_id in load_balancer.instance_ids %}
      <member>
        <InstanceId>{{ instance_id }}</InstanceId>
      </member>
    {% endfor %}
  </Instances>
</DeregisterInstancesWithLoadBalancerResult>"""

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
