import copy
import itertools
import json
from collections import defaultdict
from typing import Optional
from moto.core import CloudFormationModel
from moto.core.utils import aws_api_matches
from ..exceptions import (
    DependencyViolationError,
    InvalidCIDRSubnetError,
    InvalidPermissionNotFoundError,
    InvalidPermissionDuplicateError,
    InvalidSecurityGroupDuplicateError,
    InvalidSecurityGroupNotFoundError,
    MissingParameterError,
    MotoNotImplementedError,
    RulesPerSecurityGroupLimitExceededError,
)
from .core import TaggedEC2Resource
from ..utils import (
    random_security_group_id,
    random_security_group_rule_id,
    is_valid_cidr,
    is_valid_ipv6_cidr,
    is_tag_filter,
    tag_filter_matches,
)


class SecurityRule(object):
    def __init__(
        self,
        account_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups,
        prefix_list_ids=None,
    ):
        self.account_id = account_id
        self.id = random_security_group_rule_id()
        self.ip_protocol = str(ip_protocol)
        self.ip_ranges = ip_ranges or []
        self.source_groups = source_groups or []
        self.prefix_list_ids = prefix_list_ids or []
        self.from_port = self.to_port = None

        if self.ip_protocol != "-1":
            self.from_port = int(from_port)
            self.to_port = int(to_port)

        ip_protocol_keywords = {
            "tcp": "tcp",
            "6": "tcp",
            "udp": "udp",
            "17": "udp",
            "all": "-1",
            "-1": "-1",
            "tCp": "tcp",
            "6": "tcp",
            "UDp": "udp",
            "17": "udp",
            "ALL": "-1",
            "icMp": "icmp",
            "1": "icmp",
            "icmp": "icmp",
        }
        proto = ip_protocol_keywords.get(self.ip_protocol.lower())
        self.ip_protocol = proto if proto else self.ip_protocol

    @property
    def owner_id(self):
        return self.account_id

    def __eq__(self, other):
        if self.ip_protocol != other.ip_protocol:
            return False
        ip_ranges = list(
            [item for item in self.ip_ranges if item not in other.ip_ranges]
            + [item for item in other.ip_ranges if item not in self.ip_ranges]
        )
        if ip_ranges:
            return False
        source_groups = list(
            [item for item in self.source_groups if item not in other.source_groups]
            + [item for item in other.source_groups if item not in self.source_groups]
        )
        if source_groups:
            return False
        prefix_list_ids = list(
            [item for item in self.prefix_list_ids if item not in other.prefix_list_ids]
            + [
                item
                for item in other.prefix_list_ids
                if item not in self.prefix_list_ids
            ]
        )
        if prefix_list_ids:
            return False
        if self.ip_protocol != "-1":
            if self.from_port != other.from_port:
                return False
            if self.to_port != other.to_port:
                return False

        return True


