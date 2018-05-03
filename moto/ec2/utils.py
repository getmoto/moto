from __future__ import unicode_literals

import fnmatch
import random
import re
import six

EC2_RESOURCE_TO_PREFIX = {
    'customer-gateway': 'cgw',
    'dhcp-options': 'dopt',
    'image': 'ami',
    'instance': 'i',
    'internet-gateway': 'igw',
    'nat-gateway': 'nat',
    'network-acl': 'acl',
    'network-acl-subnet-assoc': 'aclassoc',
    'network-interface': 'eni',
    'network-interface-attachment': 'eni-attach',
    'reserved-instance': 'uuid4',
    'route-table': 'rtb',
    'route-table-association': 'rtbassoc',
    'security-group': 'sg',
    'snapshot': 'snap',
    'spot-instance-request': 'sir',
    'spot-fleet-request': 'sfr',
    'subnet': 'subnet',
    'reservation': 'r',
    'volume': 'vol',
    'vpc': 'vpc',
    'vpc-cidr-association-id': 'vpc-cidr-assoc',
    'vpc-elastic-ip': 'eipalloc',
    'vpc-elastic-ip-association': 'eipassoc',
    'vpc-peering-connection': 'pcx',
    'vpn-connection': 'vpn',
    'vpn-gateway': 'vgw'}


EC2_PREFIX_TO_RESOURCE = dict((v, k) for (k, v) in EC2_RESOURCE_TO_PREFIX.items())


def random_resource_id(size=8):
    chars = list(range(10)) + ['a', 'b', 'c', 'd', 'e', 'f']
    resource_id = ''.join(six.text_type(random.choice(chars)) for x in range(size))
    return resource_id


def random_id(prefix='', size=8):
    return '{0}-{1}'.format(prefix, random_resource_id(size))


def random_ami_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['image'])


def random_instance_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['instance'], size=17)


def random_reservation_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['reservation'])


def random_security_group_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['security-group'])


def random_snapshot_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['snapshot'])


def random_spot_request_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['spot-instance-request'])


def random_spot_fleet_request_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['spot-fleet-request'])


def random_subnet_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['subnet'])


def random_subnet_association_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['route-table-association'])


def random_network_acl_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['network-acl'])


def random_network_acl_subnet_association_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['network-acl-subnet-assoc'])


def random_vpn_gateway_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['vpn-gateway'])


def random_vpn_connection_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['vpn-connection'])


def random_customer_gateway_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['customer-gateway'])


def random_volume_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['volume'])


def random_vpc_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['vpc'])


def random_vpc_cidr_association_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['vpc-cidr-association-id'])


def random_vpc_peering_connection_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['vpc-peering-connection'])


def random_eip_association_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['vpc-elastic-ip-association'])


def random_internet_gateway_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['internet-gateway'])


def random_route_table_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['route-table'])


def random_eip_allocation_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['vpc-elastic-ip'])


def random_dhcp_option_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['dhcp-options'])


def random_eni_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['network-interface'])


def random_eni_attach_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['network-interface-attachment'])


def random_nat_gateway_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['nat-gateway'], size=17)


def random_public_ip():
    return '54.214.{0}.{1}'.format(random.choice(range(255)),
                                   random.choice(range(255)))


def random_private_ip():
    return '10.{0}.{1}.{2}'.format(random.choice(range(255)),
                                   random.choice(range(255)),
                                   random.choice(range(255)))


def random_ip():
    return "127.{0}.{1}.{2}".format(
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )


def random_ipv6_cidr():
    return "2400:6500:{}:{}::/56".format(random_resource_id(4), random_resource_id(4))


def generate_route_id(route_table_id, cidr_block):
    return "%s~%s" % (route_table_id, cidr_block)


def split_route_id(route_id):
    values = route_id.split('~')
    return values[0], values[1]


def tags_from_query_string(querystring_dict):
    prefix = 'Tag'
    suffix = 'Key'
    response_values = {}
    for key, value in querystring_dict.items():
        if key.startswith(prefix) and key.endswith(suffix):
            tag_index = key.replace(prefix + ".", "").replace("." + suffix, "")
            tag_key = querystring_dict.get("Tag.{0}.Key".format(tag_index))[0]
            tag_value_key = "Tag.{0}.Value".format(tag_index)
            if tag_value_key in querystring_dict:
                response_values[tag_key] = querystring_dict.get(tag_value_key)[
                    0]
            else:
                response_values[tag_key] = None
    return response_values


def dhcp_configuration_from_querystring(querystring, option=u'DhcpConfiguration'):
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

    key_needle = re.compile(u'{0}.[0-9]+.Key'.format(option), re.UNICODE)
    response_values = {}

    for key, value in querystring.items():
        if key_needle.match(key):
            values = []
            key_index = key.split(".")[1]
            value_index = 1
            while True:
                value_key = u'{0}.{1}.Value.{2}'.format(
                    option, key_index, value_index)
                if value_key in querystring:
                    values.extend(querystring[value_key])
                else:
                    break
                value_index += 1
            response_values[value[0]] = values
    return response_values


def filters_from_querystring(querystring_dict):
    response_values = {}
    for key, value in querystring_dict.items():
        match = re.search(r"Filter.(\d).Name", key)
        if match:
            filter_index = match.groups()[0]
            value_prefix = "Filter.{0}.Value".format(filter_index)
            filter_values = [filter_value[0] for filter_key, filter_value in querystring_dict.items() if
                             filter_key.startswith(value_prefix)]
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


def get_object_value(obj, attr):
    keys = attr.split('.')
    val = obj
    for key in keys:
        if hasattr(val, key):
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
    return (filter_name.startswith('tag:') or
            filter_name.startswith('tag-value') or
            filter_name.startswith('tag-key'))


