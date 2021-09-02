import boto3
import sure  # noqa

from moto import mock_ec2
from moto.core import ACCOUNT_ID


@mock_ec2
def test_create():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    prefix_list = ec2.create_managed_prefix_list(
        PrefixListName="examplelist", MaxEntries=2, AddressFamily="?"
    )["PrefixList"]
    prefix_list.should.have.key("PrefixListId").match("pl-[a-z0-9]+")
    prefix_list.should.have.key("AddressFamily").equals("?")
    prefix_list.should.have.key("State").equals("create-complete")
    prefix_list.should.have.key("PrefixListArn").equals(
        "arn:aws:ec2:us-west-1:{}:prefix-list/{}".format(
            ACCOUNT_ID, prefix_list["PrefixListId"]
        )
    )
    prefix_list.should.have.key("PrefixListName").equals("examplelist")
    prefix_list.should.have.key("MaxEntries").equals(2)
    prefix_list.should.have.key("Version").equals(1)
    prefix_list.should.have.key("Tags").equals([])
    prefix_list.should.have.key("OwnerId").equals(ACCOUNT_ID)


@mock_ec2
def test_create_with_tags():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    prefix_list = ec2.create_managed_prefix_list(
        PrefixListName="examplelist",
        MaxEntries=2,
        AddressFamily="?",
        TagSpecifications=[
            {"ResourceType": "", "Tags": [{"Key": "key1", "Value": "val1"}]}
        ],
    )["PrefixList"]
    prefix_list.should.have.key("PrefixListId").match("pl-[a-z0-9]+")
    prefix_list.should.have.key("State").equals("create-complete")
    prefix_list.should.have.key("Version").equals(1)
    prefix_list.should.have.key("Tags").equals([{"Key": "key1", "Value": "val1"}])


@mock_ec2
def test_describe_managed_prefix_lists():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    default_lists = ec2.describe_managed_prefix_lists()["PrefixLists"]
    set([l["OwnerId"] for l in default_lists]).should.equal({"aws"})

    ec2.create_managed_prefix_list(
        PrefixListName="examplelist", MaxEntries=2, AddressFamily="?"
    )

    all_lists = ec2.describe_managed_prefix_lists()["PrefixLists"]
    all_lists.should.have.length_of(len(default_lists) + 1)
    set([l["OwnerId"] for l in all_lists]).should.equal({"aws", ACCOUNT_ID})


@mock_ec2
def test_describe_managed_prefix_lists_with_prefix():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    default_lists = ec2.describe_managed_prefix_lists()["PrefixLists"]
    set([l["OwnerId"] for l in default_lists]).should.equal({"aws"})

    random_list_id = default_lists[0]["PrefixListId"]

    lists_by_id = ec2.describe_managed_prefix_lists(PrefixListIds=[random_list_id])[
        "PrefixLists"
    ]
    lists_by_id.should.have.length_of(1)
    lists_by_id[0]["OwnerId"].should.equal("aws")


@mock_ec2
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
    entries.should.have.length_of(2)
    entries.should.contain({"Cidr": "10.0.0.1", "Description": "entry1"})
    entries.should.contain({"Cidr": "10.0.0.2", "Description": "entry2"})


@mock_ec2
def test_get_managed_prefix_list_entries_0_entries():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    resp = ec2.create_managed_prefix_list(
        PrefixListName="examplelist", MaxEntries=2, AddressFamily="?"
    )
    prefix_list_id = resp["PrefixList"]["PrefixListId"]

    entries = ec2.get_managed_prefix_list_entries(PrefixListId=prefix_list_id)[
        "Entries"
    ]
    entries.should.equal([])


@mock_ec2
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
    lists_by_id.should.have.length_of(2)

    ec2.delete_managed_prefix_list(PrefixListId=id1)

    lists_by_id = ec2.describe_managed_prefix_lists(PrefixListIds=[id1, id2])[
        "PrefixLists"
    ]
    lists_by_id.should.have.length_of(2)

    set([l["State"] for l in lists_by_id]).should.equal(
        {"create-complete", "delete-complete"}
    )


