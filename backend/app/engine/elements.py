"""IEC 60909-0 Short-Circuit Calculator - Network Elements.

This module defines data classes for all supported network elements
and their impedance calculations (Z1, Z2, Z0).
"""

from __future__ import annotations

import cmath
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NeutralGrounding(Enum):
    """Neutral point grounding type."""
    GROUNDED = "grounded"
    ISOLATED = "isolated"
    IMPEDANCE = "impedance"


class InputMode(Enum):
    """Motor input parameter mode."""
    POWER = "power"
    CURRENT = "current"


class ValidationStatus(Enum):
    """Element validation status."""
    PENDING = "pending"
    VALID = "valid"
    ERROR = "error"


@dataclass
class ComplexImpedance:
    """Complex impedance representation."""
    r: float  # Resistance [Ohm]
    x: float  # Reactance [Ohm]

    @property
    def z(self) -> complex:
        """Complex impedance."""
        return complex(self.r, self.x)

    @property
    def magnitude(self) -> float:
        """Impedance magnitude |Z|."""
        return abs(self.z)

    @property
    def angle(self) -> float:
        """Impedance angle in radians."""
        return cmath.phase(self.z)

    @classmethod
    def from_complex(cls, z: complex) -> ComplexImpedance:
        """Create from complex number."""
        return cls(r=z.real, x=z.imag)

    @classmethod
    def from_polar(cls, magnitude: float, angle_rad: float) -> ComplexImpedance:
        """Create from polar form (magnitude, angle in radians)."""
        z = cmath.rect(magnitude, angle_rad)
        return cls(r=z.real, x=z.imag)

    def __add__(self, other: ComplexImpedance) -> ComplexImpedance:
        return ComplexImpedance(self.r + other.r, self.x + other.x)

    def __mul__(self, scalar: float) -> ComplexImpedance:
        return ComplexImpedance(self.r * scalar, self.x * scalar)

    def parallel(self, other: ComplexImpedance) -> ComplexImpedance:
        """Parallel combination of two impedances."""
        z1, z2 = self.z, other.z
        if abs(z1 + z2) < 1e-12:
            return ComplexImpedance(0, 0)
        z_par = (z1 * z2) / (z1 + z2)
        return ComplexImpedance.from_complex(z_par)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {"r": self.r, "x": self.x}


# Infinite impedance for blocked Z0 paths
Z_INFINITE = ComplexImpedance(r=1e12, x=1e12)


@dataclass
class NetworkElement(ABC):
    """Base class for all network elements."""
    id: str
    name: Optional[str] = None
    in_service: bool = True
    validation_status: ValidationStatus = ValidationStatus.PENDING

    @property
    @abstractmethod
    def element_type(self) -> str:
        """Element type identifier."""
        pass


@dataclass
class Busbar(NetworkElement):
    """Network node / busbar."""
    Un: float = 0.0  # Nominal voltage [kV]
    is_reference: bool = False

    @property
    def element_type(self) -> str:
        return "busbar"


@dataclass
class ExternalGrid(NetworkElement):
    """External supply network / equivalent source."""
    bus_id: str = ""
    Sk_max: float = 0.0  # Maximum short-circuit power [MVA]
    Sk_min: float = 0.0  # Minimum short-circuit power [MVA]
    rx_ratio: float = 0.1  # R/X ratio
    c_max: float = 1.1  # Voltage factor for max calculation
    c_min: float = 1.0  # Voltage factor for min calculation
    Z0_Z1_ratio: float = 1.0  # Z0/Z1 ratio
    X0_X1_ratio: float = 1.0  # X0/X1 ratio
    R0_X0_ratio: Optional[float] = None  # R0/X0 ratio

    @property
    def element_type(self) -> str:
        return "external_grid"

    def get_impedance(self, Un: float, is_max: bool = True) -> tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """
        Calculate Z1, Z2, Z0 impedances.

        Args:
            Un: Nominal voltage at connection point [kV]
            is_max: True for max calculation, False for min

        Returns:
            Tuple of (Z1, Z2, Z0) as ComplexImpedance
        """
        Sk = self.Sk_max if is_max else self.Sk_min
        c = self.c_max if is_max else self.c_min

        # Z1 calculation: Z = c * Un² / Sk
        Z1_mag = c * (Un ** 2) / Sk

        # From R/X ratio: Z = sqrt(R² + X²), R/X = rx_ratio
        # X = Z / sqrt(1 + rx²), R = X * rx
        X1 = Z1_mag / math.sqrt(1 + self.rx_ratio ** 2)
        R1 = X1 * self.rx_ratio

        Z1 = ComplexImpedance(R1, X1)
        Z2 = ComplexImpedance(R1, X1)  # Z2 = Z1 assumption

        # Z0 calculation
        X0 = X1 * self.X0_X1_ratio
        r0_x0 = self.R0_X0_ratio if self.R0_X0_ratio is not None else self.rx_ratio
        R0 = X0 * r0_x0
        Z0 = ComplexImpedance(R0, X0)

        return Z1, Z2, Z0


