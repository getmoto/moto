from __future__ import unicode_literals

import random
import string
import six
import re

from moto.core import ACCOUNT_ID


def random_password(
    password_length,
    exclude_characters,
    exclude_numbers,
    exclude_punctuation,
    exclude_uppercase,
    exclude_lowercase,
    include_space,
    require_each_included_type,
):

    password = ""
    required_characters = ""

    if not exclude_lowercase and not exclude_uppercase:
        password += string.ascii_letters
        required_characters += random.choice(
            _exclude_characters(string.ascii_lowercase, exclude_characters)
        )
        required_characters += random.choice(
            _exclude_characters(string.ascii_uppercase, exclude_characters)
        )
    elif not exclude_lowercase:
        password += string.ascii_lowercase
        required_characters += random.choice(
            _exclude_characters(string.ascii_lowercase, exclude_characters)
        )
    elif not exclude_uppercase:
        password += string.ascii_uppercase
        required_characters += random.choice(
            _exclude_characters(string.ascii_uppercase, exclude_characters)
        )
    if not exclude_numbers:
        password += string.digits
        required_characters += random.choice(
            _exclude_characters(string.digits, exclude_characters)
        )
    if not exclude_punctuation:
        password += string.punctuation
        required_characters += random.choice(
            _exclude_characters(string.punctuation, exclude_characters)
        )
    if include_space:
        password += " "
        required_characters += " "
    if exclude_characters:
        password = _exclude_characters(password, exclude_characters)

    password = "".join(
        six.text_type(random.choice(password)) for x in range(password_length)
    )

    if require_each_included_type:
        password = _add_password_require_each_included_type(
            password, required_characters
        )

    return password


def secret_arn(region, secret_id):
    id_string = "".join(random.choice(string.ascii_letters) for _ in range(5))
    return "arn:aws:secretsmanager:{0}:{1}:secret:{2}-{3}".format(
        region, ACCOUNT_ID, secret_id, id_string
    )


def get_secret_name_from_arn(secret_id):
    # can fetch by both arn and by name
    # but we are storing via name
    # so we need to change the arn to name
    # if it starts with arn then the secret id is arn
    if secret_id.startswith("arn:aws:secretsmanager:"):
        # split the arn by colon
        # then get the last value which is the name appended with a random string
        # then remove the random string
        secret_id = "-".join(secret_id.split(":")[-1].split("-")[:-1])
    return secret_id


def _exclude_characters(password, exclude_characters):
    for c in exclude_characters:
        if c in string.punctuation:
            # Escape punctuation regex usage
            c = r"\{0}".format(c)
        password = re.sub(c, "", str(password))
    return password


def _add_password_require_each_included_type(password, required_characters):
    password_with_required_char = password[: -len(required_characters)]
    password_with_required_char += required_characters

    return password_with_required_char
