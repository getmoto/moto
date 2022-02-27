import base64
import hashlib
import fnmatch
import random
import re
import ipaddress

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

from moto.core import ACCOUNT_ID
from moto.iam import iam_backends

EC2_RESOURCE_TO_PREFIX = {
    "customer-gateway": "cgw",
    "transit-gateway": "tgw",
    "transit-gateway-route-table": "tgw-rtb",
    "transit-gateway-attachment": "tgw-attach",
    "dhcp-options": "dopt",
    "flow-logs": "fl",
    "image": "ami",
    "instance": "i",
    "internet-gateway": "igw",
    "egress-only-internet-gateway": "eigw",
    "launch-template": "lt",
    "nat-gateway": "nat",
    "network-acl": "acl",
    "network-acl-subnet-assoc": "aclassoc",
    "network-interface": "eni",
    "network-interface-attachment": "eni-attach",
    "reserved-instance": "uuid4",
    "route-table": "rtb",
    "route-table-association": "rtbassoc",
    "security-group": "sg",
    "security-group-rule": "sgr",
    "snapshot": "snap",
    "spot-instance-request": "sir",
    "spot-fleet-request": "sfr",
    "subnet": "subnet",
    "subnet-ipv6-cidr-block-association": "subnet-cidr-assoc",
    "reservation": "r",
    "volume": "vol",
    "vpc": "vpc",
    "vpc-endpoint": "vpce",
    "vpc-endpoint-service": "vpce-svc",
    "managed-prefix-list": "pl",
    "vpc-cidr-association-id": "vpc-cidr-assoc",
    "vpc-elastic-ip": "eipalloc",
    "vpc-elastic-ip-association": "eipassoc",
    "vpc-peering-connection": "pcx",
    "vpn-connection": "vpn",
    "vpn-gateway": "vgw",
    "iam-instance-profile-association": "iip-assoc",
    "carrier-gateway": "cagw",
}


EC2_PREFIX_TO_RESOURCE = dict((v, k) for (k, v) in EC2_RESOURCE_TO_PREFIX.items())
HEX_CHARS = list(str(x) for x in range(10)) + ["a", "b", "c", "d", "e", "f"]


def random_resource_id(size=8):
    return "".join(random.choice(HEX_CHARS) for _ in range(size))


def random_id(prefix="", size=8):
    return f"{prefix}-{random_resource_id(size)}"


def random_ami_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["image"])


def random_instance_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["instance"], size=17)


def random_reservation_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["reservation"])


def random_security_group_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["security-group"], size=17)


def random_security_group_rule_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["security-group-rule"], size=17)


def random_flow_log_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["flow-logs"])


def random_snapshot_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["snapshot"])


def random_spot_request_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["spot-instance-request"])


def random_spot_fleet_request_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["spot-fleet-request"])


def random_subnet_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["subnet"])


def random_subnet_ipv6_cidr_block_association_id():
    return random_id(
        prefix=EC2_RESOURCE_TO_PREFIX["subnet-ipv6-cidr-block-association"]
    )


def random_subnet_association_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["route-table-association"])


def random_network_acl_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["network-acl"])


def random_network_acl_subnet_association_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["network-acl-subnet-assoc"])


def random_vpn_gateway_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["vpn-gateway"])


def random_vpn_connection_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["vpn-connection"])


def random_customer_gateway_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["customer-gateway"])


def random_volume_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["volume"])


def random_vpc_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["vpc"])


def random_vpc_ep_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["vpc-endpoint"], size=8)


def random_vpc_cidr_association_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["vpc-cidr-association-id"])


def random_vpc_peering_connection_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["vpc-peering-connection"])


def random_eip_association_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["vpc-elastic-ip-association"])


def random_internet_gateway_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["internet-gateway"])


def random_egress_only_internet_gateway_id():
    return random_id(
        prefix=EC2_RESOURCE_TO_PREFIX["egress-only-internet-gateway"], size=17
    )


def random_route_table_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["route-table"])


def random_eip_allocation_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["vpc-elastic-ip"])


def random_dhcp_option_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["dhcp-options"])


def random_eni_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["network-interface"])


