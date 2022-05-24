#!/usr/bin/env python3
"""Export a Sentry project's issues to CSV."""

import argparse
import asyncio
import csv
import logging
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import aiohttp
import pkg_resources
from multidict import MultiDict, MultiDictProxy
from yarl import URL  # part of setuptools

SENTRY_HOST = "sentry.io"

logging.basicConfig()
logger = logging.getLogger(__name__)


class Sentry2CSVException(Exception):
    """A handled exception."""

    def __init__(self, message):  # pylint: disable=super-init-not-called
        self.message = message


@dataclass(frozen=True)
class QueryParam:
    """A key-value pair for the Sentry query string."""

    field: str
    value: str

    def __repr__(self):
        return f"{self.field}:{self.value}"


@dataclass
class Enrichment:
    """An enrichment."""

    csv_field: str
    sentry_path: List[str]

    @classmethod
    def from_mapping_string(cls, mapping: str) -> "Enrichment":
        """Generate an enrichment from the supplied mapping."""
        sentry_path, csv_field = mapping.split("=")
        return cls(csv_field, sentry_path.split("."))


async def fetch(
    session: aiohttp.ClientSession, url: str, params=None
) -> Tuple[Union[List[Dict[str, Any]], Dict[str, Any]], MultiDictProxy[MultiDictProxy[Union[str, URL]]]]:
    """Fetch JSON from a URL."""
    logger.debug("Fetching %s with params: %s", url, params)
    async with session.get(url, params=params) as response:
        logger.debug("Received response: %s", response)
        if response.status == 403:
            raise Sentry2CSVException("Failed to query Sentry: access denied.")
        return await response.json(), response.links


async def enrich_issue(
    session: aiohttp.ClientSession, issue: Dict[str, Any], enrichments: List[Enrichment], host: str = SENTRY_HOST
) -> None:
    """Enrich an issue with data from the latest event."""
    event, _ = await fetch(session, f'https://{host}/api/0/issues/{issue["id"]}/events/latest/')
    issue["_enrichments"] = {}
    for enrichment in enrichments:
        assert isinstance(event, dict), f"Bad response type. Expected dict, got {type(event)}: {event}"
        issue["_enrichments"][enrichment.csv_field] = event.get(enrichment.sentry_path[0], {})
        for step in enrichment.sentry_path[1:]:
            issue["_enrichments"][enrichment.csv_field] = issue["_enrichments"][enrichment.csv_field].get(step, {})
        if issue["_enrichments"][enrichment.csv_field] == {}:
            issue["_enrichments"][enrichment.csv_field] = ""


async def fetch_issues(
    session: aiohttp.ClientSession, issues_url: str, query_params: List[QueryParam]
) -> List[Dict[str, Any]]:
    """Fetch all issues from Sentry."""
    page_count = 1
    issues: List[Dict[str, Any]] = []
    cursor = ""
    query_str = " ".join(str(param) for param in query_params)
    while True:
        print(f"Fetching issues page {page_count}")
        resp, links = await fetch(
            session, issues_url, params={"cursor": cursor, "statsPeriod": "", "query": query_str}
        )
        logger.debug("Received page %s", resp)
        if isinstance(resp, dict):
            if "detail" in resp:
                raise Sentry2CSVException(
                    f"Failed to query Sentry. Received unexpected response: {resp['detail']}"
                )
        assert isinstance(resp, list), f"Bad response type. Expected list, got {type(resp)}"
        issues.extend(resp)
        if links.get("next", cast(MultiDictProxy[Union[str, URL]], MultiDict())).get("results") != "true":
            break
        cursor = str(links["next"]["cursor"])
        page_count += 1
    return issues


