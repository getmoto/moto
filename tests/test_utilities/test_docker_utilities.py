import sure  # noqa # pylint: disable=unused-import
import pytest

from moto.utilities.docker_utilities import parse_image_ref


@pytest.mark.parametrize(
    "image_name,expected",
    [
        ("python", ("docker.io/library/python", "latest")),
        ("python:3.9", ("docker.io/library/python", "3.9")),
        ("docker.io/python", ("docker.io/library/python", "latest")),
        ("localhost/foobar", ("localhost/foobar", "latest")),
        ("lambci/lambda:python2.7", ("docker.io/lambci/lambda", "python2.7")),
        (
            "gcr.io/google.com/cloudsdktool/cloud-sdk",
            ("gcr.io/google.com/cloudsdktool/cloud-sdk", "latest"),
        ),
    ],
)
def test_parse_image_ref(image_name, expected):
    expected.should.be.equal(parse_image_ref(image_name))


def test_parse_image_ref_default_container_registry(monkeypatch):
    import moto.settings

    monkeypatch.setattr(moto.settings, "DEFAULT_CONTAINER_REGISTRY", "quay.io")
    ("quay.io/centos/centos", "latest").should.be.equal(
        parse_image_ref("centos/centos")
    )
