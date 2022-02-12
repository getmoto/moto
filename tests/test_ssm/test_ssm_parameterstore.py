import sure  # noqa # pylint: disable=unused-import

from moto.ssm.models import ParameterDict


def test_simple_setget():
    store = ParameterDict(list)
    store["/a/b/c"] = "some object"

    store.get("/a/b/c").should.equal("some object")


def test_get_none():
    store = ParameterDict(list)

    store.get(None).should.equal(None)


def test_get_aws_param():
    store = ParameterDict(list)

    p = store["/aws/service/global-infrastructure/regions/us-west-1/longName"]
    p.should.have.length_of(1)
    p[0].value.should.equal("US West (N. California)")


def test_iter():
    store = ParameterDict(list)
    store["/a/b/c"] = "some object"

    "/a/b/c".should.be.within(store)
    "/a/b/d".shouldnt.be.within(store)


def test_iter_none():
    store = ParameterDict(list)
    None.shouldnt.be.within(store)


def test_iter_aws():
    store = ParameterDict(list)

    "/aws/service/global-infrastructure/regions/us-west-1/longName".should.be.within(
        store
    )


def test_get_key_beginning_with():
    store = ParameterDict(list)
    store["/a/b/c"] = "some object"
    store["/b/c/d"] = "some other object"
    store["/a/c/d"] = "some third object"

    l = list(store.get_keys_beginning_with("/a/b", recursive=False))
    l.should.equal(["/a/b/c"])

    l = list(store.get_keys_beginning_with("/a", recursive=False))
    l.should.equal([])

    l = list(store.get_keys_beginning_with("/a", recursive=True))
    set(l).should.equal({"/a/b/c", "/a/c/d"})


def test_get_key_beginning_with_aws():
    """
    ParameterDict should load the default parameters if we request a key starting with '/aws'
    :return:
    """
    store = ParameterDict(list)

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
