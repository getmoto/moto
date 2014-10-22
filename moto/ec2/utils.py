from __future__ import unicode_literals
import random
import re
import six

EC2_RESOURCE_TO_PREFIX = {
    'customer-gateway': 'cgw',
    'dhcp-options': 'dopt',
    'image': 'ami',
    'instance': 'i',
    'internet-gateway': 'igw',
    'network-acl': 'acl',
    'network-interface': 'eni',
    'network-interface-attachment': 'eni-attach',
    'reserved-instance': 'uuid4',
    'route-table': 'rtb',
    'route-table-association': 'rtbassoc',
    'security-group': 'sg',
    'snapshot': 'snap',
    'spot-instance-request': 'sir',
    'subnet': 'subnet',
    'reservation': 'r',
    'volume': 'vol',
    'vpc': 'vpc',
    'vpc-elastic-ip': 'eipalloc',
    'vpc-elastic-ip-association': 'eipassoc',
    'vpc-peering-connection': 'pcx',
    'vpn-connection': 'vpn',
    'vpn-gateway': 'vgw'}


EC2_PREFIX_TO_RESOURCE = dict((v, k) for (k, v) in EC2_RESOURCE_TO_PREFIX.items())


def random_id(prefix=''):
    size = 8
    chars = list(range(10)) + ['a', 'b', 'c', 'd', 'e', 'f']

    resource_id = ''.join(six.text_type(random.choice(chars)) for x in range(size))
    return '{0}-{1}'.format(prefix, resource_id)


def random_ami_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['image'])


def random_instance_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['instance'])


def random_reservation_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['reservation'])


def random_security_group_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['security-group'])


def random_snapshot_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['snapshot'])


def random_spot_request_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['spot-instance-request'])


def random_subnet_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['subnet'])


def random_subnet_association_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['route-table-association'])


def random_volume_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['volume'])


def random_vpc_id():
    return random_id(prefix=EC2_RESOURCE_TO_PREFIX['vpc'])


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


def random_public_ip():
    return '54.214.{0}.{1}'.format(random.choice(range(255)),
                                   random.choice(range(255)))


def random_ip():
    return "127.{0}.{1}.{2}".format(
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )


def generate_route_id(route_table_id, cidr_block):
    return "%s~%s" % (route_table_id, cidr_block)


def split_route_id(route_id):
    values = string.split(route_id, '~')
    return values[0], values[1]


def instance_ids_from_querystring(querystring_dict):
    instance_ids = []
    for key, value in querystring_dict.items():
        if 'InstanceId' in key:
            instance_ids.append(value[0])
    return instance_ids


def image_ids_from_querystring(querystring_dict):
    image_ids = []
    for key, value in querystring_dict.items():
        if 'ImageId' in key:
            image_ids.append(value[0])
    return image_ids


def route_table_ids_from_querystring(querystring_dict):
    route_table_ids = []
    for key, value in querystring_dict.items():
        if 'RouteTableId' in key:
            route_table_ids.append(value[0])
    return route_table_ids


def vpc_ids_from_querystring(querystring_dict):
    vpc_ids = []
    for key, value in querystring_dict.items():
        if 'VpcId' in key:
            vpc_ids.append(value[0])
    return vpc_ids


def sequence_from_querystring(parameter, querystring_dict):
    parameter_values = []
    for key, value in querystring_dict.items():
        if parameter in key:
            parameter_values.append(value[0])
    return parameter_values


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
                response_values[tag_key] = querystring_dict.get(tag_value_key)[0]
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
                value_key = u'{0}.{1}.Value.{2}'.format(option, key_index, value_index)
                if value_key in querystring:
                    values.extend(querystring[value_key])
                else:
                    break
                value_index += 1
            response_values[value[0]] = values
    return response_values


def optional_from_querystring(parameter, querystring):
    parameter_array = querystring.get(parameter)
    return parameter_array[0] if parameter_array else None


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


def keypair_names_from_querystring(querystring_dict):
    keypair_names = []
    for key, value in querystring_dict.items():
        if 'KeyName' in key:
            keypair_names.append(value[0])
    return keypair_names


filter_dict_attribute_mapping = {
    'instance-state-name': 'state',
    'instance-id': 'id',
    'state-reason-code': '_state_reason.code',
}

def get_instance_value(instance, instance_attr):
    keys = instance_attr.split('.')
    val = instance
    for key in keys:
        if hasattr(val, key):
            val = getattr(val, key)
        elif isinstance(val, dict):
            val = val[key]
        else:
            return None
    return val