@dataclass
class Line(NetworkElement):
    """Overhead line or cable."""
    bus_from: str = ""
    bus_to: str = ""
    length: float = 0.0  # Length [km]
    r1_per_km: float = 0.0  # Positive sequence resistance [Ohm/km]
    x1_per_km: float = 0.0  # Positive sequence reactance [Ohm/km]
    r0_per_km: float = 0.0  # Zero sequence resistance [Ohm/km]
    x0_per_km: float = 0.0  # Zero sequence reactance [Ohm/km]
    b1_per_km: float = 0.0  # Positive sequence susceptance [uS/km]
    parallel_lines: int = 1  # Number of parallel lines
    is_cable: bool = False  # True for cable, False for overhead line
    cable_type: Optional[str] = None

    @property
    def element_type(self) -> str:
        return "cable" if self.is_cable else "overhead_line"

    def get_impedance(self) -> tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """
        Calculate Z1, Z2, Z0 impedances.

        Returns:
            Tuple of (Z1, Z2, Z0) as ComplexImpedance
        """
        factor = self.length / self.parallel_lines

        R1 = self.r1_per_km * factor
        X1 = self.x1_per_km * factor
        R0 = self.r0_per_km * factor
        X0 = self.x0_per_km * factor

        Z1 = ComplexImpedance(R1, X1)
        Z2 = ComplexImpedance(R1, X1)  # Z2 = Z1 for lines
        Z0 = ComplexImpedance(R0, X0)

        return Z1, Z2, Z0


@dataclass
class Transformer2W(NetworkElement):
    """Two-winding transformer."""
    bus_hv: str = ""
    bus_lv: str = ""
    Sn: float = 0.0  # Rated power [MVA]
    Un_hv: float = 0.0  # HV rated voltage [kV]
    Un_lv: float = 0.0  # LV rated voltage [kV]
    uk_percent: float = 0.0  # Short-circuit voltage [%]
    Pkr: float = 0.0  # Short-circuit losses [kW]
    vector_group: str = ""  # e.g., "Dyn11", "YNyn0"
    tap_position: float = 0.0  # Tap position [%]
    tap_side: str = "hv"  # "hv" or "lv"
    neutral_grounding_hv: NeutralGrounding = NeutralGrounding.ISOLATED
    neutral_grounding_lv: NeutralGrounding = NeutralGrounding.ISOLATED
    grounding_impedance_hv_id: Optional[str] = None
    grounding_impedance_lv_id: Optional[str] = None

    @property
    def element_type(self) -> str:
        return "transformer_2w"

    @property
    def transformation_ratio(self) -> float:
        """Transformation ratio Un_hv / Un_lv."""
        return self.Un_hv / self.Un_lv if self.Un_lv > 0 else 1.0

    def get_impedance(self, ref_voltage: float) -> tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """
        Calculate Z1, Z2, Z0 impedances referred to ref_voltage.

        Args:
            ref_voltage: Reference voltage [kV]

        Returns:
            Tuple of (Z1, Z2, Z0) as ComplexImpedance
        """
        # Base impedance at HV side
        Zbase = (self.Un_hv ** 2) / self.Sn  # Ohm

        # Short-circuit impedance
        Zk = (self.uk_percent / 100) * Zbase

        # Resistance from losses: Pkr = 3 * I² * R = Sn * (R/Z) * (uk/100)
        # R = Pkr * Un² / (Sn² * 1000) [kW -> MW conversion]
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

        Z1 = ComplexImpedance(R1, X1)
        Z2 = ComplexImpedance(R1, X1)  # Z2 = Z1

        # Z0 depends on vector group and grounding
        Z0 = self._calculate_z0(Z1)

        return Z1, Z2, Z0

    def _calculate_z0(self, Z1: ComplexImpedance) -> ComplexImpedance:
        """Calculate Z0 based on vector group and grounding."""
        vg = self.vector_group.upper()

        # Parse vector group
        hv_winding = vg[0] if vg else 'Y'  # D, Y, or YN
        hv_grounded = vg.startswith('YN')

        # LV winding - look for lowercase after first character
        lv_part = self.vector_group[1:] if len(self.vector_group) > 1 else ''
        lv_grounded = 'yn' in lv_part.lower() or 'zn' in lv_part.lower()

        # Apply grounding settings
        if self.neutral_grounding_hv == NeutralGrounding.GROUNDED:
            hv_grounded = True
        elif self.neutral_grounding_hv == NeutralGrounding.ISOLATED:
            hv_grounded = hv_grounded  # Keep from vector group

        if self.neutral_grounding_lv == NeutralGrounding.GROUNDED:
            lv_grounded = True
        elif self.neutral_grounding_lv == NeutralGrounding.ISOLATED:
            lv_grounded = lv_grounded  # Keep from vector group

        # Z0 transfer rules
        if hv_winding == 'D':
            # Delta on HV blocks Z0 from HV side
            if lv_grounded:
                # Z0 available on LV side only
                return Z1 * 1.0  # Simplified: Z0 ≈ Z1 for Dyn
            else:
                return Z_INFINITE
        elif hv_grounded and lv_grounded:
            # Both sides grounded - Z0 passes through
            return Z1 * 1.0  # Simplified: Z0 ≈ Z1
        elif hv_grounded or lv_grounded:
            # One side grounded
            return Z1 * 1.0
        else:
            # Neither grounded
            return Z_INFINITE

    def is_z0_blocked(self, from_side: str = "hv") -> bool:
        """Check if Z0 is blocked from specified side."""
        Z1, _, Z0 = self.get_impedance(self.Un_hv)
        return Z0.magnitude > 1e10


