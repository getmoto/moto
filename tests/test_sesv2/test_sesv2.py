import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.ses.models import Message, RawMessage, ses_backends
from tests import DEFAULT_ACCOUNT_ID

from ..test_ses.test_ses_boto3 import get_raw_email


@pytest.fixture(scope="function")
def ses_v1():
    """Use this for API calls which exist in v1 but not in v2"""
    with mock_aws():
        yield boto3.client("ses", region_name="us-east-1")


@mock_aws
def test_send_email(ses_v1):
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    kwargs = dict(
        FromEmailAddress="test@example.com",
        Destination={
            "ToAddresses": ["test_to@example.com"],
            "CcAddresses": ["test_cc@example.com"],
            "BccAddresses": ["test_bcc@example.com"],
        },
        Content={
            "Simple": {
                "Subject": {"Data": "test subject"},
                "Body": {"Text": {"Data": "test body"}},
            },
        },
    )

    # Execute
    with pytest.raises(ClientError) as e:
        conn.send_email(**kwargs)
    assert e.value.response["Error"]["Code"] == "MessageRejected"

    ses_v1.verify_domain_identity(Domain="example.com")
    resp = conn.send_email(**kwargs)
    assert resp["MessageId"] is not None

    send_quota = ses_v1.get_send_quota()

    # Verify
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 3

    if not settings.TEST_SERVER_MODE:
        backend = ses_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
        msg: Message = backend.sent_messages[0]
        assert msg.subject == "test subject"
        assert msg.body == "test body"


@mock_aws
def test_send_html_email(ses_v1):
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    ses_v1.verify_domain_identity(Domain="example.com")
    kwargs = dict(
        FromEmailAddress="test@example.com",
        Destination={
            "ToAddresses": ["test_to@example.com"],
        },
        Content={
            "Simple": {
                "Subject": {"Data": "test subject"},
                "Body": {"Html": {"Data": "<h1>Test HTML</h1>"}},
            },
        },
    )

    # Execute
    conn.send_email(**kwargs)

    # Verify
    send_quota = ses_v1.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 1

    if not settings.TEST_SERVER_MODE:
        backend = ses_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
        msg: Message = backend.sent_messages[0]
        assert msg.subject == "test subject"
        assert msg.body == "<h1>Test HTML</h1>"


@mock_aws
def test_send_raw_email(ses_v1):
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    message = get_raw_email()
    destination = {
        "ToAddresses": [x.strip() for x in message["To"].split(",")],
    }
    kwargs = dict(
        FromEmailAddress=message["From"],
        Destination=destination,
        Content={"Raw": {"Data": message.as_bytes()}},
    )

    # Execute
    ses_v1.verify_email_identity(EmailAddress="test@example.com")
    conn.send_email(**kwargs)

    # Verify
    send_quota = ses_v1.get_send_quota()
    # 2 destinations in the message, two in the 'Destination'-argument
    assert int(send_quota["SentLast24Hours"]) == 4


@mock_aws
def test_send_raw_email__with_specific_message(
    ses_v1,
):
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    message = get_raw_email()
    # This particular message means that our base64-encoded body contains a '='
    # Testing this to ensure that we parse the body as JSON, not as a query-dict
    message["Subject"] = "Test-2"
    kwargs = dict(
        Content={"Raw": {"Data": message.as_bytes()}},
    )

    # Execute
    ses_v1.verify_email_identity(EmailAddress="test@example.com")
    conn.send_email(**kwargs)

    # Verify
    send_quota = ses_v1.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 2

    if not settings.TEST_SERVER_MODE:
        backend = ses_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
        msg: RawMessage = backend.sent_messages[0]
        assert message.as_bytes() == msg.raw_data.encode("utf-8")
        assert msg.source == "test@example.com"
        assert msg.destinations == ["to@example.com", "foo@example.com"]


