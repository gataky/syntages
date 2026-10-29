"""Build recipe pages and the home page listing.

A recipe is a Markdown file in a category folder (docs/<category>/<name>.md)
with a `## Method` section. Under it, each numbered step lists the ingredients
it uses as an indented `- ` list, and `### ` headings split the method into
parts (Dough, Filling). This hook turns that section into the page's
ingredient list (in order of first use, adding up an ingredient that several
steps use in the same unit) followed by the step grid. Front matter gives the
title and the line under it: `serves` or `makes`, `time`, `source`.

Amounts that can scale are wrapped in `<span class="q" data-qty>`, which
docs/javascripts/recipe.js rewrites when the servings change.
"""

import html
import re
from fractions import Fraction

import markdown as markdown_lib
from mkdocs.exceptions import PluginError
from mkdocs.utils import meta as meta_lib

FRACTIONS = {"½": "1/2", "⅓": "1/3", "⅔": "2/3", "¼": "1/4", "¾": "3/4", "⅛": "1/8"}
_FRAC = "[" + "".join(FRACTIONS) + "]"
NUMBER = rf"(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?\s?{_FRAC}?|{_FRAC})"
QUANTITY = rf"(?P<qty>{NUMBER})(?:\s*(?:–|-|to)\s*(?P<to>{NUMBER}))?"

# Units are scaled with the number. Metric ones are shown as decimals, the
# rest as kitchen fractions (see recipe.js).
UNITS = "g kg ml dl l tsp tbsp cup cups oz lb can cans box boxes pkg clove cloves bunch pinch".split()
SINGULAR = {"cups": "cup", "cans": "can", "boxes": "box", "cloves": "clove"}
METRIC = {"g", "kg", "ml", "dl", "l"}

INGREDIENT = re.compile(
    rf"^{QUANTITY}\s*(?:(?P<unit>{'|'.join(UNITS)})\.?(?=\s|$))?\s*(?P<name>.*)$"
)
YIELD = re.compile(QUANTITY)

recipes = []  # (category, title, meta, src_uri) for the home page


def number(text):
    text = text.strip()
    for glyph, frac in FRACTIONS.items():
        text = text.replace(glyph, " " + frac)
    return sum(Fraction(part) for part in text.split())


def format_number(value, unit=None):
    """Same rounding as fmt() in recipe.js, for totals of merged ingredients."""
    if unit in METRIC or value >= 10:
        return f"{float(value):.1f}".removesuffix(".0") if value < 10 else str(round(value))
    whole, part = divmod(value, 1)
    glyph = {Fraction(0): "", Fraction(1, 2): "½", Fraction(1, 3): "⅓", Fraction(2, 3): "⅔",
             Fraction(1, 4): "¼", Fraction(3, 4): "¾", Fraction(1, 8): "⅛"}.get(part)
    if glyph is None:
        return f"{float(value):.2f}".rstrip("0").rstrip(".")
    return f"{whole or ''}{glyph}" or "0"


def unit_for(value, unit):
    plural = {v: k for k, v in SINGULAR.items()}
    return plural[unit] if value > 1 and unit in plural else unit


def quantity_span(qty, to, unit, text):
    attrs = f' data-qty="{float(qty):g}"'
    if to is not None:
        attrs += f' data-to="{float(to):g}"'
    if unit:
        attrs += f' data-unit="{unit}"'
    return f'<span class="q"{attrs}>{html.escape(text)}</span>'


