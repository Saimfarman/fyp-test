from app.prototypes import TEMPLATES, _clean_text


def test_templates_have_versioned_sections():
    assert TEMPLATES
    assert all(template["version"] and template["sections"] for template in TEMPLATES.values())


def test_editor_text_is_bounded_and_normalized():
    value = _clean_text("  A   local\nbusiness  " + "x" * 600, 40)

    assert value.startswith("A local business ")
    assert len(value) == 40
