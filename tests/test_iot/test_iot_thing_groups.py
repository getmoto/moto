import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_iot


def generate_thing_group_tree(iot_client, tree_dict, _parent=None):
    """
    Generates a thing group tree given the input tree structure.
    :param iot_client: the iot client for boto3
    :param tree_dict: dictionary with the key being the group_name, and the value being a sub tree.
        tree_dict = {
            "group_name_1a":{
                "group_name_2a":{
                    "group_name_3a":{} or None
                },
            },
            "group_name_1b":{}
        }
    :return: a dictionary of created groups, keyed by group name
    """
    if tree_dict is None:
        tree_dict = {}
    created_dict = {}
    for group_name in tree_dict.keys():
        params = {"thingGroupName": group_name}
        if _parent:
            params["parentGroupName"] = _parent
        created_group = iot_client.create_thing_group(**params)
        created_dict[group_name] = created_group
        subtree_dict = generate_thing_group_tree(
            iot_client=iot_client, tree_dict=tree_dict[group_name], _parent=group_name
        )
        created_dict.update(created_dict)
        created_dict.update(subtree_dict)
    return created_dict


class TestListThingGroup:
    group_name_1a = "my-group-name-1a"
    group_name_1b = "my-group-name-1b"
    group_name_2a = "my-group-name-2a"
    group_name_2b = "my-group-name-2b"
    group_name_3a = "my-group-name-3a"
    group_name_3b = "my-group-name-3b"
    group_name_3c = "my-group-name-3c"
    group_name_3d = "my-group-name-3d"
    tree_dict = {
        group_name_1a: {
            group_name_2a: {group_name_3a: {}, group_name_3b: {}},
            group_name_2b: {group_name_3c: {}, group_name_3d: {}},
        },
        group_name_1b: {},
    }

    @mock_iot
    def test_should_list_all_groups(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups()
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(8)

    @mock_iot
    def test_should_list_all_groups_non_recursively(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(recursive=False)
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)

    @mock_iot
    def test_should_list_all_groups_filtered_by_parent(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(parentGroup=self.group_name_1a)
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(6)
        resp = client.list_thing_groups(parentGroup=self.group_name_2a)
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)
        resp = client.list_thing_groups(parentGroup=self.group_name_1b)
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(0)
        with pytest.raises(ClientError) as e:
            client.list_thing_groups(parentGroup="inexistant-group-name")
            e.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")

    @mock_iot
    def test_should_list_all_groups_filtered_by_parent_non_recursively(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(parentGroup=self.group_name_1a, recursive=False)
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)
        resp = client.list_thing_groups(parentGroup=self.group_name_2a, recursive=False)
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)

    @mock_iot
    def test_should_list_all_groups_filtered_by_name_prefix(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(namePrefixFilter="my-group-name-1")
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)
        resp = client.list_thing_groups(namePrefixFilter="my-group-name-3")
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(4)
        resp = client.list_thing_groups(namePrefixFilter="prefix-which-doesn-not-match")
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(0)

    @mock_iot
    def test_should_list_all_groups_filtered_by_name_prefix_non_recursively(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(
            namePrefixFilter="my-group-name-1", recursive=False
        )
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)
        resp = client.list_thing_groups(
            namePrefixFilter="my-group-name-3", recursive=False
        )
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(0)

    @mock_iot
    def test_should_list_all_groups_filtered_by_name_prefix_and_parent(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(
            namePrefixFilter="my-group-name-2", parentGroup=self.group_name_1a
        )
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)
        resp = client.list_thing_groups(
            namePrefixFilter="my-group-name-3", parentGroup=self.group_name_1a
        )
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(4)
        resp = client.list_thing_groups(
            namePrefixFilter="prefix-which-doesn-not-match",
            parentGroup=self.group_name_1a,
        )
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(0)


