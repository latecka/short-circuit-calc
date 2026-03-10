"""IEC 60909-0 Short-Circuit Calculator - Validators Module.

This module implements validation logic for:
- Individual element validation
- Network-level validation
- Calculation prerequisites
- Out-of-scope detection
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .elements import (
    AsynchronousMotor,
    Busbar,
    ExternalGrid,
    GroundingImpedance,
    Impedance,
    InputMode,
    Line,
    NeutralGrounding,
    NetworkElement,
    SynchronousGenerator,
    Transformer2W,
    Transformer3W,
    ValidationStatus,
)
from .autotransformer import Autotransformer, Z0Source
from .psu import PowerStationUnit
from .network import Network


class ErrorCode(Enum):
    """Validation error codes."""
    E001 = "E001"  # Missing required field
    E002 = "E002"  # Invalid value
    E003 = "E003"  # Reference not found
    E004 = "E004"  # Unsupported configuration
    E005 = "E005"  # Topological error
    E006 = "E006"  # Consistency error
    E007 = "E007"  # PSU validation error


class WarningCode(Enum):
    """Validation warning codes."""
    W001 = "W001"  # OLTC ignored in Z0 model
    W002 = "W002"  # Motor ignored in min calculation
    W003 = "W003"  # Network not fully connected


@dataclass
class ValidationMessage:
    """Validation message with code and details."""
    code: str
    message: str
    element_id: Optional[str] = None
    field: Optional[str] = None
    is_error: bool = True

    def __str__(self) -> str:
        prefix = "ERROR" if self.is_error else "WARNING"
        elem = f" [{self.element_id}]" if self.element_id else ""
        fld = f".{self.field}" if self.field else ""
        return f"{prefix} {self.code}{elem}{fld}: {self.message}"


@dataclass
class ValidationResult:
    """Result of validation process."""
    is_valid: bool
    errors: List[ValidationMessage]
    warnings: List[ValidationMessage]

    @property
    def all_messages(self) -> List[ValidationMessage]:
        return self.errors + self.warnings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": [str(e) for e in self.errors],
            "warnings": [str(w) for w in self.warnings],
        }


class NetworkValidator:
    """Validates network for short-circuit calculation."""

    def __init__(self, network: Network):
        self.network = network
        self.errors: List[ValidationMessage] = []
        self.warnings: List[ValidationMessage] = []

    def validate(self) -> ValidationResult:
        """
        Perform full network validation.

        Returns:
            ValidationResult with errors and warnings
        """
        self.errors.clear()
        self.warnings.clear()

        # Validate structure
        self._validate_buses()
        self._validate_sources()
        self._validate_connectivity()

        # Validate elements
        for element in self.network.elements.values():
            self._validate_element(element)

        # Validate references
        self._validate_references()

        # Validate PSUs
        self._validate_psus()

        # Check for out-of-scope configurations
        self._check_out_of_scope()

        is_valid = len(self.errors) == 0
        return ValidationResult(is_valid, self.errors, self.warnings)

    def _validate_buses(self) -> None:
        """Validate bus definitions."""
        buses = self.network.get_elements_by_type(Busbar)

        if not buses:
            self.errors.append(ValidationMessage(
                ErrorCode.E005.value,
                "Network must have at least one bus"
            ))
            return

        # Check for duplicate IDs
        ids = [b.id for b in buses]
        if len(ids) != len(set(ids)):
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value,
                "Duplicate bus IDs detected"
            ))

        # Validate each bus
        for bus in buses:
            if bus.Un <= 0:
                self.errors.append(ValidationMessage(
                    ErrorCode.E002.value,
                    "Nominal voltage must be positive",
                    element_id=bus.id,
                    field="Un"
                ))

    def _validate_sources(self) -> None:
        """Validate voltage sources."""
        sources = self.network.get_sources()

        if not sources:
            self.errors.append(ValidationMessage(
                ErrorCode.E005.value,
                "Network must have at least one voltage source"
            ))

    def _validate_connectivity(self) -> None:
        """Validate network connectivity."""
        if not self.network.is_connected():
            self.warnings.append(ValidationMessage(
                WarningCode.W003.value,
                "Network is not fully connected - isolated sections detected",
                is_error=False
            ))

    def _validate_element(self, element: NetworkElement) -> None:
        """Validate individual element."""
        if isinstance(element, ExternalGrid):
            self._validate_external_grid(element)
        elif isinstance(element, Line):
            self._validate_line(element)
        elif isinstance(element, Transformer2W):
            self._validate_transformer_2w(element)
        elif isinstance(element, Transformer3W):
            self._validate_transformer_3w(element)
        elif isinstance(element, Autotransformer):
            self._validate_autotransformer(element)
        elif isinstance(element, SynchronousGenerator):
            self._validate_generator(element)
        elif isinstance(element, AsynchronousMotor):
            self._validate_motor(element)

    def _validate_external_grid(self, grid: ExternalGrid) -> None:
        """Validate external grid element."""
        if grid.Sk_max <= 0:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "Sk_max must be positive",
                element_id=grid.id, field="Sk_max"
            ))

        if grid.Sk_min <= 0:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "Sk_min must be positive",
                element_id=grid.id, field="Sk_min"
            ))

        if grid.Sk_min > grid.Sk_max:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "Sk_min cannot exceed Sk_max",
                element_id=grid.id
            ))

        if grid.rx_ratio <= 0:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "rx_ratio must be positive",
                element_id=grid.id, field="rx_ratio"
            ))

        if not grid.bus_id:
            self.errors.append(ValidationMessage(
                ErrorCode.E001.value, "bus_id is required",
                element_id=grid.id, field="bus_id"
            ))

    def _validate_line(self, line: Line) -> None:
        """Validate line element."""
        if line.length <= 0:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "Length must be positive",
                element_id=line.id, field="length"
            ))

        if line.x1_per_km <= 0:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "x1_per_km must be positive",
                element_id=line.id, field="x1_per_km"
            ))

        if line.x0_per_km <= 0:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "x0_per_km must be positive",
                element_id=line.id, field="x0_per_km"
            ))

    def _validate_transformer_2w(self, tr: Transformer2W) -> None:
        """Validate 2-winding transformer."""
        if tr.Sn <= 0:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "Sn must be positive",
                element_id=tr.id, field="Sn"
            ))

        if tr.uk_percent <= 0 or tr.uk_percent >= 100:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "uk_percent must be between 0 and 100",
                element_id=tr.id, field="uk_percent"
            ))

        if not tr.vector_group:
            self.errors.append(ValidationMessage(
                ErrorCode.E001.value, "vector_group is required",
                element_id=tr.id, field="vector_group"
            ))

    def _validate_transformer_3w(self, tr: Transformer3W) -> None:
        """Validate 3-winding transformer."""
        # Basic validation
        for field in ["Sn_hv", "Sn_mv", "Sn_lv"]:
            if getattr(tr, field) <= 0:
                self.errors.append(ValidationMessage(
                    ErrorCode.E002.value, f"{field} must be positive",
                    element_id=tr.id, field=field
                ))

        # Validate uk% consistency
        uk_hv = tr.uk_hv_mv_percent
        uk_lv = tr.uk_hv_lv_percent
        uk_ml = tr.uk_mv_lv_percent

        # Triangle inequality check (simplified)
        if uk_hv + uk_ml < uk_lv or uk_hv + uk_lv < uk_ml or uk_lv + uk_ml < uk_hv:
            self.errors.append(ValidationMessage(
                ErrorCode.E006.value,
                "uk% values violate triangle inequality",
                element_id=tr.id
            ))

    def _validate_autotransformer(self, at: Autotransformer) -> None:
        """Validate autotransformer."""
        errors = at.validate()
        for err in errors:
            code, msg = err.split(": ", 1)
            self.errors.append(ValidationMessage(
                code, msg, element_id=at.id
            ))

    def _validate_generator(self, gen: SynchronousGenerator) -> None:
        """Validate synchronous generator."""
        if gen.Sn <= 0:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "Sn must be positive",
                element_id=gen.id, field="Sn"
            ))

        if gen.Xd_pp <= 0:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "Xd_pp must be positive",
                element_id=gen.id, field="Xd_pp"
            ))

        if gen.cos_phi <= 0 or gen.cos_phi > 1:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "cos_phi must be between 0 and 1",
                element_id=gen.id, field="cos_phi"
            ))

    def _validate_motor(self, motor: AsynchronousMotor) -> None:
        """Validate asynchronous motor."""
        if motor.Ia_In <= 1:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value, "Ia_In must be greater than 1",
                element_id=motor.id, field="Ia_In"
            ))

        if motor.input_mode == InputMode.POWER:
            if not motor.Pn or motor.Pn <= 0:
                self.errors.append(ValidationMessage(
                    ErrorCode.E001.value, "Pn required for power input mode",
                    element_id=motor.id, field="Pn"
                ))
            if not motor.eta or motor.eta <= 0 or motor.eta > 1:
                self.errors.append(ValidationMessage(
                    ErrorCode.E002.value, "eta must be between 0 and 1",
                    element_id=motor.id, field="eta"
                ))
            if not motor.cos_phi or motor.cos_phi <= 0 or motor.cos_phi > 1:
                self.errors.append(ValidationMessage(
                    ErrorCode.E002.value, "cos_phi must be between 0 and 1",
                    element_id=motor.id, field="cos_phi"
                ))
        else:  # CURRENT mode
            if not motor.In or motor.In <= 0:
                self.errors.append(ValidationMessage(
                    ErrorCode.E001.value, "In required for current input mode",
                    element_id=motor.id, field="In"
                ))

    def _validate_references(self) -> None:
        """Validate all element references."""
        for element in self.network.elements.values():
            buses = []

            if hasattr(element, 'bus_id'):
                buses.append(element.bus_id)
            if hasattr(element, 'bus_from'):
                buses.append(element.bus_from)
            if hasattr(element, 'bus_to'):
                buses.append(element.bus_to)
            if hasattr(element, 'bus_hv'):
                buses.append(element.bus_hv)
            if hasattr(element, 'bus_lv'):
                buses.append(element.bus_lv)
            if hasattr(element, 'bus_mv'):
                buses.append(element.bus_mv)

            for bus_id in buses:
                if bus_id and self.network.get_bus(bus_id) is None:
                    self.errors.append(ValidationMessage(
                        ErrorCode.E003.value,
                        f"Referenced bus '{bus_id}' not found",
                        element_id=element.id
                    ))

    def _validate_psus(self) -> None:
        """Validate power station units."""
        psus = self.network.get_psus()

        # Track which generators/transformers are used
        used_generators: Set[str] = set()
        used_transformers: Set[str] = set()

        for psu in psus:
            # Check for duplicate usage
            if psu.generator_id in used_generators:
                self.errors.append(ValidationMessage(
                    ErrorCode.E007.value,
                    f"Generator {psu.generator_id} already used in another PSU",
                    element_id=psu.id
                ))
            used_generators.add(psu.generator_id)

            if psu.transformer_id in used_transformers:
                self.errors.append(ValidationMessage(
                    ErrorCode.E007.value,
                    f"Transformer {psu.transformer_id} already used in another PSU",
                    element_id=psu.id
                ))
            used_transformers.add(psu.transformer_id)

            # Validate references
            gen = self.network.get_element(psu.generator_id)
            tr = self.network.get_element(psu.transformer_id)

            if gen is None:
                self.errors.append(ValidationMessage(
                    ErrorCode.E003.value,
                    f"Generator {psu.generator_id} not found",
                    element_id=psu.id
                ))
            elif not isinstance(gen, SynchronousGenerator):
                self.errors.append(ValidationMessage(
                    ErrorCode.E002.value,
                    f"{psu.generator_id} is not a synchronous generator",
                    element_id=psu.id
                ))

            if tr is None:
                self.errors.append(ValidationMessage(
                    ErrorCode.E003.value,
                    f"Transformer {psu.transformer_id} not found",
                    element_id=psu.id
                ))
            elif not isinstance(tr, (Transformer2W, Transformer3W)):
                self.errors.append(ValidationMessage(
                    ErrorCode.E002.value,
                    f"{psu.transformer_id} is not a transformer",
                    element_id=psu.id
                ))

            # For 3W transformer, check generator_winding
            if isinstance(tr, Transformer3W):
                if not psu.generator_winding:
                    self.errors.append(ValidationMessage(
                        ErrorCode.E001.value,
                        "generator_winding required for 3W transformer",
                        element_id=psu.id
                    ))

    def _check_out_of_scope(self) -> None:
        """Check for out-of-scope configurations."""
        # Check for unsupported transformer configurations
        for element in self.network.elements.values():
            if isinstance(element, Transformer2W):
                # Check for exotic vector groups
                vg = element.vector_group.upper()
                supported_prefixes = ('D', 'Y', 'YN')
                if not any(vg.startswith(p) for p in supported_prefixes):
                    self.errors.append(ValidationMessage(
                        ErrorCode.E004.value,
                        f"Unsupported vector group: {element.vector_group}",
                        element_id=element.id
                    ))


class CalculationValidator:
    """Validates calculation request parameters."""

    VALID_FAULT_TYPES = {"Ik3", "Ik2", "Ik1"}
    VALID_MODES = {"max", "min"}

    def __init__(self, network: Network):
        self.network = network
        self.errors: List[ValidationMessage] = []
        self.warnings: List[ValidationMessage] = []

    def validate_request(
        self,
        fault_types: List[str],
        fault_buses: List[str],
        mode: str
    ) -> ValidationResult:
        """
        Validate calculation request.

        Args:
            fault_types: List of fault types to calculate
            fault_buses: List of bus IDs for fault locations
            mode: "max" or "min"

        Returns:
            ValidationResult
        """
        self.errors.clear()
        self.warnings.clear()

        # Validate mode
        if mode not in self.VALID_MODES:
            self.errors.append(ValidationMessage(
                ErrorCode.E002.value,
                f"Invalid mode '{mode}'. Must be 'max' or 'min'"
            ))

        # Validate fault types
        for ft in fault_types:
            if ft not in self.VALID_FAULT_TYPES:
                self.errors.append(ValidationMessage(
                    ErrorCode.E002.value,
                    f"Invalid fault type '{ft}'. Must be one of {self.VALID_FAULT_TYPES}"
                ))

        # Validate fault buses
        for bus_id in fault_buses:
            if self.network.get_bus(bus_id) is None:
                self.errors.append(ValidationMessage(
                    ErrorCode.E003.value,
                    f"Fault bus '{bus_id}' not found in network"
                ))

        # Check for Z0 availability if Ik1 requested
        if "Ik1" in fault_types:
            self._check_z0_availability(fault_buses)

        # Warn about motor exclusion in min mode
        if mode == "min":
            motors = self.network.get_motors()
            if motors:
                self.warnings.append(ValidationMessage(
                    WarningCode.W002.value,
                    f"{len(motors)} motor(s) will be excluded from min calculation",
                    is_error=False
                ))

        is_valid = len(self.errors) == 0
        return ValidationResult(is_valid, self.errors, self.warnings)

    def _check_z0_availability(self, fault_buses: List[str]) -> None:
        """Check if Z0 path exists to fault buses."""
        # This is a simplified check - full implementation would
        # trace Z0 paths through the network
        has_grounded_source = False

        for source in self.network.get_sources():
            if isinstance(source, ExternalGrid):
                # External grid provides Z0 path
                has_grounded_source = True
                break

        if not has_grounded_source:
            self.warnings.append(ValidationMessage(
                WarningCode.W001.value,
                "No grounded sources found - Ik1 may be zero",
                is_error=False
            ))
