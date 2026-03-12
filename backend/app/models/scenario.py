"""Scenario model for calculation scenarios."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship

from .base import Base, generate_uuid
from .calculation import CalculationMode

if TYPE_CHECKING:
    from .project import Project
    from .calculation import CalculationRun


class Scenario(Base):
    """
    Calculation scenario - defines which elements are included in a calculation.

    Each scenario belongs to a project and can specify:
    - Which elements are active (included in calculation)
    - Calculation mode (max/min)

    element_states structure:
    {
        "transformers_2w": {"T1": true, "T2": false},
        "lines": {"L1": true, "L2": true},
        "generators": {"G1": false},
        ...
    }

    Elements not listed are assumed to be active (true).
    """
    __tablename__ = "scenarios"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    calculation_mode = Column(
        Enum(CalculationMode),
        nullable=False,
        default=CalculationMode.MAX
    )

    # JSON object: { element_type: { element_id: boolean } }
    element_states = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="scenarios")
    calculation_runs = relationship(
        "CalculationRun",
        back_populates="scenario",
        cascade="all, delete-orphan"
    )

    def is_element_active(self, element_type: str, element_id: str) -> bool:
        """Check if an element is active in this scenario.

        Supports both legacy shape:
        {
            "lines": {"L1": true}
        }

        and breaker-centric shape:
        {
            "breakers": {"L1": true, "T1_HV": true, "T1_LV": false}
        }

        Compatibility rule:
        - If a breaker key for the element is explicitly present, breaker state wins.
        - If breaker key is missing, fallback to legacy per-type element state.
        """

        def _legacy_state() -> bool:
            type_states = self.element_states.get(element_type, {})
            return type_states.get(element_id, True)

        breakers = self.element_states.get("breakers")
        if isinstance(breakers, dict):
            if element_type in {"transformers_2w", "autotransformers"}:
                side_keys = [f"{element_id}_HV", f"{element_id}_LV"]
                if element_id in breakers:
                    return breakers[element_id]
                if any(k in breakers for k in side_keys):
                    return all(breakers.get(k, True) for k in side_keys)
                return _legacy_state()

            if element_type == "transformers_3w":
                side_keys = [f"{element_id}_HV", f"{element_id}_MV", f"{element_id}_LV"]
                if element_id in breakers:
                    return breakers[element_id]
                if any(k in breakers for k in side_keys):
                    return all(breakers.get(k, True) for k in side_keys)
                return _legacy_state()

            if element_id in breakers:
                return breakers[element_id]
            return _legacy_state()

        return _legacy_state()

    def set_element_state(self, element_type: str, element_id: str, active: bool):
        """Set the active state of an element."""
        if element_type not in self.element_states:
            self.element_states[element_type] = {}
        self.element_states[element_type][element_id] = active

    def get_active_elements(self, elements: dict) -> dict:
        """
        Filter elements dictionary to only include active elements.

        Args:
            elements: Full elements dictionary from NetworkVersion

        Returns:
            Filtered elements dictionary with only active elements
        """
        filtered = {}
        for elem_type, elem_list in elements.items():
            if not isinstance(elem_list, list):
                continue
            filtered[elem_type] = [
                elem for elem in elem_list
                if self.is_element_active(elem_type, elem.get('id', ''))
            ]
        return filtered

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "calculation_mode": self.calculation_mode.value,
            "element_states": self.element_states,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