def random_eni_attach_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["network-interface-attachment"])


def random_nat_gateway_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["nat-gateway"], size=17)


def random_transit_gateway_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["transit-gateway"], size=17)


def random_transit_gateway_route_table_id():
    return random_id(
        prefix=EC2_RESOURCE_TO_PREFIX["transit-gateway-route-table"], size=17
    )


def random_transit_gateway_attachment_id():
    return random_id(
        prefix=EC2_RESOURCE_TO_PREFIX["transit-gateway-attachment"], size=17
    )


def random_launch_template_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["launch-template"], size=17)


def random_iam_instance_profile_association_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["iam-instance-profile-association"])


def random_carrier_gateway_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["carrier-gateway"], size=17)


def random_public_ip():
    return "54.214.{0}.{1}".format(random.choice(range(255)), random.choice(range(255)))


def random_private_ip(cidr=None, ipv6=False):
    # prefix - ula.prefixlen : get number of remaing length for the IP.
    #                          prefix will be 32 for IPv4 and 128 for IPv6.
    #  random.getrandbits() will generate remaining bits for IPv6 or Ipv4 in decimal format
    if cidr:
        if ipv6:
            ula = ipaddress.IPv6Network(cidr)
            return str(ula.network_address + (random.getrandbits(128 - ula.prefixlen)))
        ula = ipaddress.IPv4Network(cidr)
        return str(ula.network_address + (random.getrandbits(32 - ula.prefixlen)))
    if ipv6:
        return "2001::cafe:%x/64" % random.getrandbits(16)
    return "10.{0}.{1}.{2}".format(
        random.choice(range(255)), random.choice(range(255)), random.choice(range(255))
    )


def random_ip():
    return "127.{0}.{1}.{2}".format(
        random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
    )


def generate_dns_from_ip(ip, dns_type="internal"):
    splits = ip.split("/")[0].split(".") if "/" in ip else ip.split(".")
    return "ip-{}-{}-{}-{}.ec2.{}".format(
        splits[0], splits[1], splits[2], splits[3], dns_type
    )


def random_mac_address():
    return "02:00:00:%02x:%02x:%02x" % (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
    )


def randor_ipv4_cidr():
    return "10.0.{}.{}/16".format(random.randint(0, 255), random.randint(0, 255))


def random_ipv6_cidr():
    return "2400:6500:{}:{}00::/56".format(random_resource_id(4), random_resource_id(2))


def generate_route_id(
    route_table_id, cidr_block, ipv6_cidr_block=None, prefix_list=None
):
    if ipv6_cidr_block and not cidr_block:
        cidr_block = ipv6_cidr_block
    if prefix_list and not cidr_block:
        cidr_block = prefix_list
    return "%s~%s" % (route_table_id, cidr_block)


def random_managed_prefix_list_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX["managed-prefix-list"], size=8)


def create_dns_entries(service_name, vpc_endpoint_id):
    dns_entries = {}
    dns_entries["dns_name"] = "{}-{}.{}".format(
        vpc_endpoint_id, random_resource_id(8), service_name
    )
    dns_entries["hosted_zone_id"] = random_resource_id(13).upper()
    return dns_entries


def split_route_id(route_id):
    values = route_id.split("~")
    return values[0], values[1]


def dhcp_configuration_from_querystring(querystring, option="DhcpConfiguration"):
    """
    turn:
        {u'AWSAccessKeyId': [u'the_key'],
         u'Action': [u'CreateDhcpOptions'],
         u'DhcpConfiguration.1.Key': [u'domain-name'],
         u'DhcpConfiguration.1.Value.1': [u'example.com'],
         u'DhcpConfiguration.2.Key': [u'domain-name-servers'],
         u'DhcpConfiguration.2.Value.1': [u'10.0.0.6'],
         u'DhcpConfiguration.2.Value.2': [u'10.0.0.7'],
         u'Signature': [u'uUMHYOoLM6r+sT4fhYjdNT6MHw22Wj1mafUpe0P0bY4='],
         u'SignatureMethod': [u'HmacSHA256'],
         u'SignatureVersion': [u'2'],
         u'Timestamp': [u'2014-03-18T21:54:01Z'],
         u'Version': [u'2013-10-15']}
    into:
        {u'domain-name': [u'example.com'], u'domain-name-servers': [u'10.0.0.6', u'10.0.0.7']}
    """

    key_needle = re.compile("{0}.[0-9]+.Key".format(option), re.UNICODE)
    response_values = {}

    for key, value in querystring.items():
        if key_needle.match(key):
            values = []
            key_index = key.split(".")[1]
            value_index = 1
            while True:
                value_key = "{0}.{1}.Value.{2}".format(option, key_index, value_index)
                if value_key in querystring:
                    values.extend(querystring[value_key])
                else:
                    break
                value_index += 1
            response_values[value[0]] = values
    return response_values


