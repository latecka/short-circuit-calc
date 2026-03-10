"""IEC 60909-0 Short-Circuit Calculator - Main Calculation Module.

This module implements the IEC 60909-0 short-circuit calculation methods:
- Three-phase fault (Ik3)
- Two-phase fault (Ik2)
- Single-phase to ground fault (Ik1)
- Peak current (ip)
- Correction factors (c, KG, KT, KS, KSO)

The calculation follows the equivalent voltage source method per IEC 60909-0.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .elements import (
    AsynchronousMotor,
    Busbar,
    ComplexImpedance,
    ExternalGrid,
    Line,
    SynchronousGenerator,
    Transformer2W,
    Transformer3W,
    Z_INFINITE,
)
from .autotransformer import Autotransformer
from .psu import PowerStationUnit
from .network import Network
from .validators import NetworkValidator, CalculationValidator, ValidationResult


# IEC 60909-0 voltage factors (Table 1)
C_FACTORS = {
    # Voltage range: (c_max, c_min)
    "LV": (1.05, 0.95),      # Low voltage (Un <= 1 kV)
    "MV": (1.10, 1.00),      # Medium voltage (1 kV < Un <= 35 kV)
    "HV": (1.10, 1.00),      # High voltage (Un > 35 kV)
}


def get_c_factor(Un: float, is_max: bool = True) -> float:
    """
    Get voltage factor c according to IEC 60909-0 Table 1.

    Args:
        Un: Nominal voltage [kV]
        is_max: True for maximum, False for minimum short-circuit

    Returns:
        Voltage factor c
    """
    if Un <= 1.0:
        c_max, c_min = C_FACTORS["LV"]
    elif Un <= 35.0:
        c_max, c_min = C_FACTORS["MV"]
    else:
        c_max, c_min = C_FACTORS["HV"]

    return c_max if is_max else c_min


@dataclass
class FaultResult:
    """Result for a single fault calculation."""
    bus_id: str
    fault_type: str  # "Ik3", "Ik2", "Ik1"
    Ik: float  # Initial short-circuit current [kA]
    ip: float  # Peak short-circuit current [kA]
    Zk: ComplexImpedance  # Equivalent fault impedance
    Z1: ComplexImpedance  # Positive sequence impedance
    Z2: ComplexImpedance  # Negative sequence impedance
    Z0: Optional[ComplexImpedance]  # Zero sequence impedance
    R_X_ratio: float  # R/X ratio at fault location
    c_factor: float  # Voltage factor used
    correction_factors: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    source_contributions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "bus_id": self.bus_id,
            "fault_type": self.fault_type,
            "Ik_kA": round(self.Ik, 4),
            "ip_kA": round(self.ip, 4),
            "Zk": self.Zk.to_dict(),
            "Z1": self.Z1.to_dict(),
            "Z2": self.Z2.to_dict(),
            "Z0": self.Z0.to_dict() if self.Z0 else None,
            "R_X_ratio": round(self.R_X_ratio, 4),
            "c_factor": self.c_factor,
            "correction_factors": self.correction_factors,
            "warnings": self.warnings,
            "assumptions": self.assumptions,
            "source_contributions": self.source_contributions,
        }


@dataclass
class CalculationRun:
    """Complete calculation run with all results."""
    network_name: str
    mode: str  # "max" or "min"
    fault_types: List[str]
    fault_buses: List[str]
    results: List[FaultResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    engine_version: str = "1.0.0"

    @property
    def is_success(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "network_name": self.network_name,
            "mode": self.mode,
            "fault_types": self.fault_types,
            "fault_buses": self.fault_buses,
            "results": [r.to_dict() for r in self.results],
            "errors": self.errors,
            "engine_version": self.engine_version,
            "is_success": self.is_success,
        }


class ShortCircuitCalculator:
    """
    IEC 60909-0 Short-Circuit Calculator.

    Implements the equivalent voltage source method for calculating
    short-circuit currents in three-phase AC systems.
    """

    VERSION = "1.0.0"

    def __init__(self, network: Network):
        """
        Initialize calculator with network.

        Args:
            network: Network model to calculate
        """
        self.network = network
        self._impedance_cache: Dict[str, Tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]] = {}

    def calculate(
        self,
        fault_types: List[str],
        fault_buses: List[str],
        mode: str = "max"
    ) -> CalculationRun:
        """
        Run short-circuit calculation.

        Args:
            fault_types: List of fault types ["Ik3", "Ik2", "Ik1"]
            fault_buses: List of bus IDs for fault locations
            mode: "max" or "min"

        Returns:
            CalculationRun with all results
        """
        run = CalculationRun(
            network_name=self.network.name,
            mode=mode,
            fault_types=fault_types,
            fault_buses=fault_buses,
            engine_version=self.VERSION,
        )

        # Validate network
        net_validator = NetworkValidator(self.network)
        net_result = net_validator.validate()

        if not net_result.is_valid:
            run.errors = [str(e) for e in net_result.errors]
            return run

        # Validate calculation request
        calc_validator = CalculationValidator(self.network)
        calc_result = calc_validator.validate_request(fault_types, fault_buses, mode)

        if not calc_result.is_valid:
            run.errors = [str(e) for e in calc_result.errors]
            return run

        # Resolve PSU references
        self.network.resolve_psu_references()
        self.network.resolve_grounding_references()

        is_max = (mode == "max")

        # Calculate for each fault bus and type
        for bus_id in fault_buses:
            for fault_type in fault_types:
                try:
                    result = self._calculate_fault(bus_id, fault_type, is_max)
                    run.results.append(result)
                except Exception as e:
                    run.errors.append(f"Calculation failed for {fault_type} at {bus_id}: {str(e)}")

        return run

    def _calculate_fault(
        self,
        bus_id: str,
        fault_type: str,
        is_max: bool
    ) -> FaultResult:
        """
        Calculate single fault.

        Args:
            bus_id: Fault location bus ID
            fault_type: "Ik3", "Ik2", or "Ik1"
            is_max: True for max calculation

        Returns:
            FaultResult
        """
        bus = self.network.get_bus(bus_id)
        if bus is None:
            raise ValueError(f"Bus {bus_id} not found")

        Un = bus.Un
        c = get_c_factor(Un, is_max)

        # Calculate sequence impedances at fault location
        Z1, Z2, Z0 = self._calculate_thevenin_impedance(bus_id, is_max)

        # Calculate fault current based on type
        if fault_type == "Ik3":
            Ik, Zk = self._calculate_ik3(Un, c, Z1)
        elif fault_type == "Ik2":
            Ik, Zk = self._calculate_ik2(Un, c, Z1, Z2)
        elif fault_type == "Ik1":
            Ik, Zk = self._calculate_ik1(Un, c, Z1, Z2, Z0)
        else:
            raise ValueError(f"Unknown fault type: {fault_type}")

        # Calculate peak current
        R_X = Zk.r / Zk.x if abs(Zk.x) > 1e-10 else 0
        ip = self._calculate_ip(Ik, R_X)

        # Collect correction factors used
        correction_factors = self._get_correction_factors(is_max)

        # Build result
        result = FaultResult(
            bus_id=bus_id,
            fault_type=fault_type,
            Ik=Ik,
            ip=ip,
            Zk=Zk,
            Z1=Z1,
            Z2=Z2,
            Z0=Z0 if fault_type == "Ik1" else None,
            R_X_ratio=R_X,
            c_factor=c,
            correction_factors=correction_factors,
        )

        # Add warnings
        if fault_type == "Ik1" and Z0.magnitude > 1e10:
            result.warnings.append("Z0 is infinite - no ground fault path")
            result.Ik = 0.0
            result.ip = 0.0

        if not is_max:
            motors = self.network.get_motors()
            if motors:
                result.assumptions.append(
                    f"Motors excluded from min calculation ({len(motors)} motor(s))"
                )

        return result

    def _calculate_thevenin_impedance(
        self,
        bus_id: str,
        is_max: bool
    ) -> Tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """
        Calculate Thevenin equivalent impedance at fault bus.

        This simplified implementation calculates the parallel combination
        of all source impedances seen from the fault location.

        Args:
            bus_id: Fault location bus ID
            is_max: True for max calculation

        Returns:
            Tuple of (Z1, Z2, Z0)
        """
        bus = self.network.get_bus(bus_id)
        Un = bus.Un if bus else 1.0

        Z1_total = ComplexImpedance(0, 0)
        Z2_total = ComplexImpedance(0, 0)
        Z0_total = ComplexImpedance(0, 0)

        has_source = False

        # Collect impedances from all sources
        for source in self.network.get_sources():
            if isinstance(source, ExternalGrid):
                Z1, Z2, Z0 = source.get_impedance(Un, is_max)

                # Add transformer impedance if source is not at fault bus
                if source.bus_id != bus_id:
                    Z_path = self._get_path_impedance(source.bus_id, bus_id, Un)
                    if Z_path:
                        Z1 = Z1 + Z_path[0]
                        Z2 = Z2 + Z_path[1]
                        Z0 = Z0 + Z_path[2]

                # Parallel combination
                if has_source:
                    Z1_total = Z1_total.parallel(Z1)
                    Z2_total = Z2_total.parallel(Z2)
                    if Z0.magnitude < 1e10 and Z0_total.magnitude < 1e10:
                        Z0_total = Z0_total.parallel(Z0)
                else:
                    Z1_total = Z1
                    Z2_total = Z2
                    Z0_total = Z0
                    has_source = True

            elif isinstance(source, SynchronousGenerator):
                # Check if generator is part of PSU
                psu = self._find_psu_for_generator(source.id)
                if psu:
                    # Use PSU combined impedance
                    c = get_c_factor(Un, is_max)
                    Z1, Z2, Z0 = psu.get_combined_impedance(Un, c)
                else:
                    # Direct connection - apply KG
                    Z1, Z2, Z0 = source.get_impedance(Un)
                    KG = source.get_KG(Un)
                    Z1 = Z1 * (1 / KG)  # Adjust for correction factor

                # Add path impedance
                if source.bus_id != bus_id:
                    Z_path = self._get_path_impedance(source.bus_id, bus_id, Un)
                    if Z_path:
                        Z1 = Z1 + Z_path[0]
                        Z2 = Z2 + Z_path[1]
                        # Z0 from generator is infinite, use path Z0

                # Parallel combination
                if has_source:
                    Z1_total = Z1_total.parallel(Z1)
                    Z2_total = Z2_total.parallel(Z2)
                else:
                    Z1_total = Z1
                    Z2_total = Z2
                    Z0_total = Z0
                    has_source = True

        # Add motor contributions for max calculation
        if is_max:
            for motor in self.network.get_motors():
                if motor.include_in_sc and motor.in_service:
                    Z1_m, Z2_m, _ = motor.get_impedance(Un)

                    # Add path impedance
                    if motor.bus_id != bus_id:
                        Z_path = self._get_path_impedance(motor.bus_id, bus_id, Un)
                        if Z_path:
                            Z1_m = Z1_m + Z_path[0]
                            Z2_m = Z2_m + Z_path[1]

                    if Z1_m.magnitude < 1e10:
                        Z1_total = Z1_total.parallel(Z1_m)
                        Z2_total = Z2_total.parallel(Z2_m)

        return Z1_total, Z2_total, Z0_total

    def _get_path_impedance(
        self,
        from_bus: str,
        to_bus: str,
        ref_voltage: float
    ) -> Optional[Tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]]:
        """
        Get total impedance along path between buses.

        This is a simplified BFS-based path finding that returns
        the series impedance along the shortest path.
        """
        if from_bus == to_bus:
            return ComplexImpedance(0, 0), ComplexImpedance(0, 0), ComplexImpedance(0, 0)

        # BFS to find path
        visited = set()
        queue = [(from_bus, [], [])]  # (current_bus, path, elements)

        while queue:
            current, path, elements = queue.pop(0)

            if current in visited:
                continue
            visited.add(current)

            if current == to_bus:
                # Found path - calculate total impedance
                Z1_total = ComplexImpedance(0, 0)
                Z2_total = ComplexImpedance(0, 0)
                Z0_total = ComplexImpedance(0, 0)

                for elem in elements:
                    Z1, Z2, Z0 = self._get_element_sequence_impedance(elem, ref_voltage)
                    Z1_total = Z1_total + Z1
                    Z2_total = Z2_total + Z2
                    if Z0.magnitude < 1e10:
                        Z0_total = Z0_total + Z0
                    else:
                        Z0_total = Z0

                return Z1_total, Z2_total, Z0_total

            # Explore neighbors
            for elem in self.network.get_elements_at_bus(current):
                buses = self._get_element_buses(elem)
                for next_bus in buses:
                    if next_bus != current and next_bus not in visited:
                        queue.append((next_bus, path + [current], elements + [elem]))

        return None

    def _get_element_buses(self, element) -> List[str]:
        """Get buses connected by element."""
        if hasattr(element, 'bus_from') and hasattr(element, 'bus_to'):
            return [element.bus_from, element.bus_to]
        elif hasattr(element, 'bus_hv') and hasattr(element, 'bus_lv'):
            buses = [element.bus_hv, element.bus_lv]
            if hasattr(element, 'bus_mv'):
                buses.append(element.bus_mv)
            return buses
        elif hasattr(element, 'bus_id'):
            return [element.bus_id]
        return []

    def _get_element_sequence_impedance(
        self,
        element,
        ref_voltage: float
    ) -> Tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """Get sequence impedances for element."""
        if isinstance(element, Line):
            return element.get_impedance()
        elif isinstance(element, (Transformer2W, Autotransformer)):
            return element.get_impedance(ref_voltage)
        elif isinstance(element, Transformer3W):
            # Simplified - use HV-LV path
            Z_H, Z_M, Z_L = element.get_star_impedances(ref_voltage)
            return Z_H + Z_L, Z_H + Z_L, Z_H + Z_L
        else:
            return ComplexImpedance(0, 0), ComplexImpedance(0, 0), ComplexImpedance(0, 0)

    def _find_psu_for_generator(self, generator_id: str) -> Optional[PowerStationUnit]:
        """Find PSU containing specified generator."""
        for psu in self.network.get_psus():
            if psu.generator_id == generator_id:
                return psu
        return None

    def _calculate_ik3(
        self,
        Un: float,
        c: float,
        Z1: ComplexImpedance
    ) -> Tuple[float, ComplexImpedance]:
        """
        Calculate three-phase short-circuit current.

        Ik3'' = c * Un / (sqrt(3) * |Z1|)

        Args:
            Un: Nominal voltage [kV]
            c: Voltage factor
            Z1: Positive sequence impedance

        Returns:
            Tuple of (Ik in kA, equivalent impedance)
        """
        if Z1.magnitude < 1e-10:
            return float('inf'), Z1

        # Equivalent voltage source
        E = c * Un / math.sqrt(3)  # kV, phase voltage

        # Short-circuit current (kA)
        Ik = E / Z1.magnitude

        return Ik, Z1

    def _calculate_ik2(
        self,
        Un: float,
        c: float,
        Z1: ComplexImpedance,
        Z2: ComplexImpedance
    ) -> Tuple[float, ComplexImpedance]:
        """
        Calculate two-phase short-circuit current.

        Ik2'' = c * Un / |Z1 + Z2|

        For most equipment Z2 ≈ Z1, so Ik2 ≈ (sqrt(3)/2) * Ik3

        Args:
            Un: Nominal voltage [kV]
            c: Voltage factor
            Z1: Positive sequence impedance
            Z2: Negative sequence impedance

        Returns:
            Tuple of (Ik in kA, equivalent impedance)
        """
        Zk = Z1 + Z2

        if Zk.magnitude < 1e-10:
            return float('inf'), Zk

        # Equivalent voltage
        E = c * Un  # Line voltage

        # Short-circuit current (kA)
        Ik = E / Zk.magnitude

        return Ik, Zk

    def _calculate_ik1(
        self,
        Un: float,
        c: float,
        Z1: ComplexImpedance,
        Z2: ComplexImpedance,
        Z0: ComplexImpedance
    ) -> Tuple[float, ComplexImpedance]:
        """
        Calculate single-phase to ground short-circuit current.

        Ik1'' = sqrt(3) * c * Un / |Z1 + Z2 + Z0|

        Args:
            Un: Nominal voltage [kV]
            c: Voltage factor
            Z1: Positive sequence impedance
            Z2: Negative sequence impedance
            Z0: Zero sequence impedance

        Returns:
            Tuple of (Ik in kA, equivalent impedance)
        """
        # Check for blocked Z0
        if Z0.magnitude > 1e10:
            Zk = Z1 + Z2 + Z0
            return 0.0, Zk

        Zk = Z1 + Z2 + Z0

        if Zk.magnitude < 1e-10:
            return float('inf'), Zk

        # Equivalent voltage
        E = math.sqrt(3) * c * Un

        # Short-circuit current (kA)
        Ik = E / Zk.magnitude

        return Ik, Zk

    def _calculate_ip(self, Ik: float, R_X: float) -> float:
        """
        Calculate peak short-circuit current.

        ip = kappa * sqrt(2) * Ik''

        where kappa depends on R/X ratio (IEC 60909-0 eq. 54)

        Args:
            Ik: Initial short-circuit current [kA]
            R_X: R/X ratio at fault location

        Returns:
            Peak current [kA]
        """
        if R_X <= 0:
            kappa = 2.0  # Maximum value for R/X = 0
        else:
            # IEC 60909-0 equation 54
            kappa = 1.02 + 0.98 * math.exp(-3 * R_X)

        ip = kappa * math.sqrt(2) * Ik

        return ip

    def _get_correction_factors(self, is_max: bool) -> Dict[str, float]:
        """Collect all correction factors used."""
        factors = {}

        # Voltage factors
        for bus in self.network.get_elements_by_type(Busbar):
            c = get_c_factor(bus.Un, is_max)
            factors[f"c_{bus.id}"] = c

        # Generator factors
        for gen in self.network.get_elements_by_type(SynchronousGenerator):
            bus = self.network.get_bus(gen.bus_id)
            if bus:
                psu = self._find_psu_for_generator(gen.id)
                if psu:
                    factor_name, factor_value = psu.get_correction_factor(
                        get_c_factor(bus.Un, is_max)
                    )
                    factors[f"{factor_name}_{psu.id}"] = factor_value
                else:
                    KG = gen.get_KG(bus.Un)
                    factors[f"KG_{gen.id}"] = KG

        return factors


def calculate_short_circuit(
    network: Network,
    fault_types: List[str],
    fault_buses: List[str],
    mode: str = "max"
) -> CalculationRun:
    """
    Convenience function to run short-circuit calculation.

    Args:
        network: Network model
        fault_types: List of fault types
        fault_buses: List of fault bus IDs
        mode: "max" or "min"

    Returns:
        CalculationRun with results
    """
    calculator = ShortCircuitCalculator(network)
    return calculator.calculate(fault_types, fault_buses, mode)
