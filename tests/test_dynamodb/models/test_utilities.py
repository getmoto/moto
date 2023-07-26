from moto.dynamodb.models.utilities import find_nested_key


class TestFindDictionaryKeys:
    def setup_method(self):
        self.item = {
            "simplestring": "val",
            "nesteddict": {
                "level21": {"level3.1": "val", "level3.2": "val"},
                "level22": {"level3.1": "val", "level3.2": "val"},
                "nestedlist": [
                    {"ll21": {"ll3.1": "val", "ll3.2": "val"}},
                    {"ll22": {"ll3.1": "val", "ll3.2": "val"}},
                ],
            },
            "rootlist": [
                {"ll21": {"ll3.1": "val", "ll3.2": "val"}},
                {"ll22": {"ll3.1": "val", "ll3.2": "val"}},
            ],
        }

    def test_find_nothing(self):
        assert find_nested_key([""], self.item) == {}

    def test_find_unknown_key(self):
        assert find_nested_key(["unknown"], self.item) == {}

    def test_project_single_key_string(self):
        assert find_nested_key(["simplestring"], self.item) == {"simplestring": "val"}

    def test_project_single_key_dict(self):
        assert find_nested_key(["nesteddict"], self.item) == {
            "nesteddict": {
                "level21": {"level3.1": "val", "level3.2": "val"},
                "level22": {"level3.1": "val", "level3.2": "val"},
                "nestedlist": [
                    {"ll21": {"ll3.1": "val", "ll3.2": "val"}},
                    {"ll22": {"ll3.1": "val", "ll3.2": "val"}},
                ],
            }
        }

    def test_project_nested_key(self):
        assert find_nested_key(["nesteddict", "level21"], self.item) == {
            "nesteddict": {"level21": {"level3.1": "val", "level3.2": "val"}}
        }

    def test_project_multi_level_nested_key(self):
        assert find_nested_key(["nesteddict", "level21", "level3.2"], self.item) == {
            "nesteddict": {"level21": {"level3.2": "val"}}
        }

    def test_project_nested_key__partial_fix(self):
        assert find_nested_key(["nesteddict", "levelunknown"], self.item) == {}

    def test_project_nested_key__partial_fix2(self):
        assert find_nested_key(["nesteddict", "unknown", "unknown2"], self.item) == {}

    def test_list_index(self):
        assert find_nested_key(["rootlist[0]"], self.item) == {
            "rootlist": [{"ll21": {"ll3.1": "val", "ll3.2": "val"}}]
        }

    def test_nested_list_index(self):
        assert find_nested_key(["nesteddict", "nestedlist[1]"], self.item) == {
            "nesteddict": {"nestedlist": [{"ll22": {"ll3.1": "val", "ll3.2": "val"}}]}
        }

    def test_nested_obj_in_list(self):
        assert find_nested_key(
            ["nesteddict", "nestedlist[1]", "ll22", "ll3.1"], self.item
        ) == {"nesteddict": {"nestedlist": [{"ll22": {"ll3.1": "val"}}]}}

    def test_list_unknown_indexes(self):
        assert find_nested_key(["nesteddict", "nestedlist[25]"], self.item) == {}