@mock_aws
def test_send_raw_email__with_to_address_display_name(
    ses_v1,
):
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    message = get_raw_email()
    # This particular message means that to-address with display-name which contains many ','
    del message["To"]
    display_name = ",".join(["c" for _ in range(50)])
    message["To"] = f""""{display_name}" <to@example.com>, foo@example.com"""
    kwargs = dict(
        Content={"Raw": {"Data": message.as_bytes()}},
    )

    # Execute
    ses_v1.verify_email_identity(EmailAddress="test@example.com")
    conn.send_email(**kwargs)

    # Verify
    send_quota = ses_v1.get_send_quota()
    sent_count = int(send_quota["SentLast24Hours"])
    assert sent_count == 2

    if not settings.TEST_SERVER_MODE:
        backend = ses_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
        msg: RawMessage = backend.sent_messages[0]
        assert message.as_bytes() == msg.raw_data.encode("utf-8")
        assert msg.source == "test@example.com"
        assert msg.destinations == [
            """"c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c,c" <to@example.com>""",
            "foo@example.com",
        ]


@mock_aws
def test_create_contact_list():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"

    # Execute
    conn.create_contact_list(
        ContactListName=contact_list_name,
    )
    result = conn.list_contact_lists()

    # Verify
    assert len(result["ContactLists"]) == 1
    assert result["ContactLists"][0]["ContactListName"] == contact_list_name


@mock_aws
def test_create_contact_list__with_topics():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test3"

    # Execute
    conn.create_contact_list(
        ContactListName=contact_list_name,
        Topics=[
            {
                "TopicName": "test-topic",
                "DisplayName": "display=name",
                "DefaultSubscriptionStatus": "OPT_OUT",
            }
        ],
    )
    result = conn.list_contact_lists()

    # Verify
    assert len(result["ContactLists"]) == 1
    assert result["ContactLists"][0]["ContactListName"] == contact_list_name


@mock_aws
def test_list_contact_lists():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")

    # Execute
    result = conn.list_contact_lists()

    # Verify
    assert result["ContactLists"] == []


@mock_aws
def test_get_contact_list():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"

    # Execute
    with pytest.raises(ClientError) as e:
        conn.get_contact_list(ContactListName=contact_list_name)
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    assert (
        e.value.response["Error"]["Message"]
        == f"List with name: {contact_list_name} doesn't exist."
    )

    conn.create_contact_list(
        ContactListName=contact_list_name,
    )
    result = conn.get_contact_list(ContactListName=contact_list_name)

    # Verify
    assert result["ContactListName"] == contact_list_name


@mock_aws
def test_delete_contact_list():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"

    # Execute
    with pytest.raises(ClientError) as e:
        conn.delete_contact_list(ContactListName=contact_list_name)
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    conn.create_contact_list(
        ContactListName=contact_list_name,
    )
    result = conn.list_contact_lists()
    assert len(result["ContactLists"]) == 1
    conn.delete_contact_list(
        ContactListName=contact_list_name,
    )
    result = conn.list_contact_lists()

    # Verify
    assert len(result["ContactLists"]) == 0


@mock_aws
def test_list_contacts():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    conn.create_contact_list(
        ContactListName=contact_list_name,
    )

    # Execute
    result = conn.list_contacts(ContactListName=contact_list_name)

    # Verify
    assert result["Contacts"] == []


@mock_aws
def test_create_contact_no_contact_list():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"

    # Execute
    with pytest.raises(ClientError) as e:
        conn.create_contact(
            ContactListName=contact_list_name,
            EmailAddress=email,
        )

    # Verify
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    assert (
        e.value.response["Error"]["Message"]
        == f"List with name: {contact_list_name} doesn't exist."
    )


@mock_aws
def test_create_contact():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"
    conn.create_contact_list(
        ContactListName=contact_list_name,
    )

    # Execute
    conn.create_contact(
        ContactListName=contact_list_name,
        EmailAddress=email,
    )

    result = conn.list_contacts(ContactListName=contact_list_name)

    # Verify
    assert len(result["Contacts"]) == 1
    assert result["Contacts"][0]["EmailAddress"] == email


