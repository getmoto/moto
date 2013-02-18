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
