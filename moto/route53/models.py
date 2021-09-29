from __future__ import unicode_literals

import itertools
from collections import defaultdict

import string
import random
import uuid
from jinja2 import Template

from moto.core import BaseBackend, CloudFormationModel


ROUTE53_ID_CHOICE = string.ascii_uppercase + string.digits


def create_route53_zone_id():
    # New ID's look like this Z1RWWTK7Y8UDDQ
    return "".join([random.choice(ROUTE53_ID_CHOICE) for _ in range(0, 15)])


class HealthCheck(CloudFormationModel):
    def __init__(self, health_check_id, caller_reference, health_check_args):
        self.id = health_check_id
        self.ip_address = health_check_args.get("ip_address")
        self.port = health_check_args.get("port") or 80
        self.type_ = health_check_args.get("type")
        self.resource_path = health_check_args.get("resource_path")
        self.fqdn = health_check_args.get("fqdn")
        self.search_string = health_check_args.get("search_string")
        self.request_interval = health_check_args.get("request_interval") or 30
        self.failure_threshold = health_check_args.get("failure_threshold") or 3
        self.health_threshold = health_check_args.get("health_threshold")
        self.measure_latency = health_check_args.get("measure_latency") or False
        self.inverted = health_check_args.get("inverted") or False
        self.disabled = health_check_args.get("disabled") or False
        self.enable_sni = health_check_args.get("enable_sni") or False
        self.children = health_check_args.get("children") or None
        self.caller_reference = caller_reference

    @property
    def physical_resource_id(self):
        return self.id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-route53-healthcheck.html
        return "AWS::Route53::HealthCheck"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]["HealthCheckConfig"]
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
        health_check = route53_backend.create_health_check(
            caller_reference=resource_name, health_check_args=health_check_args
        )
        return health_check

    def to_xml(self):
        template = Template(
            """<HealthCheck>
            <Id>{{ health_check.id }}</Id>
            <CallerReference>{{ health_check.caller_reference }}</CallerReference>
            <HealthCheckConfig>
                {% if health_check.type_ != "CALCULATED" %}
                    <IPAddress>{{ health_check.ip_address }}</IPAddress>
                    <Port>{{ health_check.port }}</Port>
                {% endif %}
                <Type>{{ health_check.type_ }}</Type>
                {% if health_check.resource_path %}
                    <ResourcePath>{{ health_check.resource_path }}</ResourcePath>
                {% endif %}
                {% if health_check.fqdn %}
                    <FullyQualifiedDomainName>{{ health_check.fqdn }}</FullyQualifiedDomainName>
                {% endif %}
                {% if health_check.type_ != "CALCULATED" %}
                    <RequestInterval>{{ health_check.request_interval }}</RequestInterval>
                    <FailureThreshold>{{ health_check.failure_threshold }}</FailureThreshold>
                    <MeasureLatency>{{ health_check.measure_latency }}</MeasureLatency>
                {% endif %}
                {% if health_check.type_ == "CALCULATED" %}
                    <HealthThreshold>{{ health_check.health_threshold }}</HealthThreshold>
                {% endif %}
                <Inverted>{{ health_check.inverted }}</Inverted>
                <Disabled>{{ health_check.disabled }}</Disabled>
                <EnableSNI>{{ health_check.enable_sni }}</EnableSNI>
                {% if health_check.search_string %}
                    <SearchString>{{ health_check.search_string }}</SearchString>
                {% endif %}
                {% if health_check.children %}
                    <ChildHealthChecks>
                    {% for child in health_check.children %}
                        <member>{{ child }}</member>
                    {% endfor %}
                    </ChildHealthChecks>
                {% endif %}
            </HealthCheckConfig>
            <HealthCheckVersion>1</HealthCheckVersion>
        </HealthCheck>"""
        )
        return template.render(health_check=self)