@mock_aws
def test_get_contact_no_contact_list():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"

    # Execute
    with pytest.raises(ClientError) as e:
        conn.get_contact(ContactListName=contact_list_name, EmailAddress=email)

    # Verify
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    assert (
        e.value.response["Error"]["Message"]
        == f"List with name: {contact_list_name} doesn't exist."
    )


@mock_aws
def test_get_contact():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"
    conn.create_contact_list(
        ContactListName=contact_list_name,
    )
    # Execute

    conn.create_contact(
        ContactListName=contact_list_name,
        EmailAddress=email,
    )
    result = conn.get_contact(ContactListName=contact_list_name, EmailAddress=email)

    # Verify
    assert result["ContactListName"] == contact_list_name
    assert result["EmailAddress"] == email


@mock_aws
def test_get_contact_no_contact():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"
    conn.create_contact_list(
        ContactListName=contact_list_name,
    )
    # Execute
    with pytest.raises(ClientError) as e:
        conn.get_contact(ContactListName=contact_list_name, EmailAddress=email)

    # Verify
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    assert e.value.response["Error"]["Message"] == f"{email} doesn't exist in List."


@mock_aws
def test_delete_contact_no_contact_list():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"

    # Execute
    with pytest.raises(ClientError) as e:
        conn.delete_contact(ContactListName=contact_list_name, EmailAddress=email)

    # Verify
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    assert (
        e.value.response["Error"]["Message"]
        == f"List with name: {contact_list_name} doesn't exist."
    )


@mock_aws
def test_delete_contact_no_contact():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"

    # Execute
    conn.create_contact_list(ContactListName=contact_list_name)

    with pytest.raises(ClientError) as e:
        conn.delete_contact(ContactListName=contact_list_name, EmailAddress=email)

    # Verify
    assert e.value.response["Error"]["Code"] == "NotFoundException"
    assert e.value.response["Error"]["Message"] == f"{email} doesn't exist in List."


@mock_aws
def test_delete_contact():
    # Setup
    conn = boto3.client("sesv2", region_name="us-east-1")
    contact_list_name = "test2"
    email = "test@example.com"

    # Execute
    conn.create_contact_list(ContactListName=contact_list_name)
    conn.create_contact(ContactListName=contact_list_name, EmailAddress=email)
    result = conn.list_contacts(ContactListName=contact_list_name)
    assert len(result["Contacts"]) == 1

    conn.delete_contact(ContactListName=contact_list_name, EmailAddress=email)
    result = conn.list_contacts(ContactListName=contact_list_name)

    # Verify
    assert len(result["Contacts"]) == 0


@mock_aws
def test_create_email_identity():
    # Setup
    client = boto3.client("sesv2", region_name="us-east-1")
    test_email_domain = "example.com"

    # Execute
    resp = client.create_email_identity(EmailIdentity=test_email_domain)

    # Verify
    assert resp["IdentityType"] == "DOMAIN"
    assert resp["VerifiedForSendingStatus"] is False


@mock_aws
def test_get_email_identity():
    # Setup
    client = boto3.client("sesv2", region_name="us-east-2")
    test_email_domain = "example.com"
    configuration_set_name = "test-config-set"
    tags = [{"Key": "Owner", "Value": "Zach"}]
    client.create_email_identity(
        EmailIdentity=test_email_domain,
        ConfigurationSetName=configuration_set_name,
        Tags=tags,
    )

    # Execute
    resp = client.get_email_identity(EmailIdentity=test_email_domain)

    # Verify
    assert resp["IdentityType"] == "DOMAIN"
    assert resp["ConfigurationSetName"] == configuration_set_name
    assert resp["Tags"] == tags
    assert "DkimAttributes" in resp
    assert resp["DkimAttributes"]["Status"] == "NOT_STARTED"
    assert not resp["DkimAttributes"]["SigningEnabled"]


