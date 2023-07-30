import boto3
from botocore.exceptions import ClientError

from moto import mock_iam
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
import pytest

from datetime import datetime


@mock_iam
def test_create_open_id_connect_provider():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com",
        ThumbprintList=[],  # even it is required to provide at least one thumbprint, AWS accepts an empty list
    )

    assert (
        response["OpenIDConnectProviderArn"]
        == f"arn:aws:iam::{ACCOUNT_ID}:oidc-provider/example.com"
    )

    response = client.create_open_id_connect_provider(
        Url="http://example.org", ThumbprintList=["b" * 40], ClientIDList=["b"]
    )

    assert (
        response["OpenIDConnectProviderArn"]
        == f"arn:aws:iam::{ACCOUNT_ID}:oidc-provider/example.org"
    )

    response = client.create_open_id_connect_provider(
        Url="http://example.org/oidc", ThumbprintList=[]
    )

    assert (
        response["OpenIDConnectProviderArn"]
        == f"arn:aws:iam::{ACCOUNT_ID}:oidc-provider/example.org/oidc"
    )

    response = client.create_open_id_connect_provider(
        Url="http://example.org/oidc-query?test=true", ThumbprintList=[]
    )

    assert (
        response["OpenIDConnectProviderArn"]
        == f"arn:aws:iam::{ACCOUNT_ID}:oidc-provider/example.org/oidc-query"
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
    assert len(response["Tags"]) == 2
    assert {"Key": "k1", "Value": "v1"} in response["Tags"]
    assert {"Key": "k2", "Value": "v2"} in response["Tags"]


@pytest.mark.parametrize("url", ["example.org", "example"])
@mock_iam
def test_create_open_id_connect_provider_invalid_url(url):
    client = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.create_open_id_connect_provider(Url=url, ThumbprintList=[])
    msg = e.value.response["Error"]["Message"]
    assert "Invalid Open ID Connect Provider URL" in msg


@mock_iam
def test_create_open_id_connect_provider_errors():
    client = boto3.client("iam", region_name="us-east-1")
    client.create_open_id_connect_provider(Url="https://example.com", ThumbprintList=[])

    with pytest.raises(ClientError) as exc:
        client.create_open_id_connect_provider(
            Url="https://example.com", ThumbprintList=[]
        )
    err = exc.value.response["Error"]
    assert err["Message"] == "Unknown"


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
    assert "Thumbprint list must contain fewer than 5 entries." in msg


@mock_iam
def test_create_open_id_connect_provider_quota_error():
    client = boto3.client("iam", region_name="us-east-1")

    too_many_client_ids = [f"{i}" for i in range(101)]
    with pytest.raises(ClientError) as e:
        client.create_open_id_connect_provider(
            Url="http://example.org",
            ThumbprintList=[],
            ClientIDList=too_many_client_ids,
        )
    msg = e.value.response["Error"]["Message"]
    assert "Cannot exceed quota for ClientIdsPerOpenIdConnectProvider: 100" in msg


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
    assert "3 validation errors detected:" in msg
    assert '"clientIDList" failed to satisfy constraint:' in msg
    assert "Member must have length less than or equal to 255" in msg
    assert "Member must have length greater than or equal to 1" in msg
    assert '"thumbprintList" failed to satisfy constraint:' in msg
    assert "Member must have length less than or equal to 40" in msg
    assert "Member must have length greater than or equal to 40" in msg
    assert '"url" failed to satisfy constraint:' in msg
    assert "Member must have length less than or equal to 255" in msg


@mock_iam
def test_delete_open_id_connect_provider():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com", ThumbprintList=[]
    )
    open_id_arn = response["OpenIDConnectProviderArn"]

    client.delete_open_id_connect_provider(OpenIDConnectProviderArn=open_id_arn)

    with pytest.raises(ClientError) as exc:
        client.get_open_id_connect_provider(OpenIDConnectProviderArn=open_id_arn)
    err = exc.value.response["Error"]
    assert err["Message"] == f"OpenIDConnect Provider not found for arn {open_id_arn}"

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

    assert response["Url"] == "example.com"
    assert response["ThumbprintList"] == ["b" * 40]
    assert response["ClientIDList"] == ["b"]
    assert isinstance(response["CreateDate"], datetime)


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

    assert response["Url"] == "example.com"
    assert len(response["ThumbprintList"]) == 2
    assert "c" * 40 in response["ThumbprintList"]
    assert "d" * 40 in response["ThumbprintList"]


@mock_iam
def test_get_open_id_connect_provider_errors():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_open_id_connect_provider(
        Url="https://example.com", ThumbprintList=["b" * 40], ClientIDList=["b"]
    )
    open_id_arn = response["OpenIDConnectProviderArn"]

    unknown_arn = open_id_arn + "-not-existing"
    with pytest.raises(ClientError) as exc:
        client.get_open_id_connect_provider(OpenIDConnectProviderArn=unknown_arn)
    err = exc.value.response["Error"]
    assert err["Message"] == f"OpenIDConnect Provider not found for arn {unknown_arn}"


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

    assert sorted(response["OpenIDConnectProviderList"], key=lambda i: i["Arn"]) == [
        {"Arn": open_id_arn_1},
        {"Arn": open_id_arn_2},
        {"Arn": open_id_arn_3},
    ]


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
    assert len(response["Tags"]) == 2
    assert {"Key": "k1", "Value": "v1"} in response["Tags"]
    assert {"Key": "k2", "Value": "v2"} in response["Tags"]


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
    assert len(response["Tags"]) == 1
    assert {"Key": "k1", "Value": "v1"} in response["Tags"]


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
    assert len(response["Tags"]) == 2
    assert {"Key": "k1", "Value": "v1"} in response["Tags"]
    assert {"Key": "k2", "Value": "v2"} in response["Tags"]


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
    assert len(response["Tags"]) == 100

    response = client.list_open_id_connect_provider_tags(
        OpenIDConnectProviderArn=open_id_arn, Marker=response["Marker"]
    )
    assert len(response["Tags"]) == 50
    assert "Marker" not in response


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
    assert len(response["Tags"]) == 4

    response = client.list_open_id_connect_provider_tags(
        OpenIDConnectProviderArn=open_id_arn, Marker=response["Marker"], MaxItems=4
    )
    assert len(response["Tags"]) == 4

    response = client.list_open_id_connect_provider_tags(
        OpenIDConnectProviderArn=open_id_arn, Marker=response["Marker"]
    )
    assert len(response["Tags"]) == 2
    assert "Marker" not in response
