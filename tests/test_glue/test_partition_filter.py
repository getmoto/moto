from unittest import SkipTest

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.client import ClientError

from moto import mock_glue, settings

from . import helpers


@mock_glue
def test_get_partitions_expression_unknown_column():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    values = ["2018-10-01"]
    columns = [helpers.create_column("date_col", "date")]
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    helpers.create_partition(
        client, database_name, table_name, values=values, columns=columns
    )

    with pytest.raises(ClientError) as exc:
        client.get_partitions(
            DatabaseName=database_name,
            TableName=table_name,
            Expression="unknown_col IS NULL",
        )

    exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
    exc.value.response["Error"]["Message"].should.match("Unknown column 'unknown_col'")


@mock_glue
def test_get_partitions_expression_int_column():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    columns = [helpers.create_column("int_col", "int")]

    helpers.create_database(client, database_name)

    args = (client, database_name, table_name)
    helpers.create_table(*args, partition_keys=columns)
    helpers.create_partition(*args, values=["1"], columns=columns)
    helpers.create_partition(*args, values=["2"], columns=columns)
    helpers.create_partition(*args, values=["3"], columns=columns)

    kwargs = {"DatabaseName": database_name, "TableName": table_name}

    response = client.get_partitions(**kwargs)
    partitions = response["Partitions"]
    partitions.should.have.length_of(3)

    int_col_is_two_expressions = (
        "int_col = 2",
        "int_col = '2'",
        "int_col IN (2)",
        "int_col in (6, '4', 2)",
        "int_col between 2 AND 2",
        "int_col > 1 AND int_col < 3",
        "int_col >= 2 and int_col <> 3",
        "(int_col) = ((2)) (OR) (((int_col))) = (2)",
        "int_col IS NOT NULL and int_col = 2",
        "int_col not IN (1, 3)",
        "int_col NOT BETWEEN 1 AND 1 and int_col NOT BETWEEN 3 AND 3",
        "int_col = 4 OR int_col = 5 AND int_col = '-1' OR int_col = 0 OR int_col = '2'",
    )

    for expression in int_col_is_two_expressions:
        response = client.get_partitions(**kwargs, Expression=expression)
        partitions = response["Partitions"]
        partitions.should.have.length_of(1)
        partition = partitions[0]
        partition["Values"].should.equal(["2"])

    bad_int_expressions = ("int_col = 'test'", "int_col in (2.5)")
    for expression in bad_int_expressions:
        with pytest.raises(ClientError) as exc:
            client.get_partitions(**kwargs, Expression=expression)

        exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
        exc.value.response["Error"]["Message"].should.match("is not an integer")

    with pytest.raises(ClientError) as exc:
        client.get_partitions(**kwargs, Expression="int_col LIKE '2'")

    exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
    exc.value.response["Error"]["Message"].should.match(
        "Integral data type doesn't support operation 'LIKE'"
    )


@mock_glue
def test_get_partitions_expression_decimal_column():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    columns = [helpers.create_column("decimal_col", "decimal")]

    helpers.create_database(client, database_name)

    args = (client, database_name, table_name)
    helpers.create_table(*args, partition_keys=columns)
    helpers.create_partition(*args, values=["1.2"], columns=columns)
    helpers.create_partition(*args, values=["2.6"], columns=columns)
    helpers.create_partition(*args, values=["3e14"], columns=columns)

    kwargs = {"DatabaseName": database_name, "TableName": table_name}

    response = client.get_partitions(**kwargs)
    partitions = response["Partitions"]
    partitions.should.have.length_of(3)

    decimal_col_is_two_point_six_expressions = (
        "decimal_col = 2.6",
        "decimal_col = '2.6'",
        "decimal_col IN (2.6)",
        "decimal_col in (6, '4', 2.6)",
        "decimal_col between 2 AND 3e10",
        "decimal_col > 1.5 AND decimal_col < 3",
        "decimal_col >= 2 and decimal_col <> '3e14'",
    )

    for expression in decimal_col_is_two_point_six_expressions:
        response = client.get_partitions(**kwargs, Expression=expression)
        partitions = response["Partitions"]
        partitions.should.have.length_of(1)
        partition = partitions[0]
        partition["Values"].should.equal(["2.6"])

    bad_decimal_expressions = ("decimal_col = 'test'",)
    for expression in bad_decimal_expressions:
        with pytest.raises(ClientError) as exc:
            client.get_partitions(**kwargs, Expression=expression)

        exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
        exc.value.response["Error"]["Message"].should.match("is not a decimal")

    with pytest.raises(ClientError) as exc:
        client.get_partitions(**kwargs, Expression="decimal_col LIKE '2'")

    exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
    exc.value.response["Error"]["Message"].should.match(
        "Decimal data type doesn't support operation 'LIKE'"
    )


