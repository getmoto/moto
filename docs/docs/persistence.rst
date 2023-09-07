.. _persistence:

=======================
Persistence
=======================

Moto has the ability to persist your mock AWS resources to a file and restore them. This is most useful if running server mode for a local development environment because it allows you to keep your mock data between restarts. It can also be used during testing.

By default persistence is not enabled, to enable it set the `MOTO_PERSISTENCE_FILEPATH` environment variable to the path of the file you want to use to store the data. If the file does not exist it will be created. The file is managed using [shelve](https://docs.python.org/3/library/shelve.html).
