from tests.markers import requires_docker


EXTRA_MARKERS_OTHER = {
    "lambda": (requires_docker,),
}


def pytest_collection_modifyitems(items):  # noqa: SC200
    for item in items:
        for key, markers in EXTRA_MARKERS_OTHER.items():
            if key in item.nodeid:  # noqa: SC200
                for marker in markers:
                    item.add_marker(marker)
