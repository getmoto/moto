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
        desired_hash_key.should.equal(eav[":id"])
        comparison.should.equal(None)
        range_values.should.equal([])

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
        exc.value.message.should.equal(
            "Query condition missed key schema element: job_id"
        )

    def test_unknown_hash_value(self):
        # TODO: is this correct? I'd assume that this should throw an error instead
        # Revisit after test in exceptions.py passes
        kce = "job_id = :unknown"
        eav = {":id": {"S": "asdasdasd"}}
        desired_hash_key, comparison, range_values = parse_expression(
            expression_attribute_values=eav,
            key_condition_expression=kce,
            schema=self.schema,
            expression_attribute_names=dict(),
        )
        desired_hash_key.should.equal({"S": ":unknown"})
        comparison.should.equal(None)
        range_values.should.equal([])


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
        exc.value.message.should.equal(
            "Query condition missed key schema element: job_id"
        )

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
        exc.value.message.should.equal(
            "Query condition missed key schema element: start_date"
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
        desired_hash_key.should.equal("pk")
        comparison.should.equal("BEGINS_WITH")
        range_values.should.equal(["19"])

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
        exc.value.message.should.equal(
            f"Invalid KeyConditionExpression: Invalid function name; function: {fn}"
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
        desired_hash_key.should.equal("pk")
        comparison.should.equal("BETWEEN")
        range_values.should.equal(["19", "21"])

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
        desired_hash_key.should.equal("pk")
        comparison.should.equal(operator.strip())
        range_values.should.equal(["19"])

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
        desired_hash_key.should.equal("pk")


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
        desired_hash_key.should.equal(eav[":id"])
        comparison.should.equal(None)
        range_values.should.equal([])
