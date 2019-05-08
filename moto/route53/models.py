"""
Route53 models
"""
from __future__ import unicode_literals

from collections import defaultdict

import string
import random
import uuid
from moto.core.utils import unix_time
from moto.core import BaseBackend, BaseModel

from jinja2 import Template

ROUTE53_ID_CHOICE = string.ascii_uppercase + string.digits


def create_route53_zone_id():
    """
    Create route53 zone_id
    :return:
    """
    # New ID's look like this Z1RWWTK7Y8UDDQ
    return ''.join([random.choice(ROUTE53_ID_CHOICE) for _ in range(0, 15)])


class HealthCheck(BaseModel):
    """
    Healthcheck
    """
    def __init__(self, health_check_id, health_check_args):
        """
        Initialize object
        :param health_check_id:
        :param health_check_args:
        """
        self.id = health_check_id
        self.ip_address = health_check_args.get("ip_address")
        self.port = health_check_args.get("port", 80)
        self.type_ = health_check_args.get("type")
        self.resource_path = health_check_args.get("resource_path")
        self.fqdn = health_check_args.get("fqdn")
        self.search_string = health_check_args.get("search_string")
        self.request_interval = health_check_args.get("request_interval", 30)
        self.failure_threshold = health_check_args.get("failure_threshold", 3)

    @property
    def physical_resource_id(self):
        """
        Get healthcheck id
        :return:
        """
        return self.id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        """
        Create healthcheck from cloudformation json
        :param resource_name:
        :param cloudformation_json:
        :param region_name:
        :return:
        """
        properties = cloudformation_json['Properties']['HealthCheckConfig']
        health_check_args = {
            "ip_address": properties.get('IPAddress'),
            "port": properties.get('Port'),
            "type": properties['Type'],
            "resource_path": properties.get('ResourcePath'),
            "fqdn": properties.get('FullyQualifiedDomainName'),
            "search_string": properties.get('SearchString'),
            "request_interval": properties.get('RequestInterval'),
            "failure_threshold": properties.get('FailureThreshold'),
        }
        health_check = route53_backend.create_health_check(health_check_args)
        return health_check

    def to_xml(self):
        """
        Return healthcheck as xml
        :return:
        """
        template = Template("""<HealthCheck>
            <Id>{{ health_check.id }}</Id>
            <CallerReference>example.com 192.0.2.17</CallerReference>
            <HealthCheckConfig>
                <IPAddress>{{ health_check.ip_address }}</IPAddress>
                <Port>{{ health_check.port }}</Port>
                <Type>{{ health_check.type_ }}</Type>
                <ResourcePath>{{ health_check.resource_path }}</ResourcePath>
                <FullyQualifiedDomainName>{{ health_check.fqdn }}</FullyQualifiedDomainName>
                <RequestInterval>{{ health_check.request_interval }}</RequestInterval>
                <FailureThreshold>{{ health_check.failure_threshold }}</FailureThreshold>
                {% if health_check.search_string %}
                    <SearchString>{{ health_check.search_string }}</SearchString>
                {% endif %}
            </HealthCheckConfig>
            <HealthCheckVersion>1</HealthCheckVersion>
        </HealthCheck>""")
        return template.render(health_check=self)


