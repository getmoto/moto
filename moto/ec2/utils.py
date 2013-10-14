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
