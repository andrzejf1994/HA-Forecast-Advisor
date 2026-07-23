"""Safe Jinja2 template rendering module."""

import logging
from typing import Any

from jinja2 import Environment, TemplateSyntaxError, UndefinedError

_LOGGER = logging.getLogger(__name__)

_ENV = Environment(autoescape=False)


def validate_template_syntax(template_str: str) -> tuple[bool, str | None]:
    """Validate Jinja2 template syntax. Returns (is_valid, error_message)."""
    try:
        _ENV.parse(template_str)
        return True, None
    except TemplateSyntaxError as err:
        return False, f"Syntax error at line {err.lineno}: {err.message}"
    except Exception as err:
        return False, str(err)


def render_template_safely(
    template_str: str,
    context: dict[str, Any],
    fallback: str = "Unavailable",
) -> str:
    """Render a Jinja2 template with context safely without raising exceptions."""
    is_valid, err_msg = validate_template_syntax(template_str)
    if not is_valid:
        _LOGGER.warning("Invalid template syntax: %s", err_msg)
        return fallback

    try:
        template = _ENV.from_string(template_str)
        return str(template.render(context))
    except (UndefinedError, Exception) as err:
        _LOGGER.warning("Error rendering template: %s", err)
        return fallback