@mock_aws
def test_get_email_identity_w_dkim():
    # Setup
    client = boto3.client("sesv2", region_name="us-east-2")
    test_email_domain = "example.com"
    configuration_set_name = "test-config-set"
    tags = [{"Key": "Owner", "Value": "Zach"}]
    dkim_signing_attributes = {
        "DomainSigningSelector": "test",
        "DomainSigningPrivateKey": "test",
        "NextSigningKeyLength": "2048",
        "DomainSigningAttributesOrigin": "AWS_SES",
    }
    client.create_email_identity(
        EmailIdentity=test_email_domain,
        ConfigurationSetName=configuration_set_name,
        Tags=tags,
        DkimSigningAttributes=dkim_signing_attributes,
    )

    # Execute
    resp = client.get_email_identity(EmailIdentity=test_email_domain)

    # Verify
    assert resp["IdentityType"] == "DOMAIN"
    assert resp["ConfigurationSetName"] == configuration_set_name
    assert resp["Tags"] == tags
    assert "DkimAttributes" in resp
    assert (
        resp["DkimAttributes"]["SigningAttributesOrigin"]
        == dkim_signing_attributes["DomainSigningAttributesOrigin"]
    )
    assert resp["DkimAttributes"]["Status"] == "SUCCESS"
    assert resp["DkimAttributes"]["SigningEnabled"]


@mock_aws
def test_list_email_identities():
    # Setup
    client = boto3.client("sesv2", region_name="ap-southeast-1")
    email_identities = ["example.com", "moto@example.com", "example2.com"]
    for e in email_identities:
        client.create_email_identity(EmailIdentity=e)

    # Execute
    resp = client.list_email_identities()

    # Verify
    assert len(resp["EmailIdentities"]) == 3
    for ei in resp["EmailIdentities"]:
        assert ei["IdentityName"] in email_identities
        if "@" in ei["IdentityName"]:
            assert ei["IdentityType"] == "EMAIL_ADDRESS"
        else:
            assert ei["IdentityType"] == "DOMAIN"


@mock_aws
def test_create_configuration_set():
    # Setup
    client = boto3.client("sesv2", region_name="eu-west-1")
    name = "my-sesv2-config-set"
    tracking_options = {
        "CustomRedirectDomain": "abc.com",
        "HttpsPolicy": "OPTIONAL",
    }
    delivery_options = {
        "TlsPolicy": "OPTIONAL",
        "SendingPoolName": "MySendingPool",
        "MaxDeliverySeconds": 301,
    }
    reputation_options = {
        "ReputationMetricsEnabled": False,
    }
    sending_options = {"SendingEnabled": True}
    tags = [
        {"Key": "Owner", "Value": "Zach"},
    ]
    suppression_options = {"SuppressedReasons": ["BOUNCE"]}
    vdm_options = {
        "DashboardOptions": {"EngagementMetrics": "DISABLED"},
        "GuardianOptions": {"OptimizedSharedDelivery": "DISABLED"},
    }

    # Execute
    client.create_configuration_set(
        ConfigurationSetName=name,
        TrackingOptions=tracking_options,
        DeliveryOptions=delivery_options,
        ReputationOptions=reputation_options,
        SendingOptions=sending_options,
        Tags=tags,
        SuppressionOptions=suppression_options,
        VdmOptions=vdm_options,
    )

    # Validate
    config_set = client.get_configuration_set(ConfigurationSetName=name)
    assert config_set["ConfigurationSetName"] == name


