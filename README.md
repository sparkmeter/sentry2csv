# sentry2csv

![](https://github.com/sparkmeter/sentry2csv/workflows/lint/badge.svg)
[![](https://img.shields.io/pypi/v/sentry2csv)](https://pypi.org/project/sentry2csv/)
![](https://img.shields.io/pypi/pyversions/sentry2csv)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![](https://img.shields.io/pypi/l/sentry2csv)](https://github.com/sparkmeter/sentry2csv/blob/master/LICENSE)

Dump Sentry issues to CSV for further analysis.

```bash
$ sentry2csv --token f9u3fdu821ed9j10sj19kjd991010 sparkmeter TopSecretProject13
Fetching issues page 1
Exported to sparkmeter-TopSecretProject13-export.csv
$ head -2 sparkmeter-TopSecretProject13-export.csv
Error,Location,Details,Events,Users,Notes,Link
AttributeError,secret_project.tasks.remove_every_zig,'NoneType' object has no attribute 'zig_count',12,1,,https://sentry.io/organizations/sparkmeter/issues/129481/
```

## Installation

[sentry2csv is available on PyPI](https://pypi.org/project/sentry2csv/).

**pipx (reccomended)**

[pipx](https://pypi.org/project/pipx/) is a tool that allows you to install and run Python applications in isolated environments.

1. Install pipx, following their instructions
2. Install sentry2csv: `pipx install sentry2csv`

**pip**

Alternatively, you can install sentry2csv using standard pip.

1. `pip3 install sentry2csv`


## Use

1. Get a Sentry API Token from https://sentry.io/settings/account/api/auth-tokens/
2. Run the exporter: `sentry2csv --token <API_TOKEN> <SENTRY_ORG> <SENTRY_PROJECT>`
    * For example, `sentry2csv --token f9u3fdu821ed9j10sj19kjd991010 sparkmeter TopSecretProject13`

This also accepts an optional `--enrich` flag. Enrichments augment issues with data from the latest event.
An enrichment is in the form of `CSV Field Name=dotted.sentry.path`, and multiple enrichments are comma-separated.

## Development
1. Clone this repository
2. Create a virtualenv with Python 3.7 or greater
   * e.g., `mkvirtualenv -p $(which python3.7) sentry2csv`
3. Install the package in editable mode: `pip install -e .[dev]`
4. Hack away!
