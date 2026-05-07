from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NavFormat = Literal["compact", "details", "overlay", "hybrid"]
DEFAULT_NAV_FORMAT: NavFormat = "compact"


@dataclass(frozen=True)
class PageSummary:
    title: str
    url: str
    html_url: str | None = None
    page_id: int | None = None
    display_title: str | None = None


@dataclass(frozen=True)
class ModuleNavigation:
    module_id: int
    module_name: str
    module_position: int
    pages: tuple[PageSummary, ...]
    display_title: str | None = None
    html_url: str | None = None


@dataclass(frozen=True)
class CourseNavigation:
    course_id: str
    modules: tuple[ModuleNavigation, ...]


@dataclass(frozen=True)
class CanvasPage:
    page_id: int | None
    title: str
    url: str
    html_url: str | None
    published: bool
    body: str | None = None


@dataclass(frozen=True)
class PageSelection:
    title: str
    display_title: str | None = None


@dataclass(frozen=True)
class ModuleSelection:
    module_name: str | None = None
    module_id: int | None = None
    pages: tuple[PageSelection, ...] | None = None
    display_title: str | None = None


@dataclass(frozen=True)
class SelectionConfig:
    modules: tuple[ModuleSelection, ...]
    nav_format: NavFormat = DEFAULT_NAV_FORMAT
