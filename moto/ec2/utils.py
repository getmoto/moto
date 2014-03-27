import random
import re


def random_id(prefix=''):
    size = 8
    chars = range(10) + ['a', 'b', 'c', 'd', 'e', 'f']

    instance_tag = ''.join(unicode(random.choice(chars)) for x in range(size))
    return '{0}-{1}'.format(prefix, instance_tag)


def random_ami_id():
    return random_id(prefix='ami')


def random_instance_id():
    return random_id(prefix='i')


def random_reservation_id():
    return random_id(prefix='r')


def random_security_group_id():
    return random_id(prefix='sg')


def random_snapshot_id():
    return random_id(prefix='snap')


def random_spot_request_id():
    return random_id(prefix='sir')


def random_subnet_id():
    return random_id(prefix='subnet')


def random_volume_id():
    return random_id(prefix='vol')


def random_vpc_id():
    return random_id(prefix='vpc')


def random_eip_association_id():
    return random_id(prefix='eipassoc')


def random_gateway_id():
    return random_id(prefix='igw')


def random_route_table_id():
    return random_id(prefix='rtb')


def random_eip_allocation_id():
    return random_id(prefix='eipalloc')


def random_ip():
    return "127.{0}.{1}.{2}".format(
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )


def instance_ids_from_querystring(querystring_dict):
    instance_ids = []
    for key, value in querystring_dict.iteritems():
        if 'InstanceId' in key:
            instance_ids.append(value[0])
    return instance_ids


def image_ids_from_querystring(querystring_dict):
    image_ids = []
    for key, value in querystring_dict.iteritems():
        if 'ImageId' in key:
            image_ids.append(value[0])
    return image_ids


def sequence_from_querystring(parameter, querystring_dict):
    parameter_values = []
    for key, value in querystring_dict.iteritems():
        if parameter in key:
            parameter_values.append(value[0])
    return parameter_values


def resource_ids_from_querystring(querystring_dict):
    prefix = 'ResourceId'
    response_values = {}
    for key, value in querystring_dict.iteritems():
        if key.startswith(prefix):
            resource_index = key.replace(prefix + ".", "")
            tag_key = querystring_dict.get("Tag.{0}.Key".format(resource_index))[0]

            tag_value_key = "Tag.{0}.Value".format(resource_index)
            if tag_value_key in querystring_dict:
                tag_value = querystring_dict.get(tag_value_key)[0]
            else:
                tag_value = None
            response_values[value[0]] = (tag_key, tag_value)

    return response_values


def filters_from_querystring(querystring_dict):
    response_values = {}
    for key, value in querystring_dict.iteritems():
        match = re.search("Filter.(\d).Name", key)
        if match:
            filter_index = match.groups()[0]
            value_prefix = "Filter.{0}.Value".format(filter_index)
            filter_values = [filter_value[0] for filter_key, filter_value in querystring_dict.iteritems() if filter_key.startswith(value_prefix)]
            response_values[value[0]] = filter_values
    return response_values


def keypair_names_from_querystring(querystring_dict):
    keypair_names = []
    for key, value in querystring_dict.iteritems():
        if 'KeyName' in key:
            keypair_names.append(value[0])
    return keypair_names

filter_dict_attribute_mapping = {
    'instance-state-name': 'state'
}


def passes_filter_dict(instance, filter_dict):
    for filter_name, filter_values in filter_dict.iteritems():
        if filter_name in filter_dict_attribute_mapping:
            instance_attr = filter_dict_attribute_mapping[filter_name]
        else:
            raise NotImplementedError("Filter dicts have not been implemented in Moto for '%s' yet. Feel free to open an issue at https://github.com/spulec/moto/issues", filter_name)
        instance_value = getattr(instance, instance_attr)
        if instance_value not in filter_values:
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


# not really random
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
