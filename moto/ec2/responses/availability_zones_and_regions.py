from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend


class AvailabilityZonesAndRegions(BaseResponse):
    def describe_availability_zones(self):
        zones = ec2_backend.describe_availability_zones()
        template = Template(DESCRIBE_ZONES_RESPONSE)
        return template.render(zones=zones)

    def describe_regions(self):
        regions = ec2_backend.describe_regions()
        template = Template(DESCRIBE_REGIONS_RESPONSE)
        return template.render(regions=regions)

DESCRIBE_REGIONS_RESPONSE = """<DescribeRegionsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <regionInfo>
      {% for region in regions %}
          <item>
             <regionName>{{ region.name }}</regionName>
             <regionEndpoint>{{ region.endpoint }}</regionEndpoint>
          </item>
      {% endfor %}
   </regionInfo>
</DescribeRegionsResponse>"""

DESCRIBE_ZONES_RESPONSE = """<DescribeAvailabilityZonesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <availabilityZoneInfo>
   {% for zone in zones %}
       <item>
          <zoneName>{{ zone.name }}</zoneName>
          <zoneState>available</zoneState>
          <regionName>{{ zone.region_name }}</regionName>
          <messageSet/>
       </item>
   {% endfor %}
   </availabilityZoneInfo>
</DescribeAvailabilityZonesResponse>"""
