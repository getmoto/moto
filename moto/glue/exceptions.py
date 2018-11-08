from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class GlueClientError(JsonRESTError):
    code = 400


class AlreadyExistsException(GlueClientError):
    def __init__(self, typ):
        super(GlueClientError, self).__init__(
            'AlreadyExistsException',
            '%s already exists.' % (typ),
        )


class DatabaseAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super(DatabaseAlreadyExistsException, self).__init__('Database')


class TableAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super(TableAlreadyExistsException, self).__init__('Table')


class PartitionAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super(PartitionAlreadyExistsException, self).__init__('Partition')


class EntityNotFoundException(GlueClientError):
    def __init__(self, msg):
        super(GlueClientError, self).__init__(
            'EntityNotFoundException',
            msg,
        )


class DatabaseNotFoundException(EntityNotFoundException):
    def __init__(self, db):
        super(DatabaseNotFoundException, self).__init__(
            'Database %s not found.' % db,
        )


class TableNotFoundException(EntityNotFoundException):
    def __init__(self, tbl):
        super(TableNotFoundException, self).__init__(
            'Table %s not found.' % tbl,
        )


class PartitionNotFoundException(EntityNotFoundException):
    def __init__(self):
        super(PartitionNotFoundException, self).__init__("Cannot find partition.")


class VersionNotFoundException(EntityNotFoundException):
    def __init__(self):
        super(VersionNotFoundException, self).__init__("Version not found.")
