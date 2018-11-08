from __future__ import unicode_literals

import random
import string
import six
import re


def random_password(password_length, exclude_characters, exclude_numbers,
                    exclude_punctuation, exclude_uppercase, exclude_lowercase,
                    include_space, require_each_included_type):

    password = ''
    required_characters = ''

    if not exclude_lowercase and not exclude_uppercase:
        password += string.ascii_letters
        required_characters += random.choice(_exclude_characters(
            string.ascii_lowercase, exclude_characters))
        required_characters += random.choice(_exclude_characters(
            string.ascii_uppercase, exclude_characters))
    elif not exclude_lowercase:
        password += string.ascii_lowercase
        required_characters += random.choice(_exclude_characters(
            string.ascii_lowercase, exclude_characters))
    elif not exclude_uppercase:
        password += string.ascii_uppercase
        required_characters += random.choice(_exclude_characters(
            string.ascii_uppercase, exclude_characters))
    if not exclude_numbers:
        password += string.digits
        required_characters += random.choice(_exclude_characters(
            string.digits, exclude_characters))
    if not exclude_punctuation:
        password += string.punctuation
        required_characters += random.choice(_exclude_characters(
            string.punctuation, exclude_characters))
    if include_space:
        password += " "
        required_characters += " "

    password = ''.join(
        six.text_type(random.choice(password))
        for x in range(password_length))

    if require_each_included_type:
        password = _add_password_require_each_included_type(
            password, required_characters)

    password = _exclude_characters(password, exclude_characters)
    return password


def secret_arn(region, secret_id):
    return "arn:aws:secretsmanager:{0}:1234567890:secret:{1}-rIjad".format(
        region, secret_id)


def _exclude_characters(password, exclude_characters):
    for c in exclude_characters:
        if c in string.punctuation:
            # Escape punctuation regex usage
            c = "\{0}".format(c)
        password = re.sub(c, '', str(password))
    return password


def _add_password_require_each_included_type(password, required_characters):
    password_with_required_char = password[:-len(required_characters)]
    password_with_required_char += required_characters

    return password_with_required_char
