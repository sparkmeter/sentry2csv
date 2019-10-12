"""Sentry Exporter."""

from setuptools import setup

REQUIREMENTS = [
    "aiohttp==3.6.1",
]

setup(
    name="sentry2csv",
    author="SparkMeter",
    version="1.0a0",
    packages=["sentry2csv"],
    license="License :: OSI Approved :: MIT License",
    install_requires=REQUIREMENTS,
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
    }
)
