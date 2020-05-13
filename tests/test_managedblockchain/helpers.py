from __future__ import unicode_literals


default_frameworkconfiguration = {"Fabric": {"Edition": "STARTER"}}

default_votingpolicy = {
    "ApprovalThresholdPolicy": {
        "ThresholdPercentage": 50,
        "ProposalDurationInHours": 24,
        "ThresholdComparator": "GREATER_THAN_OR_EQUAL_TO",
    }
}

default_memberconfiguration = {
    "Name": "testmember1",
    "Description": "Test Member 1",
    "FrameworkConfiguration": {
        "Fabric": {"AdminUsername": "admin", "AdminPassword": "Admin12345"}
    },
    "LogPublishingConfiguration": {
        "Fabric": {"CaLogs": {"Cloudwatch": {"Enabled": False}}}
    },
}

default_policy_actions = {"Invitations": [{"Principal": "123456789012"}]}

multiple_policy_actions = {
    "Invitations": [{"Principal": "123456789012"}, {"Principal": "123456789013"}]
}


def member_id_exist_in_list(members, memberid):
    memberidxists = False
    for member in members:
        if member["Id"] == memberid:
            memberidxists = True
            break
    return memberidxists


def create_member_configuration(
    name, adminuser, adminpass, cloudwatchenabled, description=None
):
    d = {
        "Name": name,
        "FrameworkConfiguration": {
            "Fabric": {"AdminUsername": adminuser, "AdminPassword": adminpass}
        },
        "LogPublishingConfiguration": {
            "Fabric": {"CaLogs": {"Cloudwatch": {"Enabled": cloudwatchenabled}}}
        },
    }

    if description is not None:
        d["Description"] = description

    return d


def select_invitation_id_for_network(invitations, networkid, status=None):
    # Get invitations based on network and maybe status
    invitationsfornetwork = []
    for invitation in invitations:
        if invitation["NetworkSummary"]["Id"] == networkid:
            if status is None or invitation["Status"] == status:
                invitationsfornetwork.append(invitation["InvitationId"])
    return invitationsfornetwork
