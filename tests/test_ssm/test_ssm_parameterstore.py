import sure  # noqa # pylint: disable=unused-import

from moto.ssm.models import ParameterDict


def test_simple_setget():
    store = ParameterDict("accnt", "region")
    store["/a/b/c"] = "some object"

    store.get("/a/b/c").should.equal("some object")


def test_get_none():
    store = ParameterDict("accnt", "region")

    store.get(None).should.equal(None)


def test_get_aws_param():
    store = ParameterDict("accnt", "region")

    p = store["/aws/service/global-infrastructure/regions/us-west-1/longName"]
    p.should.have.length_of(1)
    p[0].value.should.equal("US West (N. California)")


def test_iter():
    store = ParameterDict("accnt", "region")
    store["/a/b/c"] = "some object"

    "/a/b/c".should.be.within(store)
    "/a/b/d".shouldnt.be.within(store)


def test_iter_none():
    store = ParameterDict("accnt", "region")
    None.shouldnt.be.within(store)


def test_iter_aws():
    store = ParameterDict("accnt", "region")

    "/aws/service/global-infrastructure/regions/us-west-1/longName".should.be.within(
        store
    )


def test_get_key_beginning_with():
    store = ParameterDict("accnt", "region")
    store["/a/b/c"] = "some object"
    store["/b/c/d"] = "some other object"
    store["/a/c/d"] = "some third object"

    begins_with_ab = list(store.get_keys_beginning_with("/a/b", recursive=False))
    begins_with_ab.should.equal(["/a/b/c"])

    begins_with_a = list(store.get_keys_beginning_with("/a", recursive=False))
    begins_with_a.should.equal([])

    begins_with_a_recursive = list(store.get_keys_beginning_with("/a", recursive=True))
    set(begins_with_a_recursive).should.equal({"/a/b/c", "/a/c/d"})


def test_get_key_beginning_with_aws():
    """
    ParameterDict should load the default parameters if we request a key starting with '/aws'
    :return:
    """
    store = ParameterDict("accnt", "region")

    uswest_params = set(
        store.get_keys_beginning_with(
            "/aws/service/global-infrastructure/regions/us-west-1", recursive=False
        )
    )
    uswest_params.should.equal(
        {
            "/aws/service/global-infrastructure/regions/us-west-1",
            "/aws/service/global-infrastructure/regions/us-west-1/domain",
            "/aws/service/global-infrastructure/regions/us-west-1/geolocationCountry",
            "/aws/service/global-infrastructure/regions/us-west-1/geolocationRegion",
            "/aws/service/global-infrastructure/regions/us-west-1/longName",
            "/aws/service/global-infrastructure/regions/us-west-1/partition",
        }
    )


def test_ssm_parameter_from_unknown_region():
    store = ParameterDict("accnt", "region")
    list(
        store.get_keys_beginning_with(
            "/aws/service/ami-amazon-linux-latest", recursive=False
        )
    ).should.equal([])