@mock_glue
def test_get_partitions_expression_string_column():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    columns = [helpers.create_column("string_col", "string")]

    helpers.create_database(client, database_name)

    args = (client, database_name, table_name)
    helpers.create_table(*args, partition_keys=columns)
    helpers.create_partition(*args, values=["one"], columns=columns)
    helpers.create_partition(*args, values=["two"], columns=columns)
    helpers.create_partition(*args, values=["2"], columns=columns)
    helpers.create_partition(*args, values=["three"], columns=columns)

    kwargs = {"DatabaseName": database_name, "TableName": table_name}

    response = client.get_partitions(**kwargs)
    partitions = response["Partitions"]
    partitions.should.have.length_of(4)

    string_col_is_two_expressions = (
        "string_col = 'two'",
        "string_col = 2",
        "string_col IN (1, 2, 3)",
        "string_col IN ('1', '2', '3')",
        "string_col IN ('test', 'two', '3')",
        "string_col between 'twn' AND 'twp'",
        "string_col > '1' AND string_col < '3'",
        "string_col LIKE 'two'",
        "string_col LIKE 't_o'",
        "string_col LIKE 't__'",
        "string_col LIKE '%wo'",
        "string_col NOT LIKE '%e' AND string_col not like '_'",
    )

    for expression in string_col_is_two_expressions:
        response = client.get_partitions(**kwargs, Expression=expression)
        partitions = response["Partitions"]
        partitions.should.have.length_of(1)
        partition = partitions[0]
        partition["Values"].should.be.within((["two"], ["2"]))

    with pytest.raises(ClientError) as exc:
        client.get_partitions(**kwargs, Expression="unknown_col LIKE 'two'")

    exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
    exc.value.response["Error"]["Message"].should.match("Unknown column 'unknown_col'")


@mock_glue
def test_get_partitions_expression_date_column():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    columns = [helpers.create_column("date_col", "date")]

    helpers.create_database(client, database_name)

    args = (client, database_name, table_name)
    helpers.create_table(*args, partition_keys=columns)
    helpers.create_partition(*args, values=["2022-01-01"], columns=columns)
    helpers.create_partition(*args, values=["2022-02-01"], columns=columns)
    helpers.create_partition(*args, values=["2022-03-01"], columns=columns)

    kwargs = {"DatabaseName": database_name, "TableName": table_name}

    response = client.get_partitions(**kwargs)
    partitions = response["Partitions"]
    partitions.should.have.length_of(3)

    date_col_is_february_expressions = (
        "date_col = '2022-02-01'",
        "date_col IN ('2022-02-01')",
        "date_col in ('2024-02-29', '2022-02-01', '2022-02-02')",
        "date_col between '2022-01-15' AND '2022-02-15'",
        "date_col > '2022-01-15' AND date_col < '2022-02-15'",
    )

    for expression in date_col_is_february_expressions:
        response = client.get_partitions(**kwargs, Expression=expression)
        partitions = response["Partitions"]
        partitions.should.have.length_of(1)
        partition = partitions[0]
        partition["Values"].should.equal(["2022-02-01"])

    bad_date_expressions = ("date_col = 'test'", "date_col = '2022-02-32'")
    for expression in bad_date_expressions:
        with pytest.raises(ClientError) as exc:
            client.get_partitions(**kwargs, Expression=expression)

        exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
        exc.value.response["Error"]["Message"].should.match("is not a date")

    with pytest.raises(ClientError) as exc:
        client.get_partitions(**kwargs, Expression="date_col LIKE '2022-02-01'")

    exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
    exc.value.response["Error"]["Message"].should.match(
        "Date data type doesn't support operation 'LIKE'"
    )


