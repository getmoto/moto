from __future__ import unicode_literals

import datetime
import time

from .base import BaseRDSBackend


class LogFileManager(object):
    def __init__(self, engine):
        self.log_files = []
        filename = "error/{}.log".format(engine)
        if engine == "postgres":
            filename = "error/postgresql.log.{}".format(
                datetime.datetime.utcnow().strftime("%Y-%m-%d-%H")
            )
        self.log_files.append(DBLogFile(filename))

    @property
    def files(self):
        return self.log_files


class DBLogFile(object):
    def __init__(self, name):
        self.log_file_name = name
        self.last_written = int(time.time())
        self.size = 123

    @property
    def resource_id(self):
        return "{}-{}-{}".format(self.log_file_name, self.last_written, self.size)


class LogBackend(BaseRDSBackend):
    def __init__(self):
        super(LogBackend, self).__init__()
        self.events = []

    def describe_db_log_files(self, db_instance_identifier):
        database = self.get_db_instance(db_instance_identifier)
        return database.log_file_manager.files
