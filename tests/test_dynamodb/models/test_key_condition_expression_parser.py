import pytest
from moto.dynamodb.exceptions import DynamodbException
from moto.dynamodb.parsing.key_condition_expression import parse_expression


class TestHashKey:
    schema = [{"AttributeName": "job_id", "KeyType": "HASH"}]

    @pytest.mark.parametrize("expression", ["job_id = :id", "job_id = :id "])
    def test_hash_key_only(self, expression):
        eav = {":id": {"S": "asdasdasd"}}
        desired_hash_key, comparison, range_values = parse_expression(
            expression_attribute_values=eav,
            key_condition_expression=expression,
            schema=self.schema,
            expression_attribute_names=dict(),
        )
        assert desired_hash_key == eav[":id"]
        assert comparison is None
        assert range_values == []

    def test_unknown_hash_key(self):
        kce = "wrongName = :id"
        eav = {":id": "pk"}
        with pytest.raises(DynamodbException) as exc:
            parse_expression(
                expression_attribute_values=eav,
                key_condition_expression=kce,
                schema=self.schema,
                expression_attribute_names=dict(),
            )
        assert exc.value.message == "Query condition missed key schema element: job_id"


class TestHashAndRangeKey:
    schema = [
        {"AttributeName": "job_id", "KeyType": "HASH"},
        {"AttributeName": "start_date", "KeyType": "RANGE"},
    ]

    def test_unknown_hash_key(self):
        kce = "wrongName = :id AND start_date = :sk"
        eav = {":id": "pk", ":sk": "sk"}
        with pytest.raises(DynamodbException) as exc:
            parse_expression(
                expression_attribute_values=eav,
                key_condition_expression=kce,
                schema=self.schema,
                expression_attribute_names=dict(),
            )
        assert exc.value.message == "Query condition missed key schema element: job_id"

    @pytest.mark.parametrize(
        "expr",
        [
            "job_id = :id AND wrongName = :sk",
            "job_id = :id AND begins_with ( wrongName , :sk )",
            "job_id = :id AND wrongName BETWEEN :sk and :sk2",
        ],
    )
    def test_unknown_range_key(self, expr):
        eav = {":id": "pk", ":sk": "sk", ":sk2": "sk"}
        with pytest.raises(DynamodbException) as exc:
            parse_expression(
                expression_attribute_values=eav,
                key_condition_expression=expr,
                schema=self.schema,
                expression_attribute_names=dict(),
            )
        assert (
            exc.value.message == "Query condition missed key schema element: start_date"
        )

    @pytest.mark.parametrize(
        "expr",
        [
            "job_id = :id AND begins_with(start_date,:sk)",
            "job_id = :id AND begins_with(start_date, :sk)",
            "job_id = :id AND begins_with( start_date,:sk)",
            "job_id = :id AND begins_with( start_date, :sk)",
            "job_id = :id AND begins_with ( start_date, :sk ) ",
        ],
    )
    def test_begin_with(self, expr):
        eav = {":id": "pk", ":sk": "19"}
        desired_hash_key, comparison, range_values = parse_expression(
            expression_attribute_values=eav,
            key_condition_expression=expr,
            schema=self.schema,
            expression_attribute_names=dict(),
        )
        assert desired_hash_key == "pk"
        assert comparison == "BEGINS_WITH"
        assert range_values == ["19"]

    @pytest.mark.parametrize("fn", ["Begins_with", "Begins_With", "BEGINS_WITH"])
    def test_begin_with__wrong_case(self, fn):
        eav = {":id": "pk", ":sk": "19"}
        with pytest.raises(DynamodbException) as exc:
            parse_expression(
                expression_attribute_values=eav,
                key_condition_expression=f"job_id = :id AND {fn}(start_date,:sk)",
                schema=self.schema,
                expression_attribute_names=dict(),
            )
        assert (
            exc.value.message
            == f"Invalid KeyConditionExpression: Invalid function name; function: {fn}"
        )

    @pytest.mark.parametrize(
        "expr",
        [
            "job_id = :id and start_date BETWEEN :sk1 AND :sk2",
            "job_id = :id and start_date BETWEEN :sk1 and :sk2",
            "job_id = :id and start_date between :sk1 and :sk2 ",
        ],
    )
    def test_in_between(self, expr):
        eav = {":id": "pk", ":sk1": "19", ":sk2": "21"}
        desired_hash_key, comparison, range_values = parse_expression(
            expression_attribute_values=eav,
            key_condition_expression=expr,
            schema=self.schema,
            expression_attribute_names=dict(),
        )
        assert desired_hash_key == "pk"
        assert comparison == "BETWEEN"
        assert range_values == ["19", "21"]

    @pytest.mark.parametrize("operator", [" < ", " <=", "= ", ">", ">="])
    def test_numeric_comparisons(self, operator):
        eav = {":id": "pk", ":sk": "19"}
        expr = f"job_id = :id and start_date{operator}:sk"
        desired_hash_key, comparison, range_values = parse_expression(
            expression_attribute_values=eav,
            key_condition_expression=expr,
            schema=self.schema,
            expression_attribute_names=dict(),
        )
        assert desired_hash_key == "pk"
        assert comparison == operator.strip()
        assert range_values == ["19"]

    @pytest.mark.parametrize(
        "expr",
        [
            "start_date >= :sk and job_id = :id",
            "start_date>:sk and job_id=:id",
            "start_date=:sk and job_id = :id",
            "begins_with(start_date,:sk) and job_id = :id",
        ],
    )
    def test_reverse_keys(self, expr):
        eav = {":id": "pk", ":sk1": "19", ":sk2": "21"}
        desired_hash_key, comparison, range_values = parse_expression(
            expression_attribute_values=eav,
            key_condition_expression=expr,
            schema=self.schema,
            expression_attribute_names=dict(),
        )
        assert desired_hash_key == "pk"

    @pytest.mark.parametrize(
        "expr",
        [
            "(job_id = :id) and start_date = :sk",
            "job_id = :id and (start_date = :sk)",
            "(job_id = :id) and (start_date = :sk)",
        ],
    )
    def test_brackets(self, expr):
        desired_hash_key, comparison, range_values = parse_expression(
            expression_attribute_values={":id": "pk", ":sk": "19"},
            key_condition_expression=expr,
            schema=self.schema,
            expression_attribute_names=dict(),
        )
        assert desired_hash_key == "pk"


class TestNamesAndValues:
    schema = [{"AttributeName": "job_id", "KeyType": "HASH"}]

    def test_names_and_values(self):
        kce = ":j = :id"
        ean = {":j": "job_id"}
        eav = {":id": {"S": "asdasdasd"}}
        desired_hash_key, comparison, range_values = parse_expression(
            expression_attribute_values=eav,
            key_condition_expression=kce,
            schema=self.schema,
            expression_attribute_names=ean,
        )
        assert desired_hash_key == eav[":id"]
        assert comparison is None
        assert range_values == []
