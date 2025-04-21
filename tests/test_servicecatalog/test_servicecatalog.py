"""Unit tests for servicecatalog-supported APIs."""

import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_portfolio():
    """Test create_portfolio API."""
    client = boto3.client("servicecatalog", region_name="us-east-1")

    response = client.create_portfolio(
        DisplayName="Test Portfolio",
        Description="Test Portfolio Description",
        ProviderName="Test Provider",
        Tags=[{"Key": "testkey", "Value": "testvalue"}],
        IdempotencyToken="test-token",
    )

    assert "PortfolioDetail" in response
    assert "Tags" in response

    portfolio_detail = response["PortfolioDetail"]
    assert "Id" in portfolio_detail
    assert "ARN" in portfolio_detail
    assert "DisplayName" in portfolio_detail
    assert "Description" in portfolio_detail
    assert "CreatedTime" in portfolio_detail
    assert "ProviderName" in portfolio_detail

    assert portfolio_detail["DisplayName"] == "Test Portfolio"
    assert portfolio_detail["Description"] == "Test Portfolio Description"
    assert portfolio_detail["ProviderName"] == "Test Provider"

    tags = response["Tags"]
    assert len(tags) == 1
    assert tags[0]["Key"] == "testkey"
    assert tags[0]["Value"] == "testvalue"

    response2 = client.create_portfolio(
        DisplayName="Different Name",
        Description="Different Description",
        ProviderName="Different Provider",
        Tags=[],
        IdempotencyToken="test-token",
    )

    assert response["PortfolioDetail"]["Id"] == response2["PortfolioDetail"]["Id"]
    assert (
        response["PortfolioDetail"]["DisplayName"]
        == response2["PortfolioDetail"]["DisplayName"]
    )


@mock_aws
def test_delete_portfolio():
    """Test delete_portfolio API."""
    client = boto3.client("servicecatalog", region_name="us-east-1")

    create_response = client.create_portfolio(
        DisplayName="Test Portfolio",
        Description="Test Portfolio Description",
        ProviderName="Test Provider",
        Tags=[],
        IdempotencyToken="test-token",
    )

    portfolio_id = create_response["PortfolioDetail"]["Id"]

    list_response_before = client.list_portfolios()
    assert "PortfolioDetails" in list_response_before
    portfolio_ids_before = [p["Id"] for p in list_response_before["PortfolioDetails"]]
    assert portfolio_id in portfolio_ids_before

    client.delete_portfolio(Id=portfolio_id)

    list_response_after = client.list_portfolios()
    assert "PortfolioDetails" in list_response_after
    portfolio_ids_after = [p["Id"] for p in list_response_after["PortfolioDetails"]]
    assert portfolio_id not in portfolio_ids_after


@mock_aws
def test_create_portfolio_share_with_account():
    """Test create_portfolio_share API with an account ID."""
    client = boto3.client("servicecatalog", region_name="us-east-1")

    create_response = client.create_portfolio(
        DisplayName="Test Portfolio",
        Description="Test Portfolio Description",
        ProviderName="Test Provider",
        Tags=[],
        IdempotencyToken="test-token",
    )

    portfolio_id = create_response["PortfolioDetail"]["Id"]

    share_response = client.create_portfolio_share(
        PortfolioId=portfolio_id, AccountId="123456789012"
    )

    assert "PortfolioShareToken" not in share_response

    access_response = client.list_portfolio_access(PortfolioId=portfolio_id)

    assert "AccountIds" in access_response
    assert "123456789012" in access_response["AccountIds"]


@mock_aws
def test_create_portfolio_share_with_organization():
    """Test create_portfolio_share API with an organization node."""
    client = boto3.client("servicecatalog", region_name="us-east-1")

    create_response = client.create_portfolio(
        DisplayName="Test Portfolio",
        Description="Test Portfolio Description",
        ProviderName="Test Provider",
        Tags=[],
        IdempotencyToken="test-token",
    )

    portfolio_id = create_response["PortfolioDetail"]["Id"]

    share_response = client.create_portfolio_share(
        PortfolioId=portfolio_id,
        OrganizationNode={"Type": "ORGANIZATION", "Value": "o-exampleorgid"},
        ShareTagOptions=True,
        SharePrincipals=True,
    )

    assert share_response["PortfolioShareToken"].startswith(f"share-{portfolio_id}")

    assert "ORGANIZATION" in share_response["PortfolioShareToken"]
    assert "o-exampleorgid" in share_response["PortfolioShareToken"]
    assert "tags" in share_response["PortfolioShareToken"]
    assert "principals" in share_response["PortfolioShareToken"]


