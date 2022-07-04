import json
import random
import re
import string

from urllib.parse import parse_qs, urlparse


def networkid_from_managedblockchain_url(full_url):
    id_search = re.search(r"\/n-[A-Z0-9]{26}", full_url, re.IGNORECASE)
    return_id = None
    if id_search:
        return_id = id_search.group(0).replace("/", "")
    return return_id


def get_network_id():
    return "n-" + "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(26)
    )


def memberid_from_managedblockchain_request(full_url, body):
    id_search = re.search(r"\/m-[A-Z0-9]{26}", full_url, re.IGNORECASE)
    return_id = None
    if id_search:
        return_id = id_search.group(0).replace("/", "")
    else:
        # >= botocore 1.19.41 can add the memberId as a query parameter, or in the body
        parsed_url = urlparse(full_url)
        qs = parse_qs(parsed_url.query)
        if "memberId" in qs:
            return_id = qs.get("memberId")[0]
        elif body:
            body = json.loads(body)
            return_id = body["MemberId"]
    return return_id


def get_member_id():
    return "m-" + "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(26)
    )


def proposalid_from_managedblockchain_url(full_url):
    id_search = re.search(r"\/p-[A-Z0-9]{26}", full_url, re.IGNORECASE)
    return_id = None
    if id_search:
        return_id = id_search.group(0).replace("/", "")
    return return_id


def get_proposal_id():
    return "p-" + "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(26)
    )


def invitationid_from_managedblockchain_url(full_url):
    id_search = re.search(r"\/in-[A-Z0-9]{26}", full_url, re.IGNORECASE)
    return_id = None
    if id_search:
        return_id = id_search.group(0).replace("/", "")
    return return_id


def get_invitation_id():
    return "in-" + "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(26)
    )


def member_name_exist_in_network(members, networkid, membername):
    membernamexists = False
    for member_id in members:
        if members.get(member_id).network_id == networkid:
            if members.get(member_id).name == membername:
                membernamexists = True
                break
    return membernamexists


def number_of_members_in_network(members, networkid, member_status=None):
    return len(
        [
            membid
            for membid in members
            if members.get(membid).network_id == networkid
            and (
                member_status is None
                or members.get(membid).member_status == member_status
            )
        ]
    )


def admin_password_ok(password):
    if not re.search("[a-z]", password):
        return False
    elif not re.search("[A-Z]", password):
        return False
    elif not re.search("[0-9]", password):
        return False
    elif re.search("['\"@\\/]", password):
        return False
    else:
        return True


def nodeid_from_managedblockchain_url(full_url):
    id_search = re.search(r"\/nd-[A-Z0-9]{26}", full_url, re.IGNORECASE)
    return_id = None
    if id_search:
        return_id = id_search.group(0).replace("/", "")
    return return_id


def get_node_id():
    return "nd-" + "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(26)
    )


def number_of_nodes_in_member(nodes, memberid, node_status=None):
    return len(
        [
            nodid
            for nodid in nodes
            if nodes.get(nodid).member_id == memberid
            and (node_status is None or nodes.get(nodid).node_status == node_status)
        ]
    )


def nodes_in_member(nodes, memberid):
    return [nodid for nodid in nodes if nodes.get(nodid).member_id == memberid]
