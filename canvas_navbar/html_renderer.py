from __future__ import annotations

import re
from html import escape
from urllib.parse import quote, urlsplit, urlunsplit

from canvas_navbar.models import CourseNavigation, ModuleNavigation, NavFormat

START_MARKER = "<!-- CANVAS_NAVBAR:START -->"
END_MARKER = "<!-- CANVAS_NAVBAR:END -->"
MANAGED_NAVBAR_ATTRIBUTE = 'data-canvas-navbar="managed"'
NAVBAR_ARIA_LABEL = "Course unit map navigation"

_KEYWORD_LINK_LABELS = (
    ("lecture", "Lecture"),
    ("tutorial", "Tutorial"),
    ("seminar", "Seminar"),
    ("workshop", "Workshop"),
    ("lab", "Lab"),
    ("assessment", "Assessment"),
    ("exam", "Exam"),
)


def render_navbar(
    course_navigation: CourseNavigation,
    current_page_url: str | None = None,
    nav_format: NavFormat = "compact",
) -> str:
    if nav_format == "details":
        return _render_details_navbar(course_navigation, current_page_url=current_page_url)
    if nav_format == "overlay":
        return _render_overlay_navbar(course_navigation, current_page_url=current_page_url)
    if nav_format == "hybrid":
        return _render_hybrid_navbar(course_navigation, current_page_url=current_page_url)
    return _render_compact_navbar(course_navigation, current_page_url=current_page_url)


def _render_compact_navbar(course_navigation: CourseNavigation, current_page_url: str | None = None) -> str:
    module_items: list[str] = []
    for module in course_navigation.modules:
        is_current_module = _module_contains_current_page(module, current_page_url)
        module_href = escape(
            module.html_url or _fallback_module_href(course_navigation.course_id, module.module_id),
            quote=True,
        )
        module_label = escape(module.display_title or infer_module_label(module.module_name))
        page_links: list[str] = [
            f'<a href="{module_href}" style="text-decoration:none;color:#114a75;font-weight:600;display:inline-block;padding:0;margin:0;">Module</a>'
        ]
        for page in module.pages:
            href = escape(page.html_url or _fallback_page_href(course_navigation.course_id, page.url), quote=True)
            label = escape(page.display_title or infer_page_label(module.module_name, page.title))
            link_style = (
                "text-decoration:none;color:#114a75;font-weight:600;"
                "display:inline-block;padding:0;margin:0;"
            )
            if page.url == current_page_url:
                link_style += "text-decoration:underline;color:#0b3553;"
            current_attrs = ' aria-current="page"' if page.url == current_page_url else ""
            page_links.append(f'<a href="{href}" style="{link_style}"{current_attrs}>{label}</a>')

        module_items.append(
            f'<li class="canvas-navbar__item{" canvas-navbar__item--current" if is_current_module else ""}" '
            "style=\"margin:0;border:1px solid "
            + ("#6b8fc9;background:#eef5fb;" if is_current_module else "#c7d3e0;background:#ffffff;")
            + "border-radius:999px;"
            "padding:0.28rem 0.6rem;display:flex;flex-direction:column;align-items:center;gap:0.18rem;"
            "min-width:4.8rem;text-align:center;\">"
            f'<strong style="display:block;font-size:0.82rem;line-height:1.1;color:{"#0b3553" if is_current_module else "#203040"};">{module_label}</strong>'
            '<div style="display:flex;flex-direction:column;gap:0.1rem;font-size:0.8rem;line-height:1.05;">'
            f'{"".join(page_links)}'
            "</div>"
            "</li>"
        )

    return (
        f"{START_MARKER}\n"
        f'<nav {MANAGED_NAVBAR_ATTRIBUTE} aria-label="{escape(NAVBAR_ARIA_LABEL, quote=True)}" '
        'style="margin-bottom:1rem;border:1px solid #d5dce5;background:#f7f9fb;border-radius:6px;padding:0.75rem;">'
        '<p style="margin:0 0 0.4rem;"><strong>Unit map</strong></p>'
        '<ul style="list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:0.3rem;'
        f'font-size:0.88rem;line-height:1.15;">{"".join(module_items)}</ul>'
        "</nav>\n"
        f"{END_MARKER}"
    )