@mock_aws
def test_delete_portfolio_share_with_account():
    """Test delete_portfolio_share API with an account ID."""
    client = boto3.client("servicecatalog", region_name="us-east-1")

    create_response = client.create_portfolio(
        DisplayName="Test Portfolio",
        Description="Test Portfolio Description",
        ProviderName="Test Provider",
        Tags=[],
        IdempotencyToken="test-token",
    )

    portfolio_id = create_response["PortfolioDetail"]["Id"]

    client.create_portfolio_share(PortfolioId=portfolio_id, AccountId="123456789012")

    access_response = client.list_portfolio_access(PortfolioId=portfolio_id)
    assert "123456789012" in access_response["AccountIds"]

    client.delete_portfolio_share(PortfolioId=portfolio_id, AccountId="123456789012")

    access_response = client.list_portfolio_access(PortfolioId=portfolio_id)
    assert "123456789012" not in access_response["AccountIds"]


@mock_aws
def test_delete_portfolio_share_with_organization():
    """Test delete_portfolio_share API with an organization node."""
    client = boto3.client("servicecatalog", region_name="us-east-1")

    create_response = client.create_portfolio(
        DisplayName="Test Portfolio",
        Description="Test Portfolio Description",
        ProviderName="Test Provider",
        Tags=[],
        IdempotencyToken="test-token",
    )

    portfolio_id = create_response["PortfolioDetail"]["Id"]

    delete_response = client.delete_portfolio_share(
        PortfolioId=portfolio_id,
        OrganizationNode={"Type": "ORGANIZATION", "Value": "o-exampleorgid"},
    )

    assert delete_response["PortfolioShareToken"].startswith(f"share-{portfolio_id}")
    assert "ORGANIZATION" in delete_response["PortfolioShareToken"]
    assert "o-exampleorgid" in delete_response["PortfolioShareToken"]


@mock_aws
def test_list_portfolio_access():
    """Test list_portfolio_access API."""
    client = boto3.client("servicecatalog", region_name="us-east-1")

    create_response = client.create_portfolio(
        DisplayName="Test Portfolio",
        Description="Test Portfolio Description",
        ProviderName="Test Provider",
        Tags=[],
        IdempotencyToken="test-token",
    )

    portfolio_id = create_response["PortfolioDetail"]["Id"]

    client.create_portfolio_share(PortfolioId=portfolio_id, AccountId="111111111111")

    client.create_portfolio_share(PortfolioId=portfolio_id, AccountId="222222222222")

    access_response = client.list_portfolio_access(PortfolioId=portfolio_id)

    assert "111111111111" in access_response["AccountIds"]
    assert "222222222222" in access_response["AccountIds"]

    paginated_response = client.list_portfolio_access(
        PortfolioId=portfolio_id, PageSize=1
    )

    assert len(paginated_response["AccountIds"]) == 1
    assert "NextPageToken" in paginated_response

    if paginated_response.get("NextPageToken"):
        next_page = client.list_portfolio_access(
            PortfolioId=portfolio_id,
            PageSize=1,
            PageToken=paginated_response["NextPageToken"],
        )

        assert len(next_page["AccountIds"]) == 1
        assert next_page["AccountIds"][0] != paginated_response["AccountIds"][0]


@mock_aws
def test_list_portfolios():
    """Test list_portfolios API."""
    client = boto3.client("servicecatalog", region_name="us-east-1")

    client.create_portfolio(
        DisplayName="Test Portfolio 1",
        Description="Test Portfolio 1 Description",
        ProviderName="Test Provider 1",
        Tags=[],
        IdempotencyToken="test-token-1",
    )

    client.create_portfolio(
        DisplayName="Test Portfolio 2",
        Description="Test Portfolio 2 Description",
        ProviderName="Test Provider 2",
        Tags=[],
        IdempotencyToken="test-token-2",
    )

    response = client.list_portfolios()

    assert "PortfolioDetails" in response

    portfolio_details = response["PortfolioDetails"]
    assert len(portfolio_details) == 2

    for portfolio in portfolio_details:
        assert "Id" in portfolio
        assert "ARN" in portfolio
        assert "DisplayName" in portfolio
        assert "Description" in portfolio
        assert "CreatedTime" in portfolio
        assert "ProviderName" in portfolio

    paginated_response = client.list_portfolios(PageSize=1)
    assert len(paginated_response["PortfolioDetails"]) == 2