@dataclass
class Transformer3W(NetworkElement):
    """Three-winding transformer."""
    bus_hv: str = ""
    bus_mv: str = ""
    bus_lv: str = ""
    Sn_hv: float = 0.0  # HV rated power [MVA]
    Sn_mv: float = 0.0  # MV rated power [MVA]
    Sn_lv: float = 0.0  # LV rated power [MVA]
    Un_hv: float = 0.0  # HV rated voltage [kV]
    Un_mv: float = 0.0  # MV rated voltage [kV]
    Un_lv: float = 0.0  # LV rated voltage [kV]
    uk_hv_mv_percent: float = 0.0  # Short-circuit voltage HV-MV [%]
    uk_hv_lv_percent: float = 0.0  # Short-circuit voltage HV-LV [%]
    uk_mv_lv_percent: float = 0.0  # Short-circuit voltage MV-LV [%]
    Pkr_hv_mv: float = 0.0  # Short-circuit losses HV-MV [kW]
    Pkr_hv_lv: float = 0.0  # Short-circuit losses HV-LV [kW]
    Pkr_mv_lv: float = 0.0  # Short-circuit losses MV-LV [kW]
    vector_group_hv_mv: str = ""
    vector_group_hv_lv: str = ""
    tap_position: float = 0.0
    tap_side: str = "hv"

    @property
    def element_type(self) -> str:
        return "transformer_3w"

    def get_star_impedances(self, ref_voltage: float) -> tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """
        Calculate star-equivalent impedances Z_H, Z_M, Z_L referred to ref_voltage.

        The three-winding transformer is modeled as a star connection
        of three impedances from each winding to a virtual neutral point.

        Returns:
            Tuple of (Z_H, Z_M, Z_L) as ComplexImpedance
        """
        # Use HV MVA as reference
        Sn_ref = self.Sn_hv
        Zbase = (self.Un_hv ** 2) / Sn_ref

        # Convert uk% to impedances (referred to HV)
        Z_hv_mv = (self.uk_hv_mv_percent / 100) * Zbase
        Z_hv_lv = (self.uk_hv_lv_percent / 100) * Zbase
        Z_mv_lv = (self.uk_mv_lv_percent / 100) * Zbase * (self.Un_hv / self.Un_mv) ** 2

        # Star equivalent: Z_H = (Z_hv_mv + Z_hv_lv - Z_mv_lv) / 2
        Z_H = (Z_hv_mv + Z_hv_lv - Z_mv_lv) / 2
        Z_M = (Z_hv_mv + Z_mv_lv - Z_hv_lv) / 2
        Z_L = (Z_hv_lv + Z_mv_lv - Z_hv_mv) / 2

        # Ensure non-negative (can happen with measurement tolerances)
        Z_H = max(Z_H, 0.001)
        Z_M = max(Z_M, 0.001)
        Z_L = max(Z_L, 0.001)

        # Calculate R from losses (simplified - assume proportional distribution)
        total_losses = self.Pkr_hv_mv + self.Pkr_hv_lv + self.Pkr_mv_lv
        if total_losses > 0:
            R_H = (self.Pkr_hv_mv / 1000) * (self.Un_hv ** 2) / (self.Sn_hv ** 2) / 2
            R_M = (self.Pkr_hv_mv / 1000) * (self.Un_hv ** 2) / (self.Sn_hv ** 2) / 2
            R_L = (self.Pkr_hv_lv / 1000) * (self.Un_hv ** 2) / (self.Sn_hv ** 2) / 2
        else:
            R_H = R_M = R_L = 0.0

        # Calculate X from Z and R
        X_H = math.sqrt(max(Z_H ** 2 - R_H ** 2, 0))
        X_M = math.sqrt(max(Z_M ** 2 - R_M ** 2, 0))
        X_L = math.sqrt(max(Z_L ** 2 - R_L ** 2, 0))

        # Refer to ref_voltage
        voltage_ratio = (ref_voltage / self.Un_hv) ** 2

        return (
            ComplexImpedance(R_H * voltage_ratio, X_H * voltage_ratio),
            ComplexImpedance(R_M * voltage_ratio, X_M * voltage_ratio),
            ComplexImpedance(R_L * voltage_ratio, X_L * voltage_ratio)
        )


