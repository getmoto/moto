from __future__ import unicode_literals

from tempfile import NamedTemporaryFile
import boto.glacier
import sure  # noqa

from moto import mock_glacier_deprecated


@mock_glacier_deprecated
def test_create_and_delete_archive():
    the_file = NamedTemporaryFile(delete=False)
    the_file.write(b"some stuff")
    the_file.close()

    conn = boto.glacier.connect_to_region("us-west-2")
    vault = conn.create_vault("my_vault")

    archive_id = vault.upload_archive(the_file.name)

    vault.delete_archive(archive_id)
