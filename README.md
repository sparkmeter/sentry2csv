# sentry2csv (requires Python 3.7+)

Dumps sentry issues to CSV for further analysis.

## Use

1. Get a Sentry API Token from https://sentry.io/settings/account/api/auth-tokens/
2. Create a virtualenv with Python 3.7 or greater
   * e.g., `mkvirtualenv -p $(which python3.7) sentry-exporter`
3. Install the package: `pip install `
4. Run the exporter: `sentry2csv <API_TOKEN> <SENTRY_ORG> <SENTRY_PROJECT>`

This also accepts an optional `--enrich` flag. Enrichments augment issues with data from the latest event.

An enrichment is in the form of `CSV Field Name=dotted.sentry.path`, and multiple enrichments are comma-separated.
