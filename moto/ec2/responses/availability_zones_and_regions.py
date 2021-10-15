from __future__ import unicode_literals
from moto.core.responses import BaseResponse


class AvailabilityZonesAndRegions(BaseResponse):
    def describe_availability_zones(self):
        self.error_on_dryrun()
        zones = self.ec2_backend.describe_availability_zones()
        template = self.response_template(DESCRIBE_ZONES_RESPONSE)
        return template.render(zones=zones)

    def describe_regions(self):
        self.error_on_dryrun()
        region_names = self._get_multi_param("RegionName")
        regions = self.ec2_backend.describe_regions(region_names)
        template = self.response_template(DESCRIBE_REGIONS_RESPONSE)
        return template.render(regions=regions)


DESCRIBE_REGIONS_RESPONSE = """<DescribeRegionsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <regionInfo>
      {% for region in regions %}
          <item>
             <regionName>{{ region.name }}</regionName>
             <regionEndpoint>{{ region.endpoint }}</regionEndpoint>
             <optInStatus>{{ region.opt_in_status }}</optInStatus>
          </item>
      {% endfor %}
   </regionInfo>
</DescribeRegionsResponse>"""

DESCRIBE_ZONES_RESPONSE = """<DescribeAvailabilityZonesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <availabilityZoneInfo>
   {% for zone in zones %}
       <item>
          <zoneName>{{ zone.name }}</zoneName>
          <zoneState>available</zoneState>
          <regionName>{{ zone.region_name }}</regionName>
          <zoneId>{{ zone.zone_id }}</zoneId>
          <messageSet/>
       </item>
   {% endfor %}
   </availabilityZoneInfo>
</DescribeAvailabilityZonesResponse>"""