def write_csv(filename: str, issues: List[Dict[str, Any]]):
    """Write Sentry issues to CSV."""
    fieldnames = ["Error", "Location", "Details", "Events", "Users", "Notes", "Link"]
    if issues and "_enrichments" in issues[0]:
        fieldnames.extend(issues[0]["_enrichments"].keys())
    with open(filename, "w", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for issue in issues:
            try:
                # mapping from
                #  https://github.com/getsentry/sentry/blob/9910cc917d2def63b110e75d4d17dedf7f415f58/src/sentry/static/sentry/app/utils/events.tsx#L7  # pylint: disable=line-too-long
                issue_type = issue["type"]
                if issue_type == "error":
                    error = issue["metadata"].get("type", issue_type)  # get more specific if we can
                    details = issue["metadata"]["value"]
                elif issue_type == "csp":
                    error = "csp"
                    details = issue["metadata"]["message"]
                elif issue_type == "default":
                    error = "default"
                    details = issue["metadata"].get("title", "")
                else:
                    logger.debug("Unknown issue type: %s\n%s", issue_type, issue)
                    error = issue_type
                    details = ""
                row = {
                    "Error": error,
                    "Location": issue["culprit"],
                    "Details": details,
                    "Events": issue["count"],
                    "Users": issue["userCount"],
                    "Notes": "",
                    "Link": issue["permalink"],
                }
                row = {**row, **issue.get("_enrichments", {})}
                writer.writerow(row)
            except KeyError as kerr:
                logger.debug("Failed to process row, missing key: %s\n%s", kerr, issue)
                raise Sentry2CSVException("Unexpected API response. Run with -vv to debug.") from kerr


async def export(  # pylint:disable=too-many-arguments
    token: str,
    organization: str,
    project: str,
    query_params: List[QueryParam],
    enrich: Optional[List[Enrichment]] = None,
    host: str = SENTRY_HOST,
):
    """Export data from Sentry to CSV."""
    enrichments: List[Enrichment] = enrich or []
    issues_url = f"https://{host}/api/0/projects/{organization}/{project}/issues/"
    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {token}"}) as session:
        try:
            issues = await fetch_issues(session, issues_url, query_params)
            if enrichments:
                print(f"Enriching {len(issues)} issues with event data...")
                await asyncio.gather(
                    *[asyncio.ensure_future(enrich_issue(session, issue, enrichments, host)) for issue in issues]
                )
            outfile = f"{organization}-{project}-export.csv"
            write_csv(outfile, issues)
            print(f"Exported to {outfile}")
        except Sentry2CSVException as err:
            print(f"Export failed. {err.message}")
            sys.exit(1)


def extract_enrichment(mappings: Optional[str]) -> List[Enrichment]:
    """Convert the mapping string to a map.

    Mappings are in the format "<sentry_event_path>=<csv_field>[,<sentry_event_path>=<csv_field>]"
    """
    if mappings is None:
        return []
    return [Enrichment.from_mapping_string(mapping) for mapping in mappings.split(",")]


def main():
    """Do the thing."""
    version = pkg_resources.require("sentry2csv")[0].version
    parser = argparse.ArgumentParser(description="Export a Sentry project's issues to CSV")
    parser.add_argument("-v", "--verbose", default=0, action="count", help="Increase the log verbosity.")
    parser.add_argument("--version", action="version", version=version)
    parser.add_argument("--enrich", help="Optional mappings of event metadata")
    parser.add_argument("--token", metavar="API_TOKEN", nargs=1, required=True, help="The Sentry API token")
    parser.add_argument(
        "--host",
        metavar="HOST",
        nargs=1,
        required=False,
        default=[SENTRY_HOST],
        help=f"The Sentry host [default: {SENTRY_HOST}]",
    )
    parser.add_argument(
        "--environment",
        metavar="ENVIRONMENT_NAME",
        nargs=1,
        required=False,
        help="The name of the environment to query",
    )
    parser.add_argument("organization", metavar="ORGANIZATION", nargs=1, help="The Sentry organization")
    parser.add_argument("project", metavar="PROJECT", nargs=1, help="The Sentry project")
    args = parser.parse_args()
    if args.verbose > 1:
        logger.setLevel(logging.DEBUG)
    elif args.verbose == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)
    enrichments = extract_enrichment(args.enrich)
    query_params: List[QueryParam] = [QueryParam("is", "unresolved")]
    if args.environment:
        query_params.append(QueryParam("environment", args.environment[0]))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        export(
            args.token[0],
            args.organization[0],
            args.project[0],
            enrich=enrichments,
            host=args.host[0],
            query_params=query_params,
        )
    )


if __name__ == "__main__":
    main()