@mock_iot
def test_delete_thing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    group_name_1a = "my-group-name-1a"
    group_name_2a = "my-group-name-2a"
    tree_dict = {
        group_name_1a: {group_name_2a: {},},
    }
    generate_thing_group_tree(client, tree_dict)

    # delete group with child
    try:
        client.delete_thing_group(thingGroupName=group_name_1a)
    except client.exceptions.InvalidRequestException as exc:
        error_code = exc.response["Error"]["Code"]
        error_code.should.equal("InvalidRequestException")
    else:
        raise Exception("Should have raised error")

    # delete child group
    client.delete_thing_group(thingGroupName=group_name_2a)
    res = client.list_thing_groups()
    res.should.have.key("thingGroups").which.should.have.length_of(1)
    res["thingGroups"].should_not.have.key(group_name_2a)

    # now that there is no child group, we can delete the previous group safely
    client.delete_thing_group(thingGroupName=group_name_1a)
    res = client.list_thing_groups()
    res.should.have.key("thingGroups").which.should.have.length_of(0)

    # Deleting an invalid thing group does not raise an error.
    res = client.delete_thing_group(thingGroupName="non-existent-group-name")
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_iot
def test_describe_thing_group_metadata_hierarchy():
    client = boto3.client("iot", region_name="ap-northeast-1")
    group_name_1a = "my-group-name-1a"
    group_name_1b = "my-group-name-1b"
    group_name_2a = "my-group-name-2a"
    group_name_2b = "my-group-name-2b"
    group_name_3a = "my-group-name-3a"
    group_name_3b = "my-group-name-3b"
    group_name_3c = "my-group-name-3c"
    group_name_3d = "my-group-name-3d"

    tree_dict = {
        group_name_1a: {
            group_name_2a: {group_name_3a: {}, group_name_3b: {}},
            group_name_2b: {group_name_3c: {}, group_name_3d: {}},
        },
        group_name_1b: {},
    }
    group_catalog = generate_thing_group_tree(client, tree_dict)

    # describe groups
    # groups level 1
    # 1a
    thing_group_description1a = client.describe_thing_group(
        thingGroupName=group_name_1a
    )
    thing_group_description1a.should.have.key("thingGroupName").which.should.equal(
        group_name_1a
    )
    thing_group_description1a.should.have.key("thingGroupProperties")
    thing_group_description1a.should.have.key("thingGroupMetadata")
    thing_group_description1a["thingGroupMetadata"].should.have.key("creationDate")
    thing_group_description1a.should.have.key("version")
    # 1b
    thing_group_description1b = client.describe_thing_group(
        thingGroupName=group_name_1b
    )
    thing_group_description1b.should.have.key("thingGroupName").which.should.equal(
        group_name_1b
    )
    thing_group_description1b.should.have.key("thingGroupProperties")
    thing_group_description1b.should.have.key("thingGroupMetadata")
    thing_group_description1b["thingGroupMetadata"].should.have.length_of(1)
    thing_group_description1b["thingGroupMetadata"].should.have.key("creationDate")
    thing_group_description1b.should.have.key("version")
    # groups level 2
    # 2a
    thing_group_description2a = client.describe_thing_group(
        thingGroupName=group_name_2a
    )
    thing_group_description2a.should.have.key("thingGroupName").which.should.equal(
        group_name_2a
    )
    thing_group_description2a.should.have.key("thingGroupProperties")
    thing_group_description2a.should.have.key("thingGroupMetadata")
    thing_group_description2a["thingGroupMetadata"].should.have.length_of(3)
    thing_group_description2a["thingGroupMetadata"].should.have.key(
        "parentGroupName"
    ).being.equal(group_name_1a)
    thing_group_description2a["thingGroupMetadata"].should.have.key(
        "rootToParentThingGroups"
    )
    thing_group_description2a["thingGroupMetadata"][
        "rootToParentThingGroups"
    ].should.have.length_of(1)
    thing_group_description2a["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupName"
    ].should.match(group_name_1a)
    thing_group_description2a["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupArn"
    ].should.match(group_catalog[group_name_1a]["thingGroupArn"])
    thing_group_description2a.should.have.key("version")
    # 2b
    thing_group_description2b = client.describe_thing_group(
        thingGroupName=group_name_2b
    )
    thing_group_description2b.should.have.key("thingGroupName").which.should.equal(
        group_name_2b
    )
    thing_group_description2b.should.have.key("thingGroupProperties")
    thing_group_description2b.should.have.key("thingGroupMetadata")
    thing_group_description2b["thingGroupMetadata"].should.have.length_of(3)
    thing_group_description2b["thingGroupMetadata"].should.have.key(
        "parentGroupName"
    ).being.equal(group_name_1a)
    thing_group_description2b["thingGroupMetadata"].should.have.key(
        "rootToParentThingGroups"
    )
    thing_group_description2b["thingGroupMetadata"][
        "rootToParentThingGroups"
    ].should.have.length_of(1)
    thing_group_description2b["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupName"
    ].should.match(group_name_1a)
    thing_group_description2b["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupArn"
    ].should.match(group_catalog[group_name_1a]["thingGroupArn"])
    thing_group_description2b.should.have.key("version")
    # groups level 3
    # 3a
    thing_group_description3a = client.describe_thing_group(
        thingGroupName=group_name_3a
    )
    thing_group_description3a.should.have.key("thingGroupName").which.should.equal(
        group_name_3a
    )
    thing_group_description3a.should.have.key("thingGroupProperties")
    thing_group_description3a.should.have.key("thingGroupMetadata")
    thing_group_description3a["thingGroupMetadata"].should.have.length_of(3)
    thing_group_description3a["thingGroupMetadata"].should.have.key(
        "parentGroupName"
    ).being.equal(group_name_2a)
    thing_group_description3a["thingGroupMetadata"].should.have.key(
        "rootToParentThingGroups"
    )
    thing_group_description3a["thingGroupMetadata"][
        "rootToParentThingGroups"
    ].should.have.length_of(2)
    thing_group_description3a["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupName"
    ].should.match(group_name_1a)
    thing_group_description3a["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupArn"
    ].should.match(group_catalog[group_name_1a]["thingGroupArn"])
    thing_group_description3a["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupName"
    ].should.match(group_name_2a)
    thing_group_description3a["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupArn"
    ].should.match(group_catalog[group_name_2a]["thingGroupArn"])
    thing_group_description3a.should.have.key("version")
    # 3b
    thing_group_description3b = client.describe_thing_group(
        thingGroupName=group_name_3b
    )
    thing_group_description3b.should.have.key("thingGroupName").which.should.equal(
        group_name_3b
    )
    thing_group_description3b.should.have.key("thingGroupProperties")
    thing_group_description3b.should.have.key("thingGroupMetadata")
    thing_group_description3b["thingGroupMetadata"].should.have.length_of(3)
    thing_group_description3b["thingGroupMetadata"].should.have.key(
        "parentGroupName"
    ).being.equal(group_name_2a)
    thing_group_description3b["thingGroupMetadata"].should.have.key(
        "rootToParentThingGroups"
    )
    thing_group_description3b["thingGroupMetadata"][
        "rootToParentThingGroups"
    ].should.have.length_of(2)
    thing_group_description3b["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupName"
    ].should.match(group_name_1a)
    thing_group_description3b["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupArn"
    ].should.match(group_catalog[group_name_1a]["thingGroupArn"])
    thing_group_description3b["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupName"
    ].should.match(group_name_2a)
    thing_group_description3b["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupArn"
    ].should.match(group_catalog[group_name_2a]["thingGroupArn"])
    thing_group_description3b.should.have.key("version")
    # 3c
    thing_group_description3c = client.describe_thing_group(
        thingGroupName=group_name_3c
    )
    thing_group_description3c.should.have.key("thingGroupName").which.should.equal(
        group_name_3c
    )
    thing_group_description3c.should.have.key("thingGroupProperties")
    thing_group_description3c.should.have.key("thingGroupMetadata")
    thing_group_description3c["thingGroupMetadata"].should.have.length_of(3)
    thing_group_description3c["thingGroupMetadata"].should.have.key(
        "parentGroupName"
    ).being.equal(group_name_2b)
    thing_group_description3c["thingGroupMetadata"].should.have.key(
        "rootToParentThingGroups"
    )
    thing_group_description3c["thingGroupMetadata"][
        "rootToParentThingGroups"
    ].should.have.length_of(2)
    thing_group_description3c["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupName"
    ].should.match(group_name_1a)
    thing_group_description3c["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupArn"
    ].should.match(group_catalog[group_name_1a]["thingGroupArn"])
    thing_group_description3c["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupName"
    ].should.match(group_name_2b)
    thing_group_description3c["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupArn"
    ].should.match(group_catalog[group_name_2b]["thingGroupArn"])
    thing_group_description3c.should.have.key("version")
    # 3d
    thing_group_description3d = client.describe_thing_group(
        thingGroupName=group_name_3d
    )
    thing_group_description3d.should.have.key("thingGroupName").which.should.equal(
        group_name_3d
    )
    thing_group_description3d.should.have.key("thingGroupProperties")
    thing_group_description3d.should.have.key("thingGroupMetadata")
    thing_group_description3d["thingGroupMetadata"].should.have.length_of(3)
    thing_group_description3d["thingGroupMetadata"].should.have.key(
        "parentGroupName"
    ).being.equal(group_name_2b)
    thing_group_description3d["thingGroupMetadata"].should.have.key(
        "rootToParentThingGroups"
    )
    thing_group_description3d["thingGroupMetadata"][
        "rootToParentThingGroups"
    ].should.have.length_of(2)
    thing_group_description3d["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupName"
    ].should.match(group_name_1a)
    thing_group_description3d["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupArn"
    ].should.match(group_catalog[group_name_1a]["thingGroupArn"])
    thing_group_description3d["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupName"
    ].should.match(group_name_2b)
    thing_group_description3d["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupArn"
    ].should.match(group_catalog[group_name_2b]["thingGroupArn"])
    thing_group_description3d.should.have.key("version")


