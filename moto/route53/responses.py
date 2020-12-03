from __future__ import unicode_literals
from jinja2 import Template
from six.moves.urllib.parse import parse_qs, urlparse

from moto.core.responses import BaseResponse
from .models import route53_backend
import xmltodict


class Route53(BaseResponse):
    def list_or_create_hostzone_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if request.method == "POST":
            elements = xmltodict.parse(self.body)
            if "HostedZoneConfig" in elements["CreateHostedZoneRequest"]:
                comment = elements["CreateHostedZoneRequest"]["HostedZoneConfig"][
                    "Comment"
                ]
                try:
                    # in boto3, this field is set directly in the xml
                    private_zone = elements["CreateHostedZoneRequest"][
                        "HostedZoneConfig"
                    ]["PrivateZone"]
                except KeyError:
                    # if a VPC subsection is only included in xmls params when private_zone=True,
                    # see boto: boto/route53/connection.py
                    private_zone = "VPC" in elements["CreateHostedZoneRequest"]
            else:
                comment = None
                private_zone = False

            name = elements["CreateHostedZoneRequest"]["Name"]

            if name[-1] != ".":
                name += "."

            new_zone = route53_backend.create_hosted_zone(
                name, comment=comment, private_zone=private_zone
            )
            template = Template(CREATE_HOSTED_ZONE_RESPONSE)
            return 201, headers, template.render(zone=new_zone)

        elif request.method == "GET":
            all_zones = route53_backend.get_all_hosted_zones()
            template = Template(LIST_HOSTED_ZONES_RESPONSE)
            return 200, headers, template.render(zones=all_zones)

    def list_hosted_zones_by_name_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)
        query_params = parse_qs(parsed_url.query)
        dnsname = query_params.get("dnsname")

        if dnsname:
            dnsname = dnsname[
                0
            ]  # parse_qs gives us a list, but this parameter doesn't repeat
            # return all zones with that name (there can be more than one)
            zones = [
                zone
                for zone in route53_backend.get_all_hosted_zones()
                if zone.name == dnsname
            ]
        else:
            # sort by names, but with domain components reversed
            # see http://boto3.readthedocs.io/en/latest/reference/services/route53.html#Route53.Client.list_hosted_zones_by_name

            def sort_key(zone):
                domains = zone.name.split(".")
                if domains[-1] == "":
                    domains = domains[-1:] + domains[:-1]
                return ".".join(reversed(domains))

            zones = route53_backend.get_all_hosted_zones()
            zones = sorted(zones, key=sort_key)

        template = Template(LIST_HOSTED_ZONES_BY_NAME_RESPONSE)
        return 200, headers, template.render(zones=zones)

    def get_or_delete_hostzone_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)
        zoneid = parsed_url.path.rstrip("/").rsplit("/", 1)[1]
        the_zone = route53_backend.get_hosted_zone(zoneid)
        if not the_zone:
            return 404, headers, "Zone %s not Found" % zoneid

        if request.method == "GET":
            template = Template(GET_HOSTED_ZONE_RESPONSE)

            return 200, headers, template.render(zone=the_zone)
        elif request.method == "DELETE":
            route53_backend.delete_hosted_zone(zoneid)
            return 200, headers, DELETE_HOSTED_ZONE_RESPONSE

    def rrset_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        parsed_url = urlparse(full_url)
        method = request.method

        zoneid = parsed_url.path.rstrip("/").rsplit("/", 2)[1]
        the_zone = route53_backend.get_hosted_zone(zoneid)
        if not the_zone:
            return 404, headers, "Zone %s Not Found" % zoneid

        if method == "POST":
            elements = xmltodict.parse(self.body)

            change_list = elements["ChangeResourceRecordSetsRequest"]["ChangeBatch"][
                "Changes"
            ]["Change"]
            if not isinstance(change_list, list):
                change_list = [
                    elements["ChangeResourceRecordSetsRequest"]["ChangeBatch"][
                        "Changes"
                    ]["Change"]
                ]

            for value in change_list:
                action = value["Action"]
                record_set = value["ResourceRecordSet"]

                cleaned_record_name = record_set["Name"].strip(".")
                cleaned_hosted_zone_name = the_zone.name.strip(".")

                if not cleaned_record_name.endswith(cleaned_hosted_zone_name):
                    error_msg = """
                    An error occurred (InvalidChangeBatch) when calling the ChangeResourceRecordSets operation:
                    RRSet with DNS name %s is not permitted in zone %s
                    """ % (
                        record_set["Name"],
                        the_zone.name,
                    )
                    return 400, headers, error_msg

                if not record_set["Name"].endswith("."):
                    record_set["Name"] += "."

                if action in ("CREATE", "UPSERT"):
                    if "ResourceRecords" in record_set:
                        resource_records = list(record_set["ResourceRecords"].values())[
                            0
                        ]
                        if not isinstance(resource_records, list):
                            # Depending on how many records there are, this may
                            # or may not be a list
                            resource_records = [resource_records]
                        record_set["ResourceRecords"] = [
                            x["Value"] for x in resource_records
                        ]
                    if action == "CREATE":
                        the_zone.add_rrset(record_set)
                    else:
                        the_zone.upsert_rrset(record_set)
                elif action == "DELETE":
                    if "SetIdentifier" in record_set:
                        the_zone.delete_rrset_by_id(record_set["SetIdentifier"])
                    else:
                        the_zone.delete_rrset(record_set)

            return 200, headers, CHANGE_RRSET_RESPONSE

        elif method == "GET":
            querystring = parse_qs(parsed_url.query)
            template = Template(LIST_RRSET_RESPONSE)
            start_type = querystring.get("type", [None])[0]
            start_name = querystring.get("name", [None])[0]
            record_sets = the_zone.get_record_sets(start_type, start_name)
            return 200, headers, template.render(record_sets=record_sets)

    def health_check_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        parsed_url = urlparse(full_url)
        method = request.method

        if method == "POST":
            properties = xmltodict.parse(self.body)["CreateHealthCheckRequest"][
                "HealthCheckConfig"
            ]
            health_check_args = {
                "ip_address": properties.get("IPAddress"),
                "port": properties.get("Port"),
                "type": properties["Type"],
                "resource_path": properties.get("ResourcePath"),
                "fqdn": properties.get("FullyQualifiedDomainName"),
                "search_string": properties.get("SearchString"),
                "request_interval": properties.get("RequestInterval"),
                "failure_threshold": properties.get("FailureThreshold"),
            }
            health_check = route53_backend.create_health_check(health_check_args)
            template = Template(CREATE_HEALTH_CHECK_RESPONSE)
            return 201, headers, template.render(health_check=health_check)
        elif method == "DELETE":
            health_check_id = parsed_url.path.split("/")[-1]
            route53_backend.delete_health_check(health_check_id)
            return 200, headers, DELETE_HEALTH_CHECK_RESPONSE
        elif method == "GET":
            template = Template(LIST_HEALTH_CHECKS_RESPONSE)
            health_checks = route53_backend.get_health_checks()
            return 200, headers, template.render(health_checks=health_checks)

    def not_implemented_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        action = ""
        if "tags" in full_url:
            action = "tags"
        elif "trafficpolicyinstances" in full_url:
            action = "policies"
        raise NotImplementedError(
            "The action for {0} has not been implemented for route 53".format(action)
        )

    def list_or_change_tags_for_resource_request(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        parsed_url = urlparse(full_url)
        id_ = parsed_url.path.split("/")[-1]
        type_ = parsed_url.path.split("/")[-2]

        if request.method == "GET":
            tags = route53_backend.list_tags_for_resource(id_)
            template = Template(LIST_TAGS_FOR_RESOURCE_RESPONSE)
            return (
                200,
                headers,
                template.render(resource_type=type_, resource_id=id_, tags=tags),
            )

        if request.method == "POST":
            tags = xmltodict.parse(self.body)["ChangeTagsForResourceRequest"]

            if "AddTags" in tags:
                tags = tags["AddTags"]
            elif "RemoveTagKeys" in tags:
                tags = tags["RemoveTagKeys"]

            route53_backend.change_tags_for_resource(id_, tags)
            template = Template(CHANGE_TAGS_FOR_RESOURCE_RESPONSE)

            return 200, headers, template.render()

    def get_change(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if request.method == "GET":
            parsed_url = urlparse(full_url)
            change_id = parsed_url.path.rstrip("/").rsplit("/", 1)[1]
            template = Template(GET_CHANGE_RESPONSE)
            return 200, headers, template.render(change_id=change_id)


LIST_TAGS_FOR_RESOURCE_RESPONSE = """
<ListTagsForResourceResponse xmlns="https://route53.amazonaws.com/doc/2015-01-01/">
    <ResourceTagSet>
        <ResourceType>{{resource_type}}</ResourceType>
        <ResourceId>{{resource_id}}</ResourceId>
        <Tags>
            {% for key, value in tags.items() %}
            <Tag>
                <Key>{{key}}</Key>
                <Value>{{value}}</Value>
            </Tag>
            {% endfor %}
        </Tags>
    </ResourceTagSet>
</ListTagsForResourceResponse>
"""

CHANGE_TAGS_FOR_RESOURCE_RESPONSE = """<ChangeTagsForResourceResponse xmlns="https://route53.amazonaws.com/doc/2015-01-01/">
</ChangeTagsForResourceResponse>
"""

LIST_RRSET_RESPONSE = """<ListResourceRecordSetsResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <ResourceRecordSets>
   {% for record_set in record_sets %}
      {{ record_set.to_xml() }}
   {% endfor %}
   </ResourceRecordSets>
   <IsTruncated>false</IsTruncated>
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
      <Config>
        {% if zone.comment %}
            <Comment>{{ zone.comment }}</Comment>
        {% endif %}
        <PrivateZone>{{ zone.private_zone }}</PrivateZone>
      </Config>
   </HostedZone>
   <DelegationSet>
      <NameServers>
         <NameServer>moto.test.com</NameServer>
      </NameServers>
   </DelegationSet>
</GetHostedZoneResponse>"""

CREATE_HOSTED_ZONE_RESPONSE = """<CreateHostedZoneResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <HostedZone>
      <Id>/hostedzone/{{ zone.id }}</Id>
      <Name>{{ zone.name }}</Name>
      <ResourceRecordSetCount>0</ResourceRecordSetCount>
      <Config>
        {% if zone.comment %}
            <Comment>{{ zone.comment }}</Comment>
        {% endif %}
        <PrivateZone>{{ zone.private_zone }}</PrivateZone>
      </Config>
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
         <Id>/hostedzone/{{ zone.id }}</Id>
         <Name>{{ zone.name }}</Name>
         <Config>
            {% if zone.comment %}
                <Comment>{{ zone.comment }}</Comment>
            {% endif %}
           <PrivateZone>{{ zone.private_zone }}</PrivateZone>
         </Config>
         <ResourceRecordSetCount>{{ zone.rrsets|count  }}</ResourceRecordSetCount>
      </HostedZone>
      {% endfor %}
   </HostedZones>
   <IsTruncated>false</IsTruncated>
</ListHostedZonesResponse>"""

LIST_HOSTED_ZONES_BY_NAME_RESPONSE = """<ListHostedZonesByNameResponse xmlns="https://route53.amazonaws.com/doc/2013-04-01/">
  <HostedZones>
      {% for zone in zones %}
      <HostedZone>
         <Id>/hostedzone/{{ zone.id }}</Id>
         <Name>{{ zone.name }}</Name>
         <Config>
            {% if zone.comment %}
                <Comment>{{ zone.comment }}</Comment>
            {% endif %}
           <PrivateZone>{{ zone.private_zone }}</PrivateZone>
         </Config>
         <ResourceRecordSetCount>{{ zone.rrsets|count  }}</ResourceRecordSetCount>
      </HostedZone>
      {% endfor %}
   </HostedZones>
   <IsTruncated>false</IsTruncated>
</ListHostedZonesByNameResponse>"""

CREATE_HEALTH_CHECK_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<CreateHealthCheckResponse xmlns="https://route53.amazonaws.com/doc/2013-04-01/">
  {{ health_check.to_xml() }}
</CreateHealthCheckResponse>"""

LIST_HEALTH_CHECKS_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<ListHealthChecksResponse xmlns="https://route53.amazonaws.com/doc/2013-04-01/">
   <HealthChecks>
   {% for health_check in health_checks %}
      {{ health_check.to_xml() }}
    {% endfor %}
   </HealthChecks>
   <IsTruncated>false</IsTruncated>
   <MaxItems>{{ health_checks|length }}</MaxItems>
</ListHealthChecksResponse>"""

DELETE_HEALTH_CHECK_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
    <DeleteHealthCheckResponse xmlns="https://route53.amazonaws.com/doc/2013-04-01/">
</DeleteHealthCheckResponse>"""

GET_CHANGE_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<GetChangeResponse xmlns="https://route53.amazonaws.com/doc/2013-04-01/">
   <ChangeInfo>
      <Status>INSYNC</Status>
      <SubmittedAt>2010-09-10T01:36:41.958Z</SubmittedAt>
      <Id>{{ change_id }}</Id>
   </ChangeInfo>
</GetChangeResponse>"""
