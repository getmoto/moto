from moto.core.exceptions import JsonRESTError


class GlueClientError(JsonRESTError):
    code = 400


class AlreadyExistsException(GlueClientError):
    def __init__(self, typ):
        super().__init__("AlreadyExistsException", "%s already exists." % (typ))


class DatabaseAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super().__init__("Database")


class TableAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super().__init__("Table")


class PartitionAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super().__init__("Partition")


class CrawlerAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super().__init__("Crawler")


class EntityNotFoundException(GlueClientError):
    def __init__(self, msg):
        super().__init__("EntityNotFoundException", msg)


class DatabaseNotFoundException(EntityNotFoundException):
    def __init__(self, db):
        super().__init__("Database %s not found." % db)


class TableNotFoundException(EntityNotFoundException):
    def __init__(self, tbl):
        super().__init__("Table %s not found." % tbl)


class PartitionNotFoundException(EntityNotFoundException):
    def __init__(self):
        super().__init__("Cannot find partition.")


class CrawlerNotFoundException(EntityNotFoundException):
    def __init__(self, crawler):
        super().__init__("Crawler %s not found." % crawler)


class VersionNotFoundException(EntityNotFoundException):
    def __init__(self):
        super().__init__("Version not found.")


class CrawlerRunningException(GlueClientError):
    def __init__(self, msg):
        super().__init__("CrawlerRunningException", msg)


class CrawlerNotRunningException(GlueClientError):
    def __init__(self, msg):
        super().__init__("CrawlerNotRunningException", msg)
