"""IEC 60909-0 Short-Circuit Calculator - Y-Bus Matrix Module.

This module implements the admittance matrix (Y-bus) method for computing
Thévenin equivalent impedances at all network buses.

The Y-bus approach correctly handles meshed networks where multiple source
paths share common segments — unlike source superposition, which only works
for purely radial topologies.

Algorithm:
    1. Assign index to each bus
    2. Build Y-bus matrix in per-unit (Sbase = 100 MVA)
    3. For branch elements: Y[i,j] -= y; Y[i,i] += y; Y[j,j] += y
    4. For shunt elements:  Y[i,i] += y
    5. Invert Y-bus → Z-bus
    6. Diagonal Z_bus[i,i] = Thévenin impedance at bus i
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

import numpy as np

from .elements import (
    AsynchronousMotor,
    Busbar,
    ComplexImpedance,
    ExternalGrid,
    Impedance,
    Line,
    SynchronousGenerator,
    Transformer2W,
    Transformer3W,
    Z_INFINITE,
)
from .autotransformer import Autotransformer
from .psu import PowerStationUnit

if TYPE_CHECKING:
    from .network import Network

logger = logging.getLogger(__name__)

# Per-unit base power [MVA] — arbitrary, cancels in the result
S_BASE = 100.0


@dataclass
class YBusResult:
    """Result of Y-bus Thévenin impedance computation."""

    # Mapping bus_id → (Z1, Z2, Z0) in actual Ohms
    impedances: Dict[str, Tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]]

    def get(self, bus_id: str) -> Tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """Get Thévenin impedances for a bus."""
        if bus_id in self.impedances:
            return self.impedances[bus_id]
        raise KeyError(f"Bus {bus_id} not found in Y-bus results")


class YBusBuilder:
    """
    Builds Y-bus admittance matrices and computes Thévenin impedances.

    Handles three sequence networks (positive, negative, zero) and all
    IEC 60909-0 element types including correction factors KG, KS, KSO.
    """

    def __init__(self, network: Network, is_max: bool = True):
        self.network = network
        self.is_max = is_max

        # Bus indexing
        self._bus_ids: List[str] = []
        self._bus_index: Dict[str, int] = {}
        self._bus_un: Dict[str, float] = {}
        self._bus_zbase: Dict[str, float] = {}

        # Internal buses for 3W transformer star equivalents
        self._internal_bus_count = 0

        self._init_buses()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_buses(self) -> None:
        """Build bus index map and per-unit bases.

        Excludes:
        - PSU generator-side buses (modelled as part of PSU shunt)
        - Isolated buses (no path to any voltage source)
        """
        # Identify generator-side buses in PSUs (these are internal to PSU model)
        psu_gen_buses = self._get_psu_generator_buses()

        # Identify buses reachable from sources
        reachable_buses = self._get_reachable_buses()

        for bus in self.network.get_elements_by_type(Busbar):
            if bus.id in psu_gen_buses:
                # Skip generator-side buses - they're part of PSU model
                continue

            if bus.id not in reachable_buses:
                # Skip isolated buses - they have no path to sources
                logger.warning(f"Bus {bus.id} is isolated (no path to source) - excluded from Y-bus")
                continue

            idx = len(self._bus_ids)
            self._bus_ids.append(bus.id)
            self._bus_index[bus.id] = idx
            self._bus_un[bus.id] = bus.Un
            self._bus_zbase[bus.id] = (bus.Un ** 2) / S_BASE if bus.Un > 0 else 1.0


    def _get_reachable_buses(self) -> set:
        """Find all buses reachable from voltage sources via in-service elements.

        Uses BFS starting from buses with sources attached.
        """
        # Find source buses
        source_buses = set()
        for grid in self.network.get_elements_by_type(ExternalGrid):
            if grid.in_service:
                source_buses.add(grid.bus_id)
        for gen in self.network.get_elements_by_type(SynchronousGenerator):
            if gen.in_service:
                source_buses.add(gen.bus_id)
        # PSU sources
        for psu in self.network.get_psus():
            if psu._generator is not None and psu._generator.in_service:
                if psu._transformer is not None:
                    if isinstance(psu._transformer, Transformer2W):
                        source_buses.add(psu._transformer.bus_hv)
                    elif isinstance(psu._transformer, Transformer3W):
                        source_buses.add(psu._transformer.bus_hv)

        if not source_buses:
            return set()

        # Build adjacency from in-service branch elements
        adjacency: Dict[str, Set[str]] = {}
        all_buses = {b.id for b in self.network.get_elements_by_type(Busbar)}
        for bus_id in all_buses:
            adjacency[bus_id] = set()

        # Lines
        for line in self.network.get_elements_by_type(Line):
            if line.in_service:
                adjacency.setdefault(line.bus_from, set()).add(line.bus_to)
                adjacency.setdefault(line.bus_to, set()).add(line.bus_from)

        # 2W Transformers
        for tr in self.network.get_elements_by_type(Transformer2W):
            if tr.in_service and not self._is_psu_transformer(tr.id):
                adjacency.setdefault(tr.bus_hv, set()).add(tr.bus_lv)
                adjacency.setdefault(tr.bus_lv, set()).add(tr.bus_hv)

        # 3W Transformers
        for tr in self.network.get_elements_by_type(Transformer3W):
            if tr.in_service and not self._is_psu_transformer(tr.id):
                for b1, b2 in [(tr.bus_hv, tr.bus_mv), (tr.bus_hv, tr.bus_lv), (tr.bus_mv, tr.bus_lv)]:
                    adjacency.setdefault(b1, set()).add(b2)
                    adjacency.setdefault(b2, set()).add(b1)

        # Autotransformers
        for at in self.network.get_elements_by_type(Autotransformer):
            if at.in_service:
                adjacency.setdefault(at.bus_hv, set()).add(at.bus_lv)
                adjacency.setdefault(at.bus_lv, set()).add(at.bus_hv)

        # Impedances
        for imp in self.network.get_elements_by_type(Impedance):
            if imp.in_service:
                adjacency.setdefault(imp.bus_from, set()).add(imp.bus_to)
                adjacency.setdefault(imp.bus_to, set()).add(imp.bus_from)

        # BFS from source buses
        visited = set()
        queue = list(source_buses)
        while queue:
            bus = queue.pop(0)
            if bus in visited:
                continue
            visited.add(bus)
            for neighbor in adjacency.get(bus, set()):
                if neighbor not in visited:
                    queue.append(neighbor)

        return visited

    def _get_psu_generator_buses(self) -> set:
        """Get set of bus IDs that are generator-side buses in PSUs."""
        psu_gen_buses = set()
        for psu in self.network.get_psus():
            if psu._generator is not None:
                psu_gen_buses.add(psu._generator.bus_id)
        return psu_gen_buses

    def _add_internal_bus(self, tag: str, Un: float) -> str:
        """Create an internal bus (e.g. for 3W transformer star point)."""
        self._internal_bus_count += 1
        bus_id = f"__internal_{tag}_{self._internal_bus_count}"
        idx = len(self._bus_ids)
        self._bus_ids.append(bus_id)
        self._bus_index[bus_id] = idx
        self._bus_un[bus_id] = Un
        self._bus_zbase[bus_id] = (Un ** 2) / S_BASE if Un > 0 else 1.0
        return bus_id

    @property
    def n_buses(self) -> int:
        return len(self._bus_ids)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute(self) -> YBusResult:
        """
        Build Y-bus matrices, invert, and return Thévenin impedances.

        Returns:
            YBusResult with impedances for every bus
        """
        # Pre-scan for 3W transformers that need internal buses
        self._prepare_3w_transformers()

        n = self.n_buses

        # Build admittance matrices for each sequence
        Y1 = np.zeros((n, n), dtype=complex)
        Y2 = np.zeros((n, n), dtype=complex)
        Y0 = np.zeros((n, n), dtype=complex)

        self._add_external_grids(Y1, Y2, Y0)
        self._add_lines(Y1, Y2, Y0)
        self._add_impedances(Y1, Y2, Y0)
        self._add_transformers_2w(Y1, Y2, Y0)
        self._add_transformers_3w(Y1, Y2, Y0)
        self._add_autotransformers(Y1, Y2, Y0)
        self._add_generators(Y1, Y2, Y0)
        if self.is_max:
            self._add_motors(Y1, Y2, Y0)

        # Invert to get Z-bus
        Z1_bus = self._safe_invert(Y1, "Z1")
        Z2_bus = self._safe_invert(Y2, "Z2")
        Z0_bus = self._safe_invert(Y0, "Z0")

        # Extract Thévenin impedances (diagonal elements) in actual Ohms
        result = {}

        # Get PSU generator buses to identify them separately
        psu_gen_buses = self._get_psu_generator_buses()

        for bus_id in self.network.busbars:
            if bus_id in psu_gen_buses:
                # PSU generator buses are handled internally - skip
                continue

            if bus_id not in self._bus_index:
                # Isolated bus - assign infinite impedance (Ik = 0)
                Z_inf = ComplexImpedance(1e12, 1e12)
                result[bus_id] = (Z_inf, Z_inf, Z_inf)
                logger.debug(f"  Y-bus: Bus {bus_id} is isolated - Ik = 0")
                continue

            i = self._bus_index[bus_id]
            zbase = self._bus_zbase[bus_id]

            z1 = Z1_bus[i, i] * zbase if Z1_bus is not None else complex(1e12, 1e12)
            z2 = Z2_bus[i, i] * zbase if Z2_bus is not None else complex(1e12, 1e12)
            z0 = Z0_bus[i, i] * zbase if Z0_bus is not None else complex(1e12, 1e12)

            Z1 = ComplexImpedance(z1.real, z1.imag)
            Z2 = ComplexImpedance(z2.real, z2.imag)
            Z0 = ComplexImpedance(z0.real, z0.imag)

            result[bus_id] = (Z1, Z2, Z0)

            logger.debug(
                f"  Y-bus Thévenin at {bus_id}: "
                f"Z1={Z1.r:.6f}+j{Z1.x:.6f}, "
                f"Z2={Z2.r:.6f}+j{Z2.x:.6f}, "
                f"Z0={Z0.r:.6f}+j{Z0.x:.6f} Ω"
            )

        return YBusResult(impedances=result)

    # ------------------------------------------------------------------
    # Matrix helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _add_branch(Y: np.ndarray, i: int, j: int, z: complex) -> None:
        """Add a branch (series element) between bus i and bus j."""
        if abs(z) < 1e-15:
            return  # Skip zero impedance
        y = 1.0 / z
        Y[i, i] += y
        Y[j, j] += y
        Y[i, j] -= y
        Y[j, i] -= y

    @staticmethod
    def _add_shunt(Y: np.ndarray, i: int, z: complex) -> None:
        """Add a shunt (source) element at bus i."""
        if abs(z) < 1e-15 or abs(z) > 1e15:
            return  # Skip zero or infinite impedance
        Y[i, i] += 1.0 / z

    def _safe_invert(self, Y: np.ndarray, label: str) -> Optional[np.ndarray]:
        """Invert Y-bus with error handling."""
        try:
            return np.linalg.inv(Y)
        except np.linalg.LinAlgError:
            logger.warning(f"Y-bus singular for {label} — cannot compute Thévenin impedances")
            return None

    def _to_pu(self, Z: ComplexImpedance, bus_id: str) -> complex:
        """Convert impedance from actual Ohms to per-unit at bus voltage."""
        zbase = self._bus_zbase.get(bus_id, 1.0)
        if zbase < 1e-15:
            return complex(Z.r, Z.x)
        return complex(Z.r / zbase, Z.x / zbase)

    # ------------------------------------------------------------------
    # Element handlers
    # ------------------------------------------------------------------

    def _get_c_factor(self, Un: float) -> float:
        """Get voltage factor c for given voltage level."""
        from .iec60909 import get_c_factor
        return get_c_factor(Un, self.is_max)

    def _add_external_grids(self, Y1, Y2, Y0) -> None:
        """Add external grid sources as shunts."""
        for grid in self.network.get_elements_by_type(ExternalGrid):
            if not grid.in_service:
                continue
            bus_id = grid.bus_id
            if bus_id not in self._bus_index:
                continue

            i = self._bus_index[bus_id]
            Un = self._bus_un[bus_id]

            # get_impedance returns Z in actual Ohms at bus voltage
            Z1, Z2, Z0 = grid.get_impedance(Un, self.is_max)

            z1_pu = self._to_pu(Z1, bus_id)
            z2_pu = self._to_pu(Z2, bus_id)
            z0_pu = self._to_pu(Z0, bus_id)

            self._add_shunt(Y1, i, z1_pu)
            self._add_shunt(Y2, i, z2_pu)
            self._add_shunt(Y0, i, z0_pu)

            logger.debug(
                f"  Y-bus: ExternalGrid {grid.id} at {bus_id}: "
                f"z1_pu={z1_pu.real:.6f}+j{z1_pu.imag:.6f}"
            )

    def _add_lines(self, Y1, Y2, Y0) -> None:
        """Add lines/cables as branches."""
        for line in self.network.get_elements_by_type(Line):
            if not line.in_service:
                continue
            bus_from = line.bus_from
            bus_to = line.bus_to
            if bus_from not in self._bus_index or bus_to not in self._bus_index:
                continue

            i = self._bus_index[bus_from]
            j = self._bus_index[bus_to]

            Z1, Z2, Z0 = line.get_impedance()

            # Lines connect buses at the same voltage level
            z1_pu = self._to_pu(Z1, bus_from)
            z2_pu = self._to_pu(Z2, bus_from)
            z0_pu = self._to_pu(Z0, bus_from)

            self._add_branch(Y1, i, j, z1_pu)
            self._add_branch(Y2, i, j, z2_pu)
            if Z0.magnitude < 1e10:
                self._add_branch(Y0, i, j, z0_pu)

            logger.debug(
                f"  Y-bus: Line {line.id} ({bus_from}→{bus_to}): "
                f"z1_pu={z1_pu.real:.6f}+j{z1_pu.imag:.6f}"
            )

    def _add_impedances(self, Y1, Y2, Y0) -> None:
        """Add generic impedance elements as branches."""
        for imp in self.network.get_elements_by_type(Impedance):
            if not imp.in_service:
                continue
            bus_from = imp.bus_from
            bus_to = imp.bus_to
            if bus_from not in self._bus_index or bus_to not in self._bus_index:
                continue

            i = self._bus_index[bus_from]
            j = self._bus_index[bus_to]

            Z1, Z2, Z0 = imp.get_impedance()
            z1_pu = self._to_pu(Z1, bus_from)
            z2_pu = self._to_pu(Z2, bus_from)
            z0_pu = self._to_pu(Z0, bus_from)

            self._add_branch(Y1, i, j, z1_pu)
            self._add_branch(Y2, i, j, z2_pu)
            if Z0.magnitude < 1e10:
                self._add_branch(Y0, i, j, z0_pu)

    def _add_transformers_2w(self, Y1, Y2, Y0) -> None:
        """
        Add 2W transformers as branches.

        In per-unit, transformer impedance is the same on both sides:
            z_pu = (uk/100) * Sbase / Sn
        so voltage transformation is implicit.
        """
        for tr in self.network.get_elements_by_type(Transformer2W):
            if not tr.in_service:
                continue

            # Skip if this transformer is part of a PSU (handled separately)
            if self._is_psu_transformer(tr.id):
                continue

            bus_hv = tr.bus_hv
            bus_lv = tr.bus_lv
            if bus_hv not in self._bus_index or bus_lv not in self._bus_index:
                continue

            i = self._bus_index[bus_hv]
            j = self._bus_index[bus_lv]

            # Get impedance referred to HV side, then convert to per-unit
            Z1, Z2, Z0 = tr.get_impedance(tr.Un_hv)

            z1_pu = self._to_pu(Z1, bus_hv)
            z2_pu = self._to_pu(Z2, bus_hv)

            self._add_branch(Y1, i, j, z1_pu)
            self._add_branch(Y2, i, j, z2_pu)

            # Z0 depends on vector group / grounding
            if Z0.magnitude < 1e10:
                z0_pu = self._to_pu(Z0, bus_hv)
                self._add_branch(Y0, i, j, z0_pu)

            logger.debug(
                f"  Y-bus: Transformer {tr.id} ({bus_hv}→{bus_lv}): "
                f"z1_pu={z1_pu.real:.6f}+j{z1_pu.imag:.6f}"
            )

    def _prepare_3w_transformers(self) -> None:
        """Pre-create internal star-point buses for 3W transformers."""
        self._3w_star_buses: Dict[str, str] = {}  # trafo_id → internal bus_id
        for tr in self.network.get_elements_by_type(Transformer3W):
            if not tr.in_service:
                continue
            if self._is_psu_transformer(tr.id):
                continue
            # Create internal bus at HV voltage level (star impedances are at HV)
            star_bus = self._add_internal_bus(f"3w_{tr.id}", tr.Un_hv)
            self._3w_star_buses[tr.id] = star_bus

    def _add_transformers_3w(self, Y1, Y2, Y0) -> None:
        """
        Add 3W transformers using star-equivalent circuit.

        Each 3W transformer is modelled as three branches from
        an internal star node to the three terminal buses.
        """
        for tr in self.network.get_elements_by_type(Transformer3W):
            if not tr.in_service:
                continue
            if self._is_psu_transformer(tr.id):
                continue

            star_bus = self._3w_star_buses.get(tr.id)
            if star_bus is None:
                continue

            i_star = self._bus_index[star_bus]
            i_hv = self._bus_index.get(tr.bus_hv)
            i_mv = self._bus_index.get(tr.bus_mv)
            i_lv = self._bus_index.get(tr.bus_lv)

            if i_hv is None or i_mv is None or i_lv is None:
                continue

            # Star impedances referred to HV side
            Z_H, Z_M, Z_L = tr.get_star_impedances(tr.Un_hv)

            zbase_hv = self._bus_zbase.get(tr.bus_hv, 1.0)

            for (i_terminal, Z_arm) in [(i_hv, Z_H), (i_mv, Z_M), (i_lv, Z_L)]:
                z_pu = complex(Z_arm.r, Z_arm.x) / zbase_hv
                self._add_branch(Y1, i_star, i_terminal, z_pu)
                self._add_branch(Y2, i_star, i_terminal, z_pu)
                # Simplified: Z0 same as Z1 for 3W (depends on vector group)
                self._add_branch(Y0, i_star, i_terminal, z_pu)

    def _add_autotransformers(self, Y1, Y2, Y0) -> None:
        """Add autotransformers as branches."""
        for at in self.network.get_elements_by_type(Autotransformer):
            if not at.in_service:
                continue

            bus_hv = at.bus_hv
            bus_lv = at.bus_lv
            if bus_hv not in self._bus_index or bus_lv not in self._bus_index:
                continue

            i = self._bus_index[bus_hv]
            j = self._bus_index[bus_lv]

            Z1, Z2, Z0 = at.get_impedance(at.Un_hv)

            z1_pu = self._to_pu(Z1, bus_hv)
            z2_pu = self._to_pu(Z2, bus_hv)

            self._add_branch(Y1, i, j, z1_pu)
            self._add_branch(Y2, i, j, z2_pu)

            if Z0.magnitude < 1e10:
                z0_pu = self._to_pu(Z0, bus_hv)
                self._add_branch(Y0, i, j, z0_pu)

    def _add_generators(self, Y1, Y2, Y0) -> None:
        """
        Add synchronous generators.

        Generators in a PSU are handled together with their transformer.
        Direct-connected generators get KG correction factor.
        """
        psu_gen_ids = {psu.generator_id for psu in self.network.get_psus()}

        for gen in self.network.get_elements_by_type(SynchronousGenerator):
            if not gen.in_service:
                continue
            if gen.id in psu_gen_ids:
                # Handled by _add_psus()
                continue

            bus_id = gen.bus_id
            if bus_id not in self._bus_index:
                continue

            i = self._bus_index[bus_id]
            Un = self._bus_un[bus_id]

            # Base impedance at bus voltage
            Z1_base, Z2_base, Z0 = gen.get_impedance(Un)

            # Apply KG correction (IEC 60909-0 eq. 18)
            c = self._get_c_factor(gen.Un)
            KG = gen.get_KG(c)

            Z1 = Z1_base * KG
            Z2 = Z2_base * KG

            z1_pu = self._to_pu(Z1, bus_id)
            z2_pu = self._to_pu(Z2, bus_id)

            self._add_shunt(Y1, i, z1_pu)
            self._add_shunt(Y2, i, z2_pu)
            # Z0 for generators is typically infinite (not grounded)
            # → do not add to Y0

            logger.debug(
                f"  Y-bus: Generator {gen.id} at {bus_id}: "
                f"KG={KG:.4f}, z1_pu={z1_pu.real:.6f}+j{z1_pu.imag:.6f}"
            )

        # Handle PSU generators (gen + trafo block)
        self._add_psus(Y1, Y2, Y0)

    def _add_psus(self, Y1, Y2, Y0) -> None:
        """
        Add Power Station Units (generator-transformer blocks).

        A PSU is modelled as a combined shunt at the network-side bus
        of its block transformer, with KS or KSO correction.
        """
        for psu in self.network.get_psus():
            if psu._generator is None or psu._transformer is None:
                continue
            if not psu._generator.in_service:
                continue

            tr = psu._transformer
            gen = psu._generator

            # Network-side bus of the block transformer
            if isinstance(tr, Transformer2W):
                network_bus = tr.bus_hv  # Generator on LV, network on HV
            elif isinstance(tr, Transformer3W):
                network_bus = tr.bus_hv
            else:
                continue

            if network_bus not in self._bus_index:
                continue

            i = self._bus_index[network_bus]
            Un = self._bus_un[network_bus]
            c = self._get_c_factor(Un)

            # Combined impedance (gen + trafo in series)
            Z1, Z2, Z0 = psu.get_combined_impedance(Un, c)

            z1_pu = self._to_pu(Z1, network_bus)
            z2_pu = self._to_pu(Z2, network_bus)

            self._add_shunt(Y1, i, z1_pu)
            self._add_shunt(Y2, i, z2_pu)

            if Z0.magnitude < 1e10:
                z0_pu = self._to_pu(Z0, network_bus)
                self._add_shunt(Y0, i, z0_pu)

    def _add_motors(self, Y1, Y2, Y0) -> None:
        """Add asynchronous motors as shunts (max calculation only)."""
        for motor in self.network.get_motors():
            if not motor.in_service or not motor.include_in_sc:
                continue

            bus_id = motor.bus_id
            if bus_id not in self._bus_index:
                continue

            i = self._bus_index[bus_id]
            Un = self._bus_un[bus_id]

            Z1, Z2, Z0 = motor.get_impedance(Un)

            if Z1.magnitude > 1e10:
                continue  # Invalid motor parameters

            z1_pu = self._to_pu(Z1, bus_id)
            z2_pu = self._to_pu(Z2, bus_id)

            self._add_shunt(Y1, i, z1_pu)
            self._add_shunt(Y2, i, z2_pu)
            # Z0 is infinite for motors → do not add

            logger.debug(
                f"  Y-bus: Motor {motor.id} at {bus_id}: "
                f"z1_pu={z1_pu.real:.6f}+j{z1_pu.imag:.6f}"
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_psu_transformer(self, trafo_id: str) -> bool:
        """Check if a transformer belongs to a PSU."""
        return any(
            psu.transformer_id == trafo_id
            for psu in self.network.get_psus()
        )
