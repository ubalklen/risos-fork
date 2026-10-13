# risos — Universal RSS/Atom Feed Generator

System that transforms any website into RSS/Atom feeds using YAML configuration files. Each YAML describes a site (URL, CSS/XPath selectors, per-field transform pipeline). A CLI generates the feeds and a GitHub Actions workflow runs periodically, publishing to GitHub Pages.

## Quick Start — Create Your Own Feeds

1. **Fork this repository** on GitHub
2. **Enable GitHub Pages** in your fork: Settings > Pages > Source: "GitHub Actions"
3. **Ask an AI agent** (Copilot, Claude, etc.) to create a new YAML config for any site you want. Use a prompt like:

> Look at `sites/hacker-news.yaml` as a reference. Create a new YAML config in `sites/` that generates an RSS feed from `https://example.com/blog`. Fetch the page, inspect the HTML structure, identify the repeating item elements and the selectors for title, link, date, and summary, then write the YAML with the appropriate transforms.

Hopefully, the agent will inspect the target site's HTML structure, write the appropriate CSS/XPath selectors, and set up any transforms (date parsing, URL resolution, etc.) needed. Commit the new YAML, and the GitHub Actions workflow will start generating feeds automatically every 6 hours.

You can also run it locally to test before pushing — see the Usage section below.

## Installation

```bash
uv sync
```

## Usage

Process all site configs:

```bash
risos generate --all
```

Process a specific site:

```bash
risos generate --site sites/hacker-news.yaml
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--all / --no-all` | `--no-all` | Process all YAMLs in `--sites-dir` |
| `--site PATH` | — | Path to a specific YAML config |
| `--sites-dir PATH` | `sites/` | Directory containing YAML configs |
| `--output-dir PATH` | `output/` | Output directory for generated feeds |
| `-v / --verbose` | off | Enable debug logging |

## YAML Schema

```yaml
feed:
  title: "Site Name"          # Feed title (required)
  link: "https://example.com" # Site URL (required)
  description: "Description"  # Feed description (required)
  language: "en"              # Language code (default: "en")

source:
  url: "https://example.com"  # URL to scrape (required)
  headers:                    # Optional HTTP headers
    User-Agent: "risos/1.0"

selectors:
  item_list:
    css: "div.item"           # CSS selector for items (css OR xpath required)
    # xpath: "//div[@class='item']"
    include_siblings: 0       # Number of sibling elements to include (default: 0)

  fields:
    title:                    # At least 'title' or 'description' required
      css: "h1"              # CSS selector (css OR xpath required)
      # xpath: ".//h1"
      attribute: "text"       # "text" or any HTML attribute (default: "text")
      multiple: false         # Collect all matches (default: false)
      default: null           # Fallback value if not found
      transforms: []          # List of transforms to apply
```

## Available Transforms

| Type | Parameters | Description |
|------|-----------|-------------|
| `regex` | `pattern`, `group` (default: 1) | Extract regex group from value |
| `replace` | `old`, `new` | String replacement |
| `strip` | — | Strip whitespace |
| `strip_html` | — | Remove HTML tags |
| `date_parse` | `format` (optional), `locale` (optional) | Parse date to RFC 822. Supports strptime format, locale-aware parsing via Babel, and heuristic fallback via dateutil |
| `absolute_url` | `base_url` | Resolve relative URLs |
| `truncate` | `max_length` | Truncate text with ellipsis |
| `template` | `pattern` (uses `{value}`) | Apply string template |
| `split` | `separator`, `index` | Split string and pick element |
| `join` | `separator` (default: `", "`) | Join multiple values |

### Transform Examples

```yaml
transforms:
  # Extract first word
  - type: regex
    pattern: "^(\\S+)"

  # Parse date
  - type: date_parse

  # Make URL absolute
  - type: absolute_url
    base_url: "https://example.com"

  # Truncate long text
  - type: truncate
    max_length: 200
```

## GitHub Pages Setup

1. Go to repository Settings > Pages
2. Set Source to "GitHub Actions"
3. The workflow runs every 6 hours and on manual dispatch
4. Feeds are published at `https://<user>.github.io/<repo>/`

## Adding a New Site

1. Create a new YAML file in `sites/` (e.g., `sites/my-site.yaml`)
2. Define `feed`, `source`, and `selectors` sections
3. Test locally: `risos generate --site sites/my-site.yaml`
4. Commit and push — the workflow will pick it up automatically

## Development

```bash
uv sync
uv run ruff format src/ tests/
uv run ruff check src/ tests/
uv run pytest tests/ -v
```
