import copy

from moto.route53.models import ChangeList


def test_last_dot_in_name_is_ignored():
    change1 = {
        "Action": "CREATE",
        "ResourceRecordSet": {
            "Name": "test.without.dot",
            "Type": "CNAME",
            "TTL": 600,
            "ResourceRecords": [{"Value": "0.0.0.0"}],
        },
    }
    change1_alt = copy.deepcopy(change1)
    change1_alt["ResourceRecordSet"]["Name"] = "test.without.dot."

    change2 = copy.deepcopy(change1)
    change2["ResourceRecordSet"]["Name"] = "test.with.dot."
    change2_alt = copy.deepcopy(change1)
    change2_alt["ResourceRecordSet"]["Name"] = "test.with.dot"

    change_list = ChangeList()
    change_list.append(change1)
    change_list.append(change2)

    assert change1 in change_list
    assert change1_alt in change_list
    assert change2 in change_list
    assert change2_alt in change_list


def test_last_dot_is_not_stored():
    change1 = {
        "Action": "CREATE",
        "ResourceRecordSet": {
            "Name": "test.google.com.",
            "Type": "CNAME",
            "TTL": 600,
            "ResourceRecords": [{"Value": "0.0.0.0"}],
        },
    }
    change_list = ChangeList()
    change_list.append(change1)

    assert change_list[0]["ResourceRecordSet"]["Name"] == "test.google.com"


def test_optional_fields():
    change = {
        "Action": "UPSERT",
        "ResourceRecordSet": {"Name": "test.google.com.", "Type": "CNAME"},
    }
    change_list = ChangeList()
    change_list.append(change)

    assert change_list == [change]