class Recipe:
    def __init__(self, page, config):
        self.page = page
        self.md = markdown_lib.Markdown(
            extensions=config["markdown_extensions"], extension_configs=config["mdx_configs"]
        )

    def fail(self, message):
        raise PluginError(f"{self.page.file.src_uri}: {message}")

    def render(self, text, inline=False):
        out = self.md.reset().convert(text)
        if inline and out.startswith("<p>") and out.endswith("</p>") and out.count("<p>") == 1:
            out = out[3:-4]
        return out

    # -- parsing ---------------------------------------------------------

    def parse_method(self, text):
        groups, group, step = [], None, None
        for line in text.splitlines():
            if m := re.match(r"###\s+(.+?)\s*$", line):
                group = {"title": m[1], "steps": []}
                groups.append(group)
                step = None
            elif m := re.match(r"\d+\.(?:\s+(.*))?$", line):
                if group is None:
                    group = {"title": None, "steps": []}
                    groups.append(group)
                step = {"text": [m[1] or ""], "ingredients": []}
                group["steps"].append(step)
            elif m := re.match(r"\s{2,}- (.+)$", line):
                if step is None:
                    self.fail(f"ingredient outside a step: {line.strip()!r}")
                step["ingredients"].append(self.parse_ingredient(m[1]))
            elif line.strip():
                if step is None:
                    self.fail(f"text in Method outside a step: {line.strip()!r}")
                step["text"].append(line.removeprefix("    "))
            elif step is not None:
                step["text"].append("")
        return groups

    def parse_ingredient(self, text):
        m = INGREDIENT.match(text)
        if not m:
            return {"qty": None, "unit": None, "amount": "", "name": text}
        unit = m["unit"]
        amount = text[: m.start("name")].strip()
        return {
            "qty": number(m["qty"]),
            "to": number(m["to"]) if m["to"] else None,
            "unit": unit,
            "amount": amount,
            "name": m["name"],
        }

    # -- rendering -------------------------------------------------------

    def amount_html(self, ing):
        if ing["qty"] is None:
            return ""
        unit = ing["unit"]
        number_text = ing["amount"].removesuffix(".").removesuffix(unit or "").strip()
        out = quantity_span(ing["qty"], ing["to"], SINGULAR.get(unit, unit), number_text)
        if unit:
            out += f' <span class="u">{html.escape(unit)}</span>'
        return out

    def ingredient_html(self, ing):
        return (
            f'<span class="amt">{self.amount_html(ing)}</span>'
            f'<span class="ing">{self.render(ing["name"], inline=True)}</span>'
        )

    def shopping_list(self, groups):
        """Every ingredient once per group, in order of first use."""
        out = ['<section class="recipe-ingredients">', '<h2 id="ingredients">Ingredients</h2>']
        for group in groups:
            merged = {}
            for step in group["steps"]:
                for ing in step["ingredients"]:
                    unit = SINGULAR.get(ing["unit"], ing["unit"])
                    key = (unit, ing["name"].lower())
                    prev = merged.get(key)
                    if prev and ing["qty"] is not None and prev["qty"] is not None \
                            and prev["to"] is None and ing["to"] is None:
                        total = prev["qty"] + ing["qty"]
                        shown = unit_for(total, unit)
                        merged[key] = {**prev, "qty": total, "unit": shown,
                                       "amount": f"{format_number(total, unit)} {shown or ''}"}
                    elif prev:
                        merged[(key, id(ing))] = ing
                    else:
                        merged[key] = ing
            if not merged:
                continue
            if group["title"]:
                out.append(f"<h3>{html.escape(group['title'])}</h3>")
            out.append("<ul>")
            out += [
                f'<li><label><input type="checkbox">{self.ingredient_html(ing)}</label></li>'
                for ing in merged.values()
            ]
            out.append("</ul>")
        out.append("</section>")
        return "\n".join(out)

    def steps(self, groups):
        out = ['<section class="recipe-method">', '<h2 id="method">Method</h2>']
        for group in groups:
            if group["title"]:
                out.append(f"<h3>{html.escape(group['title'])}</h3>")
            out.append('<ol class="recipe-steps">')
            for n, step in enumerate(group["steps"], 1):
                ings = "".join(f"<li>{self.ingredient_html(i)}</li>" for i in step["ingredients"])
                text = "\n".join(step["text"]).strip()
                out.append(
                    '<li class="recipe-step">'
                    f'<button class="step-num" type="button" aria-pressed="false" '
                    f'title="Mark step done">{n}</button>'
                    f'<ul class="step-ingredients">{ings}</ul>'
                    f'<div class="step-text">{self.render(text) if text else ""}</div>'
                    "</li>"
                )
            out.append("</ol>")
        out.append("</section>")
        return "\n".join(out)

    def header(self):
        meta = self.page.meta
        parts = []
        for key, label in (("serves", "Serves"), ("makes", "Makes")):
            if key in meta:
                text = str(meta[key])
                m = YIELD.search(text)
                if m:
                    qty = number(m["qty"])
                    to = number(m["to"]) if m["to"] else None
                    text = html.escape(text[: m.start()]) + quantity_span(
                        qty, to, None, m[0]) + html.escape(text[m.end():])
                else:
                    text = html.escape(text)
                parts.append(f"{label} {text}")
        if "time" in meta:
            parts.append(html.escape(str(meta["time"])))
        if "source" in meta:
            parts.append(f'<a href="{html.escape(meta["source"])}">Source</a>')
        line = " · ".join(parts)
        return (
            f'<h1>{html.escape(self.page.title)}</h1>\n'
            f'<p class="recipe-meta">{line}</p>\n'
            '<div class="recipe-tools"></div>'
        )

    def build(self, markdown):
        sections = re.split(r"^## +(.+?)\s*$", markdown, flags=re.M)
        out = [self.header(), sections[0].strip()]
        found = False
        for title, body in zip(sections[1::2], sections[2::2]):
            if title == "Method":
                groups = self.parse_method(body)
                out += ['<div class="recipe">', self.shopping_list(groups), self.steps(groups), "</div>"]
                found = True
            else:
                out.append(f"## {title}\n\n{body.strip()}")
        if not found:
            self.fail("no '## Method' section")
        return "\n\n".join(part for part in out if part)


def is_recipe(file):
    return "/" in file.src_uri and not file.src_uri.endswith("index.md")


def on_files(files, config):
    recipes.clear()
    for file in files.documentation_pages():
        if is_recipe(file):
            _, meta = meta_lib.get_data(file.content_string)
            title = meta.get("title") or file.name.replace("-", " ").capitalize()
            recipes.append((file.src_uri.split("/")[0], title, meta, file.src_uri))
    return files


def on_page_markdown(markdown, page, config, files):
    if page.is_homepage:
        return markdown.replace("<!-- recipes -->", listing())
    if is_recipe(page.file):
        page.meta.setdefault("hide", []).append("toc")
        return Recipe(page, config).build(markdown)
    return markdown


def listing():
    out = []
    for category in sorted({r[0] for r in recipes}):
        out.append(f"## {category.replace('-', ' ').capitalize()}\n")
        out.append('<div class="grid cards" markdown>\n')
        for _, title, meta, src in sorted((r for r in recipes if r[0] == category), key=lambda r: r[1]):
            out.append(f"-   [**{title}**]({src})\n")
            detail = " · ".join(
                str(meta[k]) if k == "time" else f"{k.capitalize()} {meta[k]}"
                for k in ("serves", "makes", "time") if k in meta
            )
            if detail:
                out.append(f"    {detail}\n")
        out.append("</div>\n")
    return "\n".join(out)