def filters_from_querystring(querystring_dict):
    response_values = {}
    last_tag_key = None
    for key, value in sorted(querystring_dict.items()):
        match = re.search(r"Filter.(\d).Name", key)
        if match:
            filter_index = match.groups()[0]
            value_prefix = "Filter.{0}.Value".format(filter_index)
            filter_values = [
                filter_value[0]
                for filter_key, filter_value in querystring_dict.items()
                if filter_key.startswith(value_prefix)
            ]
            if value[0] == "tag-key":
                last_tag_key = "tag:" + filter_values[0]
            elif last_tag_key and value[0] == "tag-value":
                response_values[last_tag_key] = filter_values
            response_values[value[0]] = filter_values
    return response_values


def dict_from_querystring(parameter, querystring_dict):
    use_dict = {}
    for key, value in querystring_dict.items():
        match = re.search(r"{0}.(\d).(\w+)".format(parameter), key)
        if match:
            use_dict_index = match.groups()[0]
            use_dict_element_property = match.groups()[1]

            if not use_dict.get(use_dict_index):
                use_dict[use_dict_index] = {}
            use_dict[use_dict_index][use_dict_element_property] = value[0]

    return use_dict


def get_attribute_value(parameter, querystring_dict):
    for key, value in querystring_dict.items():
        match = re.search(r"{0}.Value".format(parameter), key)
        if match:
            if value[0].lower() in ["true", "false"]:
                return True if value[0].lower() in ["true"] else False
            return value[0]
    return None


def get_object_value(obj, attr):
    keys = attr.split(".")
    val = obj
    for key in keys:
        if key == "owner_id":
            return ACCOUNT_ID
        elif hasattr(val, key):
            val = getattr(val, key)
        elif isinstance(val, dict):
            val = val[key]
        elif isinstance(val, list):
            for item in val:
                item_val = get_object_value(item, key)
                if item_val:
                    return item_val
        else:
            return None
    return val


def is_tag_filter(filter_name):
    return (
        filter_name.startswith("tag:")
        or filter_name.startswith("tag-value")
        or filter_name.startswith("tag-key")
    )


def get_obj_tag(obj, filter_name):
    tag_name = filter_name.replace("tag:", "", 1)
    tags = dict((tag["key"], tag["value"]) for tag in obj.get_tags())
    return tags.get(tag_name)


def get_obj_tag_names(obj):
    tags = set((tag["key"] for tag in obj.get_tags()))
    return tags


def get_obj_tag_values(obj, key=None):
    tags = set(
        (tag["value"] for tag in obj.get_tags() if tag["key"] == key or key is None)
    )
    return tags


def add_tag_specification(tags):
    tags = tags[0] if isinstance(tags, list) and len(tags) == 1 else tags
    tags = (tags or {}).get("Tag", [])
    tags = {t["Key"]: t["Value"] for t in tags}
    return tags


def tag_filter_matches(obj, filter_name, filter_values):
    regex_filters = [re.compile(simple_aws_filter_to_re(f)) for f in filter_values]
    if filter_name == "tag-key":
        tag_values = get_obj_tag_names(obj)
    elif filter_name == "tag-value":
        tag_values = get_obj_tag_values(obj)
    elif filter_name.startswith("tag:"):
        key = filter_name[4:]
        tag_values = get_obj_tag_values(obj, key=key)
    else:
        tag_values = [get_obj_tag(obj, filter_name) or ""]

    for tag_value in tag_values:
        if any(regex.match(tag_value) for regex in regex_filters):
            return True

    return False


