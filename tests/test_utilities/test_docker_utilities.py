import sure
import pytest

from moto.utilities.docker_utilities import parse_image_name


@pytest.mark.parametrize("image_name,expected", [
    ("python", ("docker.io/library/python", "latest")),
    ("python:3.9", ("docker.io/library/python", "3.9")),
    ("lambci/lambda:python2.7", ("docker.io/lambci/lambda", "python2.7")),
    ("gcr.io/google.com/cloudsdktool/cloud-sdk", ("gcr.io/google.com/cloudsdktool/cloud-sdk", "latest")),
])
def test_parse_image_name(image_name, expected):
    expected.should.be.equal(parse_image_name(image_name))
