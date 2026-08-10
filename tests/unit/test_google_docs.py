import pytest

from app.backend.core.google_docs import extract_doc_id, sanitize_material_html


@pytest.mark.parametrize(
    "url, expected_id",
    [
        ("https://docs.google.com/document/d/1AbCdEfGhIjKlMnOp/edit", "1AbCdEfGhIjKlMnOp"),
        ("https://docs.google.com/document/d/1AbCdEfGhIjKlMnOp/edit?usp=sharing", "1AbCdEfGhIjKlMnOp"),
        ("https://docs.google.com/document/d/1AbCdEfGhIjKlMnOp/view", "1AbCdEfGhIjKlMnOp"),
    ],
)
def test_extract_doc_id_from_valid_urls(url, expected_id):
    assert extract_doc_id(url) == expected_id


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/not-a-google-doc",
        "https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOp/edit",
        "not a url at all",
        "",
    ],
)
def test_extract_doc_id_rejects_invalid_urls(url):
    with pytest.raises(ValueError):
        extract_doc_id(url)


def test_sanitize_strips_script_tags():
    dirty = "<p>Ola</p><script>alert('xss')</script>"
    clean = sanitize_material_html(dirty)
    assert "<script>" not in clean
    assert "alert" not in clean
    assert "<p>Ola</p>" in clean


def test_sanitize_strips_onerror_attribute():
    dirty = '<img src="x" onerror="alert(1)">'
    clean = sanitize_material_html(dirty)
    assert "onerror" not in clean


def test_sanitize_keeps_bold_expressed_as_span_font_weight():
    # E exatamente assim que o Google Docs exporta negrito -- span com
    # font-weight no style, nao uma tag <strong>/<b>.
    dirty = '<span style="font-weight:700;color:red;font-family:Arial">Importante</span>'
    clean = sanitize_material_html(dirty)
    assert "font-weight" in clean
    assert "Importante" in clean
    # cor e fonte nao fazem parte da allowlist de CSS -- devem sumir
    assert "color" not in clean
    assert "font-family" not in clean


def test_sanitize_drops_disallowed_tags_but_keeps_text():
    dirty = "<div><iframe src='evil'></iframe>Texto legivel</div>"
    clean = sanitize_material_html(dirty)
    assert "<iframe" not in clean
    assert "Texto legivel" in clean


def test_sanitize_keeps_safe_structural_tags():
    dirty = "<h1>Titulo</h1><ul><li>Item 1</li><li>Item 2</li></ul><table><tr><td>A</td></tr></table>"
    clean = sanitize_material_html(dirty)
    for tag in ("<h1>", "<ul>", "<li>", "<table>", "<tr>", "<td>"):
        assert tag in clean