class RecordSet(CloudFormationModel):
    def __init__(self, kwargs):
        self.name = kwargs.get("Name")
        self.type_ = kwargs.get("Type")
        self.ttl = kwargs.get("TTL")
        self.records = kwargs.get("ResourceRecords", [])
        self.set_identifier = kwargs.get("SetIdentifier")
        self.weight = kwargs.get("Weight")
        self.region = kwargs.get("Region")
        self.health_check = kwargs.get("HealthCheckId")
        self.hosted_zone_name = kwargs.get("HostedZoneName")
        self.hosted_zone_id = kwargs.get("HostedZoneId")
        self.alias_target = kwargs.get("AliasTarget")
        self.failover = kwargs.get("Failover")
        self.geo_location = kwargs.get("GeoLocation")

    @staticmethod
    def cloudformation_name_type():
        return "Name"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-route53-recordset.html
        return "AWS::Route53::RecordSet"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        zone_name = properties.get("HostedZoneName")
        if zone_name:
            hosted_zone = route53_backend.get_hosted_zone_by_name(zone_name)
        else:
            hosted_zone = route53_backend.get_hosted_zone(properties["HostedZoneId"])
        record_set = hosted_zone.add_rrset(properties)
        return record_set

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        cls.delete_from_cloudformation_json(
            original_resource.name, cloudformation_json, region_name
        )
        return cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, region_name
        )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        # this will break if you changed the zone the record is in,
        # unfortunately
        properties = cloudformation_json["Properties"]

        zone_name = properties.get("HostedZoneName")
        if zone_name:
            hosted_zone = route53_backend.get_hosted_zone_by_name(zone_name)
        else:
            hosted_zone = route53_backend.get_hosted_zone(properties["HostedZoneId"])

        try:
            hosted_zone.delete_rrset({"Name": resource_name})
        except KeyError:
            pass

    @property
    def physical_resource_id(self):
        return self.name

    def to_xml(self):
        template = Template(
            """<ResourceRecordSet>
                <Name>{{ record_set.name }}</Name>
                <Type>{{ record_set.type_ }}</Type>
                {% if record_set.set_identifier %}
                    <SetIdentifier>{{ record_set.set_identifier }}</SetIdentifier>
                {% endif %}
                {% if record_set.weight %}
                    <Weight>{{ record_set.weight }}</Weight>
                {% endif %}
                {% if record_set.region %}
                    <Region>{{ record_set.region }}</Region>
                {% endif %}
                {% if record_set.ttl %}
                    <TTL>{{ record_set.ttl }}</TTL>
                {% endif %}
                {% if record_set.failover %}
                    <Failover>{{ record_set.failover }}</Failover>
                {% endif %}
                {% if record_set.geo_location %}
                <GeoLocation>
                {% for geo_key in ['ContinentCode','CountryCode','SubdivisionCode'] %}
                  {% if record_set.geo_location[geo_key] %}<{{ geo_key }}>{{ record_set.geo_location[geo_key] }}</{{ geo_key }}>{% endif %}
                {% endfor %}
                </GeoLocation>
                {% endif %}
                {% if record_set.alias_target %}
                <AliasTarget>
                    <HostedZoneId>{{ record_set.alias_target['HostedZoneId'] }}</HostedZoneId>
                    <DNSName>{{ record_set.alias_target['DNSName'] }}</DNSName>
                    <EvaluateTargetHealth>{{ record_set.alias_target['EvaluateTargetHealth'] }}</EvaluateTargetHealth>
                </AliasTarget>
                {% else %}
                <ResourceRecords>
                    {% for record in record_set.records %}
                    <ResourceRecord>
                        <Value>{{ record|e }}</Value>
                    </ResourceRecord>
                    {% endfor %}
                </ResourceRecords>
                {% endif %}
                {% if record_set.health_check %}
                    <HealthCheckId>{{ record_set.health_check }}</HealthCheckId>
                {% endif %}
            </ResourceRecordSet>"""
        )
        return template.render(record_set=self)

    def delete(self, *args, **kwargs):
        """Not exposed as part of the Route 53 API - used for CloudFormation. args are ignored"""
        hosted_zone = route53_backend.get_hosted_zone_by_name(self.hosted_zone_name)
        if not hosted_zone:
            hosted_zone = route53_backend.get_hosted_zone(self.hosted_zone_id)
        hosted_zone.delete_rrset({"Name": self.name, "Type": self.type_})


def reverse_domain_name(domain_name):
    if domain_name.endswith("."):  # normalize without trailing dot
        domain_name = domain_name[:-1]
    return ".".join(reversed(domain_name.split(".")))


