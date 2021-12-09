"""
Adapted from https://github.com/pygame/pygameweb/blob/master/pygameweb/builds/update_version_from_git.py

For updating the version from git.
__init__.py contains a __version__ field.
Update that.
If the user supplies "patch" as a CLi argument, we want to bump the existing patch version
If the user supplied the full version as a CLI argument, we want to use that version.
Otherwise,
If we are on master, we want to update the version as a pre-release.
git describe --tags
With these:
    __init__.py
        __version__= '0.0.2'
    git describe --tags
        0.0.1-22-g729a5ae
We want this:
    __init__.py
        __version__= '0.0.2.dev22.g729a5ae'
Get the branch/tag name with this.
    git symbolic-ref -q --short HEAD || git describe --tags --exact-match
"""

import io
import os
import re
import subprocess
import sys
from packaging.version import Version


def migrate_source_attribute(attr, to_this, target_file, regex):
    """Updates __magic__ attributes in the source file"""
    change_this = re.compile(regex, re.S)
    new_file = []
    found = False

    with open(target_file, "r") as fp:
        lines = fp.readlines()

    for line in lines:
        if line.startswith(attr):
            found = True
            line = re.sub(change_this, to_this, line)
        new_file.append(line)

    if found:
        with open(target_file, "w") as fp:
            fp.writelines(new_file)


def migrate_version(target_file, new_version):
    """Updates __version__ in the source file"""
    regex = r"['\"](.*)['\"]"
    migrate_source_attribute(
        "__version__",
        '"{new_version}"'.format(new_version=new_version),
        target_file,
        regex,
    )


def is_master_branch():
    cmd = "git rev-parse --abbrev-ref HEAD"
    tag_branch = subprocess.check_output(cmd, shell=True)
    return tag_branch in [b"master\n"]


def get_git_version_info():
    cmd = "git describe --tags"
    ver_str = subprocess.check_output(cmd, shell=True)
    ver, commits_since, githash = ver_str.decode().strip().split("-")
    return Version(ver), int(commits_since), githash


def prerelease_version():
    """return what the prerelease version should be.
    https://packaging.python.org/tutorials/distributing-packages/#pre-release-versioning
    0.0.2.dev22
    """
    ver, commits_since, githash = get_git_version_info()
    initpy_ver = get_version()

    assert (
        initpy_ver > ver
    ), "the moto/__init__.py version should be newer than the last tagged release."
    return "{}.{}.{}.dev{}".format(
        initpy_ver.major, initpy_ver.minor, initpy_ver.micro, commits_since
    )


def read(*parts):
    """Reads in file from *parts."""
    try:
        return io.open(os.path.join(*parts), "r", encoding="utf-8").read()
    except IOError:
        return ""


def get_version():
    """Returns version from moto/__init__.py"""
    version_file = read("moto", "__init__.py")
    version_match = re.search(
        r'^__version__ = [\'"]([^\'"]*)[\'"]', version_file, re.MULTILINE
    )
    if not version_match:
        raise RuntimeError("Unable to find version string.")
    initpy_ver = version_match.group(1)
    assert len(initpy_ver.split(".")) in [
        3,
        4,
    ], "moto/__init__.py version should be like 0.0.2.dev"
    return Version(initpy_ver)


def increase_patch_version(old_version):
    """
    :param old_version: 2.0.1
    :return: 2.0.2.dev
    """
    return "{}.{}.{}.dev".format(
        old_version.major, old_version.minor, old_version.micro + 1
    )


def release_version_correct():
    """Makes sure the:
    - prerelease verion for master is correct.
    - release version is correct for tags.
    """
    if is_master_branch():
        # update for a pre release version.
        initpy = os.path.abspath("moto/__init__.py")

        new_version = prerelease_version()
        print(
            "updating version in __init__.py to {new_version}".format(
                new_version=new_version
            )
        )
        assert (
            len(new_version.split(".")) >= 4
        ), "moto/__init__.py version should be like 0.0.2.dev"
        migrate_version(initpy, new_version)
    else:
        assert False, "No non-master deployments yet"


if __name__ == "__main__":
    new_version = None
    if len(sys.argv) == 1:
        release_version_correct()
    elif len(sys.argv) == 2:
        for _, arg in enumerate(sys.argv):
            new_version = arg
        if new_version == "patch":
            new_version = increase_patch_version(get_version())
        initpy = os.path.abspath("moto/__init__.py")
        migrate_version(initpy, new_version)
    else:
        print(
            "Invalid usage. Supply 0 or 1 arguments. "
            "Argument can be either a version '1.2.3' or 'patch' if you want to increase the patch-version (1.2.3 -> 1.2.4.dev)"
        )