def _render_details_navbar(course_navigation: CourseNavigation, current_page_url: str | None = None) -> str:
    module_items: list[str] = []
    for module in course_navigation.modules:
        is_current_module = _module_contains_current_page(module, current_page_url)
        module_href = escape(
            module.html_url or _fallback_module_href(course_navigation.course_id, module.module_id),
            quote=True,
        )
        module_label = escape(module.display_title or module.module_name)
        page_items: list[str] = [
            '<li class="canvas-navbar__dropdown-item" style="margin:0;">'
            f'<a class="canvas-navbar__link canvas-navbar__link--module" href="{module_href}" '
            'style="display:block;padding:0.45rem 0.6rem;color:#203040;text-decoration:none;font-weight:600;background:#f7f9fb;">'
            'Module</a></li>'
        ]
        for page in module.pages:
            href = escape(page.html_url or _fallback_page_href(course_navigation.course_id, page.url), quote=True)
            current_class = " canvas-navbar__link--current" if page.url == current_page_url else ""
            current_style = "font-weight:700;background:#eef5fb;" if page.url == current_page_url else ""
            current_attrs = ' aria-current="page"' if page.url == current_page_url else ""
            api_endpoint = escape(_page_api_endpoint(course_navigation.course_id, page.url, page.html_url), quote=True)
            page_label = escape(page.display_title or page.title)
            page_items.append(
                '<li class="canvas-navbar__dropdown-item" style="margin:0;">'
                f'<a class="canvas-navbar__link{current_class}" href="{href}" '
                f'data-api-endpoint="{api_endpoint}" data-api-returntype="Page" '
                f'style="display:block;padding:0.45rem 0.6rem;color:#114a75;text-decoration:none;{current_style}"{current_attrs}>'
                f"{page_label}</a></li>"
            )

        module_items.append(
            f'<li class="canvas-navbar__item{" canvas-navbar__item--current" if is_current_module else ""}" style="margin:0;min-width:15rem;flex:1 1 15rem;">'
            f'<details class="canvas-navbar__details{" canvas-navbar__details--current" if is_current_module else ""}" '
            f'style="border:1px solid {"#6b8fc9" if is_current_module else "#c7d3e0"};border-radius:6px;'
            f'background:{"#eef5fb" if is_current_module else "#ffffff"};overflow:hidden;">'
            '<summary class="canvas-navbar__summary" '
            f'style="cursor:pointer;padding:0.65rem 0.8rem;background:{"#dce9f8" if is_current_module else "#eef5fb"};'
            f'font-weight:600;line-height:1.2;color:{"#0b3553" if is_current_module else "#203040"};">'
            f'{module_label}</summary>'
            '<ul class="canvas-navbar__dropdown" '
            'style="list-style:none;margin:0;padding:0;border-top:1px solid #d5dce5;background:#ffffff;">'
            f'{"".join(page_items)}</ul></details></li>'
        )

    return (
        f"{START_MARKER}\n"
        '<nav class="canvas-navbar" aria-label="Course module navigation" '
        'style="margin-bottom:1rem;border:1px solid #d5dce5;background:#f7f9fb;border-radius:6px;padding:0.75rem;">'
        '<ul class="canvas-navbar__list" '
        'style="list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:0.75rem;align-items:flex-start;">'
        f'{"".join(module_items)}</ul></nav>\n'
        f"{END_MARKER}"
    )


