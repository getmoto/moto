import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_get_database_default():
    """AWS pre-creates a 'default' database under AwsDataCatalog."""
    client = boto3.client("athena", region_name="us-east-1")
    result = client.get_database(CatalogName="AwsDataCatalog", DatabaseName="default")
    db = result["Database"]
    assert db["Name"] == "default"
    assert "Description" in db
    assert "Parameters" in db


@mock_aws
def test_get_database_not_found():
    """GetDatabase for a nonexistent database should raise MetadataException."""
    client = boto3.client("athena", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.get_database(CatalogName="AwsDataCatalog", DatabaseName="nonexistent_db")
    err = exc.value.response["Error"]
    assert err["Code"] == "MetadataException"
    assert "nonexistent_db" in err["Message"]


@mock_aws
def test_create_database_via_ddl_and_get():
    """CREATE DATABASE via start_query_execution should make it available via get_database."""
    client = boto3.client("athena", region_name="us-east-1")
    client.start_query_execution(
        QueryString="CREATE DATABASE my_test_db",
        ResultConfiguration={"OutputLocation": "s3://bucket/key"},
    )
    result = client.get_database(
        CatalogName="AwsDataCatalog", DatabaseName="my_test_db"
    )
    assert result["Database"]["Name"] == "my_test_db"


@mock_aws
def test_create_database_schema_keyword():
    """CREATE SCHEMA is equivalent to CREATE DATABASE in Athena."""
    client = boto3.client("athena", region_name="us-east-1")
    client.start_query_execution(
        QueryString="CREATE SCHEMA schema_db",
        ResultConfiguration={"OutputLocation": "s3://bucket/key"},
    )
    result = client.get_database(CatalogName="AwsDataCatalog", DatabaseName="schema_db")
    assert result["Database"]["Name"] == "schema_db"


@mock_aws
def test_create_database_if_not_exists():
    """CREATE DATABASE IF NOT EXISTS should not error if DB already exists."""
    client = boto3.client("athena", region_name="us-east-1")
    config = {"OutputLocation": "s3://bucket/key"}
    client.start_query_execution(
        QueryString="CREATE DATABASE my_db", ResultConfiguration=config
    )
    # Should not raise
    client.start_query_execution(
        QueryString="CREATE DATABASE IF NOT EXISTS my_db",
        ResultConfiguration=config,
    )
    result = client.get_database(CatalogName="AwsDataCatalog", DatabaseName="my_db")
    assert result["Database"]["Name"] == "my_db"


@mock_aws
def test_drop_database_via_ddl():
    """DROP DATABASE should remove the database."""
    client = boto3.client("athena", region_name="us-east-1")
    config = {"OutputLocation": "s3://bucket/key"}
    client.start_query_execution(
        QueryString="CREATE DATABASE drop_me", ResultConfiguration=config
    )
    # Verify it exists
    client.get_database(CatalogName="AwsDataCatalog", DatabaseName="drop_me")

    # Drop it
    client.start_query_execution(
        QueryString="DROP DATABASE drop_me", ResultConfiguration=config
    )

    # Should no longer exist
    with pytest.raises(ClientError) as exc:
        client.get_database(CatalogName="AwsDataCatalog", DatabaseName="drop_me")
    assert exc.value.response["Error"]["Code"] == "MetadataException"


@mock_aws
def test_drop_database_if_exists():
    """DROP DATABASE IF EXISTS should not error for nonexistent database."""
    client = boto3.client("athena", region_name="us-east-1")
    config = {"OutputLocation": "s3://bucket/key"}
    # Should not raise even though DB doesn't exist
    client.start_query_execution(
        QueryString="DROP DATABASE IF EXISTS no_such_db",
        ResultConfiguration=config,
    )


@mock_aws
def test_drop_schema_keyword():
    """DROP SCHEMA is equivalent to DROP DATABASE."""
    client = boto3.client("athena", region_name="us-east-1")
    config = {"OutputLocation": "s3://bucket/key"}
    client.start_query_execution(
        QueryString="CREATE DATABASE schema_drop_test", ResultConfiguration=config
    )
    client.start_query_execution(
        QueryString="DROP SCHEMA schema_drop_test", ResultConfiguration=config
    )
    with pytest.raises(ClientError) as exc:
        client.get_database(
            CatalogName="AwsDataCatalog", DatabaseName="schema_drop_test"
        )
    assert exc.value.response["Error"]["Code"] == "MetadataException"


@mock_aws
def test_list_databases():
    """ListDatabases should return all databases for a catalog."""
    client = boto3.client("athena", region_name="us-east-1")
    config = {"OutputLocation": "s3://bucket/key"}

    # Create a few databases
    for name in ["alpha_db", "beta_db", "gamma_db"]:
        client.start_query_execution(
            QueryString=f"CREATE DATABASE {name}", ResultConfiguration=config
        )

    result = client.list_databases(CatalogName="AwsDataCatalog")
    db_names = [db["Name"] for db in result["DatabaseList"]]

    # Should include default + the 3 we created
    assert "default" in db_names
    assert "alpha_db" in db_names
    assert "beta_db" in db_names
    assert "gamma_db" in db_names


@mock_aws
def test_list_databases_pagination():
    """ListDatabases should support MaxResults pagination."""
    client = boto3.client("athena", region_name="us-east-1")
    config = {"OutputLocation": "s3://bucket/key"}

    for i in range(5):
        client.start_query_execution(
            QueryString=f"CREATE DATABASE pag_db_{i:02d}",
            ResultConfiguration=config,
        )

    # First page
    result = client.list_databases(CatalogName="AwsDataCatalog", MaxResults=3)
    assert len(result["DatabaseList"]) == 3
    assert "NextToken" in result

    # Second page
    result2 = client.list_databases(
        CatalogName="AwsDataCatalog",
        MaxResults=3,
        NextToken=result["NextToken"],
    )
    assert len(result2["DatabaseList"]) >= 1

    # All database names should be unique across pages
    all_names = [db["Name"] for db in result["DatabaseList"]] + [
        db["Name"] for db in result2["DatabaseList"]
    ]
    assert len(all_names) == len(set(all_names))


@mock_aws
def test_list_databases_empty_catalog():
    """ListDatabases for a catalog with no databases returns empty list."""
    client = boto3.client("athena", region_name="us-east-1")
    result = client.list_databases(CatalogName="NonExistentCatalog")
    assert result["DatabaseList"] == []


@mock_aws
def test_create_database_with_backticks():
    """Database names with backticks should be handled correctly."""
    client = boto3.client("athena", region_name="us-east-1")
    client.start_query_execution(
        QueryString="CREATE DATABASE `backtick_db`",
        ResultConfiguration={"OutputLocation": "s3://bucket/key"},
    )
    result = client.get_database(
        CatalogName="AwsDataCatalog", DatabaseName="backtick_db"
    )
    assert result["Database"]["Name"] == "backtick_db"


@mock_aws
def test_database_names_are_case_insensitive():
    """AWS Athena stores database names as lowercase."""
    client = boto3.client("athena", region_name="us-east-1")
    client.start_query_execution(
        QueryString="CREATE DATABASE MyMixedCaseDB",
        ResultConfiguration={"OutputLocation": "s3://bucket/key"},
    )
    # Should be stored as lowercase
    result = client.get_database(
        CatalogName="AwsDataCatalog", DatabaseName="mymixedcasedb"
    )
    assert result["Database"]["Name"] == "mymixedcasedb"

    # Lookup with different casing should also work
    result = client.get_database(
        CatalogName="AwsDataCatalog", DatabaseName="MYMIXEDCASEDB"
    )
    assert result["Database"]["Name"] == "mymixedcasedb"


@mock_aws
def test_create_database_with_catalog_context():
    """Database should be created under the catalog specified in QueryExecutionContext."""
    client = boto3.client("athena", region_name="us-east-1")

    # First create a custom data catalog
    client.create_data_catalog(
        Name="custom_catalog", Type="GLUE", Description="Custom catalog"
    )

    client.start_query_execution(
        QueryString="CREATE DATABASE ctx_db",
        QueryExecutionContext={"Catalog": "custom_catalog"},
        ResultConfiguration={"OutputLocation": "s3://bucket/key"},
    )

    result = client.get_database(CatalogName="custom_catalog", DatabaseName="ctx_db")
    assert result["Database"]["Name"] == "ctx_db"

    # Should NOT be in AwsDataCatalog
    with pytest.raises(ClientError) as exc:
        client.get_database(CatalogName="AwsDataCatalog", DatabaseName="ctx_db")
    assert exc.value.response["Error"]["Code"] == "MetadataException"