@mock_aws
def test_describe_portfolio_shares():
    """Test describe_portfolio_shares API."""
    client = boto3.client("servicecatalog", region_name="us-east-1")

    create_response = client.create_portfolio(
        DisplayName="Test Portfolio",
        Description="Test Portfolio Description",
        ProviderName="Test Provider",
        Tags=[],
        IdempotencyToken="test-token",
    )

    portfolio_id = create_response["PortfolioDetail"]["Id"]

    client.create_portfolio_share(PortfolioId=portfolio_id, AccountId="111111111111")
    client.create_portfolio_share(PortfolioId=portfolio_id, AccountId="222222222222")
    client.create_portfolio_share(PortfolioId=portfolio_id, AccountId="333333333333")

    client.create_portfolio_share(
        PortfolioId=portfolio_id,
        OrganizationNode={"Type": "ORGANIZATION", "Value": "o-exampleorgid"},
        ShareTagOptions=True,
        SharePrincipals=True,
    )

    account_response = client.describe_portfolio_shares(
        PortfolioId=portfolio_id, Type="ACCOUNT"
    )

    assert "PortfolioShareDetails" in account_response
    assert len(account_response["PortfolioShareDetails"]) == 3

    for share in account_response["PortfolioShareDetails"]:
        assert share["Type"] == "ACCOUNT"
        assert share["Accepted"] is True
        assert share["PrincipalId"] in ["111111111111", "222222222222", "333333333333"]

    org_response = client.describe_portfolio_shares(
        PortfolioId=portfolio_id, Type="ORGANIZATION"
    )

    assert "PortfolioShareDetails" in org_response
    assert len(org_response["PortfolioShareDetails"]) == 1

    org_share = org_response["PortfolioShareDetails"][0]
    assert org_share["Type"] == "ORGANIZATION"
    assert org_share["PrincipalId"] == "o-exampleorgid"
    assert org_share["Accepted"] is True
    assert org_share["ShareTagOptions"] is True
    assert org_share["SharePrincipals"] is True

    client.delete_portfolio_share(
        PortfolioId=portfolio_id,
        OrganizationNode={"Type": "ORGANIZATION", "Value": "o-exampleorgid"},
    )

    org_response_after_delete = client.describe_portfolio_shares(
        PortfolioId=portfolio_id, Type="ORGANIZATION"
    )

    assert len(org_response_after_delete["PortfolioShareDetails"]) == 0


@mock_aws
def test_describe_portfolio():
    """Test describe_portfolio API."""
    client = boto3.client("servicecatalog", region_name="us-east-1")

    create_response = client.create_portfolio(
        DisplayName="Test Portfolio",
        Description="Test Portfolio Description",
        ProviderName="Test Provider",
        Tags=[{"Key": "testkey", "Value": "testvalue"}],
        IdempotencyToken="test-token",
    )

    portfolio_id = create_response["PortfolioDetail"]["Id"]

    describe_response = client.describe_portfolio(Id=portfolio_id)

    assert "PortfolioDetail" in describe_response
    portfolio_detail = describe_response["PortfolioDetail"]

    assert portfolio_detail["Id"] == portfolio_id
    assert "ARN" in portfolio_detail
    assert portfolio_detail["DisplayName"] == "Test Portfolio"
    assert portfolio_detail["Description"] == "Test Portfolio Description"
    assert portfolio_detail["ProviderName"] == "Test Provider"
    assert "CreatedTime" in portfolio_detail

    assert "Tags" in describe_response
    tags = describe_response["Tags"]
    assert len(tags) == 1
    assert tags[0]["Key"] == "testkey"
    assert tags[0]["Value"] == "testvalue"

    assert "TagOptions" in describe_response
    assert "Budgets" in describe_response

    non_existent_response = client.describe_portfolio(Id="non-existent-id")
    assert "PortfolioDetail" in non_existent_response
    assert non_existent_response["PortfolioDetail"] == {}
    assert non_existent_response["Tags"] == []
    assert non_existent_response["TagOptions"] == []
    assert non_existent_response["Budgets"] == []