@mock_aws
def test_get_configuration_set():
    # Test GetConfigurationSet returns resources created in both ses and sesv2
    # Setup
    client_v1 = boto3.client("ses", region_name="eu-west-1")
    client_v2 = boto3.client("sesv2", region_name="eu-west-1")

    name_v1 = "my-sesv1"
    name_v2 = "my-sesv2-config-set"
    tracking_options = {
        "CustomRedirectDomain": "abc.com",
        "HttpsPolicy": "OPTIONAL",
    }
    delivery_options = {
        "TlsPolicy": "OPTIONAL",
        "SendingPoolName": "MySendingPool",
        "MaxDeliverySeconds": 301,
    }
    reputation_options = {
        "ReputationMetricsEnabled": False,
    }
    sending_options = {"SendingEnabled": True}
    tags = [
        {"Key": "Owner", "Value": "Zach"},
    ]
    suppression_options = {"SuppressedReasons": ["BOUNCE"]}
    vdm_options = {
        "DashboardOptions": {"EngagementMetrics": "DISABLED"},
        "GuardianOptions": {"OptimizedSharedDelivery": "DISABLED"},
    }

    client_v1.create_configuration_set(ConfigurationSet=dict({"Name": name_v1}))

    client_v2.create_configuration_set(
        ConfigurationSetName=name_v2,
        TrackingOptions=tracking_options,
        DeliveryOptions=delivery_options,
        ReputationOptions=reputation_options,
        SendingOptions=sending_options,
        Tags=tags,
        SuppressionOptions=suppression_options,
        VdmOptions=vdm_options,
    )

    # Execute
    config_setv1 = client_v2.get_configuration_set(ConfigurationSetName=name_v1)
    config_setv2 = client_v2.get_configuration_set(ConfigurationSetName=name_v2)

    # Validate
    assert config_setv1["ConfigurationSetName"] == name_v1
    assert config_setv1["Tags"] == []

    assert config_setv2["ConfigurationSetName"] == name_v2
    assert config_setv2["Tags"] == tags
    assert config_setv2["DeliveryOptions"] == delivery_options

    # Check for a non-existant config set
    with pytest.raises(ClientError) as ex:
        client_v2.get_configuration_set(ConfigurationSetName="invalid")
    err = ex.value.response["Error"]
    assert err["Code"] == "ConfigurationSetDoesNotExist"


@mock_aws
def test_list_configuration_sets():
    # Test ListConfigurationSet returns resources created in both ses and sesv2
    # Setup
    client_v1 = boto3.client("ses", region_name="eu-west-1")
    client_v2 = boto3.client("sesv2", region_name="eu-west-1")

    name_v1 = "my-sesv1"
    name_v2 = "my-sesv2-config-set"
    tracking_options = {
        "CustomRedirectDomain": "abc.com",
        "HttpsPolicy": "OPTIONAL",
    }
    delivery_options = {
        "TlsPolicy": "OPTIONAL",
        "SendingPoolName": "MySendingPool",
        "MaxDeliverySeconds": 301,
    }
    reputation_options = {
        "ReputationMetricsEnabled": False,
    }
    sending_options = {"SendingEnabled": True}
    tags = [
        {"Key": "Owner", "Value": "Zach"},
    ]
    suppression_options = {"SuppressedReasons": ["BOUNCE"]}
    vdm_options = {
        "DashboardOptions": {"EngagementMetrics": "DISABLED"},
        "GuardianOptions": {"OptimizedSharedDelivery": "DISABLED"},
    }

    client_v1.create_configuration_set(ConfigurationSet=dict({"Name": name_v1}))

    client_v2.create_configuration_set(
        ConfigurationSetName=name_v2,
        TrackingOptions=tracking_options,
        DeliveryOptions=delivery_options,
        ReputationOptions=reputation_options,
        SendingOptions=sending_options,
        Tags=tags,
        SuppressionOptions=suppression_options,
        VdmOptions=vdm_options,
    )

    # Execute
    config_sets = client_v2.list_configuration_sets()

    # Validate
    assert len(config_sets["ConfigurationSets"]) == 2
    for c in config_sets["ConfigurationSets"]:
        assert c in [name_v1, name_v2]