class SecurityGroup(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        group_id,
        name,
        description,
        vpc_id=None,
        tags=None,
        is_default=None,
    ):
        self.ec2_backend = ec2_backend
        self.id = group_id
        self.group_id = self.id
        self.name = name
        self.group_name = self.name
        self.description = description
        self.ingress_rules = []
        self.egress_rules = []
        self.enis = {}
        self.vpc_id = vpc_id
        self.owner_id = ec2_backend.account_id
        self.add_tags(tags or {})
        self.is_default = is_default or False

        # Append default IPv6 egress rule for VPCs with IPv6 support
        if vpc_id:
            vpc = self.ec2_backend.vpcs.get(vpc_id)
            if vpc:
                self.egress_rules.append(
                    SecurityRule(
                        self.owner_id, "-1", None, None, [{"CidrIp": "0.0.0.0/0"}], []
                    )
                )
            if vpc and len(vpc.get_cidr_block_association_set(ipv6=True)) > 0:
                self.egress_rules.append(
                    SecurityRule(
                        self.owner_id, "-1", None, None, [{"CidrIpv6": "::/0"}], []
                    )
                )

        # each filter as a simple function in a mapping

        self.filters = {
            "description": self.filter_description,
            "egress.ip-permission.cidr": self.filter_egress__ip_permission__cidr,
            "egress.ip-permission.from-port": self.filter_egress__ip_permission__from_port,
            "egress.ip-permission.group-id": self.filter_egress__ip_permission__group_id,
            "egress.ip-permission.group-name": self.filter_egress__ip_permission__group_name,
            "egress.ip-permission.ipv6-cidr": self.filter_egress__ip_permission__ipv6_cidr,
            "egress.ip-permission.prefix-list-id": self.filter_egress__ip_permission__prefix_list_id,
            "egress.ip-permission.protocol": self.filter_egress__ip_permission__protocol,
            "egress.ip-permission.to-port": self.filter_egress__ip_permission__to_port,
            "egress.ip-permission.user-id": self.filter_egress__ip_permission__user_id,
            "group-id": self.filter_group_id,
            "group-name": self.filter_group_name,
            "ip-permission.cidr": self.filter_ip_permission__cidr,
            "ip-permission.from-port": self.filter_ip_permission__from_port,
            "ip-permission.group-id": self.filter_ip_permission__group_id,
            "ip-permission.group-name": self.filter_ip_permission__group_name,
            "ip-permission.ipv6-cidr": self.filter_ip_permission__ipv6_cidr,
            "ip-permission.prefix-list-id": self.filter_ip_permission__prefix_list_id,
            "ip-permission.protocol": self.filter_ip_permission__protocol,
            "ip-permission.to-port": self.filter_ip_permission__to_port,
            "ip-permission.user-id": self.filter_ip_permission__user_id,
            "owner-id": self.filter_owner_id,
            "vpc-id": self.filter_vpc_id,
        }

    @staticmethod
    def cloudformation_name_type():
        return "GroupName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-securitygroup.html
        return "AWS::EC2::SecurityGroup"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        from ..models import ec2_backends

        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[account_id][region_name]
        vpc_id = properties.get("VpcId")
        security_group = ec2_backend.create_security_group(
            name=resource_name,
            description=properties.get("GroupDescription"),
            vpc_id=vpc_id,
        )

        for tag in properties.get("Tags", []):
            tag_key = tag["Key"]
            tag_value = tag["Value"]
            security_group.add_tag(tag_key, tag_value)

        for ingress_rule in properties.get("SecurityGroupIngress", []):
            source_group_id = ingress_rule.get("SourceSecurityGroupId")
            source_group_name = ingress_rule.get("SourceSecurityGroupName")
            source_group = {}
            if source_group_id:
                source_group["GroupId"] = source_group_id
            if source_group_name:
                source_group["GroupName"] = source_group_name

            ec2_backend.authorize_security_group_ingress(
                group_name_or_id=security_group.id,
                ip_protocol=ingress_rule["IpProtocol"],
                from_port=ingress_rule["FromPort"],
                to_port=ingress_rule["ToPort"],
                ip_ranges=ingress_rule.get("CidrIp"),
                source_groups=[source_group] if source_group else [],
                vpc_id=vpc_id,
            )

        return security_group

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):
        cls._delete_security_group_given_vpc_id(
            original_resource.name, original_resource.vpc_id, account_id, region_name
        )
        return cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, account_id, region_name
        )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name
    ):
        properties = cloudformation_json["Properties"]
        vpc_id = properties.get("VpcId")
        cls._delete_security_group_given_vpc_id(
            resource_name, vpc_id, account_id, region_name
        )

    @classmethod
    def _delete_security_group_given_vpc_id(
        cls, resource_name, vpc_id, account_id, region_name
    ):
        from ..models import ec2_backends

        ec2_backend = ec2_backends[account_id][region_name]
        security_group = ec2_backend.get_security_group_by_name_or_id(
            resource_name, vpc_id
        )
        if security_group:
            security_group.delete(account_id, region_name)

    def delete(self, account_id, region_name):  # pylint: disable=unused-argument
        """Not exposed as part of the ELB API - used for CloudFormation."""
        self.ec2_backend.delete_security_group(group_id=self.id)

    @property
    def physical_resource_id(self):
        return self.id

    def filter_description(self, values):
        for value in values:
            if aws_api_matches(value, self.description):
                return True
        return False

    def filter_egress__ip_permission__cidr(self, values):
        for value in values:
            for rule in self.egress_rules:
                for cidr in rule.ip_ranges:
                    if aws_api_matches(value, cidr.get("CidrIp", "NONE")):
                        return True
        return False

    def filter_egress__ip_permission__from_port(self, values):
        for value in values:
            for rule in self.egress_rules:
                if rule.ip_protocol != -1 and aws_api_matches(
                    value, str(rule.from_port)
                ):
                    return True
        return False

    def filter_egress__ip_permission__group_id(self, values):
        for value in values:
            for rule in self.egress_rules:
                for sg in rule.source_groups:
                    if aws_api_matches(value, sg.get("GroupId", None)):
                        return True
        return False

    def filter_egress__ip_permission__group_name(self, values):
        for value in values:
            for rule in self.egress_rules:
                for group in rule.source_groups:
                    if aws_api_matches(value, group.get("GroupName", None)):
                        return True
        return False

    def filter_egress__ip_permission__ipv6_cidr(self, values):
        raise MotoNotImplementedError("egress.ip-permission.ipv6-cidr filter")

    def filter_egress__ip_permission__prefix_list_id(self, values):
        raise MotoNotImplementedError("egress.ip-permission.prefix-list-id filter")

    def filter_egress__ip_permission__protocol(self, values):
        for value in values:
            for rule in self.egress_rules:
                if aws_api_matches(value, rule.ip_protocol):
                    return True
        return False

    def filter_egress__ip_permission__to_port(self, values):
        for value in values:
            for rule in self.egress_rules:
                if aws_api_matches(value, rule.to_port):
                    return True
        return False

    def filter_egress__ip_permission__user_id(self, values):
        for value in values:
            for rule in self.egress_rules:
                if aws_api_matches(value, rule.owner_id):
                    return True
        return False

    def filter_group_id(self, values):
        for value in values:
            if aws_api_matches(value, self.id):
                return True
        return False

    def filter_group_name(self, values):
        for value in values:
            if aws_api_matches(value, self.group_name):
                return True
        return False

    def filter_ip_permission__cidr(self, values):
        for value in values:
            for rule in self.ingress_rules:
                for cidr in rule.ip_ranges:
                    if aws_api_matches(value, cidr.get("CidrIp", "NONE")):
                        return True
        return False

    def filter_ip_permission__from_port(self, values):
        for value in values:
            for rule in self.ingress_rules:
                if aws_api_matches(value, rule.from_port):
                    return True
        return False

    def filter_ip_permission__group_id(self, values):
        for value in values:
            for rule in self.ingress_rules:
                for group in rule.source_groups:
                    if aws_api_matches(value, group.get("GroupId", None)):
                        return True
        return False

    def filter_ip_permission__group_name(self, values):
        for value in values:
            for rule in self.ingress_rules:
                for group in rule.source_groups:
                    if aws_api_matches(value, group.get("GroupName", None)):
                        return True
        return False

    def filter_ip_permission__ipv6_cidr(self, values):
        raise MotoNotImplementedError("ip-permission.ipv6 filter")

    def filter_ip_permission__prefix_list_id(self, values):
        raise MotoNotImplementedError("ip-permission.prefix-list-id filter")

    def filter_ip_permission__protocol(self, values):
        for value in values:
            for rule in self.ingress_rules:
                if aws_api_matches(value, rule.protocol):
                    return True
        return False

    def filter_ip_permission__to_port(self, values):
        for value in values:
            for rule in self.ingress_rules:
                if aws_api_matches(value, rule.to_port):
                    return True
        return False

    def filter_ip_permission__user_id(self, values):
        for value in values:
            for rule in self.ingress_rules:
                if aws_api_matches(value, rule.owner_id):
                    return True
        return False

    def filter_owner_id(self, values):
        for value in values:
            if aws_api_matches(value, self.owner_id):
                return True
        return False

    def filter_vpc_id(self, values):
        for value in values:
            if aws_api_matches(value, self.vpc_id):
                return True
        return False

    def matches_filter(self, key, filter_value):
        if is_tag_filter(key):
            tag_value = self.get_filter_value(key)
            if isinstance(filter_value, list):
                return tag_filter_matches(self, key, filter_value)
            return tag_value in filter_value
        else:
            return self.filters[key](filter_value)

    def matches_filters(self, filters):
        for key, value in filters.items():
            if not self.matches_filter(key, value):
                return False
        return True

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["GroupId"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "GroupId":
            return self.id
        raise UnformattedGetAttTemplateException()

    def add_ingress_rule(self, rule):
        if rule in self.ingress_rules:
            raise InvalidPermissionDuplicateError()
        self.ingress_rules.append(rule)

    def add_egress_rule(self, rule):
        if rule in self.egress_rules:
            raise InvalidPermissionDuplicateError()
        self.egress_rules.append(rule)

    def get_number_of_ingress_rules(self):
        return sum(
            len(rule.ip_ranges) + len(rule.source_groups) for rule in self.ingress_rules
        )

    def get_number_of_egress_rules(self):
        return sum(
            len(rule.ip_ranges) + len(rule.source_groups) for rule in self.egress_rules
        )


class SecurityGroupBackend:
    def __init__(self):
        # the key in the dict group is the vpc_id or None (non-vpc)
        self.groups = defaultdict(dict)
        # This will help us in RuleLimitExceed errors.
        self.sg_old_ingress_ruls = {}
        self.sg_old_egress_ruls = {}

    def create_security_group(
        self, name, description, vpc_id=None, tags=None, force=False, is_default=None
    ):
        vpc_id = vpc_id or self.default_vpc.id
        if not description:
            raise MissingParameterError("GroupDescription")

        group_id = random_security_group_id()
        if not force:
            existing_group = self.get_security_group_by_name_or_id(name, vpc_id)
            if existing_group:
                raise InvalidSecurityGroupDuplicateError(name)
        group = SecurityGroup(
            self,
            group_id,
            name,
            description,
            vpc_id=vpc_id,
            tags=tags,
            is_default=is_default,
        )

        self.groups[vpc_id][group_id] = group
        return group

    def describe_security_groups(self, group_ids=None, groupnames=None, filters=None):
        all_groups = self.groups.copy()
        matches = itertools.chain(*[x.copy().values() for x in all_groups.values()])
        if group_ids:
            matches = [grp for grp in matches if grp.id in group_ids]
            if len(group_ids) > len(matches):
                unknown_ids = set(group_ids) - set(matches)
                raise InvalidSecurityGroupNotFoundError(unknown_ids)
        if groupnames:
            matches = [grp for grp in matches if grp.name in groupnames]
            if len(groupnames) > len(matches):
                unknown_names = set(groupnames) - set(matches)
                raise InvalidSecurityGroupNotFoundError(unknown_names)
        if filters:
            matches = [grp for grp in matches if grp.matches_filters(filters)]

        return matches

    def _delete_security_group(self, vpc_id, group_id):
        vpc_id = vpc_id or self.default_vpc.id
        if self.groups[vpc_id][group_id].enis:
            raise DependencyViolationError(
                "{0} is being utilized by {1}".format(group_id, "ENIs")
            )
        return self.groups[vpc_id].pop(group_id)

    def delete_security_group(self, name=None, group_id=None):
        if group_id:
            # loop over all the SGs, find the right one
            for vpc_id, groups in self.groups.items():
                if group_id in groups:
                    return self._delete_security_group(vpc_id, group_id)
            raise InvalidSecurityGroupNotFoundError(group_id)
        elif name:
            # Group Name.  Has to be in standard EC2, VPC needs to be
            # identified by group_id
            group = self.get_security_group_by_name_or_id(name)
            if group:
                return self._delete_security_group(None, group.id)
            raise InvalidSecurityGroupNotFoundError(name)

    def get_security_group_from_id(self, group_id: str) -> Optional[SecurityGroup]:
        # 2 levels of chaining necessary since it's a complex structure
        all_groups = itertools.chain.from_iterable(
            [x.copy().values() for x in self.groups.copy().values()]
        )
        for group in all_groups:
            if group.id == group_id:
                return group

    def get_security_group_from_name(self, name, vpc_id=None):
        if vpc_id:
            for group in self.groups[vpc_id].values():
                if group.name == name:
                    return group
        else:
            for vpc_id in self.groups:
                for group in self.groups[vpc_id].values():
                    if group.name == name:
                        return group

    def get_security_group_by_name_or_id(self, group_name_or_id, vpc_id=None):

        # try searching by id, fallbacks to name search
        group = self.get_security_group_from_id(group_name_or_id)
        if group is None:
            group = self.get_security_group_from_name(group_name_or_id, vpc_id)
        return group

    def get_default_security_group(self, vpc_id=None):
        for group in self.groups[vpc_id or self.default_vpc.id].values():
            if group.is_default:
                return group

    def authorize_security_group_ingress(
        self,
        group_name_or_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups=None,
        prefix_list_ids=None,
        vpc_id=None,
    ):
        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)
        if group is None:
            raise InvalidSecurityGroupNotFoundError(group_name_or_id)
        if ip_ranges:
            if isinstance(ip_ranges, str):
                ip_ranges = [{"CidrIp": str(ip_ranges)}]
            elif not isinstance(ip_ranges, list):
                ip_ranges = [json.loads(ip_ranges)]
        if ip_ranges:
            for cidr in ip_ranges:
                if (
                    type(cidr) is dict
                    and not any(
                        [
                            is_valid_cidr(cidr.get("CidrIp", "")),
                            is_valid_ipv6_cidr(cidr.get("CidrIpv6", "")),
                        ]
                    )
                ) or (
                    type(cidr) is str
                    and not any([is_valid_cidr(cidr), is_valid_ipv6_cidr(cidr)])
                ):
                    raise InvalidCIDRSubnetError(cidr=cidr)

        self._verify_group_will_respect_rule_count_limit(
            group, group.get_number_of_ingress_rules(), ip_ranges, source_groups
        )

        _source_groups = self._add_source_group(source_groups, vpc_id)

        security_rule = SecurityRule(
            self.account_id,
            ip_protocol,
            from_port,
            to_port,
            ip_ranges,
            _source_groups,
            prefix_list_ids,
        )

        if security_rule in group.ingress_rules:
            raise InvalidPermissionDuplicateError()
        # To match drift property of the security rules.
        # If no rule found then add security_rule as a new rule
        for rule in group.ingress_rules:
            if (
                security_rule.from_port == rule.from_port
                and security_rule.to_port == rule.to_port
                and security_rule.ip_protocol == rule.ip_protocol
            ):
                rule.ip_ranges.extend(
                    [
                        item
                        for item in security_rule.ip_ranges
                        if item not in rule.ip_ranges
                    ]
                )
                rule.source_groups.extend(
                    [
                        item
                        for item in security_rule.source_groups
                        if item not in rule.source_groups
                    ]
                )
                rule.prefix_list_ids.extend(
                    [
                        item
                        for item in security_rule.prefix_list_ids
                        if item not in rule.prefix_list_ids
                    ]
                )
                security_rule = rule
                break
        else:
            group.add_ingress_rule(security_rule)
        return security_rule, group

    def revoke_security_group_ingress(
        self,
        group_name_or_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups=None,
        prefix_list_ids=None,
        vpc_id=None,
    ):

        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)

        _source_groups = self._add_source_group(source_groups, vpc_id)

        security_rule = SecurityRule(
            self.account_id,
            ip_protocol,
            from_port,
            to_port,
            ip_ranges,
            _source_groups,
            prefix_list_ids,
        )

        # To match drift property of the security rules.
        for rule in group.ingress_rules:
            if (
                security_rule.from_port == rule.from_port
                and security_rule.to_port == rule.to_port
                and security_rule.ip_protocol == rule.ip_protocol
            ):
                security_rule = copy.deepcopy(rule)
                security_rule.ip_ranges.extend(
                    [item for item in ip_ranges if item not in rule.ip_ranges]
                )
                security_rule.source_groups.extend(
                    [item for item in _source_groups if item not in rule.source_groups]
                )
                security_rule.prefix_list_ids.extend(
                    [
                        item
                        for item in prefix_list_ids
                        if item not in rule.prefix_list_ids
                    ]
                )
                break

        if security_rule in group.ingress_rules:
            rule = group.ingress_rules[group.ingress_rules.index(security_rule)]
            self._remove_items_from_rule(
                ip_ranges, _source_groups, prefix_list_ids, rule
            )

            if (
                not rule.prefix_list_ids
                and not rule.source_groups
                and not rule.ip_ranges
            ):
                group.ingress_rules.remove(rule)
            self.sg_old_ingress_ruls[group.id] = group.ingress_rules.copy()
            return security_rule
        raise InvalidPermissionNotFoundError()

    def authorize_security_group_egress(
        self,
        group_name_or_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups=None,
        prefix_list_ids=None,
        vpc_id=None,
    ):
        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)
        if group is None:
            raise InvalidSecurityGroupNotFoundError(group_name_or_id)
        if ip_ranges and not isinstance(ip_ranges, list):

            if isinstance(ip_ranges, str) and "CidrIp" not in ip_ranges:
                ip_ranges = [{"CidrIp": ip_ranges}]
            else:
                ip_ranges = [json.loads(ip_ranges)]
        if ip_ranges:
            for cidr in ip_ranges:
                if (
                    type(cidr) is dict
                    and not any(
                        [
                            is_valid_cidr(cidr.get("CidrIp", "")),
                            is_valid_ipv6_cidr(cidr.get("CidrIpv6", "")),
                        ]
                    )
                ) or (
                    type(cidr) is str
                    and not any([is_valid_cidr(cidr), is_valid_ipv6_cidr(cidr)])
                ):
                    raise InvalidCIDRSubnetError(cidr=cidr)
        self._verify_group_will_respect_rule_count_limit(
            group,
            group.get_number_of_egress_rules(),
            ip_ranges,
            source_groups,
            egress=True,
        )

        _source_groups = self._add_source_group(source_groups, vpc_id)

        security_rule = SecurityRule(
            self.account_id,
            ip_protocol,
            from_port,
            to_port,
            ip_ranges,
            _source_groups,
            prefix_list_ids,
        )

        if security_rule in group.egress_rules:
            raise InvalidPermissionDuplicateError()
        # To match drift property of the security rules.
        # If no rule found then add security_rule as a new rule
        for rule in group.egress_rules:
            if (
                security_rule.from_port == rule.from_port
                and security_rule.to_port == rule.to_port
                and security_rule.ip_protocol == rule.ip_protocol
            ):
                rule.ip_ranges.extend(
                    [
                        item
                        for item in security_rule.ip_ranges
                        if item not in rule.ip_ranges
                    ]
                )
                rule.source_groups.extend(
                    [
                        item
                        for item in security_rule.source_groups
                        if item not in rule.source_groups
                    ]
                )
                rule.prefix_list_ids.extend(
                    [
                        item
                        for item in security_rule.prefix_list_ids
                        if item not in rule.prefix_list_ids
                    ]
                )
                security_rule = rule
                break
        else:
            group.add_egress_rule(security_rule)

        return security_rule, group

    def revoke_security_group_egress(
        self,
        group_name_or_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups=None,
        prefix_list_ids=None,
        vpc_id=None,
    ):

        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)

        _source_groups = self._add_source_group(source_groups, vpc_id)

        # I don't believe this is required after changing the default egress rule
        # to be {'CidrIp': '0.0.0.0/0'} instead of just '0.0.0.0/0'
        # Not sure why this would return only the IP if it was 0.0.0.0/0 instead of
        # the ip_range?
        # for ip in ip_ranges:
        #     ip_ranges = [ip.get("CidrIp") if ip.get("CidrIp") == "0.0.0.0/0" else ip]

        if group.vpc_id:
            vpc = self.vpcs.get(group.vpc_id)
            if vpc and not len(vpc.get_cidr_block_association_set(ipv6=True)) > 0:
                for item in ip_ranges.copy():
                    if "CidrIpv6" in item:
                        ip_ranges.remove(item)

        security_rule = SecurityRule(
            self.account_id,
            ip_protocol,
            from_port,
            to_port,
            ip_ranges,
            _source_groups,
            prefix_list_ids,
        )

        # To match drift property of the security rules.
        # If no rule found then add security_rule as a new rule
        for rule in group.egress_rules:
            if (
                security_rule.from_port == rule.from_port
                and security_rule.to_port == rule.to_port
                and security_rule.ip_protocol == rule.ip_protocol
            ):
                security_rule = copy.deepcopy(rule)
                security_rule.ip_ranges.extend(
                    [item for item in ip_ranges if item not in rule.ip_ranges]
                )
                security_rule.source_groups.extend(
                    [item for item in _source_groups if item not in rule.source_groups]
                )
                security_rule.prefix_list_ids.extend(
                    [
                        item
                        for item in prefix_list_ids
                        if item not in rule.prefix_list_ids
                    ]
                )
                break

        if security_rule in group.egress_rules:
            rule = group.egress_rules[group.egress_rules.index(security_rule)]
            self._remove_items_from_rule(
                ip_ranges, _source_groups, prefix_list_ids, rule
            )
            if (
                not rule.prefix_list_ids
                and not rule.source_groups
                and not rule.ip_ranges
            ):
                group.egress_rules.remove(rule)
            self.sg_old_egress_ruls[group.id] = group.egress_rules.copy()
            return security_rule
        raise InvalidPermissionNotFoundError()

    def update_security_group_rule_descriptions_ingress(
        self,
        group_name_or_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups=None,
        prefix_list_ids=None,
        vpc_id=None,
    ):

        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)
        if group is None:
            raise InvalidSecurityGroupNotFoundError(group_name_or_id)
        if ip_ranges and not isinstance(ip_ranges, list):

            if isinstance(ip_ranges, str) and "CidrIp" not in ip_ranges:
                ip_ranges = [{"CidrIp": ip_ranges}]
            else:
                ip_ranges = [json.loads(ip_ranges)]
        if ip_ranges:
            for cidr in ip_ranges:
                if (
                    type(cidr) is dict
                    and not any(
                        [
                            is_valid_cidr(cidr.get("CidrIp", "")),
                            is_valid_ipv6_cidr(cidr.get("CidrIpv6", "")),
                        ]
                    )
                ) or (
                    type(cidr) is str
                    and not any([is_valid_cidr(cidr), is_valid_ipv6_cidr(cidr)])
                ):
                    raise InvalidCIDRSubnetError(cidr=cidr)
        _source_groups = self._add_source_group(source_groups, vpc_id)

        security_rule = SecurityRule(
            self.account_id,
            ip_protocol,
            from_port,
            to_port,
            ip_ranges,
            _source_groups,
            prefix_list_ids,
        )
        for rule in group.ingress_rules:
            if (
                security_rule.from_port == rule.from_port
                and security_rule.to_port == rule.to_port
                and security_rule.ip_protocol == rule.ip_protocol
            ):
                self._sg_update_description(security_rule, rule)
        return group

    def update_security_group_rule_descriptions_egress(
        self,
        group_name_or_id,
        ip_protocol,
        from_port,
        to_port,
        ip_ranges,
        source_groups=None,
        prefix_list_ids=None,
        vpc_id=None,
    ):

        group = self.get_security_group_by_name_or_id(group_name_or_id, vpc_id)
        if group is None:
            raise InvalidSecurityGroupNotFoundError(group_name_or_id)
        if ip_ranges and not isinstance(ip_ranges, list):

            if isinstance(ip_ranges, str) and "CidrIp" not in ip_ranges:
                ip_ranges = [{"CidrIp": ip_ranges}]
            else:
                ip_ranges = [json.loads(ip_ranges)]
        if ip_ranges:
            for cidr in ip_ranges:
                if (
                    type(cidr) is dict
                    and not any(
                        [
                            is_valid_cidr(cidr.get("CidrIp", "")),
                            is_valid_ipv6_cidr(cidr.get("CidrIpv6", "")),
                        ]
                    )
                ) or (
                    type(cidr) is str
                    and not any([is_valid_cidr(cidr), is_valid_ipv6_cidr(cidr)])
                ):
                    raise InvalidCIDRSubnetError(cidr=cidr)
        _source_groups = self._add_source_group(source_groups, vpc_id)

        security_rule = SecurityRule(
            self.account_id,
            ip_protocol,
            from_port,
            to_port,
            ip_ranges,
            _source_groups,
            prefix_list_ids,
        )
        for rule in group.egress_rules:
            if (
                security_rule.from_port == rule.from_port
                and security_rule.to_port == rule.to_port
                and security_rule.ip_protocol == rule.ip_protocol
            ):
                self._sg_update_description(security_rule, rule)
        return group

    def _sg_update_description(self, security_rule, rule):
        for item in security_rule.ip_ranges:
            for cidr_item in rule.ip_ranges:
                if cidr_item.get("CidrIp") == item.get("CidrIp"):
                    cidr_item["Description"] = item.get("Description")
                if cidr_item.get("CidrIp6") == item.get("CidrIp6"):
                    cidr_item["Description"] = item.get("Description")

            for group in security_rule.source_groups:
                for source_group in rule.source_groups:
                    if source_group.get("GroupId") == group.get(
                        "GroupId"
                    ) or source_group.get("GroupName") == group.get("GroupName"):
                        source_group["Description"] = group.get("Description")

    def _remove_items_from_rule(self, ip_ranges, _source_groups, prefix_list_ids, rule):
        for item in ip_ranges:
            if item not in rule.ip_ranges:
                raise InvalidPermissionNotFoundError()
            else:
                rule.ip_ranges.remove(item)

        for item in _source_groups:
            if item not in rule.source_groups:
                raise InvalidPermissionNotFoundError()
            else:
                rule.source_groups.remove(item)

        for item in prefix_list_ids:
            if item not in rule.prefix_list_ids:
                raise InvalidPermissionNotFoundError()
            else:
                rule.prefix_list_ids.remove(item)
        pass

    def _add_source_group(self, source_groups, vpc_id):
        _source_groups = []
        for item in source_groups or []:
            if "OwnerId" not in item:
                item["OwnerId"] = self.account_id
            # for VPCs
            if "GroupId" in item:
                if not self.get_security_group_by_name_or_id(
                    item.get("GroupId"), vpc_id
                ):
                    raise InvalidSecurityGroupNotFoundError(item.get("GroupId"))
            if "GroupName" in item:
                source_group = self.get_security_group_by_name_or_id(
                    item.get("GroupName"), vpc_id
                )
                if not source_group:
                    raise InvalidSecurityGroupNotFoundError(item.get("GroupName"))
                else:
                    item["GroupId"] = source_group.id
                    item.pop("GroupName")

            _source_groups.append(item)
        return _source_groups

    def _verify_group_will_respect_rule_count_limit(
        self, group, current_rule_nb, ip_ranges, source_groups=None, egress=False
    ):
        max_nb_rules = 60 if group.vpc_id else 100
        future_group_nb_rules = current_rule_nb
        if ip_ranges:
            future_group_nb_rules += len(ip_ranges)
        if source_groups:
            future_group_nb_rules += len(source_groups)
        if future_group_nb_rules > max_nb_rules:
            if group and not egress:
                group.ingress_rules = self.sg_old_ingress_ruls[group.id]
            if group and egress:
                group.egress_rules = self.sg_old_egress_ruls[group.id]
            raise RulesPerSecurityGroupLimitExceededError


