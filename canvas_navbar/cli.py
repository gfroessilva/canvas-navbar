from __future__ import annotations

import argparse
import os
import sys

from canvas_navbar.canvas_api import CanvasAPIError, CanvasClient
from canvas_navbar.config import ConfigError
from canvas_navbar.navigation import NavigationError
from canvas_navbar.service import generate_config_file, sync_course_navbar


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    canvas_url = args.canvas_url or os.environ.get("CANVAS_BASE_URL")
    token = args.token or os.environ.get("CANVAS_API_TOKEN")

    if not canvas_url:
        parser.error("Canvas base URL is required via --canvas-url or CANVAS_BASE_URL.")
    if not token:
        parser.error("Canvas API token is required via --token or CANVAS_API_TOKEN.")

    client = CanvasClient(base_url=canvas_url, token=token, timeout=args.timeout)

    try:
        if args.generate_config:
            result = generate_config_file(
                client=client,
                course_id=args.course_id,
                output_path=args.generate_config,
                nav_format=args.nav_format,
            )
            print(f"Config file: {result.config_path}")
            print(f"Modules exported: {result.module_count}")
            print(f"Pages exported: {result.page_count}")
            print("Config generation complete: no Canvas pages were changed.")
            return 0

        result = sync_course_navbar(
            client=client,
            course_id=args.course_id,
            config_path=args.config,
            dry_run=args.dry_run,
            preview_path=args.preview_file,
            nav_format=args.nav_format,
        )
    except (CanvasAPIError, ConfigError, NavigationError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Modules in navbar: {result.module_count}")
    print(f"Target pages: {result.target_page_count}")
    if result.preview_path:
        print(f"Preview file: {result.preview_path}")
    if result.dry_run:
        print(f"Pages that would be updated: {result.updated_page_count}")
        print(f"Pages already up to date: {result.unchanged_page_count}")
        print("Dry run complete: no Canvas pages were changed.")
    else:
        print(f"Pages updated: {result.updated_page_count}")
        print(f"Pages already up to date: {result.unchanged_page_count}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and synchronize a Canvas page navbar from published module pages."
    )
    parser.add_argument("--course-id", required=True, help="Canvas course id to synchronize.")
    parser.add_argument("--canvas-url", help="Canvas base URL. Defaults to CANVAS_BASE_URL.")
    parser.add_argument("--token", help="Canvas API token. Defaults to CANVAS_API_TOKEN.")
    parser.add_argument(
        "--config",
        help="Optional JSON config file that narrows which modules/pages appear in the navbar.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the navbar and compare page bodies without updating Canvas.",
    )
    parser.add_argument(
        "--preview-file",
        help="Optional local HTML file to write a navbar preview before updating Canvas.",
    )
    parser.add_argument(
        "--generate-config",
        help="Write a starter config JSON from published modules/pages and exit without updating Canvas.",
    )
    parser.add_argument(
        "--nav-format",
        choices=["compact", "details", "overlay", "hybrid"],
        help="Override the navbar format used for preview, sync, or generated config output.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-request timeout in seconds.",
    )
    return parser
