import string
import re
from moto.moto_api._internal import mock_random as random


def random_password(
    password_length: int,
    exclude_characters: str,
    exclude_numbers: bool,
    exclude_punctuation: bool,
    exclude_uppercase: bool,
    exclude_lowercase: bool,
    include_space: bool,
    require_each_included_type: bool,
) -> str:

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

    password = "".join(str(random.choice(password)) for x in range(password_length))

    if require_each_included_type:
        password = _add_password_require_each_included_type(
            password, required_characters
        )

    return password


def secret_arn(account_id: str, region: str, secret_id: str) -> str:
    id_string = "".join(random.choice(string.ascii_letters) for _ in range(6))
    return (
        f"arn:aws:secretsmanager:{region}:{account_id}:secret:{secret_id}-{id_string}"
    )


def get_secret_name_from_partial_arn(partial_arn: str) -> str:
    # We can retrieve a secret either using a full ARN, or using a partial ARN
    # name:        testsecret
    # full ARN:    arn:aws:secretsmanager:us-west-2:123456789012:secret:testsecret-xxxxxx
    # partial ARN: arn:aws:secretsmanager:us-west-2:123456789012:secret:testsecret
    #
    # This method only deals with partial ARN's, and will return the name: testsecret
    #
    # If you were to pass in  full url, this method will return 'testsecret-xxxxxx' - which has no meaning on it's own
    if partial_arn.startswith("arn:aws:secretsmanager:"):
        # split the arn by colon
        # then get the last value which is the name appended with a random string
        return partial_arn.split(":")[-1]
    return partial_arn


def _exclude_characters(password: str, exclude_characters: str) -> str:
    for c in exclude_characters:
        if c in string.punctuation:
            # Escape punctuation regex usage
            c = rf"\{c}"
        password = re.sub(c, "", str(password))
    return password


def _add_password_require_each_included_type(
    password: str, required_characters: str
) -> str:
    password_with_required_char = password[: -len(required_characters)]
    password_with_required_char += required_characters

    return password_with_required_char
