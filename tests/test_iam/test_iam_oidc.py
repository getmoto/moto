import boto3
import sure  # noqa  # pylint: disable=unused-import
from botocore.exceptions import ClientError

from moto import mock_iam
from moto.core import ACCOUNT_ID
import pytest

from datetime import datetime


@mock_iam
def test_create_open_id_connect_provider():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com",
        ThumbprintList=[],  # even it is required to provide at least one thumbprint, AWS accepts an empty list
    )

    response["OpenIDConnectProviderArn"].should.equal(
        "arn:aws:iam::{}:oidc-provider/example.com".format(ACCOUNT_ID)
    )

    response = client.create_open_id_connect_provider(
        Url="http://example.org", ThumbprintList=["b" * 40], ClientIDList=["b"]
    )

    response["OpenIDConnectProviderArn"].should.equal(
        "arn:aws:iam::{}:oidc-provider/example.org".format(ACCOUNT_ID)
    )

    response = client.create_open_id_connect_provider(
        Url="http://example.org/oidc", ThumbprintList=[]
    )

    response["OpenIDConnectProviderArn"].should.equal(
        "arn:aws:iam::{}:oidc-provider/example.org/oidc".format(ACCOUNT_ID)
    )

    response = client.create_open_id_connect_provider(
        Url="http://example.org/oidc-query?test=true", ThumbprintList=[]
    )

    response["OpenIDConnectProviderArn"].should.equal(
        "arn:aws:iam::{}:oidc-provider/example.org/oidc-query".format(ACCOUNT_ID)
    )


@mock_iam
def test_create_open_id_connect_provider_with_tags():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com",
        ThumbprintList=[],
        Tags=[{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
    )
    open_id_arn = response["OpenIDConnectProviderArn"]

    response = client.get_open_id_connect_provider(OpenIDConnectProviderArn=open_id_arn)
    response.should.have.key("Tags").length_of(2)
    response["Tags"].should.contain({"Key": "k1", "Value": "v1"})
    response["Tags"].should.contain({"Key": "k2", "Value": "v2"})


@pytest.mark.parametrize("url", ["example.org", "example"])
@mock_iam
def test_create_open_id_connect_provider_invalid_url(url):
    client = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.create_open_id_connect_provider(Url=url, ThumbprintList=[])
    msg = e.value.response["Error"]["Message"]
    msg.should.contain("Invalid Open ID Connect Provider URL")


@mock_iam
def test_create_open_id_connect_provider_errors():
    client = boto3.client("iam", region_name="us-east-1")
    client.create_open_id_connect_provider(Url="https://example.com", ThumbprintList=[])

    client.create_open_id_connect_provider.when.called_with(
        Url="https://example.com", ThumbprintList=[]
    ).should.throw(ClientError, "Unknown")


@mock_iam
def test_create_open_id_connect_provider_too_many_entries():
    client = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.create_open_id_connect_provider(
            Url="http://example.org",
            ThumbprintList=[
                "a" * 40,
                "b" * 40,
                "c" * 40,
                "d" * 40,
                "e" * 40,
                "f" * 40,
            ],
        )
    msg = e.value.response["Error"]["Message"]
    msg.should.contain("Thumbprint list must contain fewer than 5 entries.")


@mock_iam
def test_create_open_id_connect_provider_quota_error():
    client = boto3.client("iam", region_name="us-east-1")

    too_many_client_ids = ["{}".format(i) for i in range(101)]
    with pytest.raises(ClientError) as e:
        client.create_open_id_connect_provider(
            Url="http://example.org",
            ThumbprintList=[],
            ClientIDList=too_many_client_ids,
        )
    msg = e.value.response["Error"]["Message"]
    msg.should.contain("Cannot exceed quota for ClientIdsPerOpenIdConnectProvider: 100")


@mock_iam
def test_create_open_id_connect_provider_multiple_errors():
    client = boto3.client("iam", region_name="us-east-1")

    too_long_url = "b" * 256
    too_long_thumbprint = "b" * 41
    too_long_client_id = "b" * 256
    with pytest.raises(ClientError) as e:
        client.create_open_id_connect_provider(
            Url=too_long_url,
            ThumbprintList=[too_long_thumbprint],
            ClientIDList=[too_long_client_id],
        )
    msg = e.value.response["Error"]["Message"]
    msg.should.contain("3 validation errors detected:")
    msg.should.contain('"clientIDList" failed to satisfy constraint:')
    msg.should.contain("Member must have length less than or equal to 255")
    msg.should.contain("Member must have length greater than or equal to 1")
    msg.should.contain('"thumbprintList" failed to satisfy constraint:')
    msg.should.contain("Member must have length less than or equal to 40")
    msg.should.contain("Member must have length greater than or equal to 40")
    msg.should.contain('"url" failed to satisfy constraint:')
    msg.should.contain("Member must have length less than or equal to 255")


@mock_iam
def test_delete_open_id_connect_provider():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com", ThumbprintList=[]
    )
    open_id_arn = response["OpenIDConnectProviderArn"]

    client.delete_open_id_connect_provider(OpenIDConnectProviderArn=open_id_arn)

    client.get_open_id_connect_provider.when.called_with(
        OpenIDConnectProviderArn=open_id_arn
    ).should.throw(
        ClientError, "OpenIDConnect Provider not found for arn {}".format(open_id_arn)
    )

    # deleting a non existing provider should be successful
    client.delete_open_id_connect_provider(OpenIDConnectProviderArn=open_id_arn)


