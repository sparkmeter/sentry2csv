"""Sentry Exporter."""

import codecs
import os
import re
from setuptools import setup

with open("README.md", "r") as README:
    LONG_DESCRIPTION = README.read()

REQUIREMENTS = [
    "aiohttp==3.8.1",
]

HERE = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    """Read the file at the given path."""
    with codecs.open(os.path.join(HERE, *parts), "r") as readfile:
        return readfile.read()


def find_version(*file_paths):
    """Extract the version from the file at the given path."""
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="sentry2csv",
    author="SparkMeter",
    author_email="aru.sahni@sparkmeter.io",
    version=find_version("sentry2csv", "__init__.py"),
    packages=["sentry2csv"],
    description="Export Sentry issues to CSV for further analysis",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
    ],
    install_requires=REQUIREMENTS,
    url="https://github.com/sparkmeter/sentry2csv",
    project_urls={
        "Bug Tracker": "https://github.com/sparkmeter/sentry2csv/issues",
        "Source Code": "https://github.com/sparkmeter/sentry2csv",
    },
    entry_points={
        "console_scripts": ["sentry2csv=sentry2csv.sentry2csv:main"]
    },
    extras_require={
        "dev": [
            "aioresponses==0.7.3",
            "asynctest==0.13.0",
            "black==19.3b0",
            "mypy==0.931",
            "mypy-extensions==0.4.3",
            "types-setuptools==57.4.9",
            "pylint==2.12.2",
            "pytest==7.0.1",
            "pytest-asyncio==0.18.1",
            "pytest-cov==2.8.1",
            "pytest-mock==1.11.2",
        ]
    },
    python_requires=">=3.7",
)
