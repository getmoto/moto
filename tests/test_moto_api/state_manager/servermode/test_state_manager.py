import json
import requests
import sure  # noqa # pylint: disable=unused-import


from moto import settings
from unittest import SkipTest


def test_set_transition():
    if not settings.TEST_SERVER_MODE:
        raise SkipTest("We only want to test ServerMode here")

    post_body = dict(
        model_name="test_model0", transition={"progression": "waiter", "wait_times": 3}
    )
    resp = requests.post(
        "http://localhost:5000/moto-api/state-manager/set-transition",
        data=json.dumps(post_body),
    )
    resp.status_code.should.equal(201)

    resp = requests.get(
        "http://localhost:5000/moto-api/state-manager/get-transition?model_name=test_model0"
    )
    resp.status_code.should.equal(200)
    json.loads(resp.content).should.equal({"progression": "waiter", "wait_times": 3})


def test_unset_transition():
    if not settings.TEST_SERVER_MODE:
        raise SkipTest("We only want to test ServerMode here")

    post_body = dict(
        model_name="test::model1", transition={"progression": "waiter", "wait_times": 3}
    )
    requests.post(
        "http://localhost:5000/moto-api/state-manager/set-transition",
        data=json.dumps(post_body),
    )

    post_body = dict(model_name="test::model1")
    resp = requests.post(
        "http://localhost:5000/moto-api/state-manager/unset-transition",
        data=json.dumps(post_body),
    )

    resp = requests.get(
        "http://localhost:5000/moto-api/state-manager/get-transition?model_name=test::model1"
    )
    resp.status_code.should.equal(200)
    json.loads(resp.content).should.equal({"progression": "immediate"})


def test_get_default_transition():
    if not settings.TEST_SERVER_MODE:
        raise SkipTest("We only want to test ServerMode here")

    resp = requests.get(
        "http://localhost:5000/moto-api/state-manager/get-transition?model_name=unknown"
    )
    resp.status_code.should.equal(200)
    json.loads(resp.content).should.equal({"progression": "immediate"})
