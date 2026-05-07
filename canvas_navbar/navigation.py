from __future__ import annotations

from collections import defaultdict
from typing import Mapping, Sequence

from canvas_navbar.models import CanvasPage, CourseNavigation, ModuleNavigation, PageSelection, PageSummary, SelectionConfig


class NavigationError(ValueError):
    """Raised when Canvas data or filtering rules cannot produce a valid navbar."""


def build_course_navigation(
    course_id: str | int,
    modules_data: Sequence[dict],
    module_items_by_module: Mapping[int, Sequence[dict]],
    pages_data: Sequence[dict],
) -> CourseNavigation:
    published_pages = [_page_from_payload(page) for page in pages_data]
    pages_by_url = {page.url: page for page in published_pages if page.published}
    pages_by_id = {page.page_id: page for page in published_pages if page.published and page.page_id is not None}

    modules: list[ModuleNavigation] = []
    for module in sorted(modules_data, key=_module_sort_key):
        if module.get("published") is False:
            continue

        module_id = _coerce_int(module.get("id"), "module id")
        module_name = _normalize_text(module.get("name"), fallback=f"Module {module_id}")
        module_position = _position_value(module.get("position"))

        pages: list[PageSummary] = []
        seen_page_urls: set[str] = set()
        for item in sorted(module_items_by_module.get(module_id, []), key=_module_item_sort_key):
            if item.get("type") != "Page":
                continue
            if item.get("published") is False:
                continue

            page = _resolve_page(item, pages_by_url, pages_by_id)
            if page is None or page.url in seen_page_urls:
                continue

            seen_page_urls.add(page.url)
            pages.append(
                PageSummary(
                    title=page.title,
                    url=page.url,
                    html_url=page.html_url,
                    page_id=page.page_id,
                )
            )

        if pages:
            modules.append(
                ModuleNavigation(
                    module_id=module_id,
                    module_name=module_name,
                    module_position=module_position,
                    pages=tuple(pages),
                    html_url=_module_html_url(module),
                )
            )

    return CourseNavigation(course_id=str(course_id), modules=tuple(modules))


def filter_navigation(
    course_navigation: CourseNavigation, selection_config: SelectionConfig | None
) -> CourseNavigation:
    if selection_config is None:
        return course_navigation

    module_lookup_by_id = {module.module_id: module for module in course_navigation.modules}
    modules_by_name: dict[str, list[ModuleNavigation]] = defaultdict(list)
    for module in course_navigation.modules:
        modules_by_name[module.module_name].append(module)

    selected_rules: dict[int, tuple[ModuleNavigation, ModuleSelection]] = {}

    for selection in selection_config.modules:
        module = _resolve_selected_module(selection, module_lookup_by_id, modules_by_name)
        if module.module_id in selected_rules:
            raise NavigationError(f"Module '{module.module_name}' was selected more than once.")
        _validate_selected_pages(module, selection.pages)
        selected_rules[module.module_id] = (module, selection)

    filtered_modules: list[ModuleNavigation] = []
    for module in course_navigation.modules:
        rule = selected_rules.get(module.module_id)
        if rule is None:
            continue

        _, selection = rule
        selected_pages = selection.pages
        if selected_pages is None:
            filtered_modules.append(
                ModuleNavigation(
                    module_id=module.module_id,
                    module_name=module.module_name,
                    module_position=module.module_position,
                    pages=module.pages,
                    display_title=selection.display_title,
                    html_url=module.html_url,
                )
            )
            continue

        page_aliases = {page.title: page.display_title for page in selected_pages}
        filtered_pages = tuple(
            PageSummary(
                title=page.title,
                url=page.url,
                html_url=page.html_url,
                page_id=page.page_id,
                display_title=page_aliases.get(page.title),
            )
            for page in module.pages
            if page.title in page_aliases
        )
        if filtered_pages:
            filtered_modules.append(
                ModuleNavigation(
                    module_id=module.module_id,
                    module_name=module.module_name,
                    module_position=module.module_position,
                    pages=filtered_pages,
                    display_title=selection.display_title,
                    html_url=module.html_url,
                )
            )

    if not filtered_modules:
        raise NavigationError("The selected config did not leave any published module pages to render.")

    return CourseNavigation(course_id=course_navigation.course_id, modules=tuple(filtered_modules))