@mock_iam
def test_get_open_id_connect_provider():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com", ThumbprintList=["b" * 40], ClientIDList=["b"]
    )
    open_id_arn = response["OpenIDConnectProviderArn"]

    response = client.get_open_id_connect_provider(OpenIDConnectProviderArn=open_id_arn)

    response["Url"].should.equal("example.com")
    response["ThumbprintList"].should.equal(["b" * 40])
    response["ClientIDList"].should.equal(["b"])
    response.should.have.key("CreateDate").should.be.a(datetime)


@mock_iam
def test_update_open_id_connect_provider():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com", ThumbprintList=["b" * 40]
    )
    open_id_arn = response["OpenIDConnectProviderArn"]

    client.update_open_id_connect_provider_thumbprint(
        OpenIDConnectProviderArn=open_id_arn, ThumbprintList=["c" * 40, "d" * 40]
    )

    response = client.get_open_id_connect_provider(OpenIDConnectProviderArn=open_id_arn)

    response["Url"].should.equal("example.com")
    response["ThumbprintList"].should.have.length_of(2)
    response["ThumbprintList"].should.contain("c" * 40)
    response["ThumbprintList"].should.contain("d" * 40)


@mock_iam
def test_get_open_id_connect_provider_errors():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com", ThumbprintList=["b" * 40], ClientIDList=["b"]
    )
    open_id_arn = response["OpenIDConnectProviderArn"]

    client.get_open_id_connect_provider.when.called_with(
        OpenIDConnectProviderArn=open_id_arn + "-not-existing"
    ).should.throw(
        ClientError,
        "OpenIDConnect Provider not found for arn {}".format(
            open_id_arn + "-not-existing"
        ),
    )


@mock_iam
def test_list_open_id_connect_providers():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com", ThumbprintList=[]
    )
    open_id_arn_1 = response["OpenIDConnectProviderArn"]

    response = client.create_open_id_connect_provider(
        Url="http://example.org", ThumbprintList=["b" * 40], ClientIDList=["b"]
    )
    open_id_arn_2 = response["OpenIDConnectProviderArn"]

    response = client.create_open_id_connect_provider(
        Url="http://example.org/oidc", ThumbprintList=[]
    )
    open_id_arn_3 = response["OpenIDConnectProviderArn"]

    response = client.list_open_id_connect_providers()

    sorted(response["OpenIDConnectProviderList"], key=lambda i: i["Arn"]).should.equal(
        [{"Arn": open_id_arn_1}, {"Arn": open_id_arn_2}, {"Arn": open_id_arn_3}]
    )