@dataclass
class SynchronousGenerator(NetworkElement):
    """Synchronous generator."""
    bus_id: str = ""
    Sn: float = 0.0  # Rated power [MVA]
    Un: float = 0.0  # Rated voltage [kV]
    Xd_pp: float = 0.0  # Subtransient reactance Xd'' [%]
    Ra: float = 0.0  # Stator resistance [%]
    cos_phi: float = 0.85  # Power factor
    connection: str = "direct"  # "direct" or "via_transformer"

    @property
    def element_type(self) -> str:
        return "synchronous_generator"

    def get_impedance(self, ref_voltage: float) -> tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """
        Calculate Z1, Z2, Z0 impedances referred to ref_voltage.

        Returns:
            Tuple of (Z1, Z2, Z0) as ComplexImpedance
        """
        # Base impedance
        Zbase = (self.Un ** 2) / self.Sn

        # Z1 from Xd'' and Ra
        X1 = (self.Xd_pp / 100) * Zbase
        R1 = (self.Ra / 100) * Zbase

        # Refer to ref_voltage
        voltage_ratio = (ref_voltage / self.Un) ** 2
        R1 *= voltage_ratio
        X1 *= voltage_ratio

        Z1 = ComplexImpedance(R1, X1)
        Z2 = ComplexImpedance(R1, X1)  # Z2 ≈ Z1 for synchronous generators
        Z0 = Z_INFINITE  # Generator neutral usually not grounded directly

        return Z1, Z2, Z0

    def get_KG(self, Un_network: float) -> float:
        """
        Calculate correction factor KG for direct connection.

        IEC 60909-0 §3.6.1, equations 17-18

        Args:
            Un_network: Network nominal voltage at connection point [kV]

        Returns:
            Correction factor KG
        """
        sin_phi = math.sqrt(1 - self.cos_phi ** 2)
        xd_pp_pu = self.Xd_pp / 100

        # KG = Un / (UrG * (1 + xd'' * sin(phi)))
        KG = Un_network / (self.Un * (1 + xd_pp_pu * sin_phi))

        return KG


