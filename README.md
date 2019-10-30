# sentry2csv

![](https://github.com/sparkmeter/sentry2csv/workflows/build/badge.svg)

**Requires Python 3.7+**

Dump Sentry issues to CSV for further analysis.

## Use

1. Install the package: `pip install sentry2csv`
2. Get a Sentry API Token from https://sentry.io/settings/account/api/auth-tokens/
3. Run the exporter: `sentry2csv <API_TOKEN> <SENTRY_ORG> <SENTRY_PROJECT>`

This also accepts an optional `--enrich` flag. Enrichments augment issues with data from the latest event.
An enrichment is in the form of `CSV Field Name=dotted.sentry.path`, and multiple enrichments are comma-separated.

## Development
1. Clone this repository
2. Create a virtualenv with Python 3.7 or greater
   * e.g., `mkvirtualenv -p $(which python3.7) sentry2csv`
3. From the repository root directory, install the dev package in editable mode: `pip install -e ".[dev]"`
4. Hack away!
