"""Sentry Exporter."""

from setuptools import setup

with open("README.md", "r") as README:
    LONG_DESCRIPTION = README.read()

REQUIREMENTS = [
    "aiohttp==3.6.1",
]

setup(
    name="sentry2csv",
    author="SparkMeter",
    author_email="aru.sahni@sparkmeter.io",
    version="1.0a1",
    packages=["sentry2csv"],
    description="Export Sentry issues to CSV for further analysis",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
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
            "black==19.3b0",
            "mypy==0.730",
            "mypy-extensions==0.4.2",
            "pylint==2.4.2",
        ]
    },
    python_requires=">=3.7",
)