def passes_filter_dict(instance, filter_dict):
    for filter_name, filter_values in filter_dict.items():
        if filter_name in filter_dict_attribute_mapping:
            instance_attr = filter_dict_attribute_mapping[filter_name]
            instance_value = get_instance_value(instance, instance_attr)
            if instance_value not in filter_values:
                return False
        elif filter_name.startswith('tag:'):
            tags = dict((tag['key'], tag['value']) for tag in instance.get_tags())
            tag_name = filter_name.replace('tag:', '', 1)
            tag_value = tags.get(tag_name)
            if tag_value not in filter_values:
                return False
        else:
            raise NotImplementedError(
                "Filter dicts have not been implemented in Moto for '%s' yet. Feel free to open an issue at https://github.com/spulec/moto/issues",
                filter_name)
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


def is_filter_matching(obj, filter, filter_value):
    value = obj.get_filter_value(filter)

    if isinstance(value, six.string_types):
        return value in filter_value

    try:
        value = set(value)
        return (value and value.issubset(filter_value)) or value.issuperset(filter_value)
    except TypeError:
        return value in filter_value


def generic_filter(filters, objects):
    if filters:
        for (_filter, _filter_value) in filters.items():
            objects = [obj for obj in objects if is_filter_matching(obj, _filter, _filter_value)]

    return objects


def simple_aws_filter_to_re(filter_string):
    import fnmatch
    tmp_filter = filter_string.replace('\?','[?]')
    tmp_filter = tmp_filter.replace('\*','[*]')
    tmp_filter = fnmatch.translate(tmp_filter)
    return tmp_filter


# not really random ( http://xkcd.com/221/ )
def random_key_pair():
    return {
        'fingerprint': ('1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:'
                        '7d:b8:ca:9f:f5:f1:6f'),
        'material': """---- BEGIN RSA PRIVATE KEY ----
MIICiTCCAfICCQD6m7oRw0uXOjANBgkqhkiG9w0BAQUFADCBiDELMAkGA1UEBhMC
VVMxCzAJBgNVBAgTAldBMRAwDgYDVQQHEwdTZWF0dGxlMQ8wDQYDVQQKEwZBbWF6
b24xFDASBgNVBAsTC0lBTSBDb25zb2xlMRIwEAYDVQQDEwlUZXN0Q2lsYWMxHzAd
BgkqhkiG9w0BCQEWEG5vb25lQGFtYXpvbi5jb20wHhcNMTEwNDI1MjA0NTIxWhcN
MTIwNDI0MjA0NTIxWjCBiDELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAldBMRAwDgYD
VQQHEwdTZWF0dGxlMQ8wDQYDVQQKEwZBbWF6b24xFDASBgNVBAsTC0lBTSBDb25z
b2xlMRIwEAYDVQQDEwlUZXN0Q2lsYWMxHzAdBgkqhkiG9w0BCQEWEG5vb25lQGFt
YXpvbi5jb20wgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAMaK0dn+a4GmWIWJ
21uUSfwfEvySWtC2XADZ4nB+BLYgVIk60CpiwsZ3G93vUEIO3IyNoH/f0wYK8m9T
rDHudUZg3qX4waLG5M43q7Wgc/MbQITxOUSQv7c7ugFFDzQGBzZswY6786m86gpE
Ibb3OhjZnzcvQAaRHhdlQWIMm2nrAgMBAAEwDQYJKoZIhvcNAQEFBQADgYEAtCu4
nUhVVxYUntneD9+h8Mg9q6q+auNKyExzyLwaxlAoo7TJHidbtS4J5iNmZgXL0Fkb
FFBjvSfpJIlJ00zbhNYS5f6GuoEDmFJl0ZxBHjJnyp378OD8uTs7fLvjx79LjSTb
NYiytVbZPQUQ5Yaxu2jXnimvw3rrszlaEXAMPLE
-----END RSA PRIVATE KEY-----"""
    }


def get_prefix(resource_id):
    resource_id_prefix, separator, after = resource_id.partition('-')
    if resource_id_prefix == EC2_RESOURCE_TO_PREFIX['network-interface']:
        if after.startswith('attach'):
            resource_id_prefix = EC2_RESOURCE_TO_PREFIX['network-interface-attachment']
    if not resource_id_prefix in EC2_RESOURCE_TO_PREFIX.values():
        uuid4hex = re.compile('[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}\Z', re.I)
        if uuid4hex.match(resource_id) is not None:
            resource_id_prefix = EC2_RESOURCE_TO_PREFIX['reserved-instance']
        else:
            return None
    return resource_id_prefix


def is_valid_resource_id(resource_id):
    valid_prefixes = EC2_RESOURCE_TO_PREFIX.values()
    resource_id_prefix = get_prefix(resource_id)
    if not resource_id_prefix in valid_prefixes:
        return False
    resource_id_pattern = resource_id_prefix + '-[0-9a-f]{8}'
    resource_pattern_re = re.compile(resource_id_pattern)
    return resource_pattern_re.match(resource_id) is not None


def is_valid_cidr(cird):
    cidr_pattern = '^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/(\d|[1-2]\d|3[0-2]))$'
    cidr_pattern_re = re.compile(cidr_pattern)
    return cidr_pattern_re.match(cird) is not None
