import io
import stat
import tarfile
import zipfile

from moto.awslambda.models import zip2tar


def test_zip2tar_preserves_executable_permissions():
    """
    Test that zip2tar preserves Unix file permissions from ZIP external attributes.
    When a ZIP contains files with executable permissions (e.g. 0o755), the resulting
    tar should retain those permissions rather than using the default 0o644.
    """
    # Build a ZIP in memory with explicit Unix permissions
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        # Executable script (rwxr-xr-x)
        info_exec = zipfile.ZipInfo("bootstrap")
        info_exec.external_attr = 0o100755 << 16  # Unix file type + mode
        zf.writestr(info_exec, "#!/bin/bash\necho hello\n")

        # Regular file (rw-r--r--)
        info_regular = zipfile.ZipInfo("config.json")
        info_regular.external_attr = 0o100644 << 16
        zf.writestr(info_regular, '{"key": "value"}\n')

        # Another executable (rwxr-xr-x)
        info_exec2 = zipfile.ZipInfo("bin/app")
        info_exec2.external_attr = 0o100755 << 16
        zf.writestr(info_exec2, "#!/usr/bin/env python3\nprint('hi')\n")

        # File with no Unix attrs (external_attr == 0, e.g. created on Windows)
        info_no_attr = zipfile.ZipInfo("README.md")
        info_no_attr.external_attr = 0
        zf.writestr(info_no_attr, "# README\n")

    zip_bytes = zip_buffer.getvalue()

    # Convert to tar using the moto function
    tar_stream = zip2tar(zip_bytes)

    # Read the tar and verify permissions
    with tarfile.open(fileobj=tar_stream) as tf:
        members = {m.name: m for m in tf.getmembers()}

        assert "bootstrap" in members
        assert stat.S_ISREG(members["bootstrap"].mode)
        assert members["bootstrap"].mode & 0o777 == 0o755, (
            f"Expected 0o755, got {oct(members['bootstrap'].mode & 0o777)}"
        )

        assert "config.json" in members
        assert stat.S_ISREG(members["config.json"].mode)
        assert members["config.json"].mode & 0o777 == 0o644, (
            f"Expected 0o644, got {oct(members['config.json'].mode & 0o777)}"
        )

        assert "bin/app" in members
        assert stat.S_ISREG(members["bin/app"].mode)
        assert members["bin/app"].mode & 0o777 == 0o755, (
            f"Expected 0o755, got {oct(members['bin/app'].mode & 0o777)}"
        )

        assert "README.md" in members
        # When external_attr is 0 (no Unix attrs), the default TarInfo mode (0o644) is used
        assert stat.S_ISREG(members["README.md"].mode)
