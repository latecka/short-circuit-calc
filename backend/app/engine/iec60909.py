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
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

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
from .ybus import YBusBuilder, YBusResult


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
        self._ybus_result: Optional[YBusResult] = None
        self._ybus_mode: Optional[bool] = None  # tracks is_max for cache validity
        self._meshed_warning_shown: bool = False  # show meshed warning only once
        self._is_meshed: Optional[bool] = None  # cached topology detection

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

        # Collect correction factors used
        correction_factors = self._get_correction_factors(is_max)

        # Build result (will add ip and warnings after)
        result = FaultResult(
            bus_id=bus_id,
            fault_type=fault_type,
            Ik=Ik,
            ip=0.0,  # Will be set below
            Zk=Zk,
            Z1=Z1,
            Z2=Z2,
            Z0=Z0 if fault_type == "Ik1" else None,
            R_X_ratio=R_X,
            c_factor=c,
            correction_factors=correction_factors,
        )

        # Calculate peak current with topology warning
        ip = self._calculate_ip(Ik, R_X, bus_id, result.warnings)
        result.ip = ip

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
        Calculate Thevenin equivalent impedance at fault bus using Y-bus matrix.

        Builds the network admittance matrix, inverts it to obtain the
        impedance matrix (Z-bus), and reads the diagonal element Z[i,i]
        which equals the Thévenin impedance seen from bus i.

        This approach correctly handles meshed networks where multiple
        source paths share common segments.

        Args:
            bus_id: Fault location bus ID
            is_max: True for max calculation

        Returns:
            Tuple of (Z1, Z2, Z0)
        """
        # Build Y-bus once per mode, then cache
        if self._ybus_result is None or self._ybus_mode != is_max:
            logger.debug(f"=== Building Y-bus matrix (mode={'MAX' if is_max else 'MIN'}) ===")
            builder = YBusBuilder(self.network, is_max)
            self._ybus_result = builder.compute()
            self._ybus_mode = is_max

        Z1, Z2, Z0 = self._ybus_result.get(bus_id)

        logger.debug(
            f"=== Thevenin at {bus_id}: Z1={Z1.r:.6f}+j{Z1.x:.6f}, "
            f"Z2={Z2.r:.6f}+j{Z2.x:.6f} Ω ==="
        )

        return Z1, Z2, Z0

    def _get_path_impedance(
        self,
        from_bus: str,
        to_bus: str,
        ref_voltage: float
    ) -> Optional[Tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]]:
        """
        Get total impedance along path between buses.

        This implementation:
        1. Finds all paths using BFS
        2. For each segment, calculates parallel impedance of all elements
        3. Sums segment impedances in series
        """
        if from_bus == to_bus:
            return ComplexImpedance(0, 0), ComplexImpedance(0, 0), ComplexImpedance(0, 0)

        # First, find the shortest path (sequence of buses)
        path_buses = self._find_bus_path(from_bus, to_bus)
        if not path_buses:
            return None

        # For each segment, calculate parallel impedance of all connecting elements
        Z1_total = ComplexImpedance(0, 0)
        Z2_total = ComplexImpedance(0, 0)
        Z0_total = ComplexImpedance(0, 0)

        for i in range(len(path_buses) - 1):
            bus_a = path_buses[i]
            bus_b = path_buses[i + 1]

            # Find all elements connecting bus_a and bus_b
            Z1_segment, Z2_segment, Z0_segment = self._get_parallel_impedance_between(
                bus_a, bus_b, ref_voltage
            )

            Z1_total = Z1_total + Z1_segment
            Z2_total = Z2_total + Z2_segment
            if Z0_segment.magnitude < 1e10:
                Z0_total = Z0_total + Z0_segment
            else:
                Z0_total = Z0_segment

        return Z1_total, Z2_total, Z0_total

    def _find_bus_path(self, from_bus: str, to_bus: str) -> Optional[List[str]]:
        """Find shortest path of buses using BFS."""
        if from_bus == to_bus:
            return [from_bus]

        visited = set()
        queue = [(from_bus, [from_bus])]

        while queue:
            current, path = queue.pop(0)

            if current in visited:
                continue
            visited.add(current)

            if current == to_bus:
                return path

            # Find neighboring buses
            for elem in self.network.get_elements_at_bus(current):
                buses = self._get_element_buses(elem)
                for next_bus in buses:
                    if next_bus != current and next_bus not in visited:
                        queue.append((next_bus, path + [next_bus]))

        return None

    def _get_parallel_impedance_between(
        self,
        bus_a: str,
        bus_b: str,
        ref_voltage: float
    ) -> Tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """Get parallel impedance of all elements connecting two buses."""
        Z1_parallel = None
        Z2_parallel = None
        Z0_parallel = None

        # Find all elements connecting bus_a and bus_b
        for elem in self.network.get_elements_at_bus(bus_a):
            buses = self._get_element_buses(elem)
            if bus_b in buses:
                Z1, Z2, Z0 = self._get_element_sequence_impedance(elem, ref_voltage)

                if Z1_parallel is None:
                    Z1_parallel = Z1
                    Z2_parallel = Z2
                    Z0_parallel = Z0
                else:
                    Z1_parallel = Z1_parallel.parallel(Z1)
                    Z2_parallel = Z2_parallel.parallel(Z2)
                    if Z0.magnitude < 1e10 and Z0_parallel.magnitude < 1e10:
                        Z0_parallel = Z0_parallel.parallel(Z0)

        if Z1_parallel is None:
            return ComplexImpedance(0, 0), ComplexImpedance(0, 0), ComplexImpedance(0, 0)

        return Z1_parallel, Z2_parallel, Z0_parallel

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
            # Use get_impedance with default target bus (lv)
            return element.get_impedance(ref_voltage, "lv")
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

    def _calculate_ip(
        self,
        Ik: float,
        R_X: float,
        bus_id: str = "",
        warnings: list = None
    ) -> float:
        """
        Calculate peak short-circuit current.

        ip = kappa * sqrt(2) * Ik''

        where kappa depends on R/X ratio (IEC 60909-0 eq. 54)

        For radial networks, uses the standard formula.
        For meshed networks, IEC 60909-0 recommends Method B or C which
        require per-branch R/X analysis. This implementation uses the
        standard radial formula with warning for meshed networks.

        Args:
            Ik: Initial short-circuit current [kA]
            R_X: R/X ratio at fault location
            bus_id: Bus ID for topology detection
            warnings: List to append warnings to

        Returns:
            Peak current [kA]
        """
        if R_X <= 0:
            kappa = 2.0  # Maximum value for R/X = 0
        else:
            # IEC 60909-0 equation 54
            kappa = 1.02 + 0.98 * math.exp(-3 * R_X)

        # Check if network is meshed and add warning (only once per calculator instance)
        if bus_id and warnings is not None and not self._meshed_warning_shown:
            is_meshed = self._is_meshed_topology()
            if is_meshed:
                warnings.append(
                    "Meshed network detected: kappa calculated using radial "
                    "Method A (IEC 60909-0 §4.3.1.1). For higher accuracy, "
                    "Method B or C may be required for meshed networks."
                )
                self._meshed_warning_shown = True

        ip = kappa * math.sqrt(2) * Ik

        return ip

    def _is_meshed_topology(self) -> bool:
        """
        Detect if network has meshed (non-radial) topology.

        A network is meshed if there are multiple paths between any
        two buses, or if it has cycles (loops).

        Simple heuristic: count if there are more branch elements
        than (buses - 1), which would indicate cycles.

        Returns:
            True if network appears to be meshed
        """
        # Return cached result if available
        if self._is_meshed is not None:
            return self._is_meshed

        # Count buses and branches
        buses = list(self.network.get_elements_by_type(Busbar))
        n_buses = len(buses)

        if n_buses <= 1:
            return False

        # Count branch elements (lines, transformers, etc.)
        n_branches = 0

        for line in self.network.get_elements_by_type(Line):
            if line.in_service:
                n_branches += 1

        for tr in self.network.get_elements_by_type(Transformer2W):
            if tr.in_service:
                n_branches += 1

        for tr in self.network.get_elements_by_type(Transformer3W):
            if tr.in_service:
                n_branches += 2  # 3W transformer contributes 2 branches

        # Count sources (external grids, generators) - more than 1 suggests mesh
        n_sources = 0
        for grid in self.network.get_elements_by_type(ExternalGrid):
            if grid.in_service:
                n_sources += 1
        for gen in self.network.get_elements_by_type(SynchronousGenerator):
            if gen.in_service:
                n_sources += 1

        # Heuristics:
        # 1. If branches > buses - 1, there are cycles
        # 2. If there are multiple active sources feeding different buses
        has_cycles = n_branches > (n_buses - 1)
        has_multiple_sources = n_sources > 1

        # Cache result
        self._is_meshed = has_cycles or has_multiple_sources
        return self._is_meshed

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
