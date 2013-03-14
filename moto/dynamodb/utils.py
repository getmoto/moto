import datetime


def unix_time(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return delta.total_seconds()


def value_from_dynamo_type(dynamo_type):
    """
    Dynamo return attributes like {"S": "AttributeValue1"}.
    This function takes that value and returns "AttributeValue1".

    # TODO eventually this should be smarted to actually read the type of
    the attribute
    """
    if dynamo_type:
        return dynamo_type.values()[0]


def values_from_dynamo_types(dynamo_types):
    return [value_from_dynamo_type(dynamo_type) for dynamo_type in dynamo_types]
