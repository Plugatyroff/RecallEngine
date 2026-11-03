"""Turns a note's fields and a card template into the HTML shown on a card.

Supports the parts of Anki's template syntax used by typical note types:
    {{Field}}                      the field's value
    {{FrontSide}}                  on the back: the rendered front
    {{#Field}} ... {{/Field}}      only if the field is not empty
    {{^Field}} ... {{/Field}}      only if the field is empty
    {{text:Field}}                 the field without HTML tags
Other filters (e.g. {{hint:Field}}) currently fall back to the plain field value.
"""

import html
import re

_SECTION = re.compile(r"\{\{([#^])\s*([^}]+?)\s*\}\}(.*?)\{\{/\s*\2\s*\}\}", re.DOTALL)
_TAG = re.compile(r"\{\{\s*([^#^/}][^}]*?)\s*\}\}")
_HTML_TAG = re.compile(r"<[^>]+>")


def strip_html(value: str) -> str:
    """Plain text of an HTML fragment, e.g. for previews."""
    text = _HTML_TAG.sub(" ", value)
    return " ".join(html.unescape(text).split())


def _is_empty(value: str) -> bool:
    return strip_html(value) == "" and "<img" not in value


def render(template: str, fields: dict[str, str], front_side: str = "") -> str:
    """Render one side of a card. Pass the rendered front as `front_side` when rendering the back."""

    def section(match: re.Match) -> str:
        kind, name, body = match.groups()
        shown = not _is_empty(fields.get(name, ""))
        return body if shown == (kind == "#") else ""

    # Sections first, repeatedly, so nested sections work
    previous = None
    while previous != template:
        previous, template = template, _SECTION.sub(section, template)

    def tag(match: re.Match) -> str:
        expression = match.group(1)
        if expression == "FrontSide":
            return front_side
        *filters, name = [part.strip() for part in expression.split(":")]
        value = fields.get(name, "")
        return strip_html(value) if "text" in filters else value

    return _TAG.sub(tag, template)


def front_is_empty(rendered_front: str) -> bool:
    """Anki creates no card for a template whose front would be empty (e.g. an optional reverse)."""
    return _is_empty(rendered_front)
