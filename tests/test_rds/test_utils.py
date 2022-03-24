import pytest

from moto.rds.utils import (
    FilterDef,
    apply_filter,
    merge_filters,
    validate_filters,
)


class TestFilterValidation(object):
    @classmethod
    def setup_class(cls):
        cls.filter_defs = {
            "not-implemented": FilterDef(None, ""),
            "identifier": FilterDef(["identifier"], "Object Identifiers"),
        }

    def test_unrecognized_filter_raises_exception(self):
        filters = {"invalid-filter-name": ["test-value"]}
        with pytest.raises(KeyError) as ex:
            validate_filters(filters, self.filter_defs)
        assert "Unrecognized filter name: invalid-filter-name" in str(ex)

    def test_empty_filter_values_raises_exception(self):
        filters = {"identifier": []}
        with pytest.raises(ValueError) as ex:
            validate_filters(filters, self.filter_defs)
        assert "Object Identifiers must not be empty" in str(ex)

    def test_unimplemented_filter_raises_exception(self):
        filters = {"not-implemented": ["test-value"]}
        with pytest.raises(NotImplementedError):
            validate_filters(filters, self.filter_defs)


class Resource(object):
    def __init__(self, identifier, **kwargs):
        self.identifier = identifier
        self.__dict__.update(kwargs)


class TestResourceFiltering(object):
    @classmethod
    def setup_class(cls):
        cls.filter_defs = {
            "identifier": FilterDef(["identifier"], "Object Identifiers"),
            "nested-resource": FilterDef(["nested.identifier"], "Nested Identifiers"),
            "common-attr": FilterDef(["common_attr"], ""),
            "multiple-attrs": FilterDef(["common_attr", "uncommon_attr"], ""),
        }
        cls.resources = {
            "identifier-0": Resource("identifier-0"),
            "identifier-1": Resource("identifier-1", common_attr="common"),
            "identifier-2": Resource("identifier-2"),
            "identifier-3": Resource("identifier-3", nested=Resource("nested-id-1")),
            "identifier-4": Resource("identifier-4", common_attr="common"),
            "identifier-5": Resource("identifier-5", uncommon_attr="common"),
        }

    def test_filtering_on_nested_attribute(self):
        filters = {"nested-resource": ["nested-id-1"]}
        filtered_resources = apply_filter(self.resources, filters, self.filter_defs)
        filtered_resources.should.have.length_of(1)
        filtered_resources.should.have.key("identifier-3")

    def test_filtering_on_common_attribute(self):
        filters = {"common-attr": ["common"]}
        filtered_resources = apply_filter(self.resources, filters, self.filter_defs)
        filtered_resources.should.have.length_of(2)
        filtered_resources.should.have.key("identifier-1")
        filtered_resources.should.have.key("identifier-4")

    def test_filtering_on_multiple_attributes(self):
        filters = {"multiple-attrs": ["common"]}
        filtered_resources = apply_filter(self.resources, filters, self.filter_defs)
        filtered_resources.should.have.length_of(3)
        filtered_resources.should.have.key("identifier-1")
        filtered_resources.should.have.key("identifier-4")
        filtered_resources.should.have.key("identifier-5")

    def test_filters_with_multiple_values(self):
        filters = {"identifier": ["identifier-0", "identifier-3", "identifier-5"]}
        filtered_resources = apply_filter(self.resources, filters, self.filter_defs)
        filtered_resources.should.have.length_of(3)
        filtered_resources.should.have.key("identifier-0")
        filtered_resources.should.have.key("identifier-3")
        filtered_resources.should.have.key("identifier-5")

    def test_multiple_filters(self):
        filters = {
            "identifier": ["identifier-1", "identifier-3", "identifier-5"],
            "common-attr": ["common"],
            "multiple-attrs": ["common"],
        }
        filtered_resources = apply_filter(self.resources, filters, self.filter_defs)
        filtered_resources.should.have.length_of(1)
        filtered_resources.should.have.key("identifier-1")


class TestMergingFilters(object):
    def test_when_filters_to_update_is_none(self):
        filters_to_update = {"filter-name": ["value1"]}
        merged = merge_filters(filters_to_update, None)
        assert merged == filters_to_update

    def test_when_filters_to_merge_is_none(self):
        filters_to_merge = {"filter-name": ["value1"]}
        merged = merge_filters(None, filters_to_merge)
        assert merged == filters_to_merge

    def test_when_both_filters_are_none(self):
        merged = merge_filters(None, None)
        assert merged == {}

    def test_values_are_merged(self):
        filters_to_update = {"filter-name": ["value1"]}
        filters_to_merge = {"filter-name": ["value2"]}
        merged = merge_filters(filters_to_update, filters_to_merge)
        assert merged == {"filter-name": ["value1", "value2"]}

    def test_complex_merge(self):
        filters_to_update = {
            "filter-name-1": ["value1"],
            "filter-name-2": ["value1", "value2"],
            "filter-name-3": ["value1"],
        }
        filters_to_merge = {
            "filter-name-1": ["value2"],
            "filter-name-3": ["value2"],
            "filter-name-4": ["value1", "value2"],
        }
        merged = merge_filters(filters_to_update, filters_to_merge)
        assert len(merged.keys()) == 4
        for key in merged.keys():
            assert merged[key] == ["value1", "value2"]
