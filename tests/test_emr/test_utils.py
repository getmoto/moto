import pytest

from moto.emr.utils import ReleaseLabel


def test_invalid_release_labels_raise_exception():
    invalid_releases = [
        "",
        "0",
        "1.0",
        "emr-2.0",
    ]
    for invalid_release in invalid_releases:
        with pytest.raises(ValueError):
            ReleaseLabel(invalid_release)


def test_release_label_comparisons():
    assert str(ReleaseLabel("emr-5.1.2")) == "emr-5.1.2"

    assert ReleaseLabel("emr-5.0.0") != ReleaseLabel("emr-5.0.1")
    assert ReleaseLabel("emr-5.0.0") == ReleaseLabel("emr-5.0.0")

    assert ReleaseLabel("emr-5.31.0") > ReleaseLabel("emr-5.7.0")
    assert ReleaseLabel("emr-6.0.0") > ReleaseLabel("emr-5.7.0")

    assert ReleaseLabel("emr-5.7.0") < ReleaseLabel("emr-5.10.0")
    assert ReleaseLabel("emr-5.10.0") < ReleaseLabel("emr-5.10.1")

    assert ReleaseLabel("emr-5.60.0") >= ReleaseLabel("emr-5.7.0")
    assert ReleaseLabel("emr-6.0.0") >= ReleaseLabel("emr-6.0.0")

    assert ReleaseLabel("emr-5.7.0") <= ReleaseLabel("emr-5.17.0")
    assert ReleaseLabel("emr-5.7.0") <= ReleaseLabel("emr-5.7.0")

    releases_unsorted = [
        ReleaseLabel("emr-5.60.2"),
        ReleaseLabel("emr-4.0.1"),
        ReleaseLabel("emr-4.0.0"),
        ReleaseLabel("emr-5.7.3"),
    ]
    releases_sorted = [str(label) for label in sorted(releases_unsorted)]
    expected = [
        "emr-4.0.0",
        "emr-4.0.1",
        "emr-5.7.3",
        "emr-5.60.2",
    ]
    assert releases_sorted == expected