def get_obj_tag(obj, filter_name):
    tag_name = filter_name.replace('tag:', '', 1)
    tags = dict((tag['key'], tag['value']) for tag in obj.get_tags())
    return tags.get(tag_name)


def get_obj_tag_names(obj):
    tags = set((tag['key'] for tag in obj.get_tags()))
    return tags


def get_obj_tag_values(obj):
    tags = set((tag['value'] for tag in obj.get_tags()))
    return tags


def tag_filter_matches(obj, filter_name, filter_values):
    regex_filters = [re.compile(simple_aws_filter_to_re(f))
                     for f in filter_values]
    if filter_name == 'tag-key':
        tag_values = get_obj_tag_names(obj)
    elif filter_name == 'tag-value':
        tag_values = get_obj_tag_values(obj)
    else:
        tag_values = [get_obj_tag(obj, filter_name) or '']

    for tag_value in tag_values:
        if any(regex.match(tag_value) for regex in regex_filters):
            return True

    return False


filter_dict_attribute_mapping = {
    'instance-state-name': 'state',
    'instance-id': 'id',
    'state-reason-code': '_state_reason.code',
    'source-dest-check': 'source_dest_check',
    'vpc-id': 'vpc_id',
    'group-id': 'security_groups.id',
    'instance.group-id': 'security_groups.id',
    'instance.group-name': 'security_groups.name',
    'instance-type': 'instance_type',
    'private-ip-address': 'private_ip',
    'ip-address': 'public_ip',
    'availability-zone': 'placement',
    'architecture': 'architecture',
    'image-id': 'image_id',
    'network-interface.private-dns-name': 'private_dns',
    'private-dns-name': 'private_dns'
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
                "Filter dicts have not been implemented in Moto for '%s' yet. Feel free to open an issue at https://github.com/spulec/moto/issues" %
                filter_name)
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
                filter_name)
    return True


def filter_internet_gateways(igws, filter_dict):
    result = []
    for igw in igws:
        if passes_igw_filter_dict(igw, filter_dict):
            result.append(igw)
    return result


def is_filter_matching(obj, filter, filter_value):
    value = obj.get_filter_value(filter)

    if not filter_value:
        return False

    if isinstance(value, six.string_types):
        if not isinstance(filter_value, list):
            filter_value = [filter_value]
        if any(fnmatch.fnmatch(value, pattern) for pattern in filter_value):
            return True
        return False

    try:
        value = set(value)
        return (value and value.issubset(filter_value)) or value.issuperset(filter_value)
    except TypeError:
        return value in filter_value


def generic_filter(filters, objects):
    if filters:
        for (_filter, _filter_value) in filters.items():
            objects = [obj for obj in objects if is_filter_matching(
                obj, _filter, _filter_value)]

    return objects


def simple_aws_filter_to_re(filter_string):
    tmp_filter = filter_string.replace('\?', '[?]')
    tmp_filter = tmp_filter.replace('\*', '[*]')
    tmp_filter = fnmatch.translate(tmp_filter)
    return tmp_filter


def random_key_pair():
    def random_hex():
        return chr(random.choice(list(range(48, 58)) + list(range(97, 102))))

    def random_fingerprint():
        return ':'.join([random_hex() + random_hex() for i in range(20)])

    def random_material():
        return ''.join([
            chr(random.choice(list(range(65, 91)) + list(range(48, 58)) +
                              list(range(97, 102))))
            for i in range(1000)
        ])
    material = "---- BEGIN RSA PRIVATE KEY ----" + random_material() + \
        "-----END RSA PRIVATE KEY-----"
    return {
        'fingerprint': random_fingerprint(),
        'material': material
    }


def get_prefix(resource_id):
    resource_id_prefix, separator, after = resource_id.partition('-')
    if resource_id_prefix == EC2_RESOURCE_TO_PREFIX['network-interface']:
        if after.startswith('attach'):
            resource_id_prefix = EC2_RESOURCE_TO_PREFIX[
                'network-interface-attachment']
    if resource_id_prefix not in EC2_RESOURCE_TO_PREFIX.values():
        uuid4hex = re.compile(
            '[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}\Z', re.I)
        if uuid4hex.match(resource_id) is not None:
            resource_id_prefix = EC2_RESOURCE_TO_PREFIX['reserved-instance']
        else:
            return None
    return resource_id_prefix


def is_valid_resource_id(resource_id):
    valid_prefixes = EC2_RESOURCE_TO_PREFIX.values()
    resource_id_prefix = get_prefix(resource_id)
    if resource_id_prefix not in valid_prefixes:
        return False
    resource_id_pattern = resource_id_prefix + '-[0-9a-f]{8}'
    resource_pattern_re = re.compile(resource_id_pattern)
    return resource_pattern_re.match(resource_id) is not None


def is_valid_cidr(cird):
    cidr_pattern = '^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/(\d|[1-2]\d|3[0-2]))$'
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
        'devPayProductCodes': None,
        'availabilityZone': instance.placement['AvailabilityZone'],
        'privateIp': instance.private_ip_address,
        'version': '2010-8-31',
        'region': instance.placement['AvailabilityZone'][:-1],
        'instanceId': instance.id,
        'billingProducts': None,
        'instanceType': instance.instance_type,
        'accountId': '012345678910',
        'pendingTime': '2015-11-19T16:32:11Z',
        'imageId': instance.image_id,
        'kernelId': instance.kernel_id,
        'ramdiskId': instance.ramdisk_id,
        'architecture': instance.architecture,
    }

    return document
