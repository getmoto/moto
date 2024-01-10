from moto.lakeformation.models import Permission


def test_permission_equals():
    permission_1 = Permission(
        principal={"test": "test"},
        resource={"test": "test"},
        permissions=[],
        permissions_with_grant_options=[],
    )
    permission_2 = Permission(
        principal={"test": "test"},
        resource={"test": "test"},
        permissions=[],
        permissions_with_grant_options=[],
    )
    assert permission_1 == permission_2


def test_permission_not_equals():
    permission_1 = Permission(
        principal={"test": "test"},
        resource={"test": "test"},
        permissions=[],
        permissions_with_grant_options=[],
    )
    permission_2 = Permission(
        principal={"test": "test_2"},
        resource={"test": "test_2"},
        permissions=[],
        permissions_with_grant_options=[],
    )
    permission_3 = Permission(
        principal={"test": "test"},
        resource={"test": "test"},
        permissions=["new_permission"],
        permissions_with_grant_options=[],
    )
    assert permission_1 != permission_2
    assert permission_1 is not None
    assert permission_1 != permission_3
