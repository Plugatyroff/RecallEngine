"""Card HTML must keep its formatting but lose anything that can run code."""

import pytest

from app.services.sanitize import sanitize


@pytest.mark.parametrize(
    "unsafe, expected",
    [
        ("<b>hi</b><script>alert(1)</script>", "<b>hi</b>"),
        ('<img src="a.jpg" onerror="alert(1)">', '<img src="a.jpg">'),
        ('<a href="javascript:alert(1)">x</a>', '<a rel="noopener noreferrer">x</a>'),
        ('<a href="data:text/html,<script>alert(1)</script>">x</a>', '<a rel="noopener noreferrer">x</a>'),
        ('<div onclick="steal()">text</div>', "<div>text</div>"),
        ("<iframe src='https://evil.example'></iframe>after", "after"),
        ('<span style="color: red; background-image: url(x)">c</span>', '<span style="color:red">c</span>'),
    ],
)
def test_executable_content_is_removed(unsafe: str, expected: str) -> None:
    assert sanitize(unsafe) == expected


@pytest.mark.parametrize(
    "card_html",
    [
        '<span class="cloze">[...]</span>',
        "alma<br><hr id=\"answer\"><i>apple</i>",
        '<audio controls="" preload="none" src="hola.mp3"></audio>',
        '<font color="#01c67e">THEOREM 1</font>',
        '<img src="CodeCogsEqn (1).png">',
        '<img src="data:image/png;base64,iVBORw0KGgo=">',
        r"\(\det(A) \neq 0\) and \[x^2\]",
        "a &lt; b",
        "<table><tbody><tr><td>1</td></tr></tbody></table>",
    ],
)
def test_normal_card_content_is_kept(card_html: str) -> None:
    assert sanitize(card_html) == card_html
