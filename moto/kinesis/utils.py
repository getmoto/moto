import sys
import base64

from .exceptions import InvalidArgumentError


if sys.version_info[0] == 2:
    encode_method = base64.encodestring
    decode_method = base64.decodestring
elif sys.version_info[0] == 3:
    encode_method = base64.encodebytes
    decode_method = base64.decodebytes
else:
    raise Exception("Python version is not supported")


def compose_new_shard_iterator(stream_name, shard, shard_iterator_type, starting_sequence_number,
                               at_timestamp):
    if shard_iterator_type == "AT_SEQUENCE_NUMBER":
        last_sequence_id = int(starting_sequence_number) - 1
    elif shard_iterator_type == "AFTER_SEQUENCE_NUMBER":
        last_sequence_id = int(starting_sequence_number)
    elif shard_iterator_type == "TRIM_HORIZON":
        last_sequence_id = 0
    elif shard_iterator_type == "LATEST":
        last_sequence_id = shard.get_max_sequence_number()
    elif shard_iterator_type == "AT_TIMESTAMP":
        last_sequence_id = shard.get_sequence_number_at(at_timestamp)
    else:
        raise InvalidArgumentError(
            "Invalid ShardIteratorType: {0}".format(shard_iterator_type))
    return compose_shard_iterator(stream_name, shard, last_sequence_id)


def compose_shard_iterator(stream_name, shard, last_sequence_id):
    return encode_method(
        "{0}:{1}:{2}".format(
            stream_name,
            shard.shard_id,
            last_sequence_id,
        ).encode("utf-8")
    ).decode("utf-8")


def decompose_shard_iterator(shard_iterator):
    return decode_method(shard_iterator.encode("utf-8")).decode("utf-8").split(":")
