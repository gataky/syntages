# Syntages

Personal recipes, published with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) on GitHub Pages at https://gataky.github.io/syntages/.

## Adding a recipe

1. Put a `.md` file in the category folder under `docs/` (`breads`, `desserts`, `mains`, `sides`, `soups`). A new folder becomes a new category.
2. Commit and push to `main`. The site rebuilds automatically. The sidebar and home page pick the recipe up on their own.

A recipe looks like this:

```markdown
---
title: Banana Bread
makes: 1 loaf                  # or serves: 4, serves: 10–12
time: 10 min prep · 40 min bake
source: https://example.com/   # optional
---

Optional intro text.

## Method

### Dough                      # optional: splits the recipe into parts

1. Heat the oven to 180 °C / 350 °F.
2. Blend everything until smooth.
    - 170 g oat flour
    - 4 large bananas

## Notes                       # any other section is shown as written
```

Each step lists the ingredients it uses, indented four spaces with `- `. The page builds the full ingredient list from these, and adds up an ingredient that appears in several steps with the same name and unit (2 tbsp + 1 tbsp olive oil shows as 3 tbsp).

To scale, an amount has to come first: `1 lemon, zested`, not `zest of 1 lemon`. Write fractions as ½ ⅓ ⅔ ¼ ¾ ⅛ (`1½ cups`). Write ranges as `1–2 tbsp`. Lines with no amount, like `salt and pepper`, are fine.

Conventions: grams wherever the original gives them, and temperatures in both °C and °F.

## Working locally

Tool versions (Python, uv) are pinned in `.tool-versions` for asdf, and Python packages in `pyproject.toml` and `uv.lock`. `.envrc` puts the tools and the `.venv` on your PATH when you `cd` here. Run `direnv allow` once (and again after editing `.envrc`), then:

```sh
make install   # uv sync: create .venv from uv.lock
make serve     # preview at http://127.0.0.1:8000
```

Run `make` to see every target.
