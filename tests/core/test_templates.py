"""Unit tests for safe template rendering."""

from custom_components.forecast_fusion.core.templates import (
    render_template_safely,
    validate_template_syntax,
)


def test_validate_template_syntax():
    """Test syntax validation."""
    valid, err = validate_template_syntax("Hello {{ name }}!")
    assert valid is True
    assert err is None

    invalid, err2 = validate_template_syntax("Hello {{ name ")
    assert invalid is False
    assert err2 is not None


def test_render_template_safely():
    """Test rendering valid and fallback template cases."""
    context = {"name": "World", "temp": 22.5}
    rendered = render_template_safely("Hello {{ name }}, temp is {{ temp }}°C", context)
    assert rendered == "Hello World, temp is 22.5°C"

    # Fallback on undefined variable / syntax error
    err_rendered = render_template_safely("Invalid {{ name ", context, fallback="N/A")
    assert err_rendered == "N/A"
