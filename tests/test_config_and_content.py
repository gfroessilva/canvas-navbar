import unittest

from canvas_navbar.config import ConfigError, parse_selection_config
from canvas_navbar.html_renderer import END_MARKER, START_MARKER, render_navbar, render_preview_document
from canvas_navbar.models import CourseNavigation, ModuleNavigation, PageSummary
from canvas_navbar.page_content import upsert_navbar


class ConfigParsingTests(unittest.TestCase):
    def test_parse_selection_config_accepts_string_and_object_entries(self) -> None:
        config = parse_selection_config(
            {
                "nav_format": "details",
                "modules": [
                    "Week 1",
                    {"name": "Week 2", "label": "W2", "pages": "all"},
                    {"id": 3, "pages": ["Intro", {"title": "Tutorial", "label": "Tute"}]},
                ]
            }
        )

        self.assertEqual(3, len(config.modules))
        self.assertEqual("details", config.nav_format)
        self.assertEqual("Week 1", config.modules[0].module_name)
        self.assertEqual("W2", config.modules[1].display_title)
        self.assertIsNone(config.modules[1].pages)
        self.assertEqual("Intro", config.modules[2].pages[0].title)
        self.assertEqual("Tutorial", config.modules[2].pages[1].title)
        self.assertEqual("Tute", config.modules[2].pages[1].display_title)

    def test_parse_selection_config_rejects_invalid_nav_format(self) -> None:
        with self.assertRaises(ConfigError):
            parse_selection_config({"nav_format": "accordion", "modules": ["Week 1"]})

    def test_parse_selection_config_accepts_overlay_nav_format(self) -> None:
        config = parse_selection_config({"nav_format": "overlay", "modules": ["Week 1"]})

        self.assertEqual("overlay", config.nav_format)

    def test_parse_selection_config_accepts_hybrid_nav_format(self) -> None:
        config = parse_selection_config({"nav_format": "hybrid", "modules": ["Week 1"]})

        self.assertEqual("hybrid", config.nav_format)

    def test_parse_selection_config_rejects_duplicate_page_names(self) -> None:
        with self.assertRaises(ConfigError):
            parse_selection_config({"modules": [{"name": "Week 1", "pages": ["Intro", "Intro"]}]})

    def test_parse_selection_config_rejects_blank_page_label(self) -> None:
        with self.assertRaises(ConfigError):
            parse_selection_config({"modules": [{"name": "Week 1", "pages": [{"title": "Intro", "label": " "}]}]})

    def test_parse_selection_config_rejects_blank_module_label(self) -> None:
        with self.assertRaises(ConfigError):
            parse_selection_config({"modules": [{"name": "Week 1", "label": " "}]} )


