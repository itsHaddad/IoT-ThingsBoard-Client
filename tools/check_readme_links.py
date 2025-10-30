"""CLI tool to validate HTTP(S) links in Markdown files."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set
from urllib.parse import urlparse

import requests
from requests import Response, Session


URL_PATTERN = re.compile(
    r"""
    (?P<url>
        https?://[^\s<>\[\](){}"']+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass
class LinkCheckResult:
    url: str
    ok: bool
    status: Optional[int] = None
    error: Optional[str] = None
    skipped: bool = False
    reason: Optional[str] = None


def positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid timeout value: {value}") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("timeout must be greater than zero")
    return parsed


def parse_ignore_list(ignore_option: Optional[str]) -> Set[str]:
    if not ignore_option:
        return set()
    hosts = {item.strip().lower() for item in ignore_option.split(",")}
    return {host for host in hosts if host}


def extract_links(markdown_text: str) -> List[str]:
    links: Set[str] = set()
    for match in URL_PATTERN.finditer(markdown_text):
        url = match.group("url").rstrip(").,;'\"")
        links.add(url)
    return sorted(links)


def should_ignore(url: str, ignore_hosts: Set[str]) -> bool:
    hostname = urlparse(url).hostname
    return bool(hostname and hostname.lower() in ignore_hosts)


def _request_with_fallback(
    session: Session, method: str, url: str, timeout: float
) -> Response:
    return session.request(method=method, url=url, timeout=timeout, allow_redirects=True)


def check_single_link(url: str, session: Session, timeout: float) -> LinkCheckResult:
    try:
        head_response = _request_with_fallback(session, "HEAD", url, timeout)
    except requests.exceptions.RequestException as exc:
        return LinkCheckResult(url=url, ok=False, error=str(exc))

    if head_response.status_code in {405, 501}:
        try:
            get_response = _request_with_fallback(session, "GET", url, timeout)
        except requests.exceptions.RequestException as exc:
            return LinkCheckResult(url=url, ok=False, error=str(exc))
        if 200 <= get_response.status_code < 300:
            return LinkCheckResult(url=url, ok=True, status=get_response.status_code)
        return LinkCheckResult(
            url=url,
            ok=False,
            status=get_response.status_code,
            error=get_response.reason,
        )

    if 200 <= head_response.status_code < 300:
        return LinkCheckResult(url=url, ok=True, status=head_response.status_code)

    return LinkCheckResult(
        url=url,
        ok=False,
        status=head_response.status_code,
        error=head_response.reason,
    )


def check_links(
    urls: Sequence[str],
    ignore_hosts: Set[str],
    timeout: float,
    session: Optional[Session] = None,
) -> List[LinkCheckResult]:
    session = session or requests.Session()
    results: List[LinkCheckResult] = []
    for url in urls:
        if should_ignore(url, ignore_hosts):
            results.append(
                LinkCheckResult(
                    url=url,
                    ok=True,
                    skipped=True,
                    reason="ignored host",
                )
            )
            continue
        results.append(check_single_link(url, session, timeout))
    return results


def format_summary(results: Iterable[LinkCheckResult]) -> str:
    total = 0
    failed = 0
    skipped = 0
    for result in results:
        if result.skipped:
            skipped += 1
            continue
        total += 1
        if not result.ok:
            failed += 1
    return (
        f"Checked {total} link(s); {failed} failure(s); {skipped} skipped via ignore list."
    )


def run_checker(file_path: Path, timeout: float, ignore_hosts: Set[str]) -> List[LinkCheckResult]:
    markdown = file_path.read_text(encoding="utf-8")
    urls = extract_links(markdown)
    if not urls:
        return []
    with requests.Session() as session:
        return check_links(urls, ignore_hosts, timeout, session=session)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate HTTP/HTTPS links inside a Markdown file."
    )
    parser.add_argument(
        "--file",
        default="README.md",
        help="Path to the Markdown file to scan (default: README.md).",
    )
    parser.add_argument(
        "--timeout",
        default=5.0,
        type=positive_float,
        help="Per-request timeout in seconds (default: 5).",
    )
    parser.add_argument(
        "--ignore",
        default="",
        help="Comma-separated list of hostnames to skip (e.g., localhost,example.com).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    file_path = Path(args.file)
    if not file_path.is_file():
        parser.error(f"file not found: {file_path}")

    ignore_hosts = parse_ignore_list(args.ignore)
    results = run_checker(file_path, args.timeout, ignore_hosts)

    if not results:
        print("No HTTP/HTTPS links found.")
        return 0

    failures = 0
    for result in results:
        if result.skipped:
            print(f"[SKIP] {result.url} ({result.reason})")
            continue
        if result.ok:
            status = result.status if result.status is not None else "OK"
            print(f"[ OK ] {result.url} (status: {status})")
        else:
            failures += 1
            detail = result.error or "request failed"
            status = (
                f"status: {result.status}" if result.status is not None else "no status"
            )
            print(f"[FAIL] {result.url} ({status}; {detail})")

    print(format_summary(results))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
