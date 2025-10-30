import requests
from requests import exceptions

from tools.check_readme_links import (
    LinkCheckResult,
    check_links,
    check_single_link,
    extract_links,
    parse_ignore_list,
)


class DummyResponse:
    def __init__(self, status_code: int, reason: str = "OK"):
        self.status_code = status_code
        self.reason = reason


class SequenceSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def request(self, method, url, timeout, allow_redirects=True):
        self.calls.append(method)
        if not self.outcomes:
            raise AssertionError("No more outcomes configured for SequenceSession")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_extract_links_deduplicates_and_sorts():
    markdown = (
        "Refer to [docs](https://example.com/docs).\n"
        "Another <https://example.org/guide> reference.\n"
        "[ref]: https://example.com/docs\n"
    )

    links = extract_links(markdown)

    assert links == [
        "https://example.com/docs",
        "https://example.org/guide",
    ]


def test_check_single_link_falls_back_to_get_when_head_not_allowed():
    session = SequenceSession(
        [
            DummyResponse(405, "Method Not Allowed"),
            DummyResponse(200, "OK"),
        ]
    )
    result = check_single_link("https://example.com", session, timeout=5)

    assert result.ok
    assert session.calls == ["HEAD", "GET"]
    assert result.status == 200


def test_check_single_link_handles_timeout_as_failure():
    session = SequenceSession([exceptions.Timeout("timeout")])

    result = check_single_link("https://slow.example.com", session, timeout=1)

    assert not result.ok
    assert "timeout" in (result.error or "").lower()
    assert session.calls == ["HEAD"]


def test_check_links_skips_ignored_hosts():
    ignore_hosts = parse_ignore_list("example.org")
    session = SequenceSession(
        [
            DummyResponse(200, "OK"),
        ]
    )

    urls = ["https://example.com", "https://example.org/page"]
    results = check_links(urls, ignore_hosts, timeout=5, session=session)

    assert session.calls == ["HEAD"]
    assert results[0].ok and not results[0].skipped
    assert results[1].ok and results[1].skipped and results[1].reason == "ignored host"


def test_check_single_link_reports_non_200_failure():
    session = SequenceSession([DummyResponse(500, "Server Error")])

    result = check_single_link("https://example.com/broken", session, timeout=5)

    assert not result.ok
    assert result.status == 500
    assert result.error == "Server Error"
