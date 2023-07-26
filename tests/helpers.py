from uuid import UUID

from sure import assertion


@assertion
def match_uuid4(context):
    try:
        uuid_obj = UUID(context.obj, version=4)
    except ValueError:
        return False
    return str(uuid_obj) == context.obj
