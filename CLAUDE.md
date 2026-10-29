# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Personal recipe collection: an MkDocs Material site deployed to GitHub Pages (https://gataky.github.io/syntages/) by `.github/workflows/deploy.yml` on every push to `main`. Set up like `../greek-notes` (same tooling, no PWA).

## Commands

Tools are pinned in `.tool-versions` (asdf: Python, uv); Python packages in `pyproject.toml` + `uv.lock`. `.envrc` (direnv) loads them and `.venv`; the Makefile works without direnv.

```sh
make install   # uv sync
make serve     # dev server at http://127.0.0.1:8000
make build     # mkdocs build --strict (CI fails on any warning)
make upgrade   # uv lock --upgrade
```

uv is configured with `python-preference = "only-system"`, so it uses asdf's Python. MkDocs is capped below 2.0 because Material doesn't support 2.0.

## Recipes

- One Markdown file per recipe in `docs/<category>/`. The folder is the category: nav is auto-generated (no `nav:` in `mkdocs.yml`), and `docs/index.md`'s `<!-- recipes -->` placeholder is replaced with cards grouped by folder.
- The format is documented in `README.md`: front matter (`title`, `serves` or `makes`, `time`, `source`), then `## Method` whose numbered steps carry their ingredients as indented `- ` lines, with optional `### Part` headings. Other `##` sections pass through as Markdown.
- Conventions when converting recipes: grams wherever the source gives them (exact weight conversions like lb/oz → g are fine; never estimate cups → grams), temperatures as `180 °C / 350 °F`, the amount first so it scales, unicode fractions, en dash for ranges.
- The originals are Google Docs in the owner's Drive folder `recipes` (ID `1CSQVNBF4bup8Sgl9p_KSATk5A-r2wUQv`). They're link-shared, so `https://docs.google.com/document/d/<id>/export?format=md` downloads one without signing in.

## How a recipe page is built

1. **`hooks/recipes.py`** (an MkDocs hook) rewrites the `## Method` section of every page in a category folder into HTML: the ingredient list (one `<ul>` per `###` part, in order of first use, merging the same name + unit within a part) followed by the step grid (number button | the step's ingredients | text). It parses each ingredient line into quantity, unit (`UNITS`) and name. A missing Method, or text or an ingredient outside a step, fails the build. Step text and ingredient names are rendered with a separate Markdown instance, so links in them aren't rewritten by MkDocs: write them as built URLs (`../pie-crust/`), not `.md` paths.
2. Scalable amounts become `<span class="q" data-qty data-to data-unit>`, followed by `<span class="u">` when there's a unit. The yield number in `serves`/`makes` gets the same span.
3. **`docs/javascripts/recipe.js`** runs per page via Material's `document$` (instant navigation). It adds the ½×/1×/2×/3× scaler (only if something scales), tick-off for ingredients and steps (saved in `localStorage` per page, with a Reset button), and a keep-screen-on toggle (Wake Lock API, preference saved globally, hidden where unsupported). Its `fmt()` must round like `format_number()` in the hook: decimals for metric units, kitchen fractions otherwise, and 1000 g/ml shown as kg/l.
4. **`docs/stylesheets/recipe.css`** has the palette (terracotta on warm paper, warm slate in dark mode) and the layout. Below 45em the step grid collapses so a step's ingredients sit above its text. Material indents list items with `[dir=ltr]` selectors, so overrides need matching specificity.
