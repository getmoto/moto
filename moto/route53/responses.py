"""Handles Route53 API requests, invokes method and returns response."""
from functools import wraps
from urllib.parse import parse_qs, urlparse

from jinja2 import Template
import xmltodict

from moto.core.responses import BaseResponse
from moto.route53.exceptions import Route53ClientError, InvalidChangeBatch
from moto.route53.models import route53_backend

XMLNS = "https://route53.amazonaws.com/doc/2013-04-01/"


def error_handler(f):
    @wraps(f)
    def _wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Route53ClientError as e:
            return e.code, e.get_headers(), e.get_body()

    return _wrapper


class Route53(BaseResponse):
    """Handler for Route53 requests and responses."""

    @error_handler
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
            all_zones = route53_backend.list_hosted_zones()
            template = Template(LIST_HOSTED_ZONES_RESPONSE)
            return 200, headers, template.render(zones=all_zones)

    def list_hosted_zones_by_name_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)
        query_params = parse_qs(parsed_url.query)
        dnsname = query_params.get("dnsname")

        dnsname, zones = route53_backend.list_hosted_zones_by_name(dnsname)

        template = Template(LIST_HOSTED_ZONES_BY_NAME_RESPONSE)
        return 200, headers, template.render(zones=zones, dnsname=dnsname, xmlns=XMLNS)

    @error_handler
    def get_or_delete_hostzone_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)
        zoneid = parsed_url.path.rstrip("/").rsplit("/", 1)[1]

        if request.method == "GET":
            the_zone = route53_backend.get_hosted_zone(zoneid)
            template = Template(GET_HOSTED_ZONE_RESPONSE)
            return 200, headers, template.render(zone=the_zone)
        elif request.method == "DELETE":
            route53_backend.delete_hosted_zone(zoneid)
            return 200, headers, DELETE_HOSTED_ZONE_RESPONSE

    @error_handler
    def rrset_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        parsed_url = urlparse(full_url)
        method = request.method

        zoneid = parsed_url.path.rstrip("/").rsplit("/", 2)[1]

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

            # Enforce quotas https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/DNSLimitations.html#limits-api-requests-changeresourcerecordsets
            #  - A request cannot contain more than 1,000 ResourceRecord elements. When the value of the Action element is UPSERT, each ResourceRecord element is counted twice.
            effective_rr_count = 0
            for value in change_list:
                record_set = value["ResourceRecordSet"]
                if (
                    "ResourceRecords" not in record_set
                    or not record_set["ResourceRecords"]
                ):
                    continue
                resource_records = list(record_set["ResourceRecords"].values())[0]
                effective_rr_count += len(resource_records)
                if value["Action"] == "UPSERT":
                    effective_rr_count += len(resource_records)
            if effective_rr_count > 1000:
                raise InvalidChangeBatch

            error_msg = route53_backend.change_resource_record_sets(zoneid, change_list)
            if error_msg:
                return 400, headers, error_msg

            return 200, headers, CHANGE_RRSET_RESPONSE

        elif method == "GET":
            querystring = parse_qs(parsed_url.query)
            template = Template(LIST_RRSET_RESPONSE)
            start_type = querystring.get("type", [None])[0]
            start_name = querystring.get("name", [None])[0]

            if start_type and not start_name:
                return 400, headers, "The input is not valid"

            record_sets = route53_backend.list_resource_record_sets(
                zoneid, start_type=start_type, start_name=start_name
            )
            return 200, headers, template.render(record_sets=record_sets)

    def health_check_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        parsed_url = urlparse(full_url)
        method = request.method

        if method == "POST":
            json_body = xmltodict.parse(self.body)["CreateHealthCheckRequest"]
            caller_reference = json_body["CallerReference"]
            config = json_body["HealthCheckConfig"]
            health_check_args = {
                "ip_address": config.get("IPAddress"),
                "port": config.get("Port"),
                "type": config["Type"],
                "resource_path": config.get("ResourcePath"),
                "fqdn": config.get("FullyQualifiedDomainName"),
                "search_string": config.get("SearchString"),
                "request_interval": config.get("RequestInterval"),
                "failure_threshold": config.get("FailureThreshold"),
                "health_threshold": config.get("HealthThreshold"),
                "measure_latency": config.get("MeasureLatency"),
                "inverted": config.get("Inverted"),
                "disabled": config.get("Disabled"),
                "enable_sni": config.get("EnableSNI"),
                "children": config.get("ChildHealthChecks", {}).get("ChildHealthCheck"),
            }
            health_check = route53_backend.create_health_check(
                caller_reference, health_check_args
            )
            template = Template(CREATE_HEALTH_CHECK_RESPONSE)
            return 201, headers, template.render(health_check=health_check, xmlns=XMLNS)
        elif method == "DELETE":
            health_check_id = parsed_url.path.split("/")[-1]
            route53_backend.delete_health_check(health_check_id)
            template = Template(DELETE_HEALTH_CHECK_RESPONSE)
            return 200, headers, template.render(xmlns=XMLNS)
        elif method == "GET":
            template = Template(LIST_HEALTH_CHECKS_RESPONSE)
            health_checks = route53_backend.list_health_checks()
            return (
                200,
                headers,
                template.render(health_checks=health_checks, xmlns=XMLNS),
            )

    def not_implemented_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        action = ""
        if "tags" in full_url:
            action = "tags"
        elif "trafficpolicyinstances" in full_url:
            action = "policies"
        raise NotImplementedError(
            f"The action for {action} has not been implemented for route 53"
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
            return 200, headers, template.render(change_id=change_id, xmlns=XMLNS)

    @error_handler
    def list_or_create_query_logging_config_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if request.method == "POST":
            json_body = xmltodict.parse(self.body)["CreateQueryLoggingConfigRequest"]
            hosted_zone_id = json_body["HostedZoneId"]
            log_group_arn = json_body["CloudWatchLogsLogGroupArn"]

            query_logging_config = route53_backend.create_query_logging_config(
                self.region, hosted_zone_id, log_group_arn
            )

            template = Template(CREATE_QUERY_LOGGING_CONFIG_RESPONSE)
            headers["Location"] = query_logging_config.location
            return (
                201,
                headers,
                template.render(query_logging_config=query_logging_config, xmlns=XMLNS),
            )

        elif request.method == "GET":
            hosted_zone_id = self._get_param("hostedzoneid")
            next_token = self._get_param("nexttoken")
            max_results = self._get_int_param("maxresults")

            # The paginator picks up named arguments, returns tuple.
            # pylint: disable=unbalanced-tuple-unpacking
            (all_configs, next_token,) = route53_backend.list_query_logging_configs(
                hosted_zone_id=hosted_zone_id,
                next_token=next_token,
                max_results=max_results,
            )

            template = Template(LIST_QUERY_LOGGING_CONFIGS_RESPONSE)
            return (
                200,
                headers,
                template.render(
                    query_logging_configs=all_configs,
                    next_token=next_token,
                    xmlns=XMLNS,
                ),
            )

    @error_handler
    def get_or_delete_query_logging_config_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)
        query_logging_config_id = parsed_url.path.rstrip("/").rsplit("/", 1)[1]

        if request.method == "GET":
            query_logging_config = route53_backend.get_query_logging_config(
                query_logging_config_id
            )
            template = Template(GET_QUERY_LOGGING_CONFIG_RESPONSE)
            return (
                200,
                headers,
                template.render(query_logging_config=query_logging_config, xmlns=XMLNS),
            )

        elif request.method == "DELETE":
            route53_backend.delete_query_logging_config(query_logging_config_id)
            return 200, headers, ""


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

