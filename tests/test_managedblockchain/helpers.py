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

default_nodeconfiguration = {
    "InstanceType": "bc.t3.small",
    "AvailabilityZone": "us-east-1a",
    "LogPublishingConfiguration": {
        "Fabric": {
            "ChaincodeLogs": {"Cloudwatch": {"Enabled": False}},
            "PeerLogs": {"Cloudwatch": {"Enabled": False}},
        }
    },
}


def member_id_exist_in_list(members, memberid):
    return any([member["Id"] == memberid for member in members])


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


def node_id_exist_in_list(nodes, nodeid):
    return any([node["Id"] == nodeid for node in nodes])
