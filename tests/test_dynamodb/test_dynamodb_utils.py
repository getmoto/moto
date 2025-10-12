from moto.dynamodb.utils import find_duplicates, find_path_overlaps


def test_find_duplicates_simple_duplicate():
    assert find_duplicates(["a", "a"]) == ["a", "a"]


def test_find_duplicates_no_duplicates():
    assert find_duplicates(["a", "b"]) == []


def test_find_duplicates_out_of_order():
    assert find_duplicates(["b", "a", "b"]) == ["b", "b"]


def test_find_path_overlaps_simple_overlap():
    assert find_path_overlaps(["a", "a.b"]) == ["a", "a.b"]


def test_find_path_overlaps_no_overlap():
    assert find_path_overlaps(["a", "b"]) == []


def test_find_path_overlaps_reverse_overlap():
    assert find_path_overlaps(["a.b", "a"]) == ["a.b", "a"]
