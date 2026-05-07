from __future__ import annotations

import re

from canvas_navbar.html_renderer import END_MARKER, START_MARKER

_MANAGED_BLOCK_PATTERN = re.compile(
    rf"^\s*{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}\s*",
    re.DOTALL,
)
_LEGACY_STYLE_PATTERN = re.compile(
    r"^\s*<style\b[^>]*>.*?canvas-navbar.*?</style>\s*",
    re.DOTALL | re.IGNORECASE,
)
_LEGACY_MANAGED_NAV_PATTERN = re.compile(
    r'^\s*<nav\b[^>]*\bdata-canvas-navbar\s*=\s*["\']managed["\'][^>]*>.*?</nav>\s*',
    re.DOTALL | re.IGNORECASE,
)
_LEGACY_ARIA_NAV_PATTERN = re.compile(
    r'^\s*<nav\b[^>]*\baria-label\s*=\s*["\'][^"\']*(course module navigation|course unit map navigation)[^"\']*["\'][^>]*>.*?</nav>\s*',
    re.DOTALL | re.IGNORECASE,
)
_GENERIC_LEADING_NAV_PATTERN = re.compile(
    r"^\s*<nav\b[^>]*>.*?</nav>\s*",
    re.DOTALL | re.IGNORECASE,
)
_LEADING_CANVAS_ASSET_PATTERN = re.compile(
    r"^(?P<prefix>(?:\s|<link\b[^>]*>\s*|<script\b[^>]*>.*?</script>\s*|<style\b[^>]*>.*?</style>\s*)*)",
    re.DOTALL | re.IGNORECASE,
)


def upsert_navbar(existing_body: str | None, navbar_html: str) -> str:
    body = existing_body or ""
    cleaned_body = _strip_existing_navbars(body)
    if not cleaned_body:
        return navbar_html
    return f"{navbar_html}\n{cleaned_body}"


def _strip_existing_navbars(body: str) -> str:
    working = body

    while True:
        previous = working
        working, replaced = _strip_one_leading_navbar(working)
        if replaced:
            continue
        if working == previous:
            break

    start_present = START_MARKER in working
    end_present = END_MARKER in working
    if start_present != end_present:
        raise ValueError("Found an incomplete managed navbar block in the Canvas page body.")

    return working.lstrip()


def _strip_one_leading_navbar(body: str) -> tuple[str, bool]:
    prefix_match = _LEADING_CANVAS_ASSET_PATTERN.match(body)
    prefix = prefix_match.group("prefix") if prefix_match else ""
    remainder = body[len(prefix):]

    for pattern in (
        _MANAGED_BLOCK_PATTERN,
        _LEGACY_STYLE_PATTERN,
        _LEGACY_MANAGED_NAV_PATTERN,
        _LEGACY_ARIA_NAV_PATTERN,
        _GENERIC_LEADING_NAV_PATTERN,
    ):
        stripped_remainder, replaced = pattern.subn("", remainder, count=1)
        if replaced:
            return f"{prefix}{stripped_remainder}", True

    return body, False