@mock_glue
def test_get_partitions_expression_timestamp_column():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    columns = [helpers.create_column("timestamp_col", "timestamp")]

    helpers.create_database(client, database_name)

    args = (client, database_name, table_name)
    helpers.create_table(*args, partition_keys=columns)
    helpers.create_partition(*args, values=["2022-01-01 12:34:56.789"], columns=columns)
    helpers.create_partition(
        *args, values=["2022-02-01 00:00:00.000000"], columns=columns
    )
    helpers.create_partition(
        *args, values=["2022-03-01 21:00:12.3456789"], columns=columns
    )

    kwargs = {"DatabaseName": database_name, "TableName": table_name}

    response = client.get_partitions(**kwargs)
    partitions = response["Partitions"]
    partitions.should.have.length_of(3)

    timestamp_col_is_february_expressions = (
        "timestamp_col = '2022-02-01 00:00:00'",
        "timestamp_col = '2022-02-01 00:00:00.0'",
        "timestamp_col = '2022-02-01 00:00:00.000000000'",
        "timestamp_col IN ('2022-02-01 00:00:00.000')",
        "timestamp_col between '2022-01-15 00:00:00' AND '2022-02-15 00:00:00'",
        "timestamp_col > '2022-01-15 00:00:00' AND "
        "timestamp_col < '2022-02-15 00:00:00'",
        "timestamp_col > '2022-01-31 23:59:59.999999499' AND"
        " timestamp_col < '2022-02-01 00:00:00.0000009'",
        "timestamp_col > '2022-01-31 23:59:59.999999999' AND"
        " timestamp_col < '2022-02-01 00:00:00.000000001'",
    )

    for expression in timestamp_col_is_february_expressions:
        response = client.get_partitions(**kwargs, Expression=expression)
        partitions = response["Partitions"]
        partitions.should.have.length_of(1)
        partition = partitions[0]
        partition["Values"].should.equal(["2022-02-01 00:00:00.000000"])

    bad_timestamp_expressions = (
        "timestamp_col = '2022-02-01'",
        "timestamp_col = '2022-02-15 00:00:00.'",
        "timestamp_col = '2022-02-32 00:00:00'",
    )
    for expression in bad_timestamp_expressions:
        with pytest.raises(ClientError) as exc:
            client.get_partitions(**kwargs, Expression=expression)

        exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
        exc.value.response["Error"]["Message"].should.match("is not a timestamp")

    with pytest.raises(ClientError) as exc:
        client.get_partitions(
            **kwargs, Expression="timestamp_col LIKE '2022-02-01 00:00:00'"
        )

    exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
    exc.value.response["Error"]["Message"].should.match(
        "Timestamp data type doesn't support operation 'LIKE'"
    )


@mock_glue
def test_get_partition_expression_warnings_and_exceptions():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Cannot catch warnings in server mode")

    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    columns = [
        helpers.create_column("string_col", "string"),
        helpers.create_column("int_col", "int"),
        helpers.create_column("float_col", "float"),
    ]

    helpers.create_database(client, database_name)

    args = (client, database_name, table_name)
    helpers.create_table(*args, partition_keys=columns)
    helpers.create_partition(*args, values=["test", "int", "3.14"], columns=columns)

    kwargs = {"DatabaseName": database_name, "TableName": table_name}

    response = client.get_partitions(**kwargs, Expression="string_col = 'test'")
    partitions = response["Partitions"]
    partitions.should.have.length_of(1)
    partition = partitions[0]
    partition["Values"].should.equal(["test", "int", "3.14"])

    with pytest.raises(ClientError) as exc:
        client.get_partitions(**kwargs, Expression="float_col = 3.14")

    exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
    exc.value.response["Error"]["Message"].should.match("Unknown type : 'float'")

    with pytest.raises(ClientError) as exc:
        client.get_partitions(**kwargs, Expression="int_col = 2")

    exc.value.response["Error"]["Code"].should.equal("InvalidStateException")
    exc.value.response["Error"]["Message"].should.match('"int" is not an integer')

    with pytest.raises(ClientError) as exc:
        client.get_partitions(**kwargs, Expression="unknown_col = 'test'")

    exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
    exc.value.response["Error"]["Message"].should.match("Unknown column 'unknown_col'")

    with pytest.raises(ClientError) as exc:
        client.get_partitions(
            **kwargs, Expression="string_col IS test' AND not parsable"
        )

    exc.value.response["Error"]["Code"].should.equal("InvalidInputException")
    exc.value.response["Error"]["Message"].should.match("Unsupported expression")
