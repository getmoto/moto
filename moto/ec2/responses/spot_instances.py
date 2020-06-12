from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring


class SpotInstances(BaseResponse):
    def cancel_spot_instance_requests(self):
        request_ids = self._get_multi_param("SpotInstanceRequestId")
        if self.is_not_dryrun("CancelSpotInstance"):
            requests = self.ec2_backend.cancel_spot_instance_requests(request_ids)
            template = self.response_template(CANCEL_SPOT_INSTANCES_TEMPLATE)
            return template.render(requests=requests)

    def create_spot_datafeed_subscription(self):
        if self.is_not_dryrun("CreateSpotDatafeedSubscription"):
            raise NotImplementedError(
                "SpotInstances.create_spot_datafeed_subscription is not yet implemented"
            )

    def delete_spot_datafeed_subscription(self):
        if self.is_not_dryrun("DeleteSpotDatafeedSubscription"):
            raise NotImplementedError(
                "SpotInstances.delete_spot_datafeed_subscription is not yet implemented"
            )

    def describe_spot_datafeed_subscription(self):
        raise NotImplementedError(
            "SpotInstances.describe_spot_datafeed_subscription is not yet implemented"
        )

    def describe_spot_instance_requests(self):
        filters = filters_from_querystring(self.querystring)
        requests = self.ec2_backend.describe_spot_instance_requests(filters=filters)
        template = self.response_template(DESCRIBE_SPOT_INSTANCES_TEMPLATE)
        return template.render(requests=requests)

    def describe_spot_price_history(self):
        raise NotImplementedError(
            "SpotInstances.describe_spot_price_history is not yet implemented"
        )

    def request_spot_instances(self):
        price = self._get_param("SpotPrice")
        image_id = self._get_param("LaunchSpecification.ImageId")
        count = self._get_int_param("InstanceCount", 1)
        type = self._get_param("Type", "one-time")
        valid_from = self._get_param("ValidFrom")
        valid_until = self._get_param("ValidUntil")
        launch_group = self._get_param("LaunchGroup")
        availability_zone_group = self._get_param("AvailabilityZoneGroup")
        key_name = self._get_param("LaunchSpecification.KeyName")
        security_groups = self._get_multi_param("LaunchSpecification.SecurityGroup")
        user_data = self._get_param("LaunchSpecification.UserData")
        instance_type = self._get_param("LaunchSpecification.InstanceType", "m1.small")
        placement = self._get_param("LaunchSpecification.Placement.AvailabilityZone")
        kernel_id = self._get_param("LaunchSpecification.KernelId")
        ramdisk_id = self._get_param("LaunchSpecification.RamdiskId")
        monitoring_enabled = self._get_param("LaunchSpecification.Monitoring.Enabled")
        subnet_id = self._get_param("LaunchSpecification.SubnetId")

        if self.is_not_dryrun("RequestSpotInstance"):
            requests = self.ec2_backend.request_spot_instances(
                price=price,
                image_id=image_id,
                count=count,
                type=type,
                valid_from=valid_from,
                valid_until=valid_until,
                launch_group=launch_group,
                availability_zone_group=availability_zone_group,
                key_name=key_name,
                security_groups=security_groups,
                user_data=user_data,
                instance_type=instance_type,
                placement=placement,
                kernel_id=kernel_id,
                ramdisk_id=ramdisk_id,
                monitoring_enabled=monitoring_enabled,
                subnet_id=subnet_id,
            )

            template = self.response_template(REQUEST_SPOT_INSTANCES_TEMPLATE)
            return template.render(requests=requests)


REQUEST_SPOT_INSTANCES_TEMPLATE = """<RequestSpotInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <spotInstanceRequestSet>
    {% for request in requests %}
    <item>
      <spotInstanceRequestId>{{ request.id }}</spotInstanceRequestId>
      <spotPrice>{{ request.price }}</spotPrice>
      <type>{{ request.type }}</type>
      <state>{{ request.state }}</state>
      <status>
        <code>pending-evaluation</code>
        <updateTime>2015-01-01T00:00:00.000Z</updateTime>
        <message>Your Spot request has been submitted for review, and is pending evaluation.</message>
      </status>
      <instanceId>{{ request.instance_id }}</instanceId>
      <availabilityZoneGroup>{{ request.availability_zone_group }}</availabilityZoneGroup>
      <launchSpecification>
        <imageId>{{ request.launch_specification.image_id }}</imageId>
        <keyName>{{ request.launch_specification.key_name }}</keyName>
        <groupSet>
          {% for group in request.launch_specification.groups %}
          <item>
            <groupId>{{ group.id }}</groupId>
            <groupName>{{ group.name }}</groupName>
          </item>
          {% endfor %}
        </groupSet>
        <kernelId>{{ request.launch_specification.kernel }}</kernelId>
        <ramdiskId>{{ request.launch_specification.ramdisk }}</ramdiskId>
        <subnetId>{{ request.launch_specification.subnet_id }}</subnetId>
        <instanceType>{{ request.launch_specification.instance_type }}</instanceType>
        <blockDeviceMapping/>
        <monitoring>
          <enabled>{{ request.launch_specification.monitored }}</enabled>
        </monitoring>
        <ebsOptimized>{{ request.launch_specification.ebs_optimized }}</ebsOptimized>
        <PlacementRequestType>
          <availabilityZone>{{ request.launch_specification.placement }}</availabilityZone>
          <groupName></groupName>
        </PlacementRequestType>
      </launchSpecification>
      <launchGroup>{{ request.launch_group }}</launchGroup>
      <createTime>2015-01-01T00:00:00.000Z</createTime>
      {% if request.valid_from %}
      <validFrom>{{ request.valid_from }}</validFrom>
      {% endif %}
      {% if request.valid_until %}
      <validUntil>{{ request.valid_until }}</validUntil>
      {% endif %}
      <productDescription>Linux/UNIX</productDescription>
    </item>
    {% endfor %}
 </spotInstanceRequestSet>
</RequestSpotInstancesResponse>"""

