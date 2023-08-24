from moto.dynamodb.models.dynamo_type import DynamoType, Item
from moto.dynamodb.models.dynamo_type import serializer


class TestFindNestedKeys:
    def setup_method(self):
        self.dct = {
            "simplestring": "val",
            "nesteddict": {
                "level21": {"ll31": "val", "ll32": "val"},
                "level22": {"ll31": "val", "ll32": "val"},
                "nestedlist": [
                    {"ll21": {"ll31": "val", "ll32": "val"}},
                    {"ll22": {"ll31": "val", "ll32": "val"}},
                ],
            },
            "rootlist": [
                {"ll21": {"ll31": "val", "ll32": "val"}},
                {"ll22": {"ll31": "val", "ll32": "val"}},
            ],
        }
        x = serializer.serialize(self.dct)["M"]
        self.item = Item(
            hash_key=DynamoType({"pk": {"S": "v"}}), range_key=None, attrs=x
        )

    def _project(self, expression, result):
        x = self.item.project(expression)
        y = Item(
            hash_key=DynamoType({"pk": {"S": "v"}}),
            range_key=None,
            attrs=serializer.serialize(result)["M"],
        )
        assert x == y

    def test_find_nothing(self):
        self._project([[""]], result={})

    def test_find_unknown_key(self):
        self._project([["unknown"]], result={})

    def test_project_single_key_string(self):
        self._project([["simplestring"]], result={"simplestring": "val"})

    def test_project_single_key_dict(self):
        self._project(
            [["nesteddict"]],
            result={
                "nesteddict": {
                    "level21": {"ll31": "val", "ll32": "val"},
                    "level22": {"ll31": "val", "ll32": "val"},
                    "nestedlist": [
                        {"ll21": {"ll31": "val", "ll32": "val"}},
                        {"ll22": {"ll31": "val", "ll32": "val"}},
                    ],
                }
            },
        )

    def test_project_nested_key(self):
        self._project(
            [["nesteddict", "level21"]],
            result={"nesteddict": {"level21": {"ll31": "val", "ll32": "val"}}},
        )

    def test_project_multi_level_nested_key(self):
        self._project(
            [["nesteddict", "level21", "ll32"]],
            result={"nesteddict": {"level21": {"ll32": "val"}}},
        )

    def test_project_nested_key__partial_fix(self):
        self._project([["nesteddict", "levelunknown"]], result={})

    def test_project_nested_key__partial_fix2(self):
        self._project([["nesteddict", "unknown", "unknown2"]], result={})

    def test_list_index(self):
        self._project(
            [["rootlist[0]"]],
            result={"rootlist": [{"ll21": {"ll31": "val", "ll32": "val"}}]},
        )

    def test_nested_list_index(self):
        self._project(
            [["nesteddict", "nestedlist[1]"]],
            result={
                "nesteddict": {"nestedlist": [{"ll22": {"ll31": "val", "ll32": "val"}}]}
            },
        )

    def test_nested_obj_in_list(self):
        self._project(
            [["nesteddict", "nestedlist[1]", "ll22", "ll31"]],
            result={"nesteddict": {"nestedlist": [{"ll22": {"ll31": "val"}}]}},
        )

    def test_list_unknown_indexes(self):
        self._project([["nesteddict", "nestedlist[25]"]], result={})

    def test_multiple_projections(self):
        self._project(
            [["nesteddict", "nestedlist[1]", "ll22"], ["rootlist[0]"]],
            result={
                "nesteddict": {
                    "nestedlist": [{"ll22": {"ll31": "val", "ll32": "val"}}]
                },
                "rootlist": [{"ll21": {"ll31": "val", "ll32": "val"}}],
            },
        )
