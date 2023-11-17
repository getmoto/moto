import random
import string

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
        data_type = querystring.get(data_type_key, [None])[0]

        data_type_parts = (data_type or "").split(".")[0]

        type_prefix = "String"
        if data_type_parts == "Binary":
            type_prefix = "Binary"

        value_key = base + "{0}.{1}.{2}{3}Value".format(
            key, index, value_namespace, type_prefix
        )
        value = querystring.get(value_key, [None])[0]

        message_attributes[name[0]] = {
            "data_type": data_type,
            type_prefix.lower() + "_value": value,
        }

        index += 1

    validate_message_attributes(message_attributes)

    return message_attributes


def validate_message_attributes(message_attributes) -> None:
    for name, value in (message_attributes or {}).items():
        data_type = value["data_type"]

        if not data_type:
            raise MessageAttributesInvalid(
                f"The message attribute '{name}' must contain non-empty message attribute value."
            )

        data_type_parts = data_type.split(".")[0]
        if data_type_parts not in [
            "String",
            "Binary",
            "Number",
        ]:
            raise MessageAttributesInvalid(
                f"The message attribute '{name}' has an invalid message attribute type, the set of supported type prefixes is Binary, Number, and String."
            )

        possible_value_fields = ["string_value", "binary_value"]
        for field in possible_value_fields:
            if field in value and value[field] is None:
                raise MessageAttributesInvalid(
                    f"The message attribute '{name}' must contain non-empty message attribute value for message attribute type '{data_type}'."
                )