filter_dict_attribute_mapping = {
    "instance-state-name": "state",
    "instance-id": "id",
    "state-reason-code": "_state_reason.code",
    "source-dest-check": "source_dest_check",
    "vpc-id": "vpc_id",
    "group-id": "security_groups.id",
    "instance.group-id": "security_groups.id",
    "instance.group-name": "security_groups.name",
    "instance-type": "instance_type",
    "private-ip-address": "private_ip",
    "ip-address": "public_ip",
    "availability-zone": "placement",
    "architecture": "architecture",
    "image-id": "image_id",
    "network-interface.private-dns-name": "private_dns",
    "private-dns-name": "private_dns",
    "owner-id": "owner_id",
    "subnet-id": "subnet_id",
    "dns-name": "public_dns",
}


def passes_filter_dict(instance, filter_dict):
    for filter_name, filter_values in filter_dict.items():
        if filter_name in filter_dict_attribute_mapping:
            instance_attr = filter_dict_attribute_mapping[filter_name]
            instance_value = get_object_value(instance, instance_attr)
            if not instance_value_in_filter_values(instance_value, filter_values):
                return False

        elif is_tag_filter(filter_name):
            if not tag_filter_matches(instance, filter_name, filter_values):
                return False
        else:
            raise NotImplementedError(
                "Filter dicts have not been implemented in Moto for '%s' yet. Feel free to open an issue at https://github.com/spulec/moto/issues"
                % filter_name
            )
    return True


def instance_value_in_filter_values(instance_value, filter_values):
    if isinstance(instance_value, list):
        if not set(filter_values).intersection(set(instance_value)):
            return False
    elif instance_value not in filter_values:
        return False
    return True


def filter_reservations(reservations, filter_dict):
    result = []
    for reservation in reservations:
        new_instances = []
        for instance in reservation.instances:
            if passes_filter_dict(instance, filter_dict):
                new_instances.append(instance)
        if new_instances:
            reservation.instances = new_instances
            result.append(reservation)
    return result


filter_dict_igw_mapping = {
    "attachment.vpc-id": "vpc.id",
    "attachment.state": "attachment_state",
    "internet-gateway-id": "id",
}


def passes_igw_filter_dict(igw, filter_dict):
    for filter_name, filter_values in filter_dict.items():
        if filter_name in filter_dict_igw_mapping:
            igw_attr = filter_dict_igw_mapping[filter_name]
            if get_object_value(igw, igw_attr) not in filter_values:
                return False
        elif is_tag_filter(filter_name):
            if not tag_filter_matches(igw, filter_name, filter_values):
                return False
        else:
            raise NotImplementedError(
                "Internet Gateway filter dicts have not been implemented in Moto for '%s' yet. Feel free to open an issue at https://github.com/spulec/moto/issues",
                filter_name,
            )
    return True


def filter_internet_gateways(igws, filter_dict):
    result = []
    for igw in igws:
        if passes_igw_filter_dict(igw, filter_dict):
            result.append(igw)
    return result


def is_filter_matching(obj, _filter, filter_value):
    value = obj.get_filter_value(_filter)

    if filter_value is None:
        return False

    if isinstance(value, str):
        if not isinstance(filter_value, list):
            filter_value = [filter_value]
        if any(fnmatch.fnmatch(value, pattern) for pattern in filter_value):
            return True
        return False

    if isinstance(value, type({}.keys())):
        if isinstance(filter_value, str) and filter_value in value:
            return True

    try:
        value = set(value)
        return (value and value.issubset(filter_value)) or value.issuperset(
            filter_value
        )
    except TypeError:
        return value in filter_value


def generic_filter(filters, objects):
    if filters:
        for (_filter, _filter_value) in filters.items():
            objects = [
                obj
                for obj in objects
                if is_filter_matching(obj, _filter, _filter_value)
            ]

    return objects


