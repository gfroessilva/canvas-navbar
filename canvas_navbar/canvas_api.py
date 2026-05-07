from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin
from urllib.request import Request, urlopen

from canvas_navbar.models import CanvasPage


class CanvasAPIError(RuntimeError):
    """Raised when the Canvas API returns an error or unexpected payload."""


@dataclass(frozen=True)
class _ResponseData:
    payload: Any
    headers: dict[str, str]


class CanvasClient:
    def __init__(self, base_url: str, token: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def list_modules(self, course_id: str | int) -> list[dict]:
        payload = self._list_paginated(f"/api/v1/courses/{course_id}/modules", params={"per_page": 100})
        return self._expect_list(payload, "modules")

    def list_module_items(self, course_id: str | int, module_id: int) -> list[dict]:
        payload = self._list_paginated(
            f"/api/v1/courses/{course_id}/modules/{module_id}/items",
            params={"per_page": 100},
        )
        return self._expect_list(payload, "module items")

    def list_pages(self, course_id: str | int) -> list[dict]:
        payload = self._list_paginated(f"/api/v1/courses/{course_id}/pages", params={"per_page": 100})
        return self._expect_list(payload, "pages")

    def get_page(self, course_id: str | int, page_url: str) -> CanvasPage:
        response = self._request_json(
            f"/api/v1/courses/{course_id}/pages/{quote(page_url, safe='')}",
            method="GET",
        )
        payload = self._expect_dict(response.payload, "page")
        return CanvasPage(
            page_id=_optional_int(payload.get("page_id")),
            title=str(payload.get("title") or page_url),
            url=str(payload.get("url") or page_url),
            html_url=str(payload.get("html_url")) if payload.get("html_url") else None,
            published=payload.get("published") is not False,
            body=str(payload.get("body") or ""),
        )

    def update_page_body(self, course_id: str | int, page_url: str, body: str) -> None:
        self._request_json(
            f"/api/v1/courses/{course_id}/pages/{quote(page_url, safe='')}",
            method="PUT",
            form_data={"wiki_page[body]": body},
        )

    def _list_paginated(self, path: str, params: dict[str, Any] | None = None) -> list[Any]:
        items: list[Any] = []
        next_url: str | None = path
        next_params = params

        while next_url is not None:
            response = self._request_json(next_url, method="GET", params=next_params)
            page_payload = self._expect_list(response.payload, "paginated payload")
            items.extend(page_payload)
            next_url = _extract_next_link(response.headers.get("Link"))
            next_params = None

        return items

    def _request_json(
        self,
        path_or_url: str,
        method: str,
        params: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
    ) -> _ResponseData:
        url = self._build_url(path_or_url, params=params)
        data = urlencode(form_data, doseq=True).encode("utf-8") if form_data is not None else None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        request = Request(url=url, data=data, headers=headers, method=method.upper())

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw_body = response.read().decode("utf-8")
                payload = json.loads(raw_body) if raw_body else None
                return _ResponseData(payload=payload, headers=dict(response.headers.items()))
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise CanvasAPIError(
                f"Canvas API request failed ({exc.code} {exc.reason}) for {url}: {error_body}"
            ) from exc
        except URLError as exc:
            raise CanvasAPIError(f"Canvas API request could not reach {url}: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise CanvasAPIError(f"Canvas API returned invalid JSON for {url}: {exc}") from exc

    def _build_url(self, path_or_url: str, params: dict[str, Any] | None = None) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            base = path_or_url
        else:
            base = urljoin(f"{self.base_url}/", path_or_url.lstrip("/"))

        if not params:
            return base

        query = urlencode(params, doseq=True)
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}{query}"

    @staticmethod
    def _expect_list(payload: Any, label: str) -> list:
        if not isinstance(payload, list):
            raise CanvasAPIError(f"Expected a list payload for {label}.")
        return payload

    @staticmethod
    def _expect_dict(payload: Any, label: str) -> dict:
        if not isinstance(payload, dict):
            raise CanvasAPIError(f"Expected an object payload for {label}.")
        return payload


def _extract_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None

    for match in re.finditer(r'<([^>]+)>;\s*rel="([^"]+)"', link_header):
        if match.group(2) == "next":
            return match.group(1)
    return None


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