DESCRIBE_SPOT_INSTANCES_TEMPLATE = """<DescribeSpotInstanceRequestsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <spotInstanceRequestSet>
    {% for request in requests %}
    <item>
      <spotInstanceRequestId>{{ request.id }}</spotInstanceRequestId>
      <spotPrice>{{ request.price }}</spotPrice>
      <type>{{ request.type }}</type>
      <state>{{ request.state }}</state>
      <status>
        <code>pending-evaluation</code>
        <updateTime>2015-01-01T00:00:00.000Z</updateTime>
        <message>Your Spot request has been submitted for review, and is pending evaluation.</message>
      </status>
      <instanceId>{{ request.instance_id }}</instanceId>
      {% if request.availability_zone_group %}
        <availabilityZoneGroup>{{ request.availability_zone_group }}</availabilityZoneGroup>
      {% endif %}
      <launchSpecification>
        <imageId>{{ request.launch_specification.image_id }}</imageId>
        {% if request.launch_specification.key_name %}
          <keyName>{{ request.launch_specification.key_name }}</keyName>
        {% endif %}
        <groupSet>
          {% for group in request.launch_specification.groups %}
          <item>
            <groupId>{{ group.id }}</groupId>
            <groupName>{{ group.name }}</groupName>
          </item>
          {% endfor %}
        </groupSet>
        {% if request.launch_specification.kernel %}
        <kernelId>{{ request.launch_specification.kernel }}</kernelId>
        {% endif %}
        {% if request.launch_specification.ramdisk %}
        <ramdiskId>{{ request.launch_specification.ramdisk }}</ramdiskId>
        {% endif %}
        {% if request.launch_specification.subnet_id %}
        <subnetId>{{ request.launch_specification.subnet_id }}</subnetId>
        {% endif %}
        <instanceType>{{ request.launch_specification.instance_type }}</instanceType>
        <blockDeviceMapping/>
        <monitoring>
          <enabled>{{ request.launch_specification.monitored }}</enabled>
        </monitoring>
        <ebsOptimized>{{ request.launch_specification.ebs_optimized }}</ebsOptimized>
        {% if request.launch_specification.placement %}
          <PlacementRequestType>
            <availabilityZone>{{ request.launch_specification.placement }}</availabilityZone>
            <groupName></groupName>
          </PlacementRequestType>
        {% endif %}
      </launchSpecification>
      <tagSet>
        {% for tag in request.get_tags() %}
          <item>
            <resourceId>{{ tag.resource_id }}</resourceId>
            <resourceType>{{ tag.resource_type }}</resourceType>
            <key>{{ tag.key }}</key>
            <value>{{ tag.value }}</value>
          </item>
        {% endfor %}
      </tagSet>
      {% if request.launch_group %}
        <launchGroup>{{ request.launch_group }}</launchGroup>
      {% endif %}
        <createTime>2015-01-01T00:00:00.000Z</createTime>
      {% if request.valid_from %}
        <validFrom>{{ request.valid_from }}</validFrom>
      {% endif %}
      {% if request.valid_until %}
        <validUntil>{{ request.valid_until }}</validUntil>
      {% endif %}
      <productDescription>Linux/UNIX</productDescription>
    </item>
    {% endfor %}
  </spotInstanceRequestSet>
</DescribeSpotInstanceRequestsResponse>"""

CANCEL_SPOT_INSTANCES_TEMPLATE = """<CancelSpotInstanceRequestsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <spotInstanceRequestSet>
    {% for request in requests %}
    <item>
      <spotInstanceRequestId>{{ request.id }}</spotInstanceRequestId>
      <state>cancelled</state>
    </item>
    {% endfor %}
  </spotInstanceRequestSet>
</CancelSpotInstanceRequestsResponse>"""
