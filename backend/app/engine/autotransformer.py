"""IEC 60909-0 Short-Circuit Calculator - Autotransformer Module.

This module implements the autotransformer element with its specific
Z0 model accounting for galvanic coupling between windings.

The autotransformer differs from a regular transformer in that:
1. Windings share a common section (galvanic connection)
2. Z0 transfer is governed by this galvanic coupling
3. Delta tertiary winding provides an alternative Z0 path
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .elements import (
    ComplexImpedance,
    GroundingImpedance,
    NeutralGrounding,
    NetworkElement,
    ValidationStatus,
    Z_INFINITE,
)


class Z0Source:
    """Source of Z0 data for autotransformer."""
    MEASURED = "measured"
    DERIVED = "derived"


@dataclass
class Autotransformer(NetworkElement):
    """
    Autotransformer with galvanic coupling.

    The autotransformer model includes:
    - Standard positive/negative sequence impedance calculation
    - Specific Z0 model for galvanic transfer
    - Optional delta tertiary for Z0 path
    """
    bus_hv: str = ""  # HV side bus
    bus_lv: str = ""  # LV side bus
    Sn: float = 0.0  # Rated power [MVA]
    Un_hv: float = 0.0  # HV rated voltage [kV]
    Un_lv: float = 0.0  # LV rated voltage [kV]
    uk_percent: float = 0.0  # Short-circuit voltage [%]
    Pkr: float = 0.0  # Short-circuit losses [kW]
    vector_group: str = "YNa0"  # Vector group
    has_tertiary_delta: bool = False  # Delta tertiary present
    tertiary_Sn: Optional[float] = None  # Tertiary rated power [MVA]
    neutral_grounding: NeutralGrounding = NeutralGrounding.GROUNDED
    grounding_impedance_id: Optional[str] = None
    Z0_source: str = Z0Source.DERIVED  # "measured" or "derived"
    Z0_measured_r: Optional[float] = None  # Measured R0 [Ohm]
    Z0_measured_x: Optional[float] = None  # Measured X0 [Ohm]
    tap_position: float = 0.0  # Tap position [%]

    # Runtime reference to grounding impedance element
    _grounding_impedance: Optional[GroundingImpedance] = None

    @property
    def element_type(self) -> str:
        return "autotransformer"

    @property
    def transformation_ratio(self) -> float:
        """Transformation ratio n = Un_hv / Un_lv."""
        return self.Un_hv / self.Un_lv if self.Un_lv > 0 else 1.0

    @property
    def common_winding_factor(self) -> float:
        """
        Factor representing the common winding portion.

        For autotransformer: alpha = 1 - 1/n = 1 - Un_lv/Un_hv
        This represents the fraction of the HV winding that is
        common to both HV and LV circuits.
        """
        n = self.transformation_ratio
        return 1 - (1 / n) if n > 1 else 0

    def get_impedance_z1z2(self, ref_voltage: float) -> ComplexImpedance:
        """
        Calculate Z1 = Z2 impedance referred to ref_voltage.

        Args:
            ref_voltage: Reference voltage [kV]

        Returns:
            Z1 = Z2 impedance
        """
        # Base impedance at HV side
        Zbase = (self.Un_hv ** 2) / self.Sn

        # Short-circuit impedance magnitude
        Zk = (self.uk_percent / 100) * Zbase

        # Resistance from losses
        Rk = (self.Pkr / 1000) * (self.Un_hv ** 2) / (self.Sn ** 2)

        # Reactance
        if Zk ** 2 > Rk ** 2:
            Xk = math.sqrt(Zk ** 2 - Rk ** 2)
        else:
            Xk = 0.0

        # Refer to ref_voltage
        voltage_ratio = (ref_voltage / self.Un_hv) ** 2
        R1 = Rk * voltage_ratio
        X1 = Xk * voltage_ratio

        return ComplexImpedance(R1, X1)

    def get_z0(self, ref_voltage: float) -> ComplexImpedance:
        """
        Calculate Z0 impedance with autotransformer-specific model.

        The Z0 model for autotransformers accounts for:
        1. Galvanic coupling - Z0 transfers directly through common winding
        2. Delta tertiary - provides parallel path for zero-sequence current
        3. Neutral grounding - affects Z0 availability

        Args:
            ref_voltage: Reference voltage [kV]

        Returns:
            Z0 impedance
        """
        # Check if Z0 is blocked
        if self.neutral_grounding == NeutralGrounding.ISOLATED and not self.has_tertiary_delta:
            return Z_INFINITE

        # Use measured Z0 if available
        if self.Z0_source == Z0Source.MEASURED:
            if self.Z0_measured_r is not None and self.Z0_measured_x is not None:
                voltage_ratio = (ref_voltage / self.Un_hv) ** 2
                return ComplexImpedance(
                    self.Z0_measured_r * voltage_ratio,
                    self.Z0_measured_x * voltage_ratio
                )

        # Derive Z0 from Z1 and autotransformer model
        Z1 = self.get_impedance_z1z2(ref_voltage)

        # For autotransformer with grounded neutral:
        # Z0 depends on the winding configuration and common winding
        alpha = self.common_winding_factor
        n = self.transformation_ratio

        if self.has_tertiary_delta:
            # Delta tertiary provides parallel path
            # Z0_eff = Z0_main || Z0_tertiary
            Z0_main = self._calculate_z0_galvanic(Z1, alpha, n)
            Z0_tertiary = self._calculate_z0_tertiary(ref_voltage)
            return Z0_main.parallel(Z0_tertiary)
        else:
            # Only galvanic path
            Z0_galvanic = self._calculate_z0_galvanic(Z1, alpha, n)

            # Add grounding impedance if applicable
            if self.neutral_grounding == NeutralGrounding.IMPEDANCE:
                Zg = self._get_grounding_impedance()
                # Grounding impedance appears as 3*Zg in zero sequence
                Z0_galvanic = Z0_galvanic + (Zg * 3)

            return Z0_galvanic

    def _calculate_z0_galvanic(
        self, Z1: ComplexImpedance, alpha: float, n: float
    ) -> ComplexImpedance:
        """
        Calculate Z0 through galvanic coupling.

        For an autotransformer with grounded neutral, the zero-sequence
        impedance seen from the HV side includes the effect of the
        common winding and series winding.

        Simplified model: Z0 ≈ Z1 * k_auto
        where k_auto depends on the winding configuration.

        For typical autotransformers: k_auto ≈ 0.8 to 1.2
        """
        # Autotransformer Z0 factor (typical approximation)
        # This is a simplified model - actual value depends on
        # detailed winding geometry and should be measured
        k_auto = 1.0

        # For grounded neutral, Z0 transfers with modification
        if self.neutral_grounding == NeutralGrounding.GROUNDED:
            # Direct galvanic transfer
            k_auto = 0.9  # Typical factor for grounded autotransformer
        elif self.neutral_grounding == NeutralGrounding.IMPEDANCE:
            k_auto = 1.0

        return Z1 * k_auto

    def _calculate_z0_tertiary(self, ref_voltage: float) -> ComplexImpedance:
        """
        Calculate Z0 path through delta tertiary.

        The delta tertiary winding provides a closed path for zero-sequence
        currents, effectively reducing the overall Z0.
        """
        if not self.has_tertiary_delta or not self.tertiary_Sn:
            return Z_INFINITE

        # Tertiary impedance (approximate as 10% typical)
        # In practice this should come from tertiary winding data
        uk_tertiary = 10.0  # Typical tertiary uk%

        Zbase_tertiary = (self.Un_hv ** 2) / self.tertiary_Sn
        Z_tertiary_mag = (uk_tertiary / 100) * Zbase_tertiary

        # Refer to ref_voltage
        voltage_ratio = (ref_voltage / self.Un_hv) ** 2
        Z_tertiary = Z_tertiary_mag * voltage_ratio

        # Assume mostly reactive
        return ComplexImpedance(Z_tertiary * 0.1, Z_tertiary * 0.995)

    def _get_grounding_impedance(self) -> ComplexImpedance:
        """Get grounding impedance value."""
        if self._grounding_impedance is not None:
            return self._grounding_impedance.get_impedance()
        return ComplexImpedance(0, 0)

    def set_grounding_impedance(self, gi: GroundingImpedance) -> None:
        """Set reference to grounding impedance element."""
        self._grounding_impedance = gi

    def get_impedance(
        self, ref_voltage: float
    ) -> tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """
        Calculate Z1, Z2, Z0 impedances referred to ref_voltage.

        Args:
            ref_voltage: Reference voltage [kV]

        Returns:
            Tuple of (Z1, Z2, Z0) as ComplexImpedance
        """
        Z1 = self.get_impedance_z1z2(ref_voltage)
        Z2 = Z1  # Z2 = Z1 for transformers
        Z0 = self.get_z0(ref_voltage)

        return Z1, Z2, Z0

    def is_z0_blocked(self) -> bool:
        """Check if Z0 path is blocked."""
        return (
            self.neutral_grounding == NeutralGrounding.ISOLATED
            and not self.has_tertiary_delta
        )

    def validate(self) -> list[str]:
        """
        Validate autotransformer parameters.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if self.Sn <= 0:
            errors.append("E002: Sn must be positive")

        if self.Un_hv <= 0:
            errors.append("E002: Un_hv must be positive")

        if self.Un_lv <= 0:
            errors.append("E002: Un_lv must be positive")

        if self.Un_lv >= self.Un_hv:
            errors.append("E002: Un_lv must be less than Un_hv for autotransformer")

        if self.uk_percent <= 0 or self.uk_percent >= 100:
            errors.append("E002: uk_percent must be between 0 and 100")

        if self.Pkr < 0:
            errors.append("E002: Pkr must be non-negative")

        if self.has_tertiary_delta and not self.tertiary_Sn:
            errors.append("E001: tertiary_Sn required when has_tertiary_delta is true")

        if self.neutral_grounding == NeutralGrounding.IMPEDANCE:
            if not self.grounding_impedance_id:
                errors.append("E001: grounding_impedance_id required for impedance grounding")

        if self.Z0_source == Z0Source.MEASURED:
            if self.Z0_measured_r is None or self.Z0_measured_x is None:
                errors.append("E001: Z0_measured_r and Z0_measured_x required when Z0_source is measured")

        if not self.vector_group.upper().startswith("YNA"):
            errors.append("E002: Invalid vector group for autotransformer (expected YNaX)")

        self.validation_status = (
            ValidationStatus.ERROR if errors else ValidationStatus.VALID
        )

        return errors