class SecurityGroupIngress(CloudFormationModel):
    def __init__(self, security_group, properties):
        self.security_group = security_group
        self.properties = properties

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-securitygroupingress.html
        return "AWS::EC2::SecurityGroupIngress"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        from ..models import ec2_backends

        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[account_id][region_name]
        group_name = properties.get("GroupName")
        group_id = properties.get("GroupId")
        ip_protocol = properties.get("IpProtocol")
        cidr_ip = properties.get("CidrIp")
        cidr_desc = properties.get("Description")
        cidr_ipv6 = properties.get("CidrIpv6")
        from_port = properties.get("FromPort")
        source_security_group_id = properties.get("SourceSecurityGroupId")
        source_security_group_name = properties.get("SourceSecurityGroupName")
        # source_security_owner_id =
        # properties.get("SourceSecurityGroupOwnerId")  # IGNORED AT THE MOMENT
        to_port = properties.get("ToPort")

        assert group_id or group_name
        assert (
            source_security_group_name
            or cidr_ip
            or cidr_ipv6
            or source_security_group_id
        )
        assert ip_protocol

        source_group = {}
        if source_security_group_id:
            source_group["GroupId"] = source_security_group_id
        if source_security_group_name:
            source_group["GroupName"] = source_security_group_name
        if cidr_ip:
            ip_ranges = [{"CidrIp": cidr_ip, "Description": cidr_desc}]
        else:
            ip_ranges = []

        if group_id:
            security_group = ec2_backend.describe_security_groups(group_ids=[group_id])[
                0
            ]
        else:
            security_group = ec2_backend.describe_security_groups(
                groupnames=[group_name]
            )[0]

        ec2_backend.authorize_security_group_ingress(
            group_name_or_id=security_group.id,
            ip_protocol=ip_protocol,
            from_port=from_port,
            to_port=to_port,
            ip_ranges=ip_ranges,
            source_groups=[source_group] if source_group else [],
        )

        return cls(security_group, properties)
