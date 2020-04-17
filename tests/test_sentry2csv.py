"""Test te Sentry project."""

from io import StringIO
from unittest.mock import call, mock_open

import aiohttp
import pytest
import pytest_asyncio  # pylint: disable=unused-import
from aioresponses import aioresponses
from asynctest import CoroutineMock

from sentry2csv import sentry2csv


@pytest.fixture(name="session")
async def _session():
    async with aiohttp.ClientSession() as sess:
        yield sess


@pytest.fixture(name="fetch_mock")
async def _fetch_mock(mocker):
    yield mocker.patch("sentry2csv.sentry2csv.fetch", new=CoroutineMock())


@pytest.mark.asyncio
async def test_fetch_basic(session):
    """Test fetching."""
    with aioresponses() as mock_session:
        mock_session.get("http://www.sentry.io/testurl", status=200, payload={"foo": "bar"})
        result, links = await sentry2csv.fetch(session, "http://www.sentry.io/testurl")
        assert result == {"foo": "bar"}
        assert dict(links) == {}


@pytest.mark.asyncio
async def test_fetch_auth_error(session):
    """A permission denied error."""
    with aioresponses() as mock_session:
        mock_session.get(
            "http://www.sentry.io/testurl",
            status=403,
            payload={"detail": "You do not have permission to perform this action."},
        )
        with pytest.raises(sentry2csv.Sentry2CSVException) as excinfo:
            await sentry2csv.fetch(session, "http://www.sentry.io/testurl")
        assert "access denied" in str(excinfo.value)


@pytest.mark.asyncio
async def test_fetch_with_link(session):
    """Test fetching."""
    with aioresponses() as mock_session:
        mock_session.get(
            "http://www.sentry.io/testurl/",
            status=200,
            payload={"foo": "bar"},
            headers={
                "Link": (
                    '<http://www.sentry.io/testurl/?&cursor=12345:0:0>; rel="next"; results="true"; '
                    'cursor="12345:0:0"'
                )
            },
        )
        result, links = await sentry2csv.fetch(session, "http://www.sentry.io/testurl/")
        assert result == {"foo": "bar"}
        assert "next" in links
        assert links["next"]["results"] == "true"
        assert links["next"]["cursor"] == "12345:0:0"


@pytest.mark.asyncio
async def test_fetch_issues(mocker, session):
    """Test issue fetching."""
    fetch_mock = mocker.patch("sentry2csv.sentry2csv.fetch", new=CoroutineMock())
    fetch_mock.return_value = ([1, 2, 3, 4], {})
    issues = await sentry2csv.fetch_issues(session, "http://sentry.io/issues")
    fetch_mock.assert_awaited_once_with(
        session, "http://sentry.io/issues", params={"cursor": "", "statsPeriod": "", "query": "is:unresolved"}
    )
    assert issues == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_fetch_issues_multiple_pages(mocker, session):
    """Test issue fetching."""
    fetch_mock = mocker.patch("sentry2csv.sentry2csv.fetch", new=CoroutineMock())
    fetch_mock.side_effect = [
        ([1, 2, 3, 4], {"next": {"results": "true", "cursor": "12345:0:0"}}),
        ([5, 6, 7, 8], {"next": {"results": "false"}}),
    ]
    issues = await sentry2csv.fetch_issues(session, "http://sentry.io/issues")
    fetch_mock.assert_has_awaits(
        [
            call(
                session,
                "http://sentry.io/issues",
                params={"cursor": "", "statsPeriod": "", "query": "is:unresolved"},
            ),
            call(
                session,
                "http://sentry.io/issues",
                params={"cursor": "12345:0:0", "statsPeriod": "", "query": "is:unresolved"},
            ),
        ]
    )
    assert issues == [1, 2, 3, 4, 5, 6, 7, 8]