@mock_aws
def test_delete_configuration_set():
    # Setup
    client = boto3.client("sesv2", region_name="eu-west-1")
    name = "my-sesv2-config-set"
    tracking_options = {
        "CustomRedirectDomain": "abc.com",
        "HttpsPolicy": "OPTIONAL",
    }
    delivery_options = {
        "TlsPolicy": "OPTIONAL",
        "SendingPoolName": "MySendingPool",
        "MaxDeliverySeconds": 301,
    }
    reputation_options = {
        "ReputationMetricsEnabled": False,
    }
    sending_options = {"SendingEnabled": True}
    tags = [
        {"Key": "Owner", "Value": "Zach"},
    ]
    suppression_options = {"SuppressedReasons": ["BOUNCE"]}
    vdm_options = {
        "DashboardOptions": {"EngagementMetrics": "DISABLED"},
        "GuardianOptions": {"OptimizedSharedDelivery": "DISABLED"},
    }

    client.create_configuration_set(
        ConfigurationSetName=name,
        TrackingOptions=tracking_options,
        DeliveryOptions=delivery_options,
        ReputationOptions=reputation_options,
        SendingOptions=sending_options,
        Tags=tags,
        SuppressionOptions=suppression_options,
        VdmOptions=vdm_options,
    )

    config_set = client.get_configuration_set(ConfigurationSetName=name)
    assert config_set["ConfigurationSetName"] == name

    client.delete_configuration_set(ConfigurationSetName=name)

    # Check the resource no longer exists with Get call returning an error code
    with pytest.raises(ClientError) as ex:
        client.get_configuration_set(ConfigurationSetName=name)
    err = ex.value.response["Error"]
    assert err["Code"] == "ConfigurationSetDoesNotExist"


@mock_aws
def test_create_and_get_dedicated_ip_pool():
    client = boto3.client("sesv2", "us-east-1")
    pool_name = "test-pool"
    scaling_mode = "STANDARD"
    tags = [{"Key": "Owner", "Value": "Zach"}]
    client.create_dedicated_ip_pool(
        PoolName=pool_name, ScalingMode=scaling_mode, Tags=tags
    )

    pool = client.get_dedicated_ip_pool(PoolName=pool_name)["DedicatedIpPool"]
    assert pool["PoolName"] == pool_name
    assert pool["ScalingMode"] == scaling_mode


@mock_aws
def test_list_dedicated_ip_pools():
    client = boto3.client("sesv2", "us-east-1")
    num_pools = 3
    pool_name = "test-pool"
    scaling_mode = "STANDARD"
    tags = [{"Key": "Owner", "Value": "Zach"}]
    for i in range(0, num_pools):
        client.create_dedicated_ip_pool(
            PoolName=f"{pool_name}-{i}", ScalingMode=scaling_mode, Tags=tags
        )
    pools = client.list_dedicated_ip_pools()
    assert len(pools["DedicatedIpPools"]) == num_pools


@mock_aws
def test_delete_dedicated_ip_pool():
    client = boto3.client("sesv2", "us-east-1")
    num_pools = 2
    pool_name = "test-pool"
    scaling_mode = "STANDARD"
    tags = [{"Key": "Owner", "Value": "Zach"}]
    for i in range(0, num_pools):
        client.create_dedicated_ip_pool(
            PoolName=f"{pool_name}-{i}", ScalingMode=scaling_mode, Tags=tags
        )

    target_pool_name = "test-pool-1"
    target_pool = client.get_dedicated_ip_pool(PoolName=target_pool_name)
    assert target_pool["DedicatedIpPool"]["PoolName"] == target_pool_name

    # Delete the pool and verify it's no longer found
    client.delete_dedicated_ip_pool(PoolName=target_pool_name)
    with pytest.raises(ClientError) as e:
        client.get_dedicated_ip_pool(PoolName=target_pool_name)
    assert e.value.response["Error"]["Code"] == "NotFoundException"


