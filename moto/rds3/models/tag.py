from __future__ import unicode_literals

from collections import defaultdict
from re import compile as re_compile

from moto.rds3.exceptions import InvalidParameterValue
from .base import BaseRDSBackend, BaseRDSModel


class TaggableRDSResource(BaseRDSModel):

    # TODO: Make a tags setter/delete property?
    # That way we don't have he if tags: add_tags in all the entities
    # Setter would have to disallow None values.
    @property
    def tags(self):
        return self.backend.list_tags_for_resource(self.arn)

    def add_tags(self, tags):
        self.backend.add_tags_to_resource(self.arn, tags)

    def remove_tags(self, tag_keys):
        self.backend.remove_tags_from_resource(self.arn, tag_keys)


class Tag(object):
    def __init__(self, key, value):
        self.key = key
        self.value = value


def shape_tags(tags):
    shaped_tags = []
    if isinstance(tags, dict):
        shaped_tags = [{"key": key, "value": value} for key, value in tags.items()]
    elif isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict):
                if "key" in tag and "value" in tag:
                    shaped_tags.append(tag)
            elif isinstance(tag, Tag):
                shaped_tags.append({"key": tag.key, "value": tag.value})
    return shaped_tags


class TagBackend(BaseRDSBackend):
    def __init__(self):
        super(TagBackend, self).__init__()
        self.tags = defaultdict(dict)
        self.arn_match = re_compile(
            r"^arn:aws:rds:.*:[0-9]*:(db|cluster|es|og|pg|cluster-pg|ri|secgrp|snapshot|cluster-snapshot|subgrp):.*$"
        )

    def _verify_resource(self, arn):
        if not self.arn_match.match(arn):
            raise InvalidParameterValue("Invalid resource name: {0}".format(arn))

    def add_tags_to_resource(self, resource_name=None, tags=None):
        # TODO: Add check for null tags
        # TODO: Add check for more than max tags
        # TODO: Check if resource is valid...
        self._verify_resource(resource_name)
        for tag in shape_tags(tags):
            self.tags[resource_name][tag["key"]] = tag["value"]

    def list_tags_for_resource(self, resource_name=None):
        self._verify_resource(resource_name)
        return [Tag(key, value) for key, value in self.tags[resource_name].items()]

    def remove_tags_from_resource(self, resource_name=None, tag_keys=None):
        _tag_keys = tag_keys or []
        self._verify_resource(resource_name)
        for tag in _tag_keys:
            self.tags[resource_name].pop(tag, None)
