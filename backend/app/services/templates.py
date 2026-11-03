"""Turns a note's fields and a card template into the HTML shown on a card.

Supports the parts of Anki's template syntax used by typical note types:
    {{Field}}                      the field's value
    {{FrontSide}}                  on the back: the rendered front
    {{#Field}} ... {{/Field}}      only if the field is not empty
    {{^Field}} ... {{/Field}}      only if the field is empty
    {{text:Field}}                 the field without HTML tags
    {{cloze:Field}}                a Cloze deletion card (see below)
Other filters (e.g. {{hint:Field}}) currently fall back to the plain field value.

Cloze notes contain gaps written as {{c1::answer}} or {{c1::answer::hint}}. Each gap number
becomes its own card (c1 → card 1, c2 → card 2, ...). On card N, the gaps numbered N are hidden
as [...] (or [hint]) on the front and shown highlighted on the back; other gaps show their text.
"""

import html
import re
from dataclasses import dataclass

_SECTION = re.compile(r"\{\{([#^])\s*([^}]+?)\s*\}\}(.*?)\{\{/\s*\2\s*\}\}", re.DOTALL)
_TAG = re.compile(r"\{\{\s*([^#^/}][^}]*?)\s*\}\}")
_HTML_TAG = re.compile(r"<[^>]+>")
_CLOZE = re.compile(r"\{\{c(\d+)::(.*?)(?:::(.*?))?\}\}", re.DOTALL)


@dataclass(frozen=True)
class Cloze:
    """Which gap a Cloze card tests, and whether its answer is shown (the back) or hidden (the front)."""

    number: int
    reveal: bool


def render_cloze(text: str, cloze: Cloze) -> str:
    def gap(match: re.Match) -> str:
        number, answer, hint = int(match.group(1)), match.group(2), match.group(3)
        if number != cloze.number:
            return answer
        shown = answer if cloze.reveal else f"[{hint or '...'}]"
        return f'<span class="cloze">{shown}</span>'

    return _CLOZE.sub(gap, text)


def strip_html(value: str) -> str:
    """Plain text of an HTML fragment, e.g. for previews."""
    text = _HTML_TAG.sub(" ", value)
    return " ".join(html.unescape(text).split())


def _is_empty(value: str) -> bool:
    return strip_html(value) == "" and "<img" not in value


def render(template: str, fields: dict[str, str], front_side: str = "", cloze: Cloze | None = None) -> str:
    """Render one side of a card.

    Pass the rendered front as `front_side` when rendering the back, and `cloze` for Cloze cards.
    """

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
        if "cloze" in filters and cloze is not None:
            value = render_cloze(value, cloze)
        return strip_html(value) if "text" in filters else value

    return _TAG.sub(tag, template)


def front_is_empty(rendered_front: str) -> bool:
    """Anki creates no card for a template whose front would be empty (e.g. an optional reverse)."""
    return _is_empty(rendered_front)
