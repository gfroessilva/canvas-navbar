import tempfile
import unittest
from pathlib import Path

from canvas_navbar.models import CanvasPage
from canvas_navbar.service import generate_config_file, sync_course_navbar


class FakeCanvasClient:
    def __init__(self) -> None:
        self.updated_pages: list[tuple[str, str]] = []
        self.page_fetches: list[str] = []

    def list_modules(self, course_id):
        return [{"id": 1, "name": "Week 1", "position": 1, "published": True}]

    def list_module_items(self, course_id, module_id):
        return [
            {"id": 11, "type": "Page", "position": 1, "page_url": "week-1-lecture", "published": True},
            {"id": 12, "type": "Page", "position": 2, "page_url": "week-1-tutorial", "published": True},
        ]

    def list_pages(self, course_id):
        return [
            {
                "page_id": 101,
                "title": "Week 1 Lecture",
                "url": "week-1-lecture",
                "html_url": "https://canvas.example.edu/courses/5/pages/week-1-lecture",
                "published": True,
            },
            {
                "page_id": 102,
                "title": "Week 1 Tutorial",
                "url": "week-1-tutorial",
                "html_url": "https://canvas.example.edu/courses/5/pages/week-1-tutorial",
                "published": True,
            },
        ]

    def get_page(self, course_id, page_url):
        self.page_fetches.append(page_url)
        return CanvasPage(
            page_id=101,
            title=page_url,
            url=page_url,
            html_url=f"https://canvas.example.edu/courses/5/pages/{page_url}",
            published=True,
            body="<p>Body</p>",
        )

    def update_page_body(self, course_id, page_url, body):
        self.updated_pages.append((page_url, body))


class SyncCourseNavbarTests(unittest.TestCase):
    def test_sync_course_navbar_writes_preview_file_during_dry_run(self) -> None:
        client = FakeCanvasClient()

        with tempfile.TemporaryDirectory() as temp_dir:
            preview_path = Path(temp_dir) / "preview.html"
            result = sync_course_navbar(
                client=client,
                course_id="5",
                dry_run=True,
                preview_path=preview_path,
                nav_format="details",
            )

            self.assertEqual(str(preview_path.resolve()), result.preview_path)
            self.assertTrue(preview_path.exists())
            preview_text = preview_path.read_text(encoding="utf-8")
            self.assertIn("Canvas navbar preview", preview_text)
            self.assertIn('canvas-navbar__details canvas-navbar__details--current', preview_text)
            self.assertIn('canvas-navbar__item--current', preview_text)
            self.assertEqual([], client.updated_pages)

    def test_generate_config_file_exports_published_modules_and_pages_without_canvas_writes(self) -> None:
        client = FakeCanvasClient()

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "generated-config.json"
            result = generate_config_file(client=client, course_id="5", output_path=config_path, nav_format="overlay")

            config_text = config_path.read_text(encoding="utf-8")
            self.assertEqual(str(config_path.resolve()), result.config_path)
            self.assertIn('"nav_format": "overlay"', config_text)
            self.assertIn('"name": "Week 1"', config_text)
            self.assertIn('"label": "W1"', config_text)
            self.assertIn('"title": "Week 1 Lecture"', config_text)
            self.assertIn('"label": "Lecture"', config_text)
            self.assertEqual([], client.updated_pages)
            self.assertEqual([], client.page_fetches)


if __name__ == "__main__":
    unittest.main()
