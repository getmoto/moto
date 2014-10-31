from __future__ import unicode_literals
import random
import string
import six


def random_job_id(size=13):
    chars = list(range(10)) + list(string.ascii_uppercase)
    job_tag = ''.join(six.text_type(random.choice(chars)) for x in range(size))
    return 'j-{0}'.format(job_tag)


def random_instance_group_id(size=13):
    chars = list(range(10)) + list(string.ascii_uppercase)
    job_tag = ''.join(six.text_type(random.choice(chars)) for x in range(size))
    return 'i-{0}'.format(job_tag)
