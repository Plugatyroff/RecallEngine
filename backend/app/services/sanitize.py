"""Removes anything executable from card HTML before it is sent to the app.

Cards can come from anywhere (e.g. decks downloaded from AnkiWeb), and the card view runs
JavaScript for math rendering, so card HTML must not be able to run code of its own: no <script>,
no event attributes such as onclick, no javascript: links. Everything not explicitly allowed below
is removed; the text inside removed tags is kept.

Uses nh3, a Python binding of the Rust "ammonia" sanitizer, which parses HTML like a browser does.
"""

import nh3

TAGS = nh3.ALLOWED_TAGS | {"audio", "font"}

ATTRIBUTES = {tag: set(names) for tag, names in nh3.ALLOWED_ATTRIBUTES.items()}
# On every tag: classes (e.g. Cloze highlighting) and inline styles (filtered below)
ATTRIBUTES["*"] = {"class", "style", "dir", "lang", "title"}
ATTRIBUTES["audio"] = {"controls", "src", "preload"}
ATTRIBUTES["font"] = {"color", "size", "face"}
ATTRIBUTES["hr"] = ATTRIBUTES.get("hr", set()) | {"id"}  # Anki's <hr id=answer>

# CSS properties allowed in style="..." — visual only
STYLE_PROPERTIES = {
    "color", "background-color", "font-size", "font-weight", "font-style", "font-family",
    "text-align", "text-decoration", "vertical-align", "width", "height", "max-width",
    "margin", "margin-left", "margin-right", "margin-top", "margin-bottom",
    "padding", "padding-left", "padding-right", "padding-top", "padding-bottom",
    "border", "display", "white-space", "line-height",
}

URL_SCHEMES = {"http", "https", "data"}  # data: is accepted for images only (see _filter)


def _filter(tag: str, attribute: str, value: str) -> str | None:
    # Images may be embedded as data: URLs; elsewhere (e.g. links) data: could open a page
    if value.lstrip().lower().startswith("data:") and not (tag == "img" and attribute == "src"):
        return None
    return value


def sanitize(html: str) -> str:
    return nh3.clean(
        html,
        tags=TAGS,
        attributes=ATTRIBUTES,
        attribute_filter=_filter,
        url_schemes=URL_SCHEMES,
        filter_style_properties=STYLE_PROPERTIES,
        link_rel="noopener noreferrer",
    )
