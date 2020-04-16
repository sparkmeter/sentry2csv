#!/usr/bin/env python3
"""Export a Sentry project's issues to CSV."""

import argparse
import asyncio
import csv
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp
import pkg_resources  # part of setuptools

logging.basicConfig()
logger = logging.getLogger(__name__)


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
) -> Tuple[Union[List[Dict[str, Any]], Dict[str, Any]], Dict[str, Dict[str, str]]]:
    """Fetch JSON from a URL."""
    logger.debug("Fetching %s with params: %s", url, params)
    async with session.get(url, params=params) as response:
        return await response.json(), response.links


async def enrich_issue(
    session: aiohttp.ClientSession, issue: Dict[str, Any], enrichments: List[Enrichment]
) -> None:
    """Enrich an issue with data from the latest event."""
    event, _ = await fetch(session, f'https://sentry.io/api/0/issues/{issue["id"]}/events/latest/')
    issue["_enrichments"] = {}
    for enrichment in enrichments:
        assert isinstance(event, dict), f"Bad response type. Expected dict, got {type(event)}: {event}"
        issue["_enrichments"][enrichment.csv_field] = event.get(enrichment.sentry_path[0], {})
        for step in enrichment.sentry_path[1:]:
            issue["_enrichments"][enrichment.csv_field] = issue["_enrichments"][enrichment.csv_field].get(step, {})
        if issue["_enrichments"][enrichment.csv_field] == {}:
            issue["_enrichments"][enrichment.csv_field] = ""


async def fetch_issues(session: aiohttp.ClientSession, issues_url: str) -> List[Dict[str, Any]]:
    """Fetch all issues from Sentry."""
    page_count = 1
    issues: List[Dict[str, Any]] = []
    cursor = ""
    while True:
        print(f"Fetching issues page {page_count}")
        resp, links = await fetch(
            session, issues_url, params={"cursor": cursor, "statsPeriod": "", "query": "is:unresolved"}
        )
        logger.debug("Received page %s", resp)
        assert isinstance(resp, list), f"Bad response type. Expected list, got {type(resp)}"
        issues.extend(resp)
        if links.get("next", {}).get("results") != "true":
            break
        cursor = links["next"]["cursor"]
        page_count += 1
    return issues


def write_csv(filename: str, issues: List[Dict[str, Any]]):
    """Write Sentry issues to CSV."""
    fieldnames = ["Error", "Location", "Details", "Events", "Users", "Notes", "Link"]
    if issues and "_enrichments" in issues[0]:
        fieldnames.extend(issues[0]["_enrichments"].keys())
    with open(filename, "w") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for issue in issues:
            row = {
                "Error": issue["metadata"]["type"],
                "Location": issue["culprit"],
                "Details": issue["metadata"]["value"],
                "Events": issue["count"],
                "Users": issue["userCount"],
                "Notes": "",
                "Link": issue["permalink"],
            }
            row = {**row, **issue.get("_enrichments", {})}
            writer.writerow(row)


async def export(token: str, organization: str, project: str, enrich: Optional[List[Enrichment]] = None):
    """Export data from Sentry to CSV."""
    enrichments: List[Enrichment] = enrich or []
    issues_url = f"https://sentry.io/api/0/projects/{organization}/{project}/issues/"
    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {token}"}) as session:
        issues = await fetch_issues(session, issues_url)
        if enrichments:
            print(f"Enriching {len(issues)} issues with event data...")
            await asyncio.gather(
                *[asyncio.ensure_future(enrich_issue(session, issue, enrichments)) for issue in issues]
            )
        outfile = f"{organization}-{project}-export.csv"
        write_csv(outfile, issues)
        print(f"Exported to {outfile}")


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
    loop = asyncio.get_event_loop()
    loop.run_until_complete(export(args.token[0], args.organization[0], args.project[0], enrich=enrichments))
