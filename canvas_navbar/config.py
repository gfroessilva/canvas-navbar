from __future__ import annotations

import json
from pathlib import Path

from canvas_navbar.models import DEFAULT_NAV_FORMAT, ModuleSelection, NavFormat, PageSelection, SelectionConfig


class ConfigError(ValueError):
    """Raised when the optional config file is invalid."""


def load_selection_config(path: str | Path | None) -> SelectionConfig | None:
    if path is None:
        return None

    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file is not valid JSON: {config_path} ({exc})") from exc

    return parse_selection_config(raw, source=str(config_path))


def parse_selection_config(data: object, source: str = "<memory>") -> SelectionConfig:
    if not isinstance(data, dict):
        raise ConfigError(f"{source}: top-level config must be a JSON object.")

    nav_format = _parse_nav_format(data.get("nav_format"), source=source)
    modules_raw = data.get("modules")
    if not isinstance(modules_raw, list) or not modules_raw:
        raise ConfigError(f"{source}: 'modules' must be a non-empty list.")

    modules: list[ModuleSelection] = []
    seen_keys: set[tuple[str, str | int]] = set()

    for index, raw_module in enumerate(modules_raw, start=1):
        selection = _parse_module_selection(raw_module, source=source, index=index)
        key = ("id", selection.module_id) if selection.module_id is not None else ("name", selection.module_name or "")
        if key in seen_keys:
            raise ConfigError(f"{source}: duplicate module selector at entry {index}.")
        seen_keys.add(key)
        modules.append(selection)

    return SelectionConfig(modules=tuple(modules), nav_format=nav_format)


def _parse_module_selection(raw_module: object, source: str, index: int) -> ModuleSelection:
    if isinstance(raw_module, str):
        name = raw_module.strip()
        if not name:
            raise ConfigError(f"{source}: module entry {index} must not be blank.")
        return ModuleSelection(module_name=name, pages=None)

    if not isinstance(raw_module, dict):
        raise ConfigError(f"{source}: module entry {index} must be a string or object.")

    module_name = raw_module.get("name")
    module_id = raw_module.get("id")
    display_title = raw_module.get("label", raw_module.get("display_title"))

    if module_name is None and module_id is None:
        raise ConfigError(f"{source}: module entry {index} must define 'name' or 'id'.")

    if module_name is not None:
        if not isinstance(module_name, str) or not module_name.strip():
            raise ConfigError(f"{source}: module entry {index} has an invalid 'name'.")
        module_name = module_name.strip()

    if module_id is not None:
        if not isinstance(module_id, int) or module_id <= 0:
            raise ConfigError(f"{source}: module entry {index} has an invalid 'id'.")

    if display_title is not None:
        if not isinstance(display_title, str) or not display_title.strip():
            raise ConfigError(f"{source}: module entry {index} has an invalid label.")
        display_title = display_title.strip()

    pages_raw = raw_module.get("pages")
    pages = _parse_pages(pages_raw, source=source, index=index)

    return ModuleSelection(module_name=module_name, module_id=module_id, pages=pages, display_title=display_title)


def _parse_pages(pages_raw: object, source: str, index: int) -> tuple[PageSelection, ...] | None:
    if pages_raw is None or pages_raw == "all":
        return None

    if not isinstance(pages_raw, list) or not pages_raw:
        raise ConfigError(f"{source}: module entry {index} has an invalid 'pages' value.")

    pages: list[PageSelection] = []
    seen: set[str] = set()
    for page_index, raw_page in enumerate(pages_raw, start=1):
        page = _parse_page_selection(raw_page, source=source, module_index=index, page_index=page_index)
        if page.title in seen:
            raise ConfigError(f"{source}: module entry {index} contains duplicate page '{page.title}'.")
        seen.add(page.title)
        pages.append(page)

    return tuple(pages)


def _parse_page_selection(raw_page: object, source: str, module_index: int, page_index: int) -> PageSelection:
    if isinstance(raw_page, str):
        page_name = raw_page.strip()
        if not page_name:
            raise ConfigError(
                f"{source}: module entry {module_index} page entry {page_index} must be a non-empty string."
            )
        return PageSelection(title=page_name)

    if not isinstance(raw_page, dict):
        raise ConfigError(
            f"{source}: module entry {module_index} page entry {page_index} must be a string or object."
        )

    title = raw_page.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ConfigError(
            f"{source}: module entry {module_index} page entry {page_index} must define a non-empty 'title'."
        )

    display_title = raw_page.get("label", raw_page.get("display_title"))
    if display_title is not None:
        if not isinstance(display_title, str) or not display_title.strip():
            raise ConfigError(
                f"{source}: module entry {module_index} page entry {page_index} has an invalid label."
            )
        display_title = display_title.strip()

    return PageSelection(title=title.strip(), display_title=display_title)


def _parse_nav_format(raw_value: object, source: str) -> NavFormat:
    if raw_value is None:
        return DEFAULT_NAV_FORMAT
    if raw_value in ("compact", "details", "overlay", "hybrid"):
        return raw_value
    raise ConfigError(f"{source}: 'nav_format' must be one of 'compact', 'details', 'overlay', or 'hybrid'.")
