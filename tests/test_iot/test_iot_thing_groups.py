import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


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
    group_name_1a = "my-group:name-1a"
    group_name_1b = "my-group:name-1b"
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

    @mock_aws
    def test_should_list_all_groups(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups()
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 8

    @mock_aws
    def test_should_list_all_groups_non_recursively(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(recursive=False)
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 2

    @mock_aws
    def test_should_list_all_groups_filtered_by_parent(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(parentGroup=self.group_name_1a)
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 6
        resp = client.list_thing_groups(parentGroup=self.group_name_2a)
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 2
        resp = client.list_thing_groups(parentGroup=self.group_name_1b)
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 0
        with pytest.raises(ClientError) as e:
            client.list_thing_groups(parentGroup="inexistant-group-name")
            assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"

    @mock_aws
    def test_should_list_all_groups_filtered_by_parent_non_recursively(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(parentGroup=self.group_name_1a, recursive=False)
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 2
        resp = client.list_thing_groups(parentGroup=self.group_name_2a, recursive=False)
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 2

    @mock_aws
    def test_should_list_all_groups_filtered_by_name_prefix(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(namePrefixFilter="my-group:name-1")
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 2
        resp = client.list_thing_groups(namePrefixFilter="my-group-name-3")
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 4
        resp = client.list_thing_groups(namePrefixFilter="prefix-which-doesn-not-match")
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 0

    @mock_aws
    def test_should_list_all_groups_filtered_by_name_prefix_non_recursively(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(
            namePrefixFilter="my-group:name-1", recursive=False
        )
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 2
        resp = client.list_thing_groups(
            namePrefixFilter="my-group-name-3", recursive=False
        )
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 0

    @mock_aws
    def test_should_list_all_groups_filtered_by_name_prefix_and_parent(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(
            namePrefixFilter="my-group-name-2", parentGroup=self.group_name_1a
        )
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 2
        resp = client.list_thing_groups(
            namePrefixFilter="my-group-name-3", parentGroup=self.group_name_1a
        )
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 4
        resp = client.list_thing_groups(
            namePrefixFilter="prefix-which-doesn-not-match",
            parentGroup=self.group_name_1a,
        )
        assert "thingGroups" in resp
        assert len(resp["thingGroups"]) == 0


@mock_aws
def test_delete_thing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    group_name_1a = "my-group:name-1a"
    group_name_2a = "my-group-name-2a"
    tree_dict = {group_name_1a: {group_name_2a: {}}}
    generate_thing_group_tree(client, tree_dict)

    # delete group with child
    try:
        client.delete_thing_group(thingGroupName=group_name_1a)
    except client.exceptions.InvalidRequestException as exc:
        error_code = exc.response["Error"]["Code"]
        assert error_code == "InvalidRequestException"
    else:
        raise Exception("Should have raised error")

    # delete child group
    client.delete_thing_group(thingGroupName=group_name_2a)
    res = client.list_thing_groups()
    assert len(res["thingGroups"]) == 1
    assert group_name_2a not in res["thingGroups"]

    # now that there is no child group, we can delete the previous group safely
    client.delete_thing_group(thingGroupName=group_name_1a)
    res = client.list_thing_groups()
    assert len(res["thingGroups"]) == 0

    # Deleting an invalid thing group does not raise an error.
    res = client.delete_thing_group(thingGroupName="non-existent-group-name")
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_describe_thing_group_metadata_hierarchy():
    client = boto3.client("iot", region_name="ap-northeast-1")
    group_name_1a = "my-group:name-1a"
    group_name_1b = "my-group:name-1b"
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
    desc1a = client.describe_thing_group(thingGroupName=group_name_1a)
    assert desc1a["thingGroupName"] == group_name_1a
    assert "thingGroupProperties" in desc1a
    assert "creationDate" in desc1a["thingGroupMetadata"]
    assert "version" in desc1a
    # 1b
    desc1b = client.describe_thing_group(thingGroupName=group_name_1b)
    assert desc1b["thingGroupName"] == group_name_1b
    assert "thingGroupProperties" in desc1b
    assert len(desc1b["thingGroupMetadata"]) == 1
    assert "creationDate" in desc1b["thingGroupMetadata"]
    assert "version" in desc1b
    # groups level 2
    # 2a
    desc2a = client.describe_thing_group(thingGroupName=group_name_2a)
    assert desc2a["thingGroupName"] == group_name_2a
    assert "thingGroupProperties" in desc2a
    assert len(desc2a["thingGroupMetadata"]) == 3
    assert desc2a["thingGroupMetadata"]["parentGroupName"] == group_name_1a
    desc2a_groups = desc2a["thingGroupMetadata"]["rootToParentThingGroups"]
    assert len(desc2a_groups) == 1
    assert desc2a_groups[0]["groupName"] == group_name_1a
    assert desc2a_groups[0]["groupArn"] == group_catalog[group_name_1a]["thingGroupArn"]
    assert "version" in desc2a
    # 2b
    desc2b = client.describe_thing_group(thingGroupName=group_name_2b)
    assert desc2b["thingGroupName"] == group_name_2b
    assert "thingGroupProperties" in desc2b
    assert len(desc2b["thingGroupMetadata"]) == 3
    assert desc2b["thingGroupMetadata"]["parentGroupName"] == group_name_1a
    desc2b_groups = desc2b["thingGroupMetadata"]["rootToParentThingGroups"]
    assert len(desc2b_groups) == 1
    assert desc2b_groups[0]["groupName"] == group_name_1a
    assert desc2b_groups[0]["groupArn"] == group_catalog[group_name_1a]["thingGroupArn"]
    assert "version" in desc2b
    # groups level 3
    # 3a
    desc3a = client.describe_thing_group(thingGroupName=group_name_3a)
    assert desc3a["thingGroupName"] == group_name_3a
    assert "thingGroupProperties" in desc3a
    assert len(desc3a["thingGroupMetadata"]) == 3
    assert desc3a["thingGroupMetadata"]["parentGroupName"] == group_name_2a
    desc3a_groups = desc3a["thingGroupMetadata"]["rootToParentThingGroups"]
    assert len(desc3a_groups) == 2
    assert desc3a_groups[0]["groupName"] == group_name_1a
    assert desc3a_groups[0]["groupArn"] == group_catalog[group_name_1a]["thingGroupArn"]
    assert desc3a_groups[1]["groupName"] == group_name_2a
    assert desc3a_groups[1]["groupArn"] == group_catalog[group_name_2a]["thingGroupArn"]
    assert "version" in desc3a
    # 3b
    desc3b = client.describe_thing_group(thingGroupName=group_name_3b)
    assert desc3b["thingGroupName"] == group_name_3b
    assert "thingGroupProperties" in desc3b
    assert len(desc3b["thingGroupMetadata"]) == 3
    assert desc3b["thingGroupMetadata"]["parentGroupName"] == group_name_2a
    desc3b_groups = desc3b["thingGroupMetadata"]["rootToParentThingGroups"]
    assert len(desc3b_groups) == 2
    assert desc3b_groups[0]["groupName"] == group_name_1a
    assert desc3b_groups[0]["groupArn"] == group_catalog[group_name_1a]["thingGroupArn"]
    assert desc3b_groups[1]["groupName"] == group_name_2a
    assert desc3b_groups[1]["groupArn"] == group_catalog[group_name_2a]["thingGroupArn"]
    assert "version" in desc3b
    # 3c
    desc3c = client.describe_thing_group(thingGroupName=group_name_3c)
    assert desc3c["thingGroupName"] == group_name_3c
    assert "thingGroupProperties" in desc3c
    assert len(desc3c["thingGroupMetadata"]) == 3
    assert desc3c["thingGroupMetadata"]["parentGroupName"] == group_name_2b
    desc3c_groups = desc3c["thingGroupMetadata"]["rootToParentThingGroups"]
    assert len(desc3c_groups) == 2
    assert desc3c_groups[0]["groupName"] == group_name_1a
    assert desc3c_groups[0]["groupArn"] == group_catalog[group_name_1a]["thingGroupArn"]
    assert desc3c_groups[1]["groupName"] == group_name_2b
    assert desc3c_groups[1]["groupArn"] == group_catalog[group_name_2b]["thingGroupArn"]
    assert "version" in desc3c
    # 3d
    desc3d = client.describe_thing_group(thingGroupName=group_name_3d)
    assert desc3d["thingGroupName"] == group_name_3d
    assert "thingGroupProperties" in desc3d
    assert len(desc3d["thingGroupMetadata"]) == 3
    assert desc3d["thingGroupMetadata"]["parentGroupName"] == group_name_2b
    desc3d_groups = desc3d["thingGroupMetadata"]["rootToParentThingGroups"]
    assert len(desc3d_groups) == 2
    assert desc3d_groups[0]["groupName"] == group_name_1a
    assert desc3d_groups[0]["groupArn"] == group_catalog[group_name_1a]["thingGroupArn"]
    assert desc3d_groups[1]["groupName"] == group_name_2b
    assert desc3d_groups[1]["groupArn"] == group_catalog[group_name_2b]["thingGroupArn"]
    assert "version" in desc3d


@mock_aws
def test_thing_groups():
    client = boto3.client("iot", region_name="ap-northeast-1")
    group_name = "my-group:name"

    # thing group
    thing_group = client.create_thing_group(thingGroupName=group_name)
    assert thing_group["thingGroupName"] == group_name
    assert "thingGroupArn" in thing_group
    assert group_name in thing_group["thingGroupArn"]

    res = client.list_thing_groups()
    assert len(res["thingGroups"]) == 1
    for thing_group in res["thingGroups"]:
        assert thing_group["groupName"] is not None
        assert thing_group["groupArn"] is not None

    thing_group = client.describe_thing_group(thingGroupName=group_name)
    assert thing_group["thingGroupName"] == group_name
    assert "thingGroupProperties" in thing_group
    assert "thingGroupMetadata" in thing_group
    assert "version" in thing_group
    assert "thingGroupArn" in thing_group
    assert group_name in thing_group["thingGroupArn"]

    # delete thing group
    client.delete_thing_group(thingGroupName=group_name)
    res = client.list_thing_groups()
    assert len(res["thingGroups"]) == 0

    # props create test
    props = {
        "thingGroupDescription": "my first thing group",
        "attributePayload": {"attributes": {"key1": "val01", "Key02": "VAL2"}},
    }
    thing_group = client.create_thing_group(
        thingGroupName=group_name, thingGroupProperties=props
    )
    assert thing_group["thingGroupName"] == group_name
    assert "thingGroupArn" in thing_group

    thing_group = client.describe_thing_group(thingGroupName=group_name)
    assert "attributes" in thing_group["thingGroupProperties"]["attributePayload"]
    res_props = thing_group["thingGroupProperties"]["attributePayload"]["attributes"]
    assert res_props["key1"] == "val01"
    assert res_props["Key02"] == "VAL2"

    # props update test with merge
    new_props = {"attributePayload": {"attributes": {"k3": "v3"}, "merge": True}}
    client.update_thing_group(thingGroupName=group_name, thingGroupProperties=new_props)
    thing_group = client.describe_thing_group(thingGroupName=group_name)
    assert "attributes" in thing_group["thingGroupProperties"]["attributePayload"]
    res_props = thing_group["thingGroupProperties"]["attributePayload"]["attributes"]
    assert res_props["key1"] == "val01"
    assert res_props["Key02"] == "VAL2"

    assert res_props["k3"] == "v3"

    # props update test
    new_props = {"attributePayload": {"attributes": {"k4": "v4"}}}
    client.update_thing_group(thingGroupName=group_name, thingGroupProperties=new_props)
    thing_group = client.describe_thing_group(thingGroupName=group_name)
    assert "attributes" in thing_group["thingGroupProperties"]["attributePayload"]
    res_props = thing_group["thingGroupProperties"]["attributePayload"]["attributes"]
    assert res_props["k4"] == "v4"
    assert "key1" not in res_props


@mock_aws
def test_thing_group_relations():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"
    group_name = "my-group-name"

    # thing group
    thing_group = client.create_thing_group(thingGroupName=group_name)
    assert thing_group["thingGroupName"] == group_name
    assert "thingGroupArn" in thing_group

    # thing
    thing = client.create_thing(thingName=name)
    assert thing["thingName"] == name
    assert "thingArn" in thing

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
    assert "things" in things
    assert len(things["things"]) == 1

    thing_groups = client.list_thing_groups_for_thing(thingName=name)
    assert "thingGroups" in thing_groups
    assert len(thing_groups["thingGroups"]) == 1

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
    assert "things" in things
    assert len(things["things"]) == 0

    # update thing group for thing
    client.update_thing_groups_for_thing(thingName=name, thingGroupsToAdd=[group_name])
    things = client.list_things_in_thing_group(thingGroupName=group_name)
    assert "things" in things
    assert len(things["things"]) == 1

    client.update_thing_groups_for_thing(
        thingName=name, thingGroupsToRemove=[group_name]
    )
    things = client.list_things_in_thing_group(thingGroupName=group_name)
    assert "things" in things
    assert len(things["things"]) == 0


@mock_aws
def test_thing_group_already_exists_with_different_properties_raises():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_group_name = "my-group-name"
    client.create_thing_group(
        thingGroupName=thing_group_name,
        thingGroupProperties={"thingGroupDescription": "Current description"},
    )

    with pytest.raises(
        client.exceptions.ResourceAlreadyExistsException,
        match=f"Thing Group {thing_group_name} already exists in current account with different properties",
    ):
        client.create_thing_group(thingGroupName=thing_group_name)


@mock_aws
def test_thing_group_already_exists_with_same_properties_returned():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_group_name = "my-group-name"
    thing_group_properties = {"thingGroupDescription": "Current description"}
    current_thing_group = client.create_thing_group(
        thingGroupName=thing_group_name, thingGroupProperties=thing_group_properties
    )
    current_thing_group.pop("ResponseMetadata")

    thing_group = client.create_thing_group(
        thingGroupName=thing_group_name, thingGroupProperties=thing_group_properties
    )
    thing_group.pop("ResponseMetadata")
    assert thing_group == current_thing_group


@mock_aws
def test_thing_group_updates_description():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing-group"
    new_description = "new description"
    client.create_thing_group(
        thingGroupName=name,
        thingGroupProperties={"thingGroupDescription": "initial-description"},
    )

    client.update_thing_group(
        thingGroupName=name,
        thingGroupProperties={"thingGroupDescription": new_description},
    )

    thing_group = client.describe_thing_group(thingGroupName=name)
    assert (
        thing_group["thingGroupProperties"]["thingGroupDescription"] == new_description
    )


@mock_aws
def test_thing_group_update_with_no_previous_attributes_no_merge():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-group-name"
    client.create_thing_group(thingGroupName=name)

    client.update_thing_group(
        thingGroupName=name,
        thingGroupProperties={
            "attributePayload": {
                "attributes": {
                    "key1": "val01",
                },
                "merge": False,
            }
        },
    )

    updated_thing_group = client.describe_thing_group(thingGroupName=name)
    assert updated_thing_group["thingGroupProperties"]["attributePayload"][
        "attributes"
    ] == {"key1": "val01"}


@mock_aws
def test_thing_group_update_with_no_previous_attributes_with_merge():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-group-name"
    client.create_thing_group(thingGroupName=name)

    client.update_thing_group(
        thingGroupName=name,
        thingGroupProperties={
            "attributePayload": {
                "attributes": {
                    "key1": "val01",
                },
                "merge": True,
            }
        },
    )

    updated_thing_group = client.describe_thing_group(thingGroupName=name)
    assert updated_thing_group["thingGroupProperties"]["attributePayload"][
        "attributes"
    ] == {"key1": "val01"}


@mock_aws
def test_thing_group_updated_with_empty_attributes_no_merge_no_attributes_added():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-group-name"
    client.create_thing_group(thingGroupName=name)

    client.update_thing_group(
        thingGroupName=name,
        thingGroupProperties={
            "attributePayload": {
                "attributes": {},
                "merge": False,
            }
        },
    )

    updated_thing_group = client.describe_thing_group(thingGroupName=name)
    assert "attributePayload" not in updated_thing_group["thingGroupProperties"]
