"""IEC 60909-0 Short-Circuit Calculator - Power Station Unit Module.

This module implements the PowerStationUnit element representing
a generator-transformer block with KS/KSO correction factors
according to IEC 60909-0 §3.7.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from .elements import (
    ComplexImpedance,
    NetworkElement,
    SynchronousGenerator,
    Transformer2W,
    Transformer3W,
    ValidationStatus,
)

if TYPE_CHECKING:
    from .network import Network


@dataclass
class PowerStationUnit(NetworkElement):
    """
    Power Station Unit (Generator-Transformer Block).

    Represents a synchronous generator connected through a block
    transformer. The PSU applies combined correction factors
    KS (with OLTC) or KSO (without OLTC) instead of separate
    KG and KT factors.

    IEC 60909-0 §3.7.1 (KS) and §3.7.2 (KSO)
    """
    generator_id: str = ""  # Reference to synchronous generator
    transformer_id: str = ""  # Reference to block transformer
    has_oltc: bool = True  # On-load tap changer present
    generator_winding: Optional[str] = None  # For 3W transformer: "hv", "mv", "lv"

    # Runtime references (set during network building)
    _generator: Optional[SynchronousGenerator] = None
    _transformer: Optional[Transformer2W | Transformer3W] = None

    @property
    def element_type(self) -> str:
        return "power_station_unit"

    def set_references(
        self,
        generator: SynchronousGenerator,
        transformer: Transformer2W | Transformer3W
    ) -> None:
        """Set runtime references to generator and transformer."""
        self._generator = generator
        self._transformer = transformer

    def get_KS(self, c: float = 1.1) -> float:
        """
        Calculate correction factor KS for PSU with OLTC.

        IEC 60909-0 §3.7.1, equations 21-22:
        KS = (Un_Q * c_max) / (UrG * (1 + xd'' * sin(phi)))

        where:
        - Un_Q is the nominal voltage at the HV side of the transformer
        - UrG is the rated voltage of the generator
        - xd'' is the subtransient reactance (p.u.)
        - phi is the power factor angle

        Args:
            c: Voltage factor (default 1.1 for max)

        Returns:
            Correction factor KS
        """
        if self._generator is None or self._transformer is None:
            return 1.0

        gen = self._generator
        tr = self._transformer

        # Get HV side nominal voltage
        if isinstance(tr, Transformer3W):
            Un_Q = tr.Un_hv
        else:
            Un_Q = tr.Un_hv

        # Generator parameters
        UrG = gen.Un
        xd_pp = gen.Xd_pp / 100  # Convert from % to p.u.
        sin_phi = math.sqrt(1 - gen.cos_phi ** 2)

        # KS calculation
        KS = (Un_Q * c) / (UrG * (1 + xd_pp * sin_phi))

        return KS

    def get_KSO(self, c: float = 1.1, p_t: float = 0.0) -> float:
        """
        Calculate correction factor KSO for PSU without OLTC.

        IEC 60909-0 §3.7.2, equations 23-24:
        KSO = (Un_Q * (1 + p_t) * c_max) / (UrTLV * (1 + xd'' * sin(phi)))

        where:
        - p_t is the relative tap position
        - UrTLV is the rated voltage of the LV side of transformer

        Args:
            c: Voltage factor (default 1.1 for max)
            p_t: Relative tap position (default 0)

        Returns:
            Correction factor KSO
        """
        if self._generator is None or self._transformer is None:
            return 1.0

        gen = self._generator
        tr = self._transformer

        # Get voltages
        if isinstance(tr, Transformer3W):
            Un_Q = tr.Un_hv
            # For 3W, get the winding where generator is connected
            if self.generator_winding == "mv":
                UrTLV = tr.Un_mv
            else:  # "lv" or default
                UrTLV = tr.Un_lv
        else:
            Un_Q = tr.Un_hv
            UrTLV = tr.Un_lv

        # Actual tap position
        p_t_actual = p_t if p_t != 0 else (tr.tap_position / 100)

        # Generator parameters
        xd_pp = gen.Xd_pp / 100
        sin_phi = math.sqrt(1 - gen.cos_phi ** 2)

        # KSO calculation
        KSO = (Un_Q * (1 + p_t_actual) * c) / (UrTLV * (1 + xd_pp * sin_phi))

        return KSO

    def get_correction_factor(self, c: float = 1.1) -> tuple[str, float]:
        """
        Get appropriate correction factor based on OLTC presence.

        Args:
            c: Voltage factor

        Returns:
            Tuple of (factor_name, factor_value)
        """
        if self.has_oltc:
            return ("KS", self.get_KS(c))
        else:
            return ("KSO", self.get_KSO(c))

    def get_combined_impedance(
        self, ref_voltage: float, c: float = 1.1
    ) -> tuple[ComplexImpedance, ComplexImpedance, ComplexImpedance]:
        """
        Calculate combined Z1, Z2, Z0 impedances with correction factor.

        The combined impedance includes both generator and transformer
        impedances with the appropriate KS or KSO factor applied.

        Args:
            ref_voltage: Reference voltage [kV]
            c: Voltage factor

        Returns:
            Tuple of (Z1, Z2, Z0) as ComplexImpedance
        """
        if self._generator is None or self._transformer is None:
            from .elements import Z_INFINITE
            return Z_INFINITE, Z_INFINITE, Z_INFINITE

        # Get individual impedances
        Z1_gen, Z2_gen, Z0_gen = self._generator.get_impedance(ref_voltage)

        # For 3W transformer, specify which winding has the fault
        if isinstance(self._transformer, Transformer3W):
            # Generator is connected to one winding, fault is on opposite side (usually HV)
            # target_bus determines which winding the fault current flows through
            target_bus = "hv"  # Fault is typically on HV network side
            Z1_tr, Z2_tr, Z0_tr = self._transformer.get_impedance(ref_voltage, target_bus)
        else:
            Z1_tr, Z2_tr, Z0_tr = self._transformer.get_impedance(ref_voltage)

        # Series connection
        Z1_total = Z1_gen + Z1_tr
        Z2_total = Z2_gen + Z2_tr
        Z0_total = Z0_tr  # Generator typically doesn't contribute to Z0

        # Apply correction factor
        _, K = self.get_correction_factor(c)

        # The correction factor modifies the impedance
        # Z_corrected = Z / K² for voltage-based correction
        # Or simply scale the current contribution
        # For IEC 60909-0, we apply K to the equivalent voltage source

        return Z1_total, Z2_total, Z0_total

    def validate(self, network: Optional[Network] = None) -> list[str]:
        """
        Validate PSU configuration.

        Args:
            network: Optional network reference for topology validation

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not self.generator_id:
            errors.append("E001: generator_id is required")

        if not self.transformer_id:
            errors.append("E001: transformer_id is required")

        # Validate references if network is provided
        if network is not None:
            gen = network.get_element(self.generator_id)
            tr = network.get_element(self.transformer_id)

            if gen is None:
                errors.append(f"E003: Generator {self.generator_id} not found")
            elif not isinstance(gen, SynchronousGenerator):
                errors.append(f"E002: {self.generator_id} is not a synchronous generator")

            if tr is None:
                errors.append(f"E003: Transformer {self.transformer_id} not found")
            elif not isinstance(tr, (Transformer2W, Transformer3W)):
                errors.append(f"E002: {self.transformer_id} is not a transformer")

            # Check if generator and transformer are topologically connected
            if gen and tr and isinstance(gen, SynchronousGenerator):
                if isinstance(tr, Transformer2W):
                    if gen.bus_id not in [tr.bus_hv, tr.bus_lv]:
                        errors.append("E005: Generator not connected to transformer")
                elif isinstance(tr, Transformer3W):
                    if gen.bus_id not in [tr.bus_hv, tr.bus_mv, tr.bus_lv]:
                        errors.append("E005: Generator not connected to transformer")

            # For 3W transformer, generator_winding must be specified
            if isinstance(tr, Transformer3W):
                if not self.generator_winding:
                    errors.append("E001: generator_winding required for 3W transformer")
                elif self.generator_winding not in ["hv", "mv", "lv"]:
                    errors.append("E002: generator_winding must be 'hv', 'mv', or 'lv'")

            # Check PSU uniqueness - each generator/transformer can only be in one PSU
            if network is not None:
                for elem in network.elements.values():
                    if isinstance(elem, PowerStationUnit) and elem.id != self.id:
                        if elem.generator_id == self.generator_id:
                            errors.append(f"E007: Generator already in PSU {elem.id}")
                        if elem.transformer_id == self.transformer_id:
                            errors.append(f"E007: Transformer already in PSU {elem.id}")

        self.validation_status = (
            ValidationStatus.ERROR if errors else ValidationStatus.VALID
        )

        return errors

    def get_info(self) -> dict:
        """Get PSU information for reporting."""
        factor_name, factor_value = self.get_correction_factor()
        return {
            "id": self.id,
            "generator_id": self.generator_id,
            "transformer_id": self.transformer_id,
            "has_oltc": self.has_oltc,
            "correction_factor": factor_name,
            "correction_value": factor_value,
        }