def target_page_urls(course_navigation: CourseNavigation) -> list[str]:
    ordered_urls: list[str] = []
    seen: set[str] = set()
    for module in course_navigation.modules:
        for page in module.pages:
            if page.url in seen:
                continue
            seen.add(page.url)
            ordered_urls.append(page.url)
    return ordered_urls


def _page_from_payload(payload: dict) -> CanvasPage:
    return CanvasPage(
        page_id=_optional_int(payload.get("page_id")),
        title=_normalize_text(payload.get("title"), fallback=str(payload.get("url") or "Untitled page")),
        url=str(payload.get("url") or ""),
        html_url=str(payload.get("html_url")) if payload.get("html_url") else None,
        published=payload.get("published") is not False,
        body=payload.get("body"),
    )


def _resolve_page(
    item: Mapping[str, object],
    pages_by_url: Mapping[str, CanvasPage],
    pages_by_id: Mapping[int, CanvasPage],
) -> CanvasPage | None:
    page_url = item.get("page_url")
    if isinstance(page_url, str):
        page = pages_by_url.get(page_url)
        if page is not None:
            return page

    content_id = _optional_int(item.get("content_id"))
    if content_id is not None:
        return pages_by_id.get(content_id)

    return None


def _resolve_selected_module(
    selection,
    module_lookup_by_id: Mapping[int, ModuleNavigation],
    modules_by_name: Mapping[str, Sequence[ModuleNavigation]],
) -> ModuleNavigation:
    if selection.module_id is not None:
        module = module_lookup_by_id.get(selection.module_id)
        if module is None:
            raise NavigationError(f"Config references module id {selection.module_id}, but it was not found.")
        return module

    module_name = selection.module_name or ""
    matches = modules_by_name.get(module_name, ())
    if not matches:
        raise NavigationError(f"Config references module '{module_name}', but it was not found.")
    if len(matches) > 1:
        raise NavigationError(
            f"Config references module '{module_name}', but multiple published modules share that name. "
            "Use the module id in the config instead."
        )
    return matches[0]


def _validate_selected_pages(module: ModuleNavigation, selected_pages: tuple[PageSelection, ...] | None) -> None:
    if selected_pages is None:
        return

    titles = [page.title for page in module.pages]
    title_counts: dict[str, int] = defaultdict(int)
    for title in titles:
        title_counts[title] += 1

    for page in selected_pages:
        title = page.title
        if title_counts[title] == 0:
            raise NavigationError(
                f"Config references page '{title}' in module '{module.module_name}', but it was not found."
            )
        if title_counts[title] > 1:
            raise NavigationError(
                f"Config references page '{title}' in module '{module.module_name}', but that title is ambiguous. "
                "Rename the Canvas pages or include all pages for that module."
            )


def _module_sort_key(module: Mapping[str, object]) -> tuple[int, int]:
    return (_position_value(module.get("position")), _coerce_int(module.get("id"), "module id"))


def _module_item_sort_key(item: Mapping[str, object]) -> tuple[int, int]:
    return (_position_value(item.get("position")), _optional_int(item.get("id")) or 0)


def _position_value(value: object) -> int:
    if isinstance(value, int):
        return value
    return 10**9


def _coerce_int(value: object, label: str) -> int:
    maybe_int = _optional_int(value)
    if maybe_int is None:
        raise NavigationError(f"Canvas {label} is missing or invalid.")
    return maybe_int


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _normalize_text(value: object, fallback: str) -> str:
    normalized = str(value or "").strip()
    if normalized:
        return normalized
    return fallback.strip()


def _module_html_url(payload: Mapping[str, object]) -> str | None:
    html_url = payload.get("html_url")
    if isinstance(html_url, str) and html_url.strip():
        return html_url.strip()
    return None