LIST_RRSET_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<ListResourceRecordSetsResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <ResourceRecordSets>
       {% for record in record_sets %}
       <ResourceRecordSet>
           <Name>{{ record.name }}</Name>
           <Type>{{ record.type_ }}</Type>
           {% if record.set_identifier %}
               <SetIdentifier>{{ record.set_identifier }}</SetIdentifier>
           {% endif %}
           {% if record.weight %}
               <Weight>{{ record.weight }}</Weight>
           {% endif %}
           {% if record.region %}
               <Region>{{ record.region }}</Region>
           {% endif %}
           {% if record.ttl %}
               <TTL>{{ record.ttl }}</TTL>
           {% endif %}
           {% if record.failover %}
               <Failover>{{ record.failover }}</Failover>
           {% endif %}
           {% if record.geo_location %}
           <GeoLocation>
           {% for geo_key in ['ContinentCode','CountryCode','SubdivisionCode'] %}
             {% if record.geo_location[geo_key] %}<{{ geo_key }}>{{ record.geo_location[geo_key] }}</{{ geo_key }}>{% endif %}
           {% endfor %}
           </GeoLocation>
           {% endif %}
           {% if record.alias_target %}
           <AliasTarget>
               <HostedZoneId>{{ record.alias_target['HostedZoneId'] }}</HostedZoneId>
               <DNSName>{{ record.alias_target['DNSName'] }}</DNSName>
               <EvaluateTargetHealth>{{ record.alias_target['EvaluateTargetHealth'] }}</EvaluateTargetHealth>
           </AliasTarget>
           {% else %}
           <ResourceRecords>
               {% for resource in record.records %}
               <ResourceRecord>
                   <Value><![CDATA[{{ resource }}]]></Value>
               </ResourceRecord>
               {% endfor %}
           </ResourceRecords>
           {% endif %}
           {% if record.health_check %}
               <HealthCheckId>{{ record.health_check }}</HealthCheckId>
           {% endif %}
        </ResourceRecordSet>
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