class RecordSet(BaseModel):
    """
    Recordset
    """
    def __init__(self, kwargs):
        """
        Initialize object
        :param kwargs:
        """
        self.name = kwargs.get('Name')
        self.type_ = kwargs.get('Type')
        self.ttl = kwargs.get('TTL')
        self.records = kwargs.get('ResourceRecords', [])
        self.set_identifier = kwargs.get('SetIdentifier')
        self.weight = kwargs.get('Weight')
        self.region = kwargs.get('Region')
        self.health_check = kwargs.get('HealthCheckId')
        self.hosted_zone_name = kwargs.get('HostedZoneName')
        self.hosted_zone_id = kwargs.get('HostedZoneId')

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        """
        Create recordset from cloudformation json
        :param resource_name:
        :param cloudformation_json:
        :param region_name:
        :return:
        """
        properties = cloudformation_json['Properties']

        zone_name = properties.get("HostedZoneName")
        if zone_name:
            hosted_zone = route53_backend.get_hosted_zone_by_name(zone_name)
        else:
            hosted_zone = route53_backend.get_hosted_zone(
                properties["HostedZoneId"])
        record_set = hosted_zone.add_rrset(properties)
        return record_set

    @classmethod
    def update_from_cloudformation_json(
            cls,
            original_resource,
            new_resource_name,
            cloudformation_json,
            region_name
    ):
        """
        Update recordset from cloudformation json
        :param original_resource:
        :param new_resource_name:
        :param cloudformation_json:
        :param region_name:
        :return:
        """

        cls.delete_from_cloudformation_json(
            original_resource.name,
            cloudformation_json,
            region_name
        )

        return cls.create_from_cloudformation_json(
            new_resource_name,
            cloudformation_json,
            region_name
        )

    @classmethod
    def delete_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        """
        Delete recordset from cloudformation json
        :param resource_name:
        :param cloudformation_json:
        :param region_name:
        :return:
        """
        # this will break if you changed the zone the record is in,
        # unfortunately
        properties = cloudformation_json['Properties']

        zone_name = properties.get("HostedZoneName")
        if zone_name:
            hosted_zone = route53_backend.get_hosted_zone_by_name(zone_name)
        else:
            hosted_zone = route53_backend.get_hosted_zone(
                properties["HostedZoneId"])

        try:
            hosted_zone.delete_rrset_by_name(resource_name)
        except KeyError:
            pass

    @property
    def physical_resource_id(self):
        """
        Get recordset resource id
        :return:
        """
        return self.name

    def to_xml(self):
        """
        Get recordset as xml
        :return:
        """
        template = Template("""<ResourceRecordSet>
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
                <ResourceRecords>
                    {% for record in record_set.records %}
                    <ResourceRecord>
                        <Value>{{ record }}</Value>
                    </ResourceRecord>
                    {% endfor %}
                </ResourceRecords>
                {% if record_set.health_check %}
                    <HealthCheckId>{{ record_set.health_check }}</HealthCheckId>
                {% endif %}
            </ResourceRecordSet>""")
        return template.render(record_set=self)

    def delete(self, *args, **kwargs):
        """
        Not exposed as part of the Route 53 API - used for CloudFormation. args are ignored
        :param args:
        :param kwargs:
        :return:
        """
        hosted_zone = route53_backend.get_hosted_zone_by_name(
            self.hosted_zone_name)
        if not hosted_zone:
            hosted_zone = route53_backend.get_hosted_zone(self.hosted_zone_id)
        hosted_zone.delete_rrset_by_name(self.name)


class FakeZone(BaseModel):
    """
    Fake hosted zone
    """
    def __init__(self, name, id_, private_zone, comment=None):
        """
        Initialize object
        :param name:
        :param id_:
        :param private_zone:
        :param comment:
        """
        self.name = name
        self.id = id_
        if comment is not None:
            self.comment = comment
        self.private_zone = private_zone
        self.rrsets = []

    def add_rrset(self, record_set):
        """
        Add recordset
        :param record_set:
        :return:
        """
        record_set = RecordSet(record_set)
        self.rrsets.append(record_set)
        return record_set

    def upsert_rrset(self, record_set):
        """
        Add or insert recordset
        :param record_set:
        :return:
        """
        new_rrset = RecordSet(record_set)
        for i, rrset in enumerate(self.rrsets):
            if rrset.name == new_rrset.name and rrset.type_ == new_rrset.type_:
                self.rrsets[i] = new_rrset
                break
        else:
            self.rrsets.append(new_rrset)
        return new_rrset

    def delete_rrset_by_name(self, name):
        """
        Delete fake zone recordset by name
        :param name:
        :return:
        """
        self.rrsets = [
            record_set for record_set in self.rrsets if record_set.name != name]

    def delete_rrset_by_id(self, set_identifier):
        """
        Delete fake zone recordset by id
        :param set_identifier:
        :return:
        """
        self.rrsets = [
            record_set for record_set in self.rrsets if record_set.set_identifier != set_identifier]

    def get_record_sets(self, start_type, start_name):
        """
        Get fake zone record sets
        :param start_type:
        :param start_name:
        :return:
        """
        record_sets = list(self.rrsets)  # Copy the list
        if start_type:
            record_sets = [
                record_set for record_set in record_sets if record_set.type_ >= start_type]
        if start_name:
            record_sets = [
                record_set for record_set in record_sets if record_set.name >= start_name]

        return record_sets

    @property
    def physical_resource_id(self):
        """
        Get fake zone id
        :return:
        """
        return self.id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        """
        Create Fake Zone from cloudformation json
        :param resource_name:
        :param cloudformation_json:
        :param region_name:
        :return:
        """
        properties = cloudformation_json['Properties']
        name = properties["Name"]

        hosted_zone = route53_backend.create_hosted_zone(
            name, private_zone=False)
        return hosted_zone


