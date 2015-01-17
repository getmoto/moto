from __future__ import unicode_literals
from jinja2 import Template
from six.moves.urllib.parse import parse_qs, urlparse
from .models import route53_backend
import xmltodict


def list_or_create_hostzone_response(request, full_url, headers):

    if request.method == "POST":
        elements = xmltodict.parse(request.body)
        new_zone = route53_backend.create_hosted_zone(elements["CreateHostedZoneRequest"]["Name"])
        template = Template(CREATE_HOSTED_ZONE_RESPONSE)
        return 201, headers, template.render(zone=new_zone)

    elif request.method == "GET":
        all_zones = route53_backend.get_all_hosted_zones()
        template = Template(LIST_HOSTED_ZONES_RESPONSE)
        return 200, headers, template.render(zones=all_zones)


def get_or_delete_hostzone_response(request, full_url, headers):
    parsed_url = urlparse(full_url)
    zoneid = parsed_url.path.rstrip('/').rsplit('/', 1)[1]
    the_zone = route53_backend.get_hosted_zone(zoneid)
    if not the_zone:
        return 404, headers, "Zone %s not Found" % zoneid

    if request.method == "GET":
        template = Template(GET_HOSTED_ZONE_RESPONSE)
        return 200, headers, template.render(zone=the_zone)
    elif request.method == "DELETE":
        route53_backend.delete_hosted_zone(zoneid)
        return 200, headers, DELETE_HOSTED_ZONE_RESPONSE


def rrset_response(request, full_url, headers):
    parsed_url = urlparse(full_url)
    method = request.method

    zoneid = parsed_url.path.rstrip('/').rsplit('/', 2)[1]
    the_zone = route53_backend.get_hosted_zone(zoneid)
    if not the_zone:
        return 404, headers, "Zone %s Not Found" % zoneid

    if method == "POST":
        elements = xmltodict.parse(request.body)

        change_list = elements['ChangeResourceRecordSetsRequest']['ChangeBatch']['Changes']['Change']
        if not isinstance(change_list, list):
            change_list = [elements['ChangeResourceRecordSetsRequest']['ChangeBatch']['Changes']['Change']]

        for value in change_list:
            action = value['Action']
            record_set = value['ResourceRecordSet']
            if action == 'CREATE':
                record_set['ResourceRecords'] = [x['Value'] for x in record_set['ResourceRecords'].values()]
                the_zone.add_rrset(record_set)
            elif action == "DELETE":
                the_zone.delete_rrset(record_set["Name"])

        return 200, headers, CHANGE_RRSET_RESPONSE

    elif method == "GET":
        querystring = parse_qs(parsed_url.query)
        template = Template(LIST_RRSET_REPONSE)
        type_filter = querystring.get("type", [None])[0]
        name_filter = querystring.get("name", [None])[0]
        record_sets = the_zone.get_record_sets(type_filter, name_filter)
        return 200, headers, template.render(record_sets=record_sets)


LIST_RRSET_REPONSE = """<ListResourceRecordSetsResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <ResourceRecordSets>
   {% for record_set in record_sets %}
      {{ record_set.to_xml() }}
   {% endfor %}
   </ResourceRecordSets>
</ListResourceRecordSetsResponse>"""

CHANGE_RRSET_RESPONSE = """<ChangeResourceRecordSetsResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <ChangeInfo>
      <Status>INSYNC</Status>
      <SubmittedAt>2010-09-10T01:36:41.958Z</SubmittedAt>
      <Id>/change/C2682N5HXP0BZ4</Id>
   </ChangeInfo>
</ChangeResourceRecordSetsResponse>"""

DELETE_HOSTED_ZONE_RESPONSE = """<DeleteHostedZoneResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <ChangeInfo>
   </ChangeInfo>
</DeleteHostedZoneResponse>"""

GET_HOSTED_ZONE_RESPONSE = """<GetHostedZoneResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <HostedZone>
      <Id>/hostedzone/{{ zone.id }}</Id>
      <Name>{{ zone.name }}</Name>
      <ResourceRecordSetCount>{{ zone.rrsets|count }}</ResourceRecordSetCount>
   </HostedZone>
   <DelegationSet>
         <NameServer>moto.test.com</NameServer>
   </DelegationSet>
</GetHostedZoneResponse>"""

CREATE_HOSTED_ZONE_RESPONSE = """<CreateHostedZoneResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <HostedZone>
      <Id>/hostedzone/{{ zone.id }}</Id>
      <Name>{{ zone.name }}</Name>
      <ResourceRecordSetCount>0</ResourceRecordSetCount>
   </HostedZone>
   <DelegationSet>
      <NameServers>
         <NameServer>moto.test.com</NameServer>
      </NameServers>
   </DelegationSet>
</CreateHostedZoneResponse>"""

LIST_HOSTED_ZONES_RESPONSE = """<ListHostedZonesResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <HostedZones>
      {% for zone in zones %}
      <HostedZone>
         <Id>{{ zone.id }}</Id>
         <Name>{{ zone.name }}</Name>
         <ResourceRecordSetCount>{{ zone.rrsets|count  }}</ResourceRecordSetCount>
      </HostedZone>
      {% endfor %}
   </HostedZones>
</ListHostedZonesResponse>"""