@mock_iam
def test_tag_open_id_connect_provider():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com", ThumbprintList=[]
    )
    open_id_arn = response["OpenIDConnectProviderArn"]
    client.tag_open_id_connect_provider(
        OpenIDConnectProviderArn=open_id_arn,
        Tags=[{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
    )

    response = client.get_open_id_connect_provider(OpenIDConnectProviderArn=open_id_arn)
    response.should.have.key("Tags").length_of(2)
    response["Tags"].should.contain({"Key": "k1", "Value": "v1"})
    response["Tags"].should.contain({"Key": "k2", "Value": "v2"})


@mock_iam
def test_untag_open_id_connect_provider():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com", ThumbprintList=[]
    )
    open_id_arn = response["OpenIDConnectProviderArn"]
    client.tag_open_id_connect_provider(
        OpenIDConnectProviderArn=open_id_arn,
        Tags=[{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
    )
    client.untag_open_id_connect_provider(
        OpenIDConnectProviderArn=open_id_arn, TagKeys=["k2"]
    )

    response = client.get_open_id_connect_provider(OpenIDConnectProviderArn=open_id_arn)
    response.should.have.key("Tags").length_of(1)
    response["Tags"].should.contain({"Key": "k1", "Value": "v1"})


@mock_iam
def test_list_open_id_connect_provider_tags():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com",
        ThumbprintList=[],
        Tags=[{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
    )
    open_id_arn = response["OpenIDConnectProviderArn"]

    response = client.list_open_id_connect_provider_tags(
        OpenIDConnectProviderArn=open_id_arn
    )
    response.should.have.key("Tags").length_of(2)
    response["Tags"].should.contain({"Key": "k1", "Value": "v1"})
    response["Tags"].should.contain({"Key": "k2", "Value": "v2"})


@mock_iam
def test_list_open_id_connect_provider_tags__paginated():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com",
        ThumbprintList=[],
        Tags=[{"Key": f"k{idx}", "Value": f"v{idx}"} for idx in range(0, 50)],
    )
    open_id_arn = response["OpenIDConnectProviderArn"]
    client.tag_open_id_connect_provider(
        OpenIDConnectProviderArn=open_id_arn,
        Tags=[{"Key": f"k{idx}", "Value": f"v{idx}"} for idx in range(50, 100)],
    )
    client.tag_open_id_connect_provider(
        OpenIDConnectProviderArn=open_id_arn,
        Tags=[{"Key": f"k{idx}", "Value": f"v{idx}"} for idx in range(100, 150)],
    )

    response = client.list_open_id_connect_provider_tags(
        OpenIDConnectProviderArn=open_id_arn
    )
    response.should.have.key("Tags").length_of(100)
    response.should.have.key("Marker")

    response = client.list_open_id_connect_provider_tags(
        OpenIDConnectProviderArn=open_id_arn, Marker=response["Marker"]
    )
    response.should.have.key("Tags").length_of(50)
    response.shouldnt.have.key("Marker")


@mock_iam
def test_list_open_id_connect_provider_tags__maxitems():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com",
        ThumbprintList=[],
        Tags=[{"Key": f"k{idx}", "Value": f"v{idx}"} for idx in range(0, 10)],
    )
    open_id_arn = response["OpenIDConnectProviderArn"]

    response = client.list_open_id_connect_provider_tags(
        OpenIDConnectProviderArn=open_id_arn, MaxItems=4
    )
    response.should.have.key("Tags").length_of(4)
    response.should.have.key("Marker")

    response = client.list_open_id_connect_provider_tags(
        OpenIDConnectProviderArn=open_id_arn, Marker=response["Marker"], MaxItems=4
    )
    response.should.have.key("Tags").length_of(4)
    response.should.have.key("Marker")

    response = client.list_open_id_connect_provider_tags(
        OpenIDConnectProviderArn=open_id_arn, Marker=response["Marker"]
    )
    response.should.have.key("Tags").length_of(2)
    response.shouldnt.have.key("Marker")