@mock_ec2
def test_describe_prefix_lists():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    default_lists = ec2.describe_prefix_lists()["PrefixLists"]
    default_lists.should.have.length_of(2)

    ec2.create_managed_prefix_list(
        PrefixListName="examplelist", MaxEntries=2, AddressFamily="?"
    )

    all_lists = ec2.describe_prefix_lists()["PrefixLists"]
    all_lists.should.have.length_of(2)
    for l in all_lists:
        l["PrefixListName"].should.contain("com.amazonaws")


@mock_ec2
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
    prefix_list["PrefixListId"].should.equal(prefix_list_id)
    prefix_list["State"].should.equal("modify-complete")
    prefix_list["Version"].should.equal(2)

    described = ec2.describe_managed_prefix_lists(PrefixListIds=[prefix_list_id])[
        "PrefixLists"
    ][0]
    described.should.equal(prefix_list)

    entries = ec2.get_managed_prefix_list_entries(PrefixListId=prefix_list_id)[
        "Entries"
    ]
    entries.should.have.length_of(2)
    entries.should.contain({"Cidr": "10.0.0.1", "Description": "entry1"})
    entries.should.contain({"Cidr": "10.0.0.3", "Description": "entry3"})

    entries.shouldnt.contain({"Cidr": "10.0.0.2", "Description": "entry2"})


@mock_ec2
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
    prefix_list["PrefixListId"].should.equal(prefix_list_id)
    prefix_list["State"].should.equal("modify-complete")
    prefix_list["Version"].should.equal(2)

    described = ec2.describe_managed_prefix_lists(PrefixListIds=[prefix_list_id])[
        "PrefixLists"
    ][0]
    described.should.equal(prefix_list)

    entries = ec2.get_managed_prefix_list_entries(PrefixListId=prefix_list_id)[
        "Entries"
    ]
    entries.should.have.length_of(1)
    entries.should.contain({"Cidr": "10.0.0.3", "Description": "entry3"})

    entries.shouldnt.contain({"Cidr": "10.0.0.2", "Description": "entry2"})


@mock_ec2
def test_modify_manage_prefix_list_name_only():
    ec2 = boto3.client("ec2", region_name="us-west-1")

    resp = ec2.create_managed_prefix_list(
        PrefixListName="examplelist", MaxEntries=2, AddressFamily="?"
    )
    prefix_list_id = resp["PrefixList"]["PrefixListId"]

    prefix_list = ec2.modify_managed_prefix_list(
        PrefixListId=prefix_list_id, PrefixListName="new name"
    )["PrefixList"]
    prefix_list["PrefixListId"].should.equal(prefix_list_id)
    prefix_list["PrefixListName"].should.equal("new name")
    prefix_list["State"].should.equal("modify-complete")
    prefix_list["Version"].should.equal(1)

    described = ec2.describe_managed_prefix_lists(PrefixListIds=[prefix_list_id])[
        "PrefixLists"
    ][0]
    described.should.equal(prefix_list)


@mock_ec2
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
    prefix_list["Version"].should.equal(2)

    prefix_list = ec2.modify_managed_prefix_list(
        PrefixListId=prefix_list_id,
        CurrentVersion=2,
        RemoveEntries=[{"Cidr": "10.0.0.1"}],
    )["PrefixList"]
    prefix_list["Version"].should.equal(3)

    described = ec2.describe_managed_prefix_lists(PrefixListIds=[prefix_list_id])[
        "PrefixLists"
    ][0]
    described.should.equal(prefix_list)

    entries = ec2.get_managed_prefix_list_entries(PrefixListId=prefix_list_id)[
        "Entries"
    ]
    entries.should.have.length_of(1)
    entries.should.contain({"Cidr": "10.0.0.3", "Description": "entry3"})
