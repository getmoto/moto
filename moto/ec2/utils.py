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


def camelcase_to_underscores(argument):
    ''' Converts a camelcase param like theNewAttribute to the equivalent
    python underscore variable like the_new_attribute'''
    result = ''
    for index, char in enumerate(argument):
        if char.istitle() and index:
            # Only add underscore is char is capital and not first letter
            result += "_"
        result += char.lower()
    return result


def method_namess_from_class(clazz):
    return [x[0] for x in inspect.getmembers(clazz, predicate=inspect.ismethod)]
