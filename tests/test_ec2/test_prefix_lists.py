import boto3

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_create():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    prefix_list = ec2.create_managed_prefix_list(
        PrefixListName="examplelist", MaxEntries=2, AddressFamily="?"
    )["PrefixList"]
    assert prefix_list["PrefixListId"].startswith("pl-")
    assert prefix_list["AddressFamily"] == "?"
    assert prefix_list["State"] == "create-complete"
    assert (
        prefix_list["PrefixListArn"]
        == f"arn:aws:ec2:us-west-1:{ACCOUNT_ID}:prefix-list/{prefix_list['PrefixListId']}"
    )
    assert prefix_list["PrefixListName"] == "examplelist"
    assert prefix_list["MaxEntries"] == 2
    assert prefix_list["Version"] == 1
    assert prefix_list["Tags"] == []
    assert prefix_list["OwnerId"] == ACCOUNT_ID


@mock_aws
def test_create_with_tags():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    prefix_list = ec2.create_managed_prefix_list(
        PrefixListName="examplelist",
        MaxEntries=2,
        AddressFamily="?",
        TagSpecifications=[
            {"ResourceType": "prefix-list", "Tags": [{"Key": "key1", "Value": "val1"}]}
        ],
    )["PrefixList"]
    assert prefix_list["PrefixListId"].startswith("pl-")
    assert prefix_list["State"] == "create-complete"
    assert prefix_list["Version"] == 1
    assert prefix_list["Tags"] == [{"Key": "key1", "Value": "val1"}]


@mock_aws
def test_describe_managed_prefix_lists():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    prefix_list = ec2.create_managed_prefix_list(
        PrefixListName="examplelist", MaxEntries=2, AddressFamily="?"
    )
    pl_id = prefix_list["PrefixList"]["PrefixListId"]

    all_lists = ec2.describe_managed_prefix_lists()["PrefixLists"]
    assert pl_id in [pl["PrefixListId"] for pl in all_lists]
    assert set([pl["OwnerId"] for pl in all_lists]) == {"aws", ACCOUNT_ID}


@mock_aws
def test_describe_managed_prefix_lists_with_prefix():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    default_lists = ec2.describe_managed_prefix_lists()["PrefixLists"]
    if not settings.TEST_SERVER_MODE:
        # ServerMode is not guaranteed to only have AWS prefix lists
        assert set([pl["OwnerId"] for pl in default_lists]) == {"aws"}

    random_list_id = default_lists[0]["PrefixListId"]

    lists_by_id = ec2.describe_managed_prefix_lists(PrefixListIds=[random_list_id])[
        "PrefixLists"
    ]
    assert len(lists_by_id) == 1
    if not settings.TEST_SERVER_MODE:
        assert lists_by_id[0]["OwnerId"] == "aws"


@mock_aws
def test_describe_managed_prefix_lists_with_tags():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    untagged_prefix_list = ec2.create_managed_prefix_list(
        PrefixListName="examplelist", MaxEntries=2, AddressFamily="?"
    )
    untagged_pl_id = untagged_prefix_list["PrefixList"]["PrefixListId"]
    tagged_prefix_list = ec2.create_managed_prefix_list(
        PrefixListName="examplelist",
        MaxEntries=2,
        AddressFamily="?",
        TagSpecifications=[
            {"ResourceType": "prefix-list", "Tags": [{"Key": "key", "Value": "value"}]}
        ],
    )
    tagged_pl_id = tagged_prefix_list["PrefixList"]["PrefixListId"]

    tagged_lists = ec2.describe_managed_prefix_lists(
        Filters=[{"Name": "tag:key", "Values": ["value"]}]
    )["PrefixLists"]
    assert tagged_pl_id in [pl["PrefixListId"] for pl in tagged_lists]
    assert untagged_pl_id not in [pl["PrefixListId"] for pl in tagged_lists]


