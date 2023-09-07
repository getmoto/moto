import boto3
import os
import shelve
import sure  # noqa # pylint: disable=unused-import
from tempfile import NamedTemporaryFile
from typing import Any

import moto.settings
from moto import mock_s3

"""
Test optional persistence behavior
"""

@mock_s3
def create_and_list(bucket_name: str):
    """
    This is declared as a function with the decorator to force another instance
    of the backend to be created. This allows tests to create multiple backend
    instances with and without persistence.
    """
    client = boto3.client("s3")
    client.create_bucket(Bucket=bucket_name)
    return client.list_buckets()["Buckets"]


def test_persist_disabled():
    filepath: Any = moto.settings.PERSISTENCE_FILEPATH
    filepath.should.be.none
    create_and_list("mybucket")
    buckets = create_and_list("yourbucket")

    buckets.should.have.length_of(1)


def test_persistence_bucket_creation(monkeypatch):
    with NamedTemporaryFile() as persist:
        os.remove(persist.name)
        monkeypatch.setattr(moto.settings, "PERSISTENCE_FILEPATH", persist.name)

        create_and_list("mybucket")
        buckets = create_and_list("yourbucket")

        buckets.should.have.length_of(2)

def test_persistence_disabling(monkeypatch):
    with NamedTemporaryFile() as persist:
        os.remove(persist.name)
        monkeypatch.setattr(moto.settings, "PERSISTENCE_FILEPATH", persist.name)

        create_and_list("mybucket")
        monkeypatch.setattr(moto.settings, "PERSISTENCE_FILEPATH", None)
        buckets = create_and_list("yourbucket")

        buckets.should.have.length_of(1)

def test_persistence_removal(monkeypatch):
    with NamedTemporaryFile() as persist:
        os.remove(persist.name)
        monkeypatch.setattr(moto.settings, "PERSISTENCE_FILEPATH", persist.name)

        create_and_list("mybucket")
        os.remove(persist.name)
        buckets = create_and_list("yourbucket")

        buckets.should.have.length_of(1)

def test_persistence_file_internals(monkeypatch):
    with NamedTemporaryFile() as persist:
        os.remove(persist.name)
        monkeypatch.setattr(moto.settings, "PERSISTENCE_FILEPATH", persist.name)

        create_and_list("mybucket")

        with shelve.open(persist.name) as db:
            db['S3Backend']['buckets'].keys().should.have.length_of(1)
