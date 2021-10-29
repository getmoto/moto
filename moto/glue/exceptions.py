from moto.core.exceptions import JsonRESTError


class GlueClientError(JsonRESTError):
    code = 400


class AlreadyExistsException(GlueClientError):
    def __init__(self, typ):
        super(GlueClientError, self).__init__(
            "AlreadyExistsException", "%s already exists." % (typ)
        )


class DatabaseAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super(DatabaseAlreadyExistsException, self).__init__("Database")


class TableAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super(TableAlreadyExistsException, self).__init__("Table")


class PartitionAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super(PartitionAlreadyExistsException, self).__init__("Partition")


class CrawlerAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super(CrawlerAlreadyExistsException, self).__init__("Crawler")


class EntityNotFoundException(GlueClientError):
    def __init__(self, msg):
        super(GlueClientError, self).__init__("EntityNotFoundException", msg)


class DatabaseNotFoundException(EntityNotFoundException):
    def __init__(self, db):
        super(DatabaseNotFoundException, self).__init__("Database %s not found." % db)


class TableNotFoundException(EntityNotFoundException):
    def __init__(self, tbl):
        super(TableNotFoundException, self).__init__("Table %s not found." % tbl)


class PartitionNotFoundException(EntityNotFoundException):
    def __init__(self):
        super(PartitionNotFoundException, self).__init__("Cannot find partition.")


class CrawlerNotFoundException(EntityNotFoundException):
    def __init__(self, crawler):
        super(CrawlerNotFoundException, self).__init__(
            "Crawler %s not found." % crawler
        )


class VersionNotFoundException(EntityNotFoundException):
    def __init__(self):
        super(VersionNotFoundException, self).__init__("Version not found.")


class CrawlerRunningException(GlueClientError):
    def __init__(self, msg):
        super(CrawlerRunningException, self).__init__("CrawlerRunningException", msg)


class CrawlerNotRunningException(GlueClientError):
    def __init__(self, msg):
        super(CrawlerNotRunningException, self).__init__(
            "CrawlerNotRunningException", msg
        )
