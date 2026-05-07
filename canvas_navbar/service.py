from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from canvas_navbar.canvas_api import CanvasClient
from canvas_navbar.config import load_selection_config
from canvas_navbar.html_renderer import infer_module_label, infer_page_label, render_navbar, render_preview_document
from canvas_navbar.models import DEFAULT_NAV_FORMAT, NavFormat
from canvas_navbar.navigation import NavigationError, build_course_navigation, filter_navigation, target_page_urls
from canvas_navbar.page_content import upsert_navbar


@dataclass(frozen=True)
class SyncResult:
    module_count: int
    target_page_count: int
    updated_page_count: int
    unchanged_page_count: int
    dry_run: bool
    preview_path: str | None = None


@dataclass(frozen=True)
class ConfigExportResult:
    config_path: str
    module_count: int
    page_count: int


def sync_course_navbar(
    client: CanvasClient,
    course_id: str | int,
    config_path: str | Path | None = None,
    dry_run: bool = False,
    preview_path: str | Path | None = None,
    nav_format: NavFormat | None = None,
) -> SyncResult:
    selection_config = load_selection_config(config_path)
    course_navigation = _fetch_course_navigation(client=client, course_id=course_id)
    course_navigation = filter_navigation(course_navigation, selection_config)
    resolved_nav_format = nav_format or (selection_config.nav_format if selection_config else DEFAULT_NAV_FORMAT)

    target_urls = target_page_urls(course_navigation)
    if not target_urls:
        raise NavigationError("No published module pages were available to update.")

    preview_path_text = _write_preview_file(preview_path, course_navigation, resolved_nav_format)

    updated_page_count = 0
    unchanged_page_count = 0

    for page_url in target_urls:
        page = client.get_page(course_id, page_url)
        navbar_html = render_navbar(course_navigation, current_page_url=page_url, nav_format=resolved_nav_format)
        new_body = upsert_navbar(page.body, navbar_html)
        if new_body == (page.body or ""):
            unchanged_page_count += 1
            continue

        if not dry_run:
            client.update_page_body(course_id, page_url, new_body)
        updated_page_count += 1

    return SyncResult(
        module_count=len(course_navigation.modules),
        target_page_count=len(target_urls),
        updated_page_count=updated_page_count,
        unchanged_page_count=unchanged_page_count,
        dry_run=dry_run,
        preview_path=preview_path_text,
    )


def generate_config_file(
    client: CanvasClient,
    course_id: str | int,
    output_path: str | Path,
    nav_format: NavFormat | None = None,
) -> ConfigExportResult:
    course_navigation = _fetch_course_navigation(client=client, course_id=course_id)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    config_payload = {
        "nav_format": nav_format or DEFAULT_NAV_FORMAT,
        "modules": [
            {
                "name": module.module_name,
                "id": module.module_id,
                "label": module.display_title or infer_module_label(module.module_name),
                "pages": [
                    {
                        "title": page.title,
                        "label": page.display_title or infer_page_label(module.module_name, page.title),
                    }
                    for page in module.pages
                ],
            }
            for module in course_navigation.modules
        ]
    }
    destination.write_text(f"{json.dumps(config_payload, indent=2)}\n", encoding="utf-8")
    return ConfigExportResult(
        config_path=str(destination.resolve()),
        module_count=len(course_navigation.modules),
        page_count=sum(len(module.pages) for module in course_navigation.modules),
    )


def _fetch_course_navigation(client: CanvasClient, course_id: str | int):
    modules_data = client.list_modules(course_id)
    module_items_by_module = {
        int(module["id"]): client.list_module_items(course_id, int(module["id"]))
        for module in modules_data
        if module.get("published") is not False and module.get("id") is not None
    }
    pages_data = client.list_pages(course_id)

    return build_course_navigation(
        course_id=course_id,
        modules_data=modules_data,
        module_items_by_module=module_items_by_module,
        pages_data=pages_data,
    )


def _write_preview_file(
    preview_path: str | Path | None,
    course_navigation,
    nav_format: NavFormat,
) -> str | None:
    if preview_path is None:
        return None

    destination = Path(preview_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_preview_document(course_navigation, nav_format=nav_format), encoding="utf-8")
    return str(destination.resolve())