class FakeZone(CloudFormationModel):
    def __init__(self, name, id_, private_zone, comment=None):
        self.name = name
        self.id = id_
        if comment is not None:
            self.comment = comment
        self.private_zone = private_zone
        self.rrsets = []

    def add_rrset(self, record_set):
        record_set = RecordSet(record_set)
        self.rrsets.append(record_set)
        return record_set

    def upsert_rrset(self, record_set):
        new_rrset = RecordSet(record_set)
        for i, rrset in enumerate(self.rrsets):
            if (
                rrset.name == new_rrset.name
                and rrset.type_ == new_rrset.type_
                and rrset.set_identifier == new_rrset.set_identifier
            ):
                self.rrsets[i] = new_rrset
                break
        else:
            self.rrsets.append(new_rrset)
        return new_rrset

    def delete_rrset(self, rrset):
        self.rrsets = [
            record_set
            for record_set in self.rrsets
            if record_set.name != rrset["Name"]
            or (rrset.get("Type") is not None and record_set.type_ != rrset["Type"])
        ]

    def delete_rrset_by_id(self, set_identifier):
        self.rrsets = [
            record_set
            for record_set in self.rrsets
            if record_set.set_identifier != set_identifier
        ]

    def get_record_sets(self, start_type, start_name):
        def predicate(rrset):
            rrset_name_reversed = reverse_domain_name(rrset.name)
            start_name_reversed = reverse_domain_name(start_name)
            return rrset_name_reversed < start_name_reversed or (
                rrset_name_reversed == start_name_reversed and rrset.type_ < start_type
            )

        record_sets = sorted(
            self.rrsets,
            key=lambda rrset: (reverse_domain_name(rrset.name), rrset.type_),
        )

        if start_name:
            start_type = start_type or ""
            record_sets = itertools.dropwhile(predicate, record_sets)

        return record_sets

    @property
    def physical_resource_id(self):
        return self.id

    @staticmethod
    def cloudformation_name_type():
        return "Name"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-route53-hostedzone.html
        return "AWS::Route53::HostedZone"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        hosted_zone = route53_backend.create_hosted_zone(
            resource_name, private_zone=False
        )
        return hosted_zone


class RecordSetGroup(CloudFormationModel):
    def __init__(self, hosted_zone_id, record_sets):
        self.hosted_zone_id = hosted_zone_id
        self.record_sets = record_sets

    @property
    def physical_resource_id(self):
        return "arn:aws:route53:::hostedzone/{0}".format(self.hosted_zone_id)

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-route53-recordsetgroup.html
        return "AWS::Route53::RecordSetGroup"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        zone_name = properties.get("HostedZoneName")
        if zone_name:
            hosted_zone = route53_backend.get_hosted_zone_by_name(zone_name)
        else:
            hosted_zone = route53_backend.get_hosted_zone(properties["HostedZoneId"])
        record_sets = properties["RecordSets"]
        for record_set in record_sets:
            hosted_zone.add_rrset(record_set)

        record_set_group = RecordSetGroup(hosted_zone.id, record_sets)
        return record_set_group


class Route53Backend(BaseBackend):
    def __init__(self):
        self.zones = {}
        self.health_checks = {}
        self.resource_tags = defaultdict(dict)

    def create_hosted_zone(self, name, private_zone, comment=None):
        new_id = create_route53_zone_id()
        new_zone = FakeZone(name, new_id, private_zone=private_zone, comment=comment)
        self.zones[new_id] = new_zone
        return new_zone

    def change_tags_for_resource(self, resource_id, tags):
        if "Tag" in tags:
            if isinstance(tags["Tag"], list):
                for tag in tags["Tag"]:
                    self.resource_tags[resource_id][tag["Key"]] = tag["Value"]
            else:
                key, value = (tags["Tag"]["Key"], tags["Tag"]["Value"])
                self.resource_tags[resource_id][key] = value
        else:
            if "Key" in tags:
                if isinstance(tags["Key"], list):
                    for key in tags["Key"]:
                        del self.resource_tags[resource_id][key]
                else:
                    del self.resource_tags[resource_id][tags["Key"]]

    def list_tags_for_resource(self, resource_id):
        if resource_id in self.resource_tags:
            return self.resource_tags[resource_id]
        return {}

    def get_all_hosted_zones(self):
        return self.zones.values()

    def get_hosted_zone(self, id_):
        return self.zones.get(id_.replace("/hostedzone/", ""))

    def get_hosted_zone_by_name(self, name):
        for zone in self.get_all_hosted_zones():
            if zone.name == name:
                return zone

    def delete_hosted_zone(self, id_):
        return self.zones.pop(id_.replace("/hostedzone/", ""), None)

    def create_health_check(self, caller_reference, health_check_args):
        health_check_id = str(uuid.uuid4())
        health_check = HealthCheck(health_check_id, caller_reference, health_check_args)
        self.health_checks[health_check_id] = health_check
        return health_check

    def get_health_checks(self):
        return self.health_checks.values()

    def delete_health_check(self, health_check_id):
        return self.health_checks.pop(health_check_id, None)


route53_backend = Route53Backend()
