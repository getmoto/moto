"""Handles Route53 API requests, invokes method and returns response."""
from urllib.parse import parse_qs, urlparse

from jinja2 import Template
import xmltodict

from moto.core.responses import BaseResponse
from moto.core.exceptions import InvalidToken
from moto.route53.exceptions import Route53ClientError, InvalidPaginationToken
from moto.route53.models import route53_backend

XMLNS = "https://route53.amazonaws.com/doc/2013-04-01/"


class Route53(BaseResponse):
    """Handler for Route53 requests and responses."""

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

    def get_or_delete_hostzone_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)
        zoneid = parsed_url.path.rstrip("/").rsplit("/", 1)[1]
        the_zone = route53_backend.get_hosted_zone(zoneid)
        if not the_zone:
            return no_such_hosted_zone_error(zoneid, headers)

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
            return no_such_hosted_zone_error(zoneid, headers)

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

            error_msg = route53_backend.change_resource_record_sets(
                the_zone, change_list
            )
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

            record_sets = the_zone.get_record_sets(start_type, start_name)
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

    def list_or_create_query_logging_config_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if request.method == "POST":
            json_body = xmltodict.parse(self.body)["CreateQueryLoggingConfigRequest"]
            hosted_zone_id = json_body["HostedZoneId"]
            log_group_arn = json_body["CloudWatchLogsLogGroupArn"]
            try:
                query_logging_config = route53_backend.create_query_logging_config(
                    self.region, hosted_zone_id, log_group_arn
                )
            except Route53ClientError as r53error:
                return r53error.code, {}, r53error.description

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
            try:
                try:
                    # The paginator picks up named arguments, returns tuple.
                    # pylint: disable=unbalanced-tuple-unpacking
                    (
                        all_configs,
                        next_token,
                    ) = route53_backend.list_query_logging_configs(
                        hosted_zone_id=hosted_zone_id,
                        next_token=next_token,
                        max_results=max_results,
                    )
                except InvalidToken as exc:
                    raise InvalidPaginationToken() from exc
            except Route53ClientError as r53error:
                return r53error.code, {}, r53error.description

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

    def get_or_delete_query_logging_config_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)
        query_logging_config_id = parsed_url.path.rstrip("/").rsplit("/", 1)[1]

        if request.method == "GET":
            try:
                query_logging_config = route53_backend.get_query_logging_config(
                    query_logging_config_id
                )
            except Route53ClientError as r53error:
                return r53error.code, {}, r53error.description
            template = Template(GET_QUERY_LOGGING_CONFIG_RESPONSE)
            return (
                200,
                headers,
                template.render(query_logging_config=query_logging_config, xmlns=XMLNS),
            )

        elif request.method == "DELETE":
            try:
                route53_backend.delete_query_logging_config(query_logging_config_id)
            except Route53ClientError as r53error:
                return r53error.code, {}, r53error.description
            return 200, headers, ""


def no_such_hosted_zone_error(zoneid, headers=None):
    if not headers:
        headers = {}
    headers["X-Amzn-ErrorType"] = "NoSuchHostedZone"
    headers["Content-Type"] = "text/xml"
    error_response = f"""<ErrorResponse xmlns="{XMLNS}">
        <Error>
            <Code>NoSuchHostedZone</Code>
            <Message>Zone {zoneid} Not Found</Message>
        </Error>
    </ErrorResponse>"""
    return 404, headers, error_response


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
