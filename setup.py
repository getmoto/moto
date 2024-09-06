import glob
import gzip
from contextlib import suppress
from pathlib import Path

from setuptools import Command, setup
from setuptools.command.build import build


class CompressJsonCommand(Command):
    def initialize_options(self) -> None:
        self.bdist_dir: Path = None

    def finalize_options(self) -> None:
        with suppress(Exception):
            self.bdist_dir = Path(self.get_finalized_command("bdist_wheel").bdist_dir)

    def run(self) -> None:
        # Only run this command when creating a binary distribution
        if self.bdist_dir:
            build_dir = self.get_finalized_command("build_py").build_lib
            json_files = glob.glob(f"{build_dir}/**/*.json", recursive=True)
            for file in json_files:
                target_filename = f"{file}.gz"
                print(f"Compressing {file} into {target_filename}...")  # noqa
                with open(file, "rb") as source:
                    with open(target_filename, "wb") as target:
                        target.write(gzip.compress(source.read()))
                print(f"Removing {file}...")  # noqa
                Path(file).unlink()


class BuildAndCompressJson(build):
    sub_commands = build.sub_commands + [("compress_json_command", None)]


setup(
    cmdclass={
        "build": BuildAndCompressJson,
        "compress_json_command": CompressJsonCommand,
    }
)