class RecordSetGroup(BaseModel):
    """
    Recordset group
    """
    def __init__(self, hosted_zone_id, record_sets):
        """
        Initialize object
        :param hosted_zone_id:
        :param record_sets:
        """
        self.hosted_zone_id = hosted_zone_id
        self.record_sets = record_sets

    @property
    def physical_resource_id(self):
        """
        Get physical resource id
        :return:
        """
        return "arn:aws:route53:::hostedzone/{0}".format(self.hosted_zone_id)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        """
        Create recordset from cloudformation json
        :param resource_name:
        :param cloudformation_json:
        :param region_name:
        :return:
        """
        properties = cloudformation_json['Properties']

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
    """
    Route53 backend
    """
    def __init__(self):
        """
        Initialize object
        """
        self.zones = {}
        self.associations = {}
        self.health_checks = {}
        self.resource_tags = defaultdict(dict)

    def create_hosted_zone(self, name, private_zone, comment=None):
        """
        Create hosted zone
        :param name:
        :param private_zone:
        :param comment:
        :return:
        """
        new_id = create_route53_zone_id()
        new_zone = FakeZone(
            name, new_id, private_zone=private_zone, comment=comment)
        self.zones[new_id] = new_zone
        return new_zone

    def change_tags_for_resource(self, resource_id, tags):
        """
        Change tags for resource
        :param resource_id:
        :param tags:
        :return:
        """
        if 'Tag' in tags:
            if isinstance(tags['Tag'], list):
                for tag in tags['Tag']:
                    self.resource_tags[resource_id][tag['Key']] = tag['Value']
            else:
                key, value = (tags['Tag']['Key'], tags['Tag']['Value'])
                self.resource_tags[resource_id][key] = value
        else:
            if 'Key' in tags:
                if isinstance(tags['Key'], list):
                    for key in tags['Key']:
                        del self.resource_tags[resource_id][key]
                else:
                    del self.resource_tags[resource_id][tags['Key']]

    def list_tags_for_resource(self, resource_id):
        """
        List tags for resource
        :param resource_id:
        :return:
        """
        if resource_id in self.resource_tags:
            return self.resource_tags[resource_id]

    def get_all_hosted_zones(self):
        """
        Get all hosted zones
        :return:
        """
        return self.zones.values()

    def get_hosted_zone(self, id_):
        """
        Get hosted zone by zone id
        :param id_:
        :return:
        """
        return self.zones.get(id_.replace("/hostedzone/", ""))

    def get_hosted_zone_by_name(self, name):
        """
        Get hosted zone by name
        :param name:
        :return:
        """
        for zone in self.get_all_hosted_zones():
            if zone.name == name:
                return zone

    def delete_hosted_zone(self, id_):
        """
        Delete hosted zone
        :param id_:
        :return:
        """
        return self.zones.pop(id_.replace("/hostedzone/", ""), None)

    def create_health_check(self, health_check_args):
        """
        Create health check
        :param health_check_args:
        :return:
        """
        health_check_id = str(uuid.uuid4())
        health_check = HealthCheck(health_check_id, health_check_args)
        self.health_checks[health_check_id] = health_check
        return health_check

    def get_health_checks(self):
        """
        Get health checks
        :return:
        """
        return self.health_checks.values()

    def delete_health_check(self, health_check_id):
        """
        Delete health check
        :param health_check_id:
        :return:
        """
        return self.health_checks.pop(health_check_id, None)

    def disassociate_vpc_with_hosted_zone(self, zone_id, vpc_region, vpc_id, comment):
        """
        Disassociate vpc with hosted zone
        :param zone_id:
        :param vpc_region:
        :param vpc_id:
        :param comment:
        :return:
        """

        zone_index_to_remove = None
        vpc_index_to_remove = None
        if str(zone_id) in self.associations:

            for items in self.associations[zone_id]:
                index = self.associations[zone_id].index(items)
                if vpc_id in items:
                    my_array = items[vpc_id]
                    if vpc_region == my_array[0]:
                        zone_index_to_remove = index
                        vpc_index_to_remove = 0
                        break

        # Delete the association from dict
        del self.associations[zone_id][zone_index_to_remove][vpc_id]

        current_date = unix_time()
        return {'created_time': current_date, 'comment': comment}


    def associate_vpc_with_hosted_zone(self, zone_id, vpc_region, vpc_id, comment):
        """
        Associate vpc with hosted zone
        :param zone_id:
        :param vpc_region:
        :param vpc_id:
        :param comment:
        :return:
        """

        temp_dict = {}
        temp_dict[vpc_id] = []
        temp_dict[vpc_id].append(vpc_region)
        temp_dict[vpc_id].append(comment)

        if str(zone_id) in self.associations:
            self.associations[zone_id].append(temp_dict)
        else:
            self.associations[zone_id] = []
            self.associations[zone_id].append(temp_dict)

        current_date = unix_time()
        return {'created_time': current_date, 'comment': comment}

    def list_vpc_association_authorizations(self, zone_id):
        """
        List vpc association authorizations
        :param zone_id:
        :return:
        """
        print('list_vpc_association_authorizations')
        return self.associations[zone_id]


route53_backend = Route53Backend()