LIST_HOSTED_ZONES_BY_NAME_RESPONSE = """<ListHostedZonesByNameResponse xmlns="{{ xmlns }}">
  {% if dnsname %}
  <DNSName>{{ dnsname }}</DNSName>
  {% endif %}
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
<CreateHealthCheckResponse xmlns="{{ xmlns }}">
  {{ health_check.to_xml() }}
</CreateHealthCheckResponse>"""

LIST_HEALTH_CHECKS_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<ListHealthChecksResponse xmlns="{{ xmlns }}">
   <HealthChecks>
   {% for health_check in health_checks %}
      {{ health_check.to_xml() }}
    {% endfor %}
   </HealthChecks>
   <IsTruncated>false</IsTruncated>
   <MaxItems>{{ health_checks|length }}</MaxItems>
</ListHealthChecksResponse>"""

DELETE_HEALTH_CHECK_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
    <DeleteHealthCheckResponse xmlns="{{ xmlns }}">
</DeleteHealthCheckResponse>"""

GET_CHANGE_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<GetChangeResponse xmlns="{{ xmlns }}">
   <ChangeInfo>
      <Status>INSYNC</Status>
      <SubmittedAt>2010-09-10T01:36:41.958Z</SubmittedAt>
      <Id>{{ change_id }}</Id>
   </ChangeInfo>
</GetChangeResponse>"""

CREATE_QUERY_LOGGING_CONFIG_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<CreateQueryLoggingConfigResponse xmlns="{{ xmlns }}">
  {{ query_logging_config.to_xml() }}
</CreateQueryLoggingConfigResponse>"""

GET_QUERY_LOGGING_CONFIG_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<CreateQueryLoggingConfigResponse xmlns="{{ xmlns }}">
  {{ query_logging_config.to_xml() }}
</CreateQueryLoggingConfigResponse>"""

LIST_QUERY_LOGGING_CONFIGS_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<ListQueryLoggingConfigsResponse xmlns="{{ xmlns }}">
   <QueryLoggingConfigs>
      {% for query_logging_config in query_logging_configs %}
         {{ query_logging_config.to_xml() }}
      {% endfor %}
   </QueryLoggingConfigs>
   {% if next_token %}
      <NextToken>{{ next_token }}</NextToken>
   {% endif %}
</ListQueryLoggingConfigsResponse>"""