def _render_overlay_navbar(course_navigation: CourseNavigation, current_page_url: str | None = None) -> str:
    module_items: list[str] = []
    for module in course_navigation.modules:
        is_current_module = _module_contains_current_page(module, current_page_url)
        module_href = escape(
            module.html_url or _fallback_module_href(course_navigation.course_id, module.module_id),
            quote=True,
        )
        module_label = escape(module.display_title or module.module_name)
        page_items: list[str] = [
            '<li class="canvas-navbar__dropdown-item" style="margin:0;">'
            f'<a class="canvas-navbar__link canvas-navbar__link--module" href="{module_href}" '
            'style="display:block;padding:0.5rem 0.7rem;color:#203040;text-decoration:none;font-weight:600;background:#f7f9fb;border-bottom:1px solid #d5dce5;">'
            'Module</a></li>'
        ]
        for page in module.pages:
            href = escape(page.html_url or _fallback_page_href(course_navigation.course_id, page.url), quote=True)
            current_class = " canvas-navbar__link--current" if page.url == current_page_url else ""
            current_style = "font-weight:700;background:#eef5fb;" if page.url == current_page_url else ""
            current_attrs = ' aria-current="page"' if page.url == current_page_url else ""
            api_endpoint = escape(_page_api_endpoint(course_navigation.course_id, page.url, page.html_url), quote=True)
            page_label = escape(page.display_title or page.title)
            page_items.append(
                '<li class="canvas-navbar__dropdown-item" style="margin:0;">'
                f'<a class="canvas-navbar__link{current_class}" href="{href}" '
                f'data-api-endpoint="{api_endpoint}" data-api-returntype="Page" '
                f'style="display:block;padding:0.45rem 0.7rem;color:#114a75;text-decoration:none;white-space:normal;{current_style}"{current_attrs}>'
                f"{page_label}</a></li>"
            )

        module_items.append(
            f'<li class="canvas-navbar__item{" canvas-navbar__item--current" if is_current_module else ""}" style="position:relative;margin:0;flex:0 0 auto;">'
            f'<details class="canvas-navbar__details{" canvas-navbar__details--current" if is_current_module else ""}" style="position:relative;">'
            '<summary class="canvas-navbar__summary" '
            f'style="cursor:pointer;list-style:none;padding:0.55rem 0.8rem;border:1px solid {"#6b8fc9" if is_current_module else "#c7d3e0"};'
            f'border-radius:6px;background:{"#eef5fb" if is_current_module else "#ffffff"};'
            f'font-weight:600;white-space:nowrap;color:{"#0b3553" if is_current_module else "#203040"};">'
            f'{module_label}</summary>'
            '<ul class="canvas-navbar__dropdown" style="list-style:none;margin:0;padding:0;position:absolute;left:0;top:calc(100% + 0.25rem);'
            'min-width:18rem;max-width:24rem;z-index:999;background:#ffffff;border:1px solid #c7d3e0;border-radius:6px;'
            'box-shadow:0 8px 18px rgba(0,0,0,0.16);overflow:hidden;">'
            f'{"".join(page_items)}</ul></details></li>'
        )

    return (
        f"{START_MARKER}\n"
        '<nav class="canvas-navbar" aria-label="Course module navigation" '
        'style="margin-bottom:1rem;border:1px solid #d5dce5;background:#f7f9fb;border-radius:6px;padding:0.75rem;overflow:visible;">'
        '<ul class="canvas-navbar__list" '
        'style="list-style:none;margin:0;padding:0;display:flex;flex-wrap:nowrap;gap:0.5rem;overflow-x:auto;overflow-y:visible;align-items:flex-start;">'
        f'{"".join(module_items)}</ul></nav>\n'
        f"{END_MARKER}"
    )


def _render_hybrid_navbar(course_navigation: CourseNavigation, current_page_url: str | None = None) -> str:
    module_items: list[str] = []
    for module in course_navigation.modules:
        is_current_module = _module_contains_current_page(module, current_page_url)
        module_href = escape(
            module.html_url or _fallback_module_href(course_navigation.course_id, module.module_id),
            quote=True,
        )
        module_label = escape(module.display_title or module.module_name)
        page_items: list[str] = [
            '<li class="canvas-navbar__dropdown-item" style="margin:0;">'
            f'<a class="canvas-navbar__link canvas-navbar__link--module" href="{module_href}" '
            'style="display:block;padding:0.5rem 0.7rem;color:#203040;text-decoration:none;font-weight:600;background:#f7f9fb;border-bottom:1px solid #d5dce5;">'
            'Module</a></li>'
        ]
        for page in module.pages:
            href = escape(page.html_url or _fallback_page_href(course_navigation.course_id, page.url), quote=True)
            current_class = " canvas-navbar__link--current" if page.url == current_page_url else ""
            current_style = "font-weight:700;background:#eef5fb;" if page.url == current_page_url else ""
            current_attrs = ' aria-current="page"' if page.url == current_page_url else ""
            api_endpoint = escape(_page_api_endpoint(course_navigation.course_id, page.url, page.html_url), quote=True)
            page_label = escape(page.display_title or page.title)
            page_items.append(
                '<li class="canvas-navbar__dropdown-item" style="margin:0;">'
                f'<a class="canvas-navbar__link{current_class}" href="{href}" '
                f'data-api-endpoint="{api_endpoint}" data-api-returntype="Page" '
                f'style="display:block;padding:0.45rem 0.7rem;color:#114a75;text-decoration:none;white-space:normal;{current_style}"{current_attrs}>'
                f"{page_label}</a></li>"
            )

        module_items.append(
            f'<li class="canvas-navbar__item{" canvas-navbar__item--current" if is_current_module else ""}" style="margin:0;flex:0 0 auto;">'
            f'<details class="canvas-navbar__details{" canvas-navbar__details--current" if is_current_module else ""}" '
            'style="display:inline-block;overflow:visible;">'
            '<summary class="canvas-navbar__summary" '
            f'style="cursor:pointer;list-style:none;padding:0.55rem 0.8rem;border:1px solid {"#6b8fc9" if is_current_module else "#c7d3e0"};'
            f'border-radius:999px;background:{"#eef5fb" if is_current_module else "#ffffff"};'
            f'font-weight:600;white-space:nowrap;color:{"#0b3553" if is_current_module else "#203040"};">'
            f'{module_label}</summary>'
            '<div class="canvas-navbar__panel" style="width:0;min-width:0;overflow:visible;">'
            '<ul class="canvas-navbar__dropdown" '
            'style="display:inline-block;list-style:none;margin:0.35rem 0 0 0;padding:0;max-width:24rem;'
            'border:1px solid #c7d3e0;border-radius:8px;background:#ffffff;overflow:hidden;'
            'box-shadow:0 4px 12px rgba(0,0,0,0.08);">'
            f'{"".join(page_items)}</ul></div></details></li>'
        )

    return (
        f"{START_MARKER}\n"
        '<nav class="canvas-navbar" aria-label="Course module navigation" '
        'style="margin-bottom:1rem;border:1px solid #d5dce5;background:#f7f9fb;border-radius:6px;padding:0.75rem;">'
        '<p style="margin:0 0 0.5rem 0;"><strong>Unit Map</strong></p><ul class="canvas-navbar__list" '
        'style="list-style:none;margin:0;padding:0;display:flex;flex-wrap:nowrap;gap:0.5rem;overflow-x:auto;align-items:flex-start;">'
        f'{"".join(module_items)}</ul></nav>\n'
        f"{END_MARKER}"
    )


