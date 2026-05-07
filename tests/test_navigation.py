import unittest

from canvas_navbar.models import CourseNavigation, ModuleNavigation, ModuleSelection, PageSelection, PageSummary, SelectionConfig
from canvas_navbar.navigation import NavigationError, build_course_navigation, filter_navigation, target_page_urls


class BuildCourseNavigationTests(unittest.TestCase):
    def test_build_course_navigation_only_keeps_published_module_pages(self) -> None:
        modules = [
            {"id": 20, "name": "Hidden", "position": 2, "published": False},
            {"id": 10, "name": "Week 1", "position": 1, "published": True},
        ]
        module_items = {
            10: [
                {"id": 100, "type": "Assignment", "position": 1, "published": True},
                {"id": 101, "type": "Page", "position": 2, "page_url": "intro", "published": True},
                {"id": 102, "type": "Page", "position": 3, "page_url": "draft", "published": True},
                {"id": 103, "type": "Page", "position": 4, "page_url": "intro", "published": True},
            ],
            20: [
                {"id": 201, "type": "Page", "position": 1, "page_url": "hidden-page", "published": True},
            ],
        }
        pages = [
            {"page_id": 1, "title": "Intro", "url": "intro", "html_url": "/courses/77/pages/intro", "published": True},
            {"page_id": 2, "title": "Draft", "url": "draft", "html_url": "/courses/77/pages/draft", "published": False},
            {"page_id": 3, "title": "Hidden page", "url": "hidden-page", "published": True},
        ]

        navigation = build_course_navigation("77", modules, module_items, pages)

        self.assertEqual(1, len(navigation.modules))
        self.assertEqual("Week 1", navigation.modules[0].module_name)
        self.assertEqual(["Intro"], [page.title for page in navigation.modules[0].pages])
        self.assertIsNone(navigation.modules[0].html_url)

    def test_build_course_navigation_trims_canvas_module_and_page_titles(self) -> None:
        modules = [{"id": 10, "name": " Preparation Resources ", "position": 1, "published": True, "html_url": " https://canvas.example.edu/modules/10 "}]
        module_items = {
            10: [
                {"id": 101, "type": "Page", "position": 1, "page_url": "prep-overview", "published": True},
            ]
        }
        pages = [
            {
                "page_id": 1,
                "title": "Preparation Resources Overview ",
                "url": "prep-overview",
                "html_url": "/courses/77/pages/prep-overview",
                "published": True,
            }
        ]

        navigation = build_course_navigation("77", modules, module_items, pages)

        self.assertEqual("Preparation Resources", navigation.modules[0].module_name)
        self.assertEqual("Preparation Resources Overview", navigation.modules[0].pages[0].title)
        self.assertEqual("https://canvas.example.edu/modules/10", navigation.modules[0].html_url)


class FilterNavigationTests(unittest.TestCase):
    def test_filter_navigation_preserves_canvas_order(self) -> None:
        navigation = CourseNavigation(
            course_id="77",
            modules=(
                ModuleNavigation(
                    module_id=1,
                    module_name="Week 1",
                    module_position=1,
                    pages=(
                        PageSummary("B page", "b-page"),
                        PageSummary("A page", "a-page"),
                    ),
                ),
                ModuleNavigation(
                    module_id=2,
                    module_name="Week 2",
                    module_position=2,
                    pages=(
                        PageSummary("X page", "x-page"),
                        PageSummary("Y page", "y-page"),
                    ),
                ),
            ),
        )
        selection = SelectionConfig(
            modules=(
                ModuleSelection(module_name="Week 2", pages=(PageSelection(title="Y page"),)),
                ModuleSelection(module_name="Week 1"),
            )
        )

        filtered = filter_navigation(navigation, selection)

        self.assertEqual(["Week 1", "Week 2"], [module.module_name for module in filtered.modules])
        self.assertEqual(["B page", "A page"], [page.title for page in filtered.modules[0].pages])
        self.assertEqual(["Y page"], [page.title for page in filtered.modules[1].pages])

    def test_filter_navigation_errors_for_missing_page(self) -> None:
        navigation = CourseNavigation(
            course_id="77",
            modules=(
                ModuleNavigation(
                    module_id=1,
                    module_name="Week 1",
                    module_position=1,
                    pages=(PageSummary("Intro", "intro"),),
                ),
            ),
        )
        selection = SelectionConfig(modules=(ModuleSelection(module_name="Week 1", pages=(PageSelection(title="Missing"),)),))

        with self.assertRaises(NavigationError):
            filter_navigation(navigation, selection)

    def test_filter_navigation_applies_configured_page_alias(self) -> None:
        navigation = CourseNavigation(
            course_id="77",
            modules=(
                ModuleNavigation(
                    module_id=1,
                    module_name="Week 1",
                    module_position=1,
                    pages=(
                        PageSummary("Week 1 Lecture", "lecture"),
                        PageSummary("Week 1 Tutorial", "tutorial"),
                    ),
                ),
            ),
        )
        selection = SelectionConfig(
            modules=(
                ModuleSelection(
                    module_name="Week 1",
                    pages=(
                        PageSelection(title="Week 1 Lecture", display_title="Read me first"),
                        PageSelection(title="Week 1 Tutorial"),
                    ),
                ),
            )
        )

        filtered = filter_navigation(navigation, selection)

        self.assertEqual("Read me first", filtered.modules[0].pages[0].display_title)
        self.assertIsNone(filtered.modules[0].pages[1].display_title)

    def test_filter_navigation_applies_configured_module_alias(self) -> None:
        navigation = CourseNavigation(
            course_id="77",
            modules=(
                ModuleNavigation(
                    module_id=1,
                    module_name="Week 1",
                    module_position=1,
                    pages=(PageSummary("Week 1 Lecture", "lecture"),),
                ),
            ),
        )
        selection = SelectionConfig(
            modules=(ModuleSelection(module_name="Week 1", display_title="Start Here"),)
        )

        filtered = filter_navigation(navigation, selection)

        self.assertEqual("Start Here", filtered.modules[0].display_title)

    def test_target_page_urls_deduplicates_across_modules(self) -> None:
        navigation = CourseNavigation(
            course_id="77",
            modules=(
                ModuleNavigation(
                    module_id=1,
                    module_name="Week 1",
                    module_position=1,
                    pages=(PageSummary("Intro", "intro"), PageSummary("Shared", "shared")),
                ),
                ModuleNavigation(
                    module_id=2,
                    module_name="Week 2",
                    module_position=2,
                    pages=(PageSummary("Shared", "shared"), PageSummary("Wrap up", "wrap-up")),
                ),
            ),
        )

        self.assertEqual(["intro", "shared", "wrap-up"], target_page_urls(navigation))


if __name__ == "__main__":
    unittest.main()