@mock_aws
def test_get_managed_prefix_list_entries():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    resp = ec2.create_managed_prefix_list(
        PrefixListName="examplelist",
        MaxEntries=2,
        AddressFamily="?",
        Entries=[
            {"Cidr": "10.0.0.1", "Description": "entry1"},
            {"Cidr": "10.0.0.2", "Description": "entry2"},
        ],
    )
    ec2.create_managed_prefix_list(
        PrefixListName="examplelist2",
        MaxEntries=2,
        AddressFamily="?",
        Entries=[
            {"Cidr": "10.0.0.3", "Description": "entry3"},
            {"Cidr": "10.0.0.4", "Description": "entry4"},
        ],
    )
    prefix_list_id = resp["PrefixList"]["PrefixListId"]

    entries = ec2.get_managed_prefix_list_entries(PrefixListId=prefix_list_id)[
        "Entries"
    ]
    assert len(entries) == 2
    assert {"Cidr": "10.0.0.1", "Description": "entry1"} in entries
    assert {"Cidr": "10.0.0.2", "Description": "entry2"} in entries


@mock_aws
def test_get_managed_prefix_list_entries_0_entries():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    resp = ec2.create_managed_prefix_list(
        PrefixListName="examplelist", MaxEntries=2, AddressFamily="?"
    )
    prefix_list_id = resp["PrefixList"]["PrefixListId"]

    entries = ec2.get_managed_prefix_list_entries(PrefixListId=prefix_list_id)[
        "Entries"
    ]
    assert entries == []


@mock_aws
def test_delete_managed_prefix_list():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    id1 = ec2.create_managed_prefix_list(
        PrefixListName="examplelist1", MaxEntries=2, AddressFamily="?"
    )["PrefixList"]["PrefixListId"]
    id2 = ec2.create_managed_prefix_list(
        PrefixListName="examplelist2", MaxEntries=2, AddressFamily="?"
    )["PrefixList"]["PrefixListId"]

    lists_by_id = ec2.describe_managed_prefix_lists(PrefixListIds=[id1, id2])[
        "PrefixLists"
    ]
    assert len(lists_by_id) == 2

    ec2.delete_managed_prefix_list(PrefixListId=id1)

    lists_by_id = ec2.describe_managed_prefix_lists(PrefixListIds=[id1, id2])[
        "PrefixLists"
    ]
    assert len(lists_by_id) == 2

    assert set([pl["State"] for pl in lists_by_id]) == {
        "create-complete",
        "delete-complete",
    }


@mock_aws
def test_describe_prefix_lists():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    default_lists = ec2.describe_prefix_lists()["PrefixLists"]
    assert len(default_lists) == 6

    ec2.create_managed_prefix_list(
        PrefixListName="examplelist", MaxEntries=2, AddressFamily="?"
    )

    all_lists = ec2.describe_prefix_lists()["PrefixLists"]
    assert len(all_lists) == 6
    for pl in all_lists:
        assert "com.amazonaws" in pl["PrefixListName"]


@mock_aws
def test_modify_manage_prefix_list():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    resp = ec2.create_managed_prefix_list(
        PrefixListName="examplelist",
        MaxEntries=2,
        AddressFamily="?",
        Entries=[
            {"Cidr": "10.0.0.1", "Description": "entry1"},
            {"Cidr": "10.0.0.2", "Description": "entry2"},
        ],
    )
    prefix_list_id = resp["PrefixList"]["PrefixListId"]

    prefix_list = ec2.modify_managed_prefix_list(
        PrefixListId=prefix_list_id,
        AddEntries=[{"Cidr": "10.0.0.3", "Description": "entry3"}],
        RemoveEntries=[{"Cidr": "10.0.0.2"}],
    )["PrefixList"]
    assert prefix_list["PrefixListId"] == prefix_list_id
    assert prefix_list["State"] == "modify-complete"
    assert prefix_list["Version"] == 2

    described = ec2.describe_managed_prefix_lists(PrefixListIds=[prefix_list_id])[
        "PrefixLists"
    ][0]
    assert described == prefix_list

    entries = ec2.get_managed_prefix_list_entries(PrefixListId=prefix_list_id)[
        "Entries"
    ]
    assert len(entries) == 2
    assert {"Cidr": "10.0.0.1", "Description": "entry1"} in entries
    assert {"Cidr": "10.0.0.3", "Description": "entry3"} in entries

    assert {"Cidr": "10.0.0.2", "Description": "entry2"} not in entries