@pytest.mark.asyncio
async def test_enrich_issue(fetch_mock, session):
    """Test issue enrichment."""
    fetch_mock.return_value = ({"packages": {"sentry2csv": {"version": "1.2.12"}}, "top_level_attr": 13}, {})
    enrichments = [
        sentry2csv.Enrichment.from_mapping_string(mapping)
        for mapping in ("packages.sentry2csv.version=Sentry2CSV Version", "top_level_attr=Top Attr")
    ]
    issue = {"id": "issue_id"}
    await sentry2csv.enrich_issue(session, issue, enrichments)
    fetch_mock.assert_awaited_once_with(session, "https://sentry.io/api/0/issues/issue_id/events/latest/")
    assert "_enrichments" in issue
    assert issue["_enrichments"]["Sentry2CSV Version"] == "1.2.12"
    assert issue["_enrichments"]["Top Attr"] == 13


@pytest.mark.asyncio
async def test_enrich_issue_missing_field(fetch_mock, session):
    """Test issue enrichment where a sentry path is missing."""
    fetch_mock.return_value = ({"top_level_attr": 13}, {})
    enrichments = [
        sentry2csv.Enrichment.from_mapping_string(mapping)
        for mapping in ("packages.sentry2csv.version=Sentry2CSV Version", "top_level_attr=Top Attr")
    ]
    issue = {"id": "issue_id"}
    await sentry2csv.enrich_issue(session, issue, enrichments)
    assert "_enrichments" in issue
    assert issue["_enrichments"]["Sentry2CSV Version"] == ""
    assert issue["_enrichments"]["Top Attr"] == 13


def test_extract_enrichment():
    """Test mapping conversion."""
    extracted = sentry2csv.extract_enrichment("packages.sentry2csv.version=Sentry Version,no-dot=No Dot")
    assert extracted == [
        sentry2csv.Enrichment("Sentry Version", ["packages", "sentry2csv", "version"]),
        sentry2csv.Enrichment("No Dot", ["no-dot"]),
    ]


def test_extract_enrichment_none():
    """Test mapping conversion."""
    extracted = sentry2csv.extract_enrichment(None)
    assert extracted == []


def test_write_csv(mocker):
    """Test CSV export."""
    open_patch = mocker.patch("builtins.open", mock_open())
    output_buffer = StringIO()
    open_patch.return_value.__enter__.return_value = output_buffer
    sentry2csv.write_csv(
        "outfile.csv",
        [
            {
                "metadata": {"type": "warning", "value": "explanation of warning"},
                "culprit": "culprit body",
                "count": 123,
                "userCount": 3,
                "permalink": "https://sentry.io/warning/warning_details",
            },
            {
                "metadata": {"type": "error", "value": "explanation of error"},
                "culprit": "culprit body",
                "count": 12,
                "userCount": 10,
                "permalink": "https://sentry.io/error/error_details",
            },
        ],
    )
    open_patch.assert_called_once()
    assert output_buffer.getvalue().split("\n") == [
        "Error,Location,Details,Events,Users,Notes,Link\r",
        "warning,culprit body,explanation of warning,123,3,,https://sentry.io/warning/warning_details\r",
        "error,culprit body,explanation of error,12,10,,https://sentry.io/error/error_details\r",
        "",
    ]


def test_write_csv_with_enrichments(mocker):
    """Test CSV export with enrichments."""
    open_patch = mocker.patch("builtins.open", mock_open())
    output_buffer = StringIO()
    open_patch.return_value.__enter__.return_value = output_buffer
    sentry2csv.write_csv(
        "outfile.csv",
        [
            {
                "metadata": {"type": "warning", "value": "explanation of warning"},
                "culprit": "culprit body",
                "count": 123,
                "userCount": 3,
                "permalink": "https://sentry.io/warning/warning_details",
                "_enrichments": {"Extra Field": 12, "Another Field": "ANOTHER FIELD"},
            },
            {
                "metadata": {"type": "error", "value": "explanation of error"},
                "culprit": "culprit body",
                "count": 12,
                "userCount": 10,
                "permalink": "https://sentry.io/error/error_details",
                "_enrichments": {"Extra Field": "Mixed Content", "Another Field": "yup"},
            },
        ],
    )
    open_patch.assert_called_once()
    assert output_buffer.getvalue().split("\n") == [
        "Error,Location,Details,Events,Users,Notes,Link,Extra Field,Another Field\r",
        "warning,culprit body,explanation of warning,123,3,,https://sentry.io/warning/warning_details,12,ANOTHER FIELD\r",  # pylint: disable=line-too-long
        "error,culprit body,explanation of error,12,10,,https://sentry.io/error/error_details,Mixed Content,yup\r",
        "",
    ]