def render_preview_document(course_navigation: CourseNavigation, nav_format: NavFormat = "compact") -> str:
    sections: list[str] = []
    for module in course_navigation.modules:
        for page in module.pages:
            navbar_html = render_navbar(course_navigation, current_page_url=page.url, nav_format=nav_format)
            page_title = escape(page.title)
            module_name = escape(module.module_name)
            sections.append(
                '<section style="margin:0 0 1.5rem 0;padding:1rem;border:1px solid #e2e8f0;'
                'border-radius:8px;background:#ffffff;">'
                f'<h2 style="margin:0 0 0.25rem 0;font-size:1rem;">Preview for {page_title}</h2>'
                f'<p style="margin:0 0 0.85rem 0;color:#51606f;font-size:0.92rem;">Current page inside {module_name}</p>'
                f"{navbar_html}"
                "</section>"
            )

    return (
        "<!DOCTYPE html>"
        '<html lang="en"><head><meta charset="utf-8"><title>Canvas Navbar Preview</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '</head><body style="margin:0;padding:24px;background:#f3f6f9;color:#1f2933;'
        'font-family:Arial,Helvetica,sans-serif;">'
        '<main style="max-width:1200px;margin:0 auto;">'
        '<h1 style="margin:0 0 0.5rem 0;">Canvas navbar preview</h1>'
        '<p style="margin:0 0 1.5rem 0;color:#52606d;">This file shows the generated navbar as it would appear '
        'on each target page before any Canvas pages are overwritten.</p>'
        f'{"".join(sections)}'
        "</main></body></html>"
    )


def _module_contains_current_page(module: ModuleNavigation, current_page_url: str | None) -> bool:
    return current_page_url is not None and any(page.url == current_page_url for page in module.pages)


def infer_module_label(module_name: str) -> str:
    match = re.search(r"\bweek\s*(\d+)\b", module_name, flags=re.IGNORECASE)
    if match:
        return f"W{match.group(1)}"
    return module_name


def infer_page_label(module_name: str, page_title: str) -> str:
    lowered = page_title.lower()
    for keyword, label in _KEYWORD_LINK_LABELS:
        if keyword in lowered:
            return label

    normalized = re.sub(r"\s+", " ", page_title).strip()
    prefix_pattern = re.compile(rf"^{re.escape(module_name)}[\s:\-|]+", flags=re.IGNORECASE)
    normalized = prefix_pattern.sub("", normalized)
    if len(normalized) <= 24:
        return normalized

    words = normalized.split()
    if 1 < len(words) <= 4:
        acronym = "".join(word[0].upper() for word in words if word)
        if len(acronym) >= 2:
            return acronym
    return normalized[:21].rstrip() + "..."


def _fallback_page_href(course_id: str, page_url: str) -> str:
    return f"/courses/{quote(str(course_id), safe='')}/pages/{quote(page_url, safe='')}"


def _fallback_module_href(course_id: str, module_id: int) -> str:
    return f"/courses/{quote(str(course_id), safe='')}/modules#module_{quote(str(module_id), safe='')}"


def _page_api_endpoint(course_id: str, page_url: str, html_url: str | None) -> str:
    relative_path = f"/api/v1/courses/{quote(str(course_id), safe='')}/pages/{quote(page_url, safe='')}"
    if not html_url:
        return relative_path

    parts = urlsplit(html_url)
    if not parts.scheme or not parts.netloc:
        return relative_path
    return urlunsplit((parts.scheme, parts.netloc, relative_path, "", ""))
