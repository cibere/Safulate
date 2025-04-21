from pathlib import Path

from setuptools import setup

ver_file = Path(__file__).parent / "safulate" / "_version.py"


def derive_version() -> str:
    version = ver_file.read_text().split("=")[-1].strip().strip('"').removeprefix("v")

    if version.endswith(("a", "b", "rc")):
        # append version identifier based on commit count
        try:
            import subprocess

            p = subprocess.Popen(
                ["git", "rev-list", "--count", "HEAD"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, _err = p.communicate()
            if out:
                version += out.decode("utf-8").strip()
            p = subprocess.Popen(
                ["git", "rev-parse", "--short", "HEAD"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, _err = p.communicate()
            if out:
                version += "+g" + out.decode("utf-8").strip()
        except Exception:
            pass

    return version


setup(version=derive_version())