@mock_aws
def test_create_email_identity_policy():
    client = boto3.client("sesv2", region_name="us-east-1")
    email_identity = "example.com"
    policy_name = "MyPolicy"
    policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                    "Action": ["ses:SendEmail", "ses:SendRawEmail"],
                    "Resource": f"arn:aws:ses:us-east-1:123456789012:identity/{email_identity}",
                }
            ],
        }
    )

    client.create_email_identity(EmailIdentity=email_identity)

    response = client.create_email_identity_policy(
        EmailIdentity=email_identity, PolicyName=policy_name, Policy=policy
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_delete_email_identity_policy():
    client = boto3.client("sesv2", region_name="us-east-1")
    email_identity = "example.com"
    policy_name = "MyPolicy"
    policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                    "Action": ["ses:SendEmail", "ses:SendRawEmail"],
                    "Resource": f"arn:aws:ses:us-east-1:123456789012:identity/{email_identity}",
                }
            ],
        }
    )

    client.create_email_identity(EmailIdentity=email_identity)
    client.create_email_identity_policy(
        EmailIdentity=email_identity, PolicyName=policy_name, Policy=policy
    )

    policies_before = client.get_email_identity_policies(EmailIdentity=email_identity)
    assert policy_name in policies_before["Policies"]

    response = client.delete_email_identity_policy(
        EmailIdentity=email_identity, PolicyName=policy_name
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    policies_after = client.get_email_identity_policies(EmailIdentity=email_identity)
    assert policy_name not in policies_after["Policies"]

    response = client.delete_email_identity_policy(
        EmailIdentity=email_identity, PolicyName="NonExistentPolicy"
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_update_email_identity_policy():
    client = boto3.client("sesv2", region_name="us-east-1")
    email_identity = "example.com"
    policy_name = "MyPolicy"

    initial_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                    "Action": ["ses:SendEmail"],
                    "Resource": f"arn:aws:ses:us-east-1:123456789012:identity/{email_identity}",
                }
            ],
        }
    )

    updated_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                    "Action": ["ses:SendEmail", "ses:SendRawEmail"],
                    "Resource": f"arn:aws:ses:us-east-1:123456789012:identity/{email_identity}",
                }
            ],
        }
    )

    client.create_email_identity(EmailIdentity=email_identity)
    client.create_email_identity_policy(
        EmailIdentity=email_identity, PolicyName=policy_name, Policy=initial_policy
    )

    initial_policies = client.get_email_identity_policies(EmailIdentity=email_identity)
    assert policy_name in initial_policies["Policies"]
    assert initial_policies["Policies"][policy_name] == initial_policy

    response = client.update_email_identity_policy(
        EmailIdentity=email_identity, PolicyName=policy_name, Policy=updated_policy
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    updated_policies = client.get_email_identity_policies(EmailIdentity=email_identity)
    assert policy_name in updated_policies["Policies"]
    assert updated_policies["Policies"][policy_name] == updated_policy
    assert updated_policies["Policies"][policy_name] != initial_policy

    new_policy_name = "NewPolicy"
    response = client.update_email_identity_policy(
        EmailIdentity=email_identity, PolicyName=new_policy_name, Policy=initial_policy
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    final_policies = client.get_email_identity_policies(EmailIdentity=email_identity)
    assert new_policy_name in final_policies["Policies"]
    assert final_policies["Policies"][new_policy_name] == initial_policy


@mock_aws
def test_get_email_identity_policies():
    client = boto3.client("sesv2", region_name="us-east-1")
    email_identity = "example.com"
    policy_name = "MyPolicy"
    policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                    "Action": ["ses:SendEmail", "ses:SendRawEmail"],
                    "Resource": f"arn:aws:ses:ap-southeast-1:123456789012:identity/{email_identity}",
                }
            ],
        }
    )

    client.create_email_identity(EmailIdentity=email_identity)
    client.create_email_identity_policy(
        EmailIdentity=email_identity, PolicyName=policy_name, Policy=policy
    )

    response = client.get_email_identity_policies(EmailIdentity=email_identity)

    assert policy_name in response["Policies"]
    assert response["Policies"][policy_name] == policy
