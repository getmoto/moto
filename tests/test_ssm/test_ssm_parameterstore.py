from moto.ssm.models import ParameterDict


def test_simple_setget():
    store = ParameterDict("accnt", "region")
    store["/a/b/c"] = "some object"

    assert store.get("/a/b/c") == "some object"


def test_get_none():
    store = ParameterDict("accnt", "region")

    assert store.get(None) is None


def test_get_aws_param():
    store = ParameterDict("accnt", "region")

    p = store["/aws/service/global-infrastructure/regions/us-west-1/longName"]
    assert len(p) == 1
    assert p[0].value == "US West (N. California)"


def test_iter():
    store = ParameterDict("accnt", "region")
    store["/a/b/c"] = "some object"

    assert "/a/b/c" in store
    assert "/a/b/d" not in store


def test_iter_none():
    store = ParameterDict("accnt", "region")
    assert None not in store


def test_iter_aws():
    store = ParameterDict("accnt", "region")

    assert "/aws/service/global-infrastructure/regions/us-west-1/longName" in store


def test_get_key_beginning_with():
    store = ParameterDict("accnt", "region")
    store["/a/b/c"] = "some object"
    store["/b/c/d"] = "some other object"
    store["/a/c/d"] = "some third object"

    begins_with_ab = list(store.get_keys_beginning_with("/a/b", recursive=False))
    assert begins_with_ab == ["/a/b/c"]

    begins_with_a = list(store.get_keys_beginning_with("/a", recursive=False))
    assert not begins_with_a

    begins_with_a_recursive = list(store.get_keys_beginning_with("/a", recursive=True))
    assert set(begins_with_a_recursive) == {"/a/b/c", "/a/c/d"}


def test_get_key_beginning_with_aws():
    """Test ParameterDict loads default params for key starting with '/aws'."""
    store = ParameterDict("accnt", "region")

    uswest_params = set(
        store.get_keys_beginning_with(
            "/aws/service/global-infrastructure/regions/us-west-1", recursive=False
        )
    )
    assert uswest_params == {
        "/aws/service/global-infrastructure/regions/us-west-1",
        "/aws/service/global-infrastructure/regions/us-west-1/domain",
        "/aws/service/global-infrastructure/regions/us-west-1/geolocationCountry",
        "/aws/service/global-infrastructure/regions/us-west-1/geolocationRegion",
        "/aws/service/global-infrastructure/regions/us-west-1/longName",
        "/aws/service/global-infrastructure/regions/us-west-1/partition",
    }


def test_ssm_parameter_from_unknown_region():
    store = ParameterDict("accnt", "region")
    assert not list(
        store.get_keys_beginning_with(
            "/aws/service/ami-amazon-linux-latest", recursive=False
        )
    )
