"""Output manager for managing user-configured entity definitions."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OutputDefinition:
    """Definition of a user-configured entity output."""

    output_id: str
    platform: str
    name: str
    unique_id: str
    enabled: bool = True
    period_id: str | None = None
    value_path: str = ""
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    template: str | None = None
    attributes: Mapping[str, str] | None = None


class OutputManager:
    """Manager for custom entity outputs CRUD."""

    def __init__(self) -> None:
        """Initialize OutputManager."""
        self.outputs: dict[str, OutputDefinition] = {}

    def add_output(self, definition: OutputDefinition) -> None:
        """Add or update an output definition."""
        self.outputs[definition.output_id] = definition

    def remove_output(self, output_id: str) -> None:
        """Remove an output definition by ID."""
        self.outputs.pop(output_id, None)

    def get_outputs_for_platform(self, platform: str) -> list[OutputDefinition]:
        """Get output definitions for a given platform."""
        return [out for out in self.outputs.values() if out.platform == platform and out.enabled]