def simple_aws_filter_to_re(filter_string):
    tmp_filter = filter_string.replace(r"\?", "[?]")
    tmp_filter = tmp_filter.replace(r"\*", "[*]")
    tmp_filter = fnmatch.translate(tmp_filter)
    return tmp_filter


def random_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    private_key_material = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key_fingerprint = rsa_public_key_fingerprint(private_key.public_key())

    return {
        "fingerprint": public_key_fingerprint,
        "material": private_key_material.decode("ascii"),
    }


def get_prefix(resource_id):
    resource_id_prefix, _, after = resource_id.partition("-")
    if resource_id_prefix == EC2_RESOURCE_TO_PREFIX["transit-gateway"]:
        if after.startswith("rtb"):
            resource_id_prefix = EC2_RESOURCE_TO_PREFIX["transit-gateway-route-table"]
        if after.startswith("attach"):
            resource_id_prefix = EC2_RESOURCE_TO_PREFIX["transit-gateway-attachment"]
    if resource_id_prefix == EC2_RESOURCE_TO_PREFIX["network-interface"]:
        if after.startswith("attach"):
            resource_id_prefix = EC2_RESOURCE_TO_PREFIX["network-interface-attachment"]
    if resource_id.startswith(EC2_RESOURCE_TO_PREFIX["vpc-endpoint-service"]):
        resource_id_prefix = EC2_RESOURCE_TO_PREFIX["vpc-endpoint-service"]
    if resource_id_prefix not in EC2_RESOURCE_TO_PREFIX.values():
        uuid4hex = re.compile(r"[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}\Z", re.I)
        if uuid4hex.match(resource_id) is not None:
            resource_id_prefix = EC2_RESOURCE_TO_PREFIX["reserved-instance"]
        else:
            return None
    return resource_id_prefix


def is_valid_resource_id(resource_id):
    valid_prefixes = EC2_RESOURCE_TO_PREFIX.values()
    resource_id_prefix = get_prefix(resource_id)
    if resource_id_prefix not in valid_prefixes:
        return False
    resource_id_pattern = resource_id_prefix + "-[0-9a-f]{8}"
    resource_pattern_re = re.compile(resource_id_pattern)
    return resource_pattern_re.match(resource_id) is not None


def is_valid_cidr(cird):
    cidr_pattern = r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/(\d|[1-2]\d|3[0-2]))$"
    cidr_pattern_re = re.compile(cidr_pattern)
    return cidr_pattern_re.match(cird) is not None


def is_valid_ipv6_cidr(cird):
    cidr_pattern = r"^s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:)))(%.+)?s*(\/([0-9]|[1-9][0-9]|1[0-1][0-9]|12[0-8]))?$"
    cidr_pattern_re = re.compile(cidr_pattern)
    return cidr_pattern_re.match(cird) is not None


def generate_instance_identity_document(instance):
    """
    http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-identity-documents.html

    A JSON file that describes an instance. Usually retrieved by URL:
    http://169.254.169.254/latest/dynamic/instance-identity/document
    Here we just fill a dictionary that represents the document

    Typically, this document is used by the amazon-ecs-agent when registering a
    new ContainerInstance
    """

    document = {
        "devPayProductCodes": None,
        "availabilityZone": instance.placement["AvailabilityZone"],
        "privateIp": instance.private_ip_address,
        "version": "2010-8-31",
        "region": instance.placement["AvailabilityZone"][:-1],
        "instanceId": instance.id,
        "billingProducts": None,
        "instanceType": instance.instance_type,
        "accountId": "012345678910",
        "pendingTime": "2015-11-19T16:32:11Z",
        "imageId": instance.image_id,
        "kernelId": instance.kernel_id,
        "ramdiskId": instance.ramdisk_id,
        "architecture": instance.architecture,
    }

    return document


def rsa_public_key_parse(key_material):
    # These imports take ~.5s; let's keep them local
    import sshpubkeys.exceptions
    from sshpubkeys.keys import SSHKey

    try:
        if not isinstance(key_material, bytes):
            key_material = key_material.encode("ascii")

        decoded_key = base64.b64decode(key_material).decode("ascii")
        public_key = SSHKey(decoded_key)
    except (sshpubkeys.exceptions.InvalidKeyException, UnicodeDecodeError):
        raise ValueError("bad key")

    if not public_key.rsa:
        raise ValueError("bad key")

    return public_key.rsa


