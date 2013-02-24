import random


def random_id(prefix=''):
    size = 8
    chars = range(10) + ['a', 'b', 'c', 'd', 'e', 'f']

    instance_tag = ''.join(unicode(random.choice(chars)) for x in range(size))
    return '{}-{}'.format(prefix, instance_tag)


def random_instance_id():
    return random_id(prefix='i')


def random_reservation_id():
    return random_id(prefix='r')


def random_ami_id():
    return random_id(prefix='ami')


def random_security_group_id():
    return random_id(prefix='sg')


def random_volume_id():
    return random_id(prefix='vol')


def random_snapshot_id():
    return random_id(prefix='snap')


def instance_ids_from_querystring(querystring_dict):
    instance_ids = []
    for key, value in querystring_dict.iteritems():
        if 'InstanceId' in key:
            instance_ids.append(value[0])
    return instance_ids


def resource_ids_from_querystring(querystring_dict):
    prefix = 'ResourceId'
    response_values = {}
    for key, value in querystring_dict.iteritems():
        if prefix in key:
            resource_index = key.replace(prefix + ".", "")
            tag_key = querystring_dict.get("Tag.{}.Key".format(resource_index))[0]
            tag_value = querystring_dict.get("Tag.{}.Value".format(resource_index))[0]
            response_values[value[0]] = (tag_key, tag_value)

    return response_values