class NavbarRenderingTests(unittest.TestCase):
    def test_render_navbar_wraps_managed_block_and_marks_current_page(self) -> None:
        navigation = CourseNavigation(
            course_id="42",
            modules=(
                ModuleNavigation(
                    module_id=1,
                    module_name="Week 1",
                    module_position=1,
                    pages=(PageSummary("Week 1 Lecture", "intro", "/courses/42/pages/intro"),),
                ),
            ),
        )

        html = render_navbar(navigation, current_page_url="intro")

        self.assertIn(START_MARKER, html)
        self.assertIn(END_MARKER, html)
        self.assertIn('aria-current="page"', html)
        self.assertIn('canvas-navbar__item--current', html)
        self.assertIn('href="/courses/42/modules#module_1"', html)
        self.assertIn(">W1</strong>", html)
        self.assertIn(">Module<", html)
        self.assertIn(">Lecture<", html)

    def test_render_navbar_prefers_configured_display_title(self) -> None:
        navigation = CourseNavigation(
            course_id="42",
            modules=(
                ModuleNavigation(
                    module_id=1,
                    module_name="Week 1",
                    module_position=1,
                    pages=(PageSummary("Week 1 Tutorial", "tutorial", display_title="Workshop"),),
                    display_title="Start Here",
                    html_url="https://canvas.example.edu/courses/42/modules/items/1",
                ),
            ),
        )

        html = render_navbar(navigation)

        self.assertIn('href="https://canvas.example.edu/courses/42/modules/items/1"', html)
        self.assertIn(">Start Here</strong>", html)
        self.assertIn(">Module<", html)
        self.assertIn(">Workshop<", html)
        self.assertNotIn(">Tutorial<", html)

    def test_render_navbar_supports_details_format(self) -> None:
        navigation = CourseNavigation(
            course_id="42",
            modules=(
                ModuleNavigation(
                    module_id=1,
                    module_name="Week 1: Intro",
                    module_position=1,
                    pages=(PageSummary("Week 1 Overview", "overview", "https://canvas.example.edu/courses/42/pages/overview"),),
                    html_url="https://canvas.example.edu/courses/42/modules/items/1",
                ),
            ),
        )

        html = render_navbar(navigation, current_page_url="overview", nav_format="details")

        self.assertIn('class="canvas-navbar__details canvas-navbar__details--current"', html)
        self.assertIn('canvas-navbar__item--current', html)
        self.assertIn('data-api-endpoint="https://canvas.example.edu/api/v1/courses/42/pages/overview"', html)
        self.assertIn('href="https://canvas.example.edu/courses/42/modules/items/1"', html)
        self.assertIn('canvas-navbar__link--module', html)
        self.assertIn(">Week 1: Intro</summary>", html)
        self.assertIn(">Module<", html)
        self.assertIn("overflow:hidden", html)

    def test_render_navbar_supports_overlay_format(self) -> None:
        navigation = CourseNavigation(
            course_id="42",
            modules=(
                ModuleNavigation(
                    module_id=1,
                    module_name="Week 1: Intro",
                    module_position=1,
                    pages=(PageSummary("Week 1 Overview", "overview", "https://canvas.example.edu/courses/42/pages/overview"),),
                    html_url="https://canvas.example.edu/courses/42/modules/items/1",
                ),
            ),
        )

        html = render_navbar(navigation, current_page_url="overview", nav_format="overlay")

        self.assertIn('position:absolute', html)
        self.assertIn('flex-wrap:nowrap', html)
        self.assertIn('overflow-x:auto', html)
        self.assertIn('canvas-navbar__item--current', html)
        self.assertIn('canvas-navbar__link--module', html)
        self.assertIn('data-api-endpoint="https://canvas.example.edu/api/v1/courses/42/pages/overview"', html)

    def test_render_navbar_supports_hybrid_format(self) -> None:
        navigation = CourseNavigation(
            course_id="42",
            modules=(
                ModuleNavigation(
                    module_id=1,
                    module_name="Week 1: Intro",
                    module_position=1,
                    pages=(PageSummary("Week 1 Overview", "overview", "https://canvas.example.edu/courses/42/pages/overview"),),
                    html_url="https://canvas.example.edu/courses/42/modules/items/1",
                ),
            ),
        )

        html = render_navbar(navigation, current_page_url="overview", nav_format="hybrid")

        self.assertIn('class="canvas-navbar__details canvas-navbar__details--current"', html)
        self.assertIn('canvas-navbar__item--current', html)
        self.assertIn('flex-wrap:nowrap', html)
        self.assertIn('overflow-x:auto', html)
        self.assertNotIn('position:absolute', html)
        self.assertIn('canvas-navbar__link--module', html)
        self.assertIn('display:inline-block', html)
        self.assertIn('width:0', html)
        self.assertIn('overflow:visible', html)
        self.assertIn('max-width:24rem', html)
        self.assertNotIn('width:16rem', html)

    def test_upsert_navbar_prepends_then_replaces_existing_block(self) -> None:
        navigation = CourseNavigation(
            course_id="42",
            modules=(
                ModuleNavigation(
                    module_id=1,
                    module_name="Week 1",
                    module_position=1,
                    pages=(PageSummary("Week 1 Lecture", "intro"),),
                ),
            ),
        )

        first_navbar = render_navbar(navigation, current_page_url="intro")
        original_body = "<p>Hello world</p>"
        updated_body = upsert_navbar(original_body, first_navbar)

        self.assertTrue(updated_body.startswith(START_MARKER))
        self.assertTrue(updated_body.endswith(original_body))

        second_navbar = first_navbar.replace("Lecture", "Lesson")
        replaced_body = upsert_navbar(updated_body, second_navbar)

        self.assertEqual(1, replaced_body.count(START_MARKER))
        self.assertIn("Lesson", replaced_body)
        self.assertNotIn(">Lecture<", replaced_body)

    def test_upsert_navbar_removes_legacy_navbar_without_markers(self) -> None:
        legacy_navbar = (
            '<nav aria-label="Course module navigation" style="margin-bottom:1rem;">'
            "<ul><li>Old navbar</li></ul></nav>\n"
        )
        body = f"{legacy_navbar}<p>Hello world</p>"
        new_body = upsert_navbar(body, "<!-- CANVAS_NAVBAR:START --><nav>New</nav><!-- CANVAS_NAVBAR:END -->")

        self.assertIn("<p>Hello world</p>", new_body)
        self.assertNotIn("Old navbar", new_body)
        self.assertEqual(1, new_body.count("CANVAS_NAVBAR:START"))

    def test_upsert_navbar_removes_leading_navbar_after_canvas_assets(self) -> None:
        existing_navbar = (
            '<nav class="canvas-navbar"><ul><li><a href="/courses/42/modules#module_1">Module</a></li></ul></nav>\n'
        )
        body = (
            '<link rel="stylesheet" href="https://canvas.example.edu/theme.css">\n'
            f"{existing_navbar}"
            "<p>Hello world</p>"
        )

        new_body = upsert_navbar(body, "<!-- CANVAS_NAVBAR:START --><nav>New</nav><!-- CANVAS_NAVBAR:END -->")

        self.assertTrue(new_body.startswith("<!-- CANVAS_NAVBAR:START -->"))
        self.assertIn('<link rel="stylesheet" href="https://canvas.example.edu/theme.css">', new_body)
        self.assertEqual(1, new_body.count("<nav"))
        self.assertIn("<p>Hello world</p>", new_body)

    def test_render_preview_document_includes_each_target_page(self) -> None:
        navigation = CourseNavigation(
            course_id="42",
            modules=(
                ModuleNavigation(
                    module_id=1,
                    module_name="Week 1",
                    module_position=1,
                    pages=(
                        PageSummary("Week 1 Lecture", "week-1-lecture"),
                        PageSummary("Week 1 Tutorial", "week-1-tutorial"),
                    ),
                ),
            ),
        )

        preview = render_preview_document(navigation, nav_format="details")

        self.assertIn("Canvas navbar preview", preview)
        self.assertIn("Preview for Week 1 Lecture", preview)
        self.assertIn("Preview for Week 1 Tutorial", preview)
        self.assertIn('canvas-navbar__details canvas-navbar__details--current', preview)
        self.assertIn('canvas-navbar__item--current', preview)


if __name__ == "__main__":
    unittest.main()