def rsa_public_key_fingerprint(rsa_public_key):
    key_data = rsa_public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    fingerprint_hex = hashlib.md5(key_data).hexdigest()
    fingerprint = re.sub(r"([a-f0-9]{2})(?!$)", r"\1:", fingerprint_hex)
    return fingerprint


def filter_iam_instance_profile_associations(iam_instance_associations, filter_dict):
    if not filter_dict:
        return iam_instance_associations
    result = []
    for iam_instance_association in iam_instance_associations:
        filter_passed = True
        if filter_dict.get("instance-id"):
            if (
                iam_instance_association.instance.id
                not in filter_dict.get("instance-id").values()
            ):
                filter_passed = False
        if filter_dict.get("state"):
            if iam_instance_association.state not in filter_dict.get("state").values():
                filter_passed = False
        if filter_passed:
            result.append(iam_instance_association)
    return result


def filter_iam_instance_profiles(iam_instance_profile_arn, iam_instance_profile_name):
    instance_profile = None
    instance_profile_by_name = None
    instance_profile_by_arn = None
    if iam_instance_profile_name:
        instance_profile_by_name = iam_backends["global"].get_instance_profile(
            iam_instance_profile_name
        )
        instance_profile = instance_profile_by_name
    if iam_instance_profile_arn:
        instance_profile_by_arn = iam_backends["global"].get_instance_profile_by_arn(
            iam_instance_profile_arn
        )
        instance_profile = instance_profile_by_arn
    # We would prefer instance profile that we found by arn
    if iam_instance_profile_arn and iam_instance_profile_name:
        if instance_profile_by_name == instance_profile_by_arn:
            instance_profile = instance_profile_by_arn
        else:
            instance_profile = None

    return instance_profile


def describe_tag_filter(filters, instances):
    result = instances.copy()
    for instance in instances:
        for key in filters:
            if key.startswith("tag:"):
                match = re.match(r"tag:(.*)", key)
                if match:
                    tag_key_name = match.group(1)
                    need_delete = True
                    for tag in instance.get_tags():
                        if tag.get("key") == tag_key_name and tag.get(
                            "value"
                        ) in filters.get(key):
                            need_delete = False
                        elif tag.get("key") == tag_key_name and tag.get(
                            "value"
                        ) not in filters.get(key):
                            need_delete = True
                    if need_delete:
                        result.remove(instance)
    return result


def gen_moto_amis(described_images, drop_images_missing_keys=True):
    """Convert `boto3.EC2.Client.describe_images` output to form acceptable to `MOTO_AMIS_PATH`

    Parameters
    ==========
    described_images : list of dicts
        as returned by :ref:`boto3:EC2.Client.describe_images` in "Images" key
    drop_images_missing_keys : bool, default=True
        When `True` any entry in `images` that is missing a required key will silently
        be excluded from the returned list

    Throws
    ======
    `KeyError` when `drop_images_missing_keys` is `False` and a required key is missing
    from an element of `images`

    Returns
    =======
    list of dicts suitable to be serialized into JSON as a target for `MOTO_AMIS_PATH` environment
    variable.

    See Also
    ========
    * :ref:`moto.ec2.models.EC2Backend`
    """
    result = []
    for image in described_images:
        try:
            tmp = {
                "ami_id": image["ImageId"],
                "name": image["Name"],
                "description": image["Description"],
                "owner_id": image["OwnerId"],
                "public": image["Public"],
                "virtualization_type": image["VirtualizationType"],
                "architecture": image["Architecture"],
                "state": image["State"],
                "platform": image.get("Platform"),
                "image_type": image["ImageType"],
                "hypervisor": image["Hypervisor"],
                "root_device_name": image["RootDeviceName"],
                "root_device_type": image["RootDeviceType"],
                "sriov": image.get("SriovNetSupport", "simple"),
            }
            result.append(tmp)
        except Exception as err:
            if not drop_images_missing_keys:
                raise err

    return result
