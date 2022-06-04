from moto.core import get_account_id
from moto.utilities.utils import filter_resources
from .core import TaggedEC2Resource
from ..utils import random_managed_prefix_list_id, describe_tag_filter


class ManagedPrefixList(TaggedEC2Resource):
    def __init__(
        self,
        backend,
        address_family=None,
        entry=None,
        max_entries=None,
        prefix_list_name=None,
        region=None,
        tags=None,
        owner_id=None,
    ):
        self.ec2_backend = backend
        self.address_family = address_family
        self.max_entries = max_entries
        self.id = random_managed_prefix_list_id()
        self.prefix_list_name = prefix_list_name
        self.state = "create-complete"
        self.state_message = "create complete"
        self.add_tags(tags or {})
        self.version = 1
        self.entries = {self.version: entry} if entry else {}
        self.resource_owner_id = owner_id if owner_id else None
        self.prefix_list_arn = self.arn(region, self.owner_id)
        self.delete_counter = 1

    def arn(self, region, owner_id):
        return "arn:aws:ec2:{region}:{owner_id}:prefix-list/{resource_id}".format(
            region=region, resource_id=self.id, owner_id=owner_id
        )

    @property
    def owner_id(self):
        return (
            get_account_id() if not self.resource_owner_id else self.resource_owner_id
        )


class ManagedPrefixListBackend:
    def __init__(self):
        self.managed_prefix_lists = {}
        self.create_default_pls()

    def create_managed_prefix_list(
        self,
        address_family=None,
        entry=None,
        max_entries=None,
        prefix_list_name=None,
        tags=None,
        owner_id=None,
    ):
        managed_prefix_list = ManagedPrefixList(
            self,
            address_family=address_family,
            entry=entry,
            max_entries=max_entries,
            prefix_list_name=prefix_list_name,
            region=self.region_name,
            tags=tags,
            owner_id=owner_id,
        )
        self.managed_prefix_lists[managed_prefix_list.id] = managed_prefix_list
        return managed_prefix_list

    def describe_managed_prefix_lists(self, prefix_list_ids=None, filters=None):
        managed_prefix_lists = list(self.managed_prefix_lists.copy().values())
        attr_pairs = (
            ("owner-id", "owner_id"),
            ("prefix-list-id", "id"),
            ("prefix-list-name", "prefix_list_name"),
        )

        if prefix_list_ids:
            managed_prefix_lists = [
                managed_prefix_list
                for managed_prefix_list in managed_prefix_lists
                if managed_prefix_list.id in prefix_list_ids
            ]

        result = managed_prefix_lists
        if filters:
            result = filter_resources(result, filters, attr_pairs)
            result = describe_tag_filter(filters, result)

        for item in result.copy():
            if not item.delete_counter:
                self.managed_prefix_lists.pop(item.id, None)
                result.remove(item)
            if item.state == "delete-complete":
                item.delete_counter -= 1
        return result

    def get_managed_prefix_list_entries(self, prefix_list_id=None):
        managed_prefix_list = self.managed_prefix_lists.get(prefix_list_id)
        return managed_prefix_list

    def delete_managed_prefix_list(self, prefix_list_id):
        managed_prefix_list = self.managed_prefix_lists.get(prefix_list_id)
        managed_prefix_list.state = "delete-complete"
        return managed_prefix_list

    def modify_managed_prefix_list(
        self,
        add_entry=None,
        prefix_list_id=None,
        current_version=None,
        prefix_list_name=None,
        remove_entry=None,
    ):
        managed_pl = self.managed_prefix_lists.get(prefix_list_id)
        managed_pl.prefix_list_name = prefix_list_name
        if remove_entry or add_entry:
            latest_version = managed_pl.entries.get(managed_pl.version)
            entries = (
                managed_pl.entries.get(current_version, latest_version).copy()
                if managed_pl.entries
                else []
            )
            for item in entries.copy():
                if item.get("Cidr", "") in remove_entry:
                    entries.remove(item)

            for item in add_entry:
                if item not in entries.copy():
                    entries.append(item)
            managed_pl.version += 1
            managed_pl.entries[managed_pl.version] = entries
        managed_pl.state = "modify-complete"
        return managed_pl

    def create_default_pls(self):
        entry = [
            {"Cidr": "52.216.0.0/15", "Description": "default"},
            {"Cidr": "3.5.0.0/19", "Description": "default"},
            {"Cidr": "54.231.0.0/16", "Description": "default"},
        ]

        managed_prefix_list = self.create_managed_prefix_list(
            address_family="IPv4",
            entry=entry,
            prefix_list_name="com.amazonaws.{}.s3".format(self.region_name),
            owner_id="aws",
        )
        managed_prefix_list.version = None
        managed_prefix_list.max_entries = None
        self.managed_prefix_lists[managed_prefix_list.id] = managed_prefix_list

        entry = [
            {"Cidr": "3.218.182.0/24", "Description": "default"},
            {"Cidr": "3.218.180.0/23", "Description": "default"},
            {"Cidr": "52.94.0.0/22", "Description": "default"},
            {"Cidr": "52.119.224.0/20", "Description": "default"},
        ]

        managed_prefix_list = self.create_managed_prefix_list(
            address_family="IPv4",
            entry=entry,
            prefix_list_name="com.amazonaws.{}.dynamodb".format(self.region_name),
            owner_id="aws",
        )
        managed_prefix_list.version = None
        managed_prefix_list.max_entries = None
        self.managed_prefix_lists[managed_prefix_list.id] = managed_prefix_list