def test_write_csv_with_errors(mocker):
    """Test CSV export with enrichments."""
    open_patch = mocker.patch("builtins.open", mock_open())
    output_buffer = StringIO()
    open_patch.return_value.__enter__.return_value = output_buffer
    with pytest.raises(sentry2csv.Sentry2CSVException) as excinfo:
        sentry2csv.write_csv(
            "outfile.csv",
            [
                {
                    "metadata": {"value": "explanation of warning"},
                    "culprit": "culprit body",
                    "count": 123,
                    "userCount": 3,
                    "permalink": "https://sentry.io/warning/warning_details",
                    "_enrichments": {"Extra Field": 12, "Another Field": "ANOTHER FIELD"},
                },
                {
                    "metadata": {"type": "error", "value": "explanation of error"},
                    "culprit": "culprit body",
                    "count": 12,
                    "userCount": 10,
                    "permalink": "https://sentry.io/error/error_details",
                    "_enrichments": {"Extra Field": "Mixed Content", "Another Field": "yup"},
                },
            ],
        )
    assert "Run with -vv to debug" in str(excinfo.value)


@pytest.mark.asyncio
async def test_export(mocker):
    """Test the export function."""
    fetch_issues_mock = mocker.patch("sentry2csv.sentry2csv.fetch_issues", new=CoroutineMock())
    fetch_issues_mock.return_value = ["issue1", "issue2"]
    write_mock = mocker.patch("sentry2csv.sentry2csv.write_csv")
    await sentry2csv.export("token", "organization", "project")
    fetch_issues_mock.assert_awaited_once()
    assert isinstance(fetch_issues_mock.call_args[0][0], aiohttp.client.ClientSession)
    assert fetch_issues_mock.call_args[0][1] == "https://sentry.io/api/0/projects/organization/project/issues/"
    write_mock.assert_called_once_with("organization-project-export.csv", ["issue1", "issue2"])


@pytest.mark.asyncio
async def test_export_with_enrichments(mocker):
    """Test the export function."""

    async def enrich_issue_fn(ses, issue_to_enrich, enrs):
        """Enrich the issue."""
        issue_to_enrich["_enriched"] = True

    fetch_issues_mock = mocker.patch("sentry2csv.sentry2csv.fetch_issues", new=CoroutineMock())
    fetch_issues_mock.return_value = [{"value": "issue1"}, {"value": "issue2"}]
    enrich_issue_mock = mocker.patch("sentry2csv.sentry2csv.enrich_issue", new=CoroutineMock())
    enrich_issue_mock.side_effect = enrich_issue_fn
    write_mock = mocker.patch("sentry2csv.sentry2csv.write_csv")
    await sentry2csv.export("token", "organization", "project", "enrichment_list")
    fetch_issues_mock.assert_awaited_once()
    assert isinstance(fetch_issues_mock.call_args[0][0], aiohttp.client.ClientSession)
    assert fetch_issues_mock.call_args[0][1] == "https://sentry.io/api/0/projects/organization/project/issues/"
    write_mock.assert_called_once_with(
        "organization-project-export.csv",
        [{"value": "issue1", "_enriched": True}, {"value": "issue2", "_enriched": True}],
    )