@dataclass
class AsynchronousMotor(NetworkElement):
    """Asynchronous motor."""
    bus_id: str = ""
    Un: float = 0.0  # Rated voltage [kV]
    input_mode: InputMode = InputMode.POWER
    # Power mode inputs
    Pn: Optional[float] = None  # Rated mechanical power [kW]
    eta: Optional[float] = None  # Efficiency
    cos_phi: Optional[float] = None  # Power factor
    # Current mode inputs
    In: Optional[float] = None  # Rated current [A]
    # Common inputs
    Ia_In: float = 0.0  # Starting current ratio
    pole_pairs: int = 1  # Number of pole pairs
    include_in_sc: bool = True  # Include in short-circuit calculation

    @property
    def element_type(self) -> str:
        return "asynchronous_motor"

    def get_rated_current(self) -> float:
        """Calculate or return rated current [A]."""
        if self.input_mode == InputMode.CURRENT:
            return self.In or 0.0
        else:
            # In = Pn / (sqrt(3) * Un * eta * cos_phi)
            if self.Pn and self.eta and self.cos_phi and self.Un > 0:
                return (self.Pn) / (math.sqrt(3) * self.Un * self.eta * self.cos_phi)
            return 0.0

    def get_rx_ratio(self) -> float:
        """
        Get R/X ratio according to IEC 60909-0 §3.8.

        Returns:
            R/X ratio
        """
        Pn_per_pole = (self.Pn or 0) / self.pole_pairs / 1000  # Convert to MW

        if self.Un > 1.0:  # > 1 kV
            if Pn_per_pole >= 1.0:  # >= 1 MW per pole pair
                return 0.10
            else:
                return 0.15
        else:  # <= 1 kV
            return 0.42

    def get_impedance(self, ref_voltage: float) -> tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """
        Calculate Z1, Z2, Z0 impedances referred to ref_voltage.

        Returns:
            Tuple of (Z1, Z2, Z0) as ComplexImpedance
        """
        In = self.get_rated_current()
        if In <= 0 or self.Ia_In <= 0:
            return Z_INFINITE, Z_INFINITE, Z_INFINITE

        # Starting current
        Ia = In * self.Ia_In

        # Motor impedance magnitude: Zm = Un / (sqrt(3) * Ia)
        Zm = (self.Un * 1000) / (math.sqrt(3) * Ia)  # kV to V

        # R/X ratio
        rx = self.get_rx_ratio()

        # Calculate R and X
        X1 = Zm / math.sqrt(1 + rx ** 2)
        R1 = X1 * rx

        # Refer to ref_voltage
        voltage_ratio = (ref_voltage / self.Un) ** 2
        R1 *= voltage_ratio
        X1 *= voltage_ratio

        Z1 = ComplexImpedance(R1, X1)
        Z2 = ComplexImpedance(R1, X1)  # Z2 ≈ Z1 for motors
        Z0 = Z_INFINITE  # Motor does not provide Z0 path

        return Z1, Z2, Z0

    def contributes_to_fault(self, fault_type: str, is_max: bool) -> bool:
        """
        Check if motor contributes to specified fault type.

        Args:
            fault_type: "Ik3", "Ik2", or "Ik1"
            is_max: True for max calculation

        Returns:
            True if motor contributes
        """
        if not self.include_in_sc:
            return False

        if not is_max:
            # Motors excluded from min calculation (IEC 60909-0)
            return False

        if fault_type == "Ik1":
            # Motor has Z0 = infinity, no contribution to single-phase faults
            return False

        return True


@dataclass
class GroundingImpedance(NetworkElement):
    """Neutral point grounding impedance."""
    R: float = 0.0  # Resistance [Ohm]
    X: float = 0.0  # Reactance [Ohm]

    @property
    def element_type(self) -> str:
        return "grounding_impedance"

    def get_impedance(self) -> ComplexImpedance:
        """Get grounding impedance."""
        return ComplexImpedance(self.R, self.X)


@dataclass
class Impedance(NetworkElement):
    """General impedance element."""
    bus_from: str = ""
    bus_to: str = ""
    R: float = 0.0  # Resistance [Ohm]
    X: float = 0.0  # Reactance [Ohm]
    R0: Optional[float] = None  # Zero sequence resistance [Ohm]
    X0: Optional[float] = None  # Zero sequence reactance [Ohm]

    @property
    def element_type(self) -> str:
        return "impedance"

    def get_impedance(self) -> tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """
        Calculate Z1, Z2, Z0 impedances.

        Returns:
            Tuple of (Z1, Z2, Z0) as ComplexImpedance
        """
        Z1 = ComplexImpedance(self.R, self.X)
        Z2 = ComplexImpedance(self.R, self.X)

        R0 = self.R0 if self.R0 is not None else self.R
        X0 = self.X0 if self.X0 is not None else self.X
        Z0 = ComplexImpedance(R0, X0)

        return Z1, Z2, Z0
