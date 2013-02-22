import inspect
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


def camelcase_to_underscores(argument):
    ''' Converts a camelcase param like theNewAttribute to the equivalent
    python underscore variable like the_new_attribute'''
    result = ''
    prev_char_title = True
    for char in argument:
        if char.istitle() and not prev_char_title:
            # Only add underscore if char is capital, not first letter, and prev
            # char wasn't capital
            result += "_"
        prev_char_title = char.istitle()
        if not char.isspace():  # Only add non-whitespace
            result += char.lower()
    return result


def method_namess_from_class(clazz):
    return [x[0] for x in inspect.getmembers(clazz, predicate=inspect.ismethod)]
