from moto.swf.utils import decapitalize


def test_decapitalize():
    cases = {"fooBar": "fooBar", "FooBar": "fooBar", "FOO BAR": "fOO BAR"}
    for before, after in cases.items():
        assert decapitalize(before) == after
