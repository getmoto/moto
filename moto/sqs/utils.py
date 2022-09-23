import string
from moto.moto_api._internal import mock_random as random
from .exceptions import MessageAttributesInvalid


def generate_receipt_handle():
    # http://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/ImportantIdentifiers.html#ImportantIdentifiers-receipt-handles
    length = 185
    return "".join(random.choice(string.ascii_lowercase) for x in range(length))


def extract_input_message_attributes(querystring):
    message_attributes = []
    index = 1
    while True:
        # Loop through looking for message attributes
        name_key = "MessageAttributeName.{0}".format(index)
        name = querystring.get(name_key)
        if not name:
            # Found all attributes
            break
        message_attributes.append(name[0])
        index = index + 1
    return message_attributes


def parse_message_attributes(
    querystring, key="MessageAttribute", base="", value_namespace="Value."
):
    message_attributes = {}
    index = 1
    while True:
        # Loop through looking for message attributes
        name_key = base + "{0}.{1}.Name".format(key, index)
        name = querystring.get(name_key)
        if not name:
            # Found all attributes
            break

        data_type_key = base + "{0}.{1}.{2}DataType".format(key, index, value_namespace)
        data_type = querystring.get(data_type_key)
        if not data_type:
            raise MessageAttributesInvalid(
                "The message attribute '{0}' must contain non-empty message attribute value.".format(
                    name[0]
                )
            )

        data_type_parts = data_type[0].split(".")
        if data_type_parts[0] not in [
            "String",
            "Binary",
            "Number",
        ]:
            raise MessageAttributesInvalid(
                "The message attribute '{0}' has an invalid message attribute type, the set of supported type prefixes is Binary, Number, and String.".format(
                    name[0]
                )
            )

        type_prefix = "String"
        if data_type_parts[0] == "Binary":
            type_prefix = "Binary"

        value_key = base + "{0}.{1}.{2}{3}Value".format(
            key, index, value_namespace, type_prefix
        )
        value = querystring.get(value_key)
        if not value:
            raise MessageAttributesInvalid(
                "The message attribute '{0}' must contain non-empty message attribute value for message attribute type '{1}'.".format(
                    name[0], data_type[0]
                )
            )

        message_attributes[name[0]] = {
            "data_type": data_type[0],
            type_prefix.lower() + "_value": value[0],
        }

        index += 1

    return message_attributes