@mock_iot
def test_thing_groups():
    client = boto3.client("iot", region_name="ap-northeast-1")
    group_name = "my-group-name"

    # thing group
    thing_group = client.create_thing_group(thingGroupName=group_name)
    thing_group.should.have.key("thingGroupName").which.should.equal(group_name)
    thing_group.should.have.key("thingGroupArn")
    thing_group["thingGroupArn"].should.contain(group_name)

    res = client.list_thing_groups()
    res.should.have.key("thingGroups").which.should.have.length_of(1)
    for thing_group in res["thingGroups"]:
        thing_group.should.have.key("groupName").which.should_not.be.none
        thing_group.should.have.key("groupArn").which.should_not.be.none

    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key("thingGroupName").which.should.equal(group_name)
    thing_group.should.have.key("thingGroupProperties")
    thing_group.should.have.key("thingGroupMetadata")
    thing_group.should.have.key("version")
    thing_group.should.have.key("thingGroupArn")
    thing_group["thingGroupArn"].should.contain(group_name)

    # delete thing group
    client.delete_thing_group(thingGroupName=group_name)
    res = client.list_thing_groups()
    res.should.have.key("thingGroups").which.should.have.length_of(0)

    # props create test
    props = {
        "thingGroupDescription": "my first thing group",
        "attributePayload": {"attributes": {"key1": "val01", "Key02": "VAL2"}},
    }
    thing_group = client.create_thing_group(
        thingGroupName=group_name, thingGroupProperties=props
    )
    thing_group.should.have.key("thingGroupName").which.should.equal(group_name)
    thing_group.should.have.key("thingGroupArn")

    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key("thingGroupProperties").which.should.have.key(
        "attributePayload"
    ).which.should.have.key("attributes")
    res_props = thing_group["thingGroupProperties"]["attributePayload"]["attributes"]
    res_props.should.have.key("key1").which.should.equal("val01")
    res_props.should.have.key("Key02").which.should.equal("VAL2")

    # props update test with merge
    new_props = {"attributePayload": {"attributes": {"k3": "v3"}, "merge": True}}
    client.update_thing_group(thingGroupName=group_name, thingGroupProperties=new_props)
    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key("thingGroupProperties").which.should.have.key(
        "attributePayload"
    ).which.should.have.key("attributes")
    res_props = thing_group["thingGroupProperties"]["attributePayload"]["attributes"]
    res_props.should.have.key("key1").which.should.equal("val01")
    res_props.should.have.key("Key02").which.should.equal("VAL2")

    res_props.should.have.key("k3").which.should.equal("v3")

    # props update test
    new_props = {"attributePayload": {"attributes": {"k4": "v4"}}}
    client.update_thing_group(thingGroupName=group_name, thingGroupProperties=new_props)
    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key("thingGroupProperties").which.should.have.key(
        "attributePayload"
    ).which.should.have.key("attributes")
    res_props = thing_group["thingGroupProperties"]["attributePayload"]["attributes"]
    res_props.should.have.key("k4").which.should.equal("v4")
    res_props.should_not.have.key("key1")


