# Canvas Navbar

`canvas-navbar` is a Python command-line tool that reads a Canvas course, builds a navbar from published module pages, and inserts or refreshes that navbar on the selected Canvas pages.

It is designed for the common Canvas workflow of:

1. pulling the published module/page structure from a course
2. previewing the generated navigation locally
3. optionally editing labels and included pages in a JSON config
4. pushing the updated navbar back to Canvas without creating duplicates

By default, the tool uses all published pages found inside published modules. You can optionally narrow the scope with a JSON config file and choose between multiple navbar formats.

## Requirements

- Python 3.10+
- A Canvas API token with permission to read courses/pages and update pages
- Your Canvas base URL, for example `https://canvas.example.edu`

## Installation

```powershell
git clone https://github.com/gfroessilva/canvas-navbar.git
cd canvas-navbar
python -m pip install -e .
```

## Credentials

You can pass Canvas credentials on the command line:

```powershell
python -m canvas_navbar --course-id 12345 --canvas-url https://canvas.example.edu --token YOUR_TOKEN
```

Or through environment variables:

```powershell
$env:CANVAS_BASE_URL="https://canvas.example.edu"
$env:CANVAS_API_TOKEN="YOUR_TOKEN"
python -m canvas_navbar --course-id 12345
```

## Recommended first-time workflow

Generate a starter config from Canvas:

```powershell
python -m canvas_navbar --course-id 12345 --generate-config .\navbar-config.generated.json
```

Preview the navbar locally before changing Canvas:

```powershell
python -m canvas_navbar --course-id 12345 --config .\navbar-config.generated.json --dry-run --preview-file .\preview\navbar-preview.html
```

Then push the navbar to Canvas:

```powershell
python -m canvas_navbar --course-id 12345 --config .\navbar-config.generated.json
```

## Common commands

```powershell
python -m canvas_navbar --help
python -m canvas_navbar --course-id 12345 --dry-run
python -m canvas_navbar --course-id 12345 --dry-run --preview-file .\preview\navbar-preview.html
python -m canvas_navbar --course-id 12345 --config .\navbar-config.json
python -m canvas_navbar --course-id 12345 --config .\navbar-config.json --nav-format compact
python -m canvas_navbar --course-id 12345 --config .\navbar-config.json --nav-format details
python -m canvas_navbar --course-id 12345 --config .\navbar-config.json --nav-format overlay
python -m canvas_navbar --course-id 12345 --config .\navbar-config.json --nav-format hybrid
python -m canvas_navbar --course-id 12345 --generate-config .\navbar-config.generated.json
```

## Navbar formats

- `compact` - small module cards with links stacked underneath
- `details` - in-flow expandable sections; safest in the Canvas editor
- `overlay` - one-row triggers with absolutely positioned dropdowns
- `hybrid` - one-row triggers with an expanding in-flow panel underneath

## Config file

The config file is JSON. It lets you restrict which modules appear in the navbar and, for each included module, whether to include all pages or only an explicit list.

You can generate a starter config file directly from Canvas:

```powershell
python -m canvas_navbar --course-id 12345 --generate-config .\navbar-config.generated.json
```

That mode only fetches published modules and published module pages, writes a local config file, and exits without updating any Canvas pages.

Example:

```json
{
  "nav_format": "compact",
  "modules": [
    "Week 1",
    {
      "name": "Week 2",
      "label": "W2",
      "pages": "all"
    },
    {
      "name": "Week 3",
      "label": "Control",
      "pages": [
        {
          "title": "Lecture notes",
          "label": "Lecture"
        },
        {
          "title": "Tutorial",
          "label": "Workshop"
        }
      ]
    },
    {
      "id": 98765,
      "pages": [
        "Assessment overview"
      ]
    }
  ]
}
```

### Config rules

- `modules` is required and must be a non-empty list.
- `nav_format` is optional and can be `compact`, `details`, `overlay`, or `hybrid`.
- Each module entry can be:
  - a string module name, equivalent to including all of that module's pages
  - an object with `name` or `id`, plus optional `label`
- `pages` is optional.
- If `pages` is omitted or set to `"all"`, all published pages from that module are included.
- If `pages` is a list, each entry can be either:
  - a string page title
  - an object with `title` and optional `label`
- `title` must match a published module page in Canvas exactly.
- `label` on a module overrides the text shown for that module in the navbar.
- `label` overrides the text shown in the navbar for that page.
- `details` format renders expandable module sections in normal document flow so open sections do not overlap surrounding content while editing in Canvas.
- `overlay` format keeps modules in a single horizontal row and uses absolutely positioned dropdowns that can sit over neighboring modules.
- `hybrid` format keeps module triggers in a single horizontal row, but expands page lists in normal flow underneath the opened trigger so the navbar area grows instead of overlaying following content.
- Canvas ordering is always preserved, even when the config file lists modules or pages in a different order.
- If the config references a missing or ambiguous module/page, the tool fails with a clear error.

## Notes on behavior

- Only **published pages that appear inside published modules** are eligible.
- If a page appears in multiple modules, it appears under every matching module in the navbar.
- When a config file is used, only pages included by the filtered navbar are updated.
- The navbar is wrapped in managed HTML comments so reruns replace the existing block instead of inserting duplicates.
- Earlier navbar variants generated by older versions of this tool are stripped from the top of the page before the new navbar is inserted.
- `--preview-file` writes a standalone local HTML preview so you can inspect the generated navbar before pushing changes to Canvas.
- `--generate-config` writes a starter config file containing all published modules and their published module pages, with generated default module/page labels that you can edit before running a sync.
- `--nav-format` overrides the format from the config file for preview, sync, or generated config output.
- In the Canvas editor, `overlay` may still be clipped or fail to reveal following text correctly because the editor layout controls stacking and overflow outside the page HTML itself.
- `hybrid` is the safer one-row option when you want the navbar area to expand instead of overlapping the text below.

## Development

### Running tests

```powershell
python -m unittest discover -s tests -v
```

## License

MIT