@mock_aws
def test_modify_manage_prefix_list_add_to_empty_list():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    resp = ec2.create_managed_prefix_list(
        PrefixListName="examplelist", MaxEntries=2, AddressFamily="?"
    )
    prefix_list_id = resp["PrefixList"]["PrefixListId"]

    prefix_list = ec2.modify_managed_prefix_list(
        PrefixListId=prefix_list_id,
        AddEntries=[{"Cidr": "10.0.0.3", "Description": "entry3"}],
        RemoveEntries=[{"Cidr": "10.0.0.2"}],
    )["PrefixList"]
    assert prefix_list["PrefixListId"] == prefix_list_id
    assert prefix_list["State"] == "modify-complete"
    assert prefix_list["Version"] == 2

    described = ec2.describe_managed_prefix_lists(PrefixListIds=[prefix_list_id])[
        "PrefixLists"
    ][0]
    assert described == prefix_list

    entries = ec2.get_managed_prefix_list_entries(PrefixListId=prefix_list_id)[
        "Entries"
    ]
    assert len(entries) == 1
    assert {"Cidr": "10.0.0.3", "Description": "entry3"} in entries

    assert {"Cidr": "10.0.0.2", "Description": "entry2"} not in entries


@mock_aws
def test_modify_manage_prefix_list_name_only():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    resp = ec2.create_managed_prefix_list(
        PrefixListName="examplelist", MaxEntries=2, AddressFamily="?"
    )
    prefix_list_id = resp["PrefixList"]["PrefixListId"]

    prefix_list = ec2.modify_managed_prefix_list(
        PrefixListId=prefix_list_id, PrefixListName="new name"
    )["PrefixList"]
    assert prefix_list["PrefixListId"] == prefix_list_id
    assert prefix_list["PrefixListName"] == "new name"
    assert prefix_list["State"] == "modify-complete"
    assert prefix_list["Version"] == 1

    described = ec2.describe_managed_prefix_lists(PrefixListIds=[prefix_list_id])[
        "PrefixLists"
    ][0]
    assert described == prefix_list


@mock_aws
def test_modify_manage_prefix_list_specifying_version():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    resp = ec2.create_managed_prefix_list(
        PrefixListName="examplelist",
        MaxEntries=2,
        AddressFamily="?",
        Entries=[
            {"Cidr": "10.0.0.1", "Description": "entry1"},
            {"Cidr": "10.0.0.2", "Description": "entry2"},
        ],
    )
    prefix_list_id = resp["PrefixList"]["PrefixListId"]

    prefix_list = ec2.modify_managed_prefix_list(
        PrefixListId=prefix_list_id,
        AddEntries=[{"Cidr": "10.0.0.3", "Description": "entry3"}],
        RemoveEntries=[{"Cidr": "10.0.0.2"}],
    )["PrefixList"]
    assert prefix_list["Version"] == 2

    prefix_list = ec2.modify_managed_prefix_list(
        PrefixListId=prefix_list_id,
        CurrentVersion=2,
        RemoveEntries=[{"Cidr": "10.0.0.1"}],
    )["PrefixList"]
    assert prefix_list["Version"] == 3

    described = ec2.describe_managed_prefix_lists(PrefixListIds=[prefix_list_id])[
        "PrefixLists"
    ][0]
    assert described == prefix_list

    entries = ec2.get_managed_prefix_list_entries(PrefixListId=prefix_list_id)[
        "Entries"
    ]
    assert len(entries) == 1
    assert {"Cidr": "10.0.0.3", "Description": "entry3"} in entries
