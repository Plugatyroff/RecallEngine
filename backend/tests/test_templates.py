from app.services.templates import Cloze, front_is_empty, render, strip_html

FIELDS = {"Front": "alma", "Back": "<b>apple</b>", "Extra": "", "Picture": '<img src="a.jpg">'}


def test_fields_are_inserted() -> None:
    assert render("{{Front}} = {{Back}}", FIELDS) == "alma = <b>apple</b>"


def test_back_can_repeat_the_front() -> None:
    front = render("{{Front}}", FIELDS)

    assert render("{{FrontSide}}<hr id=answer>{{Back}}", FIELDS, front_side=front) == "alma<hr id=answer><b>apple</b>"


def test_conditional_sections() -> None:
    assert render("{{#Back}}has back{{/Back}}", FIELDS) == "has back"
    assert render("{{#Extra}}has extra{{/Extra}}", FIELDS) == ""
    assert render("{{^Extra}}no extra{{/Extra}}", FIELDS) == "no extra"


def test_nested_sections() -> None:
    assert render("{{#Front}}[{{#Extra}}x{{/Extra}}{{#Back}}y{{/Back}}]{{/Front}}", FIELDS) == "[y]"


def test_a_field_with_only_an_image_is_not_empty() -> None:
    assert render("{{#Picture}}pic{{/Picture}}", FIELDS) == "pic"


def test_text_filter_and_unknown_fields() -> None:
    assert render("{{text:Back}}", FIELDS) == "apple"
    assert render("{{hint:Front}}", FIELDS) == "alma"
    assert render("{{Missing}}", FIELDS) == ""


def test_whitespace_inside_braces_is_allowed() -> None:
    assert render("{{ Front }}", FIELDS) == "alma"


def test_optional_reverse_card_has_an_empty_front() -> None:
    template = "{{#Add Reverse}}{{Back}}{{/Add Reverse}}"

    assert front_is_empty(render(template, {**FIELDS, "Add Reverse": ""}))
    assert not front_is_empty(render(template, {**FIELDS, "Add Reverse": "y"}))


def test_strip_html_gives_plain_text() -> None:
    assert strip_html("<div>núcleo&nbsp;(nm)</div><br>core") == "núcleo (nm) core"


CLOZE_TEXT = {"Text": "The {{c1::determinant}} is zero when {{c2::the matrix is singular::condition}}."}


def test_cloze_front_hides_only_the_tested_gap() -> None:
    assert render("{{cloze:Text}}", CLOZE_TEXT, cloze=Cloze(1, reveal=False)) == (
        'The <span class="cloze">[...]</span> is zero when the matrix is singular.'
    )
    assert render("{{cloze:Text}}", CLOZE_TEXT, cloze=Cloze(2, reveal=False)) == (
        'The determinant is zero when <span class="cloze">[condition]</span>.'  # the hint
    )


def test_cloze_back_reveals_the_tested_gap() -> None:
    assert render("{{cloze:Text}}", CLOZE_TEXT, cloze=Cloze(2, reveal=True)) == (
        'The determinant is zero when <span class="cloze">the matrix is singular</span>.'
    )


def test_cloze_gaps_can_repeat_and_contain_html() -> None:
    fields = {"Text": "{{c1::<b>A</b>}} and {{c1::B}}"}

    assert render("{{cloze:Text}}", fields, cloze=Cloze(1, reveal=False)) == (
        '<span class="cloze">[...]</span> and <span class="cloze">[...]</span>'
    )