@mock_iot
def test_thing_group_relations():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"
    group_name = "my-group-name"

    # thing group
    thing_group = client.create_thing_group(thingGroupName=group_name)
    thing_group.should.have.key("thingGroupName").which.should.equal(group_name)
    thing_group.should.have.key("thingGroupArn")

    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    # add in 4 way
    client.add_thing_to_thing_group(thingGroupName=group_name, thingName=name)
    client.add_thing_to_thing_group(
        thingGroupArn=thing_group["thingGroupArn"], thingArn=thing["thingArn"]
    )
    client.add_thing_to_thing_group(
        thingGroupName=group_name, thingArn=thing["thingArn"]
    )
    client.add_thing_to_thing_group(
        thingGroupArn=thing_group["thingGroupArn"], thingName=name
    )

    things = client.list_things_in_thing_group(thingGroupName=group_name)
    things.should.have.key("things")
    things["things"].should.have.length_of(1)

    thing_groups = client.list_thing_groups_for_thing(thingName=name)
    thing_groups.should.have.key("thingGroups")
    thing_groups["thingGroups"].should.have.length_of(1)

    # remove in 4 way
    client.remove_thing_from_thing_group(thingGroupName=group_name, thingName=name)
    client.remove_thing_from_thing_group(
        thingGroupArn=thing_group["thingGroupArn"], thingArn=thing["thingArn"]
    )
    client.remove_thing_from_thing_group(
        thingGroupName=group_name, thingArn=thing["thingArn"]
    )
    client.remove_thing_from_thing_group(
        thingGroupArn=thing_group["thingGroupArn"], thingName=name
    )
    things = client.list_things_in_thing_group(thingGroupName=group_name)
    things.should.have.key("things")
    things["things"].should.have.length_of(0)

    # update thing group for thing
    client.update_thing_groups_for_thing(thingName=name, thingGroupsToAdd=[group_name])
    things = client.list_things_in_thing_group(thingGroupName=group_name)
    things.should.have.key("things")
    things["things"].should.have.length_of(1)

    client.update_thing_groups_for_thing(
        thingName=name, thingGroupsToRemove=[group_name]
    )
    things = client.list_things_in_thing_group(thingGroupName=group_name)
    things.should.have.key("things")
    things["things"].should.have.length_of(0)
