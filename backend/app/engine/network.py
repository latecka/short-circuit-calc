"""IEC 60909-0 Short-Circuit Calculator - Network Module.

This module implements the network topology model including:
- Element storage and lookup
- Bus connectivity (Y-bus matrix concepts)
- Impedance aggregation for fault calculations
- Topological validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Type, Union
import json

from .elements import (
    Busbar,
    ComplexImpedance,
    ExternalGrid,
    GroundingImpedance,
    Impedance,
    Line,
    NetworkElement,
    SynchronousGenerator,
    Transformer2W,
    Transformer3W,
    AsynchronousMotor,
    ValidationStatus,
    Z_INFINITE,
)
from .autotransformer import Autotransformer
from .psu import PowerStationUnit


# Type alias for all element types
ElementType = Union[
    Busbar,
    ExternalGrid,
    Line,
    Transformer2W,
    Transformer3W,
    Autotransformer,
    SynchronousGenerator,
    AsynchronousMotor,
    PowerStationUnit,
    GroundingImpedance,
    Impedance,
]


@dataclass
class Network:
    """
    Network topology model.

    Contains all network elements and provides methods for:
    - Element management
    - Connectivity analysis
    - Impedance calculations
    - Validation
    """
    name: str = ""
    description: str = ""
    elements: Dict[str, ElementType] = field(default_factory=dict)
    _buses: Dict[str, Busbar] = field(default_factory=dict)
    _adjacency: Dict[str, Set[str]] = field(default_factory=dict)

    def add_element(self, element: ElementType) -> None:
        """Add element to network."""
        self.elements[element.id] = element

        if isinstance(element, Busbar):
            self._buses[element.id] = element
            if element.id not in self._adjacency:
                self._adjacency[element.id] = set()

        # Update adjacency for branch elements
        self._update_adjacency(element)

    def _update_adjacency(self, element: ElementType) -> None:
        """Update adjacency list for branch elements."""
        connections = self._get_element_buses(element)
        for bus in connections:
            if bus not in self._adjacency:
                self._adjacency[bus] = set()

        if len(connections) == 2:
            bus1, bus2 = connections
            self._adjacency[bus1].add(bus2)
            self._adjacency[bus2].add(bus1)

    def _get_element_buses(self, element: ElementType) -> List[str]:
        """Get list of buses connected by element."""
        if isinstance(element, (Line, Impedance)):
            return [element.bus_from, element.bus_to]
        elif isinstance(element, Transformer2W):
            return [element.bus_hv, element.bus_lv]
        elif isinstance(element, Transformer3W):
            return [element.bus_hv, element.bus_mv, element.bus_lv]
        elif isinstance(element, Autotransformer):
            return [element.bus_hv, element.bus_lv]
        elif isinstance(element, (ExternalGrid, SynchronousGenerator, AsynchronousMotor)):
            return [element.bus_id]
        return []

    def get_element(self, element_id: str) -> Optional[ElementType]:
        """Get element by ID."""
        return self.elements.get(element_id)

    def get_bus(self, bus_id: str) -> Optional[Busbar]:
        """Get busbar by ID."""
        return self._buses.get(bus_id)

    def get_elements_by_type(self, element_type: Type) -> List[ElementType]:
        """Get all elements of specified type."""
        return [e for e in self.elements.values() if isinstance(e, element_type)]

    def get_elements_at_bus(self, bus_id: str) -> List[ElementType]:
        """Get all elements connected to specified bus."""
        result = []
        for element in self.elements.values():
            if bus_id in self._get_element_buses(element):
                result.append(element)
        return result

    def get_adjacent_buses(self, bus_id: str) -> Set[str]:
        """Get buses directly connected to specified bus."""
        return self._adjacency.get(bus_id, set())

    def get_sources(self) -> List[Union[ExternalGrid, SynchronousGenerator]]:
        """Get all voltage sources (external grids and generators)."""
        sources = []
        for element in self.elements.values():
            if isinstance(element, (ExternalGrid, SynchronousGenerator)):
                sources.append(element)
        return sources

    def get_motors(self) -> List[AsynchronousMotor]:
        """Get all motors."""
        return self.get_elements_by_type(AsynchronousMotor)

    def get_psus(self) -> List[PowerStationUnit]:
        """Get all power station units."""
        return self.get_elements_by_type(PowerStationUnit)

    def resolve_psu_references(self) -> List[str]:
        """
        Resolve PSU references to actual generator and transformer objects.

        Returns:
            List of error messages
        """
        errors = []
        for psu in self.get_psus():
            gen = self.get_element(psu.generator_id)
            tr = self.get_element(psu.transformer_id)

            if gen is None:
                errors.append(f"E003: PSU {psu.id}: Generator {psu.generator_id} not found")
            elif not isinstance(gen, SynchronousGenerator):
                errors.append(f"E002: PSU {psu.id}: {psu.generator_id} is not a generator")

            if tr is None:
                errors.append(f"E003: PSU {psu.id}: Transformer {psu.transformer_id} not found")
            elif not isinstance(tr, (Transformer2W, Transformer3W)):
                errors.append(f"E002: PSU {psu.id}: {psu.transformer_id} is not a transformer")

            if gen and tr and isinstance(gen, SynchronousGenerator):
                if isinstance(tr, (Transformer2W, Transformer3W)):
                    psu.set_references(gen, tr)

        return errors

    def resolve_grounding_references(self) -> List[str]:
        """
        Resolve grounding impedance references.

        Returns:
            List of error messages
        """
        errors = []

        for element in self.elements.values():
            if isinstance(element, Autotransformer):
                if element.grounding_impedance_id:
                    gi = self.get_element(element.grounding_impedance_id)
                    if gi is None:
                        errors.append(
                            f"E003: Autotransformer {element.id}: "
                            f"Grounding impedance {element.grounding_impedance_id} not found"
                        )
                    elif isinstance(gi, GroundingImpedance):
                        element.set_grounding_impedance(gi)

        return errors

    def is_connected(self) -> bool:
        """Check if network is fully connected."""
        if not self._buses:
            return True

        # BFS from first bus
        start_bus = next(iter(self._buses.keys()))
        visited = set()
        queue = [start_bus]

        while queue:
            bus = queue.pop(0)
            if bus in visited:
                continue
            visited.add(bus)
            queue.extend(self._adjacency.get(bus, set()) - visited)

        return len(visited) == len(self._buses)

    def get_path_impedance(
        self,
        from_bus: str,
        to_bus: str,
        sequence: str = "Z1"
    ) -> Optional[ComplexImpedance]:
        """
        Calculate impedance between two buses (simplified - direct connection only).

        Args:
            from_bus: Source bus ID
            to_bus: Target bus ID
            sequence: "Z1", "Z2", or "Z0"

        Returns:
            Impedance or None if not directly connected
        """
        # Find elements connecting these buses
        for element in self.elements.values():
            buses = self._get_element_buses(element)
            if from_bus in buses and to_bus in buses:
                return self._get_element_impedance(element, sequence, from_bus)

        return None

    def _get_element_impedance(
        self,
        element: ElementType,
        sequence: str,
        ref_bus: str
    ) -> ComplexImpedance:
        """Get element impedance for specified sequence."""
        ref_voltage = self._get_bus_voltage(ref_bus)

        if isinstance(element, Line):
            Z1, Z2, Z0 = element.get_impedance()
        elif isinstance(element, (Transformer2W, Autotransformer)):
            Z1, Z2, Z0 = element.get_impedance(ref_voltage)
        elif isinstance(element, Impedance):
            Z1, Z2, Z0 = element.get_impedance()
        else:
            return Z_INFINITE

        if sequence == "Z1":
            return Z1
        elif sequence == "Z2":
            return Z2
        else:  # Z0
            return Z0

    def _get_bus_voltage(self, bus_id: str) -> float:
        """Get nominal voltage at bus."""
        bus = self._buses.get(bus_id)
        if bus:
            return bus.Un
        return 1.0  # Default

    def validate(self) -> List[str]:
        """
        Validate entire network.

        Returns:
            List of error/warning messages
        """
        errors = []

        # Check for required buses
        if not self._buses:
            errors.append("E005: Network has no buses")
            return errors

        # Validate all bus references exist
        for element in self.elements.values():
            for bus_id in self._get_element_buses(element):
                if bus_id and bus_id not in self._buses:
                    errors.append(f"E003: Element {element.id} references unknown bus {bus_id}")

        # Resolve references
        errors.extend(self.resolve_psu_references())
        errors.extend(self.resolve_grounding_references())

        # Check connectivity
        if not self.is_connected():
            errors.append("W003: Network is not fully connected")

        # Check for at least one source
        if not self.get_sources():
            errors.append("E005: Network has no voltage sources")

        # Validate individual elements
        for element in self.elements.values():
            if hasattr(element, 'validate'):
                if isinstance(element, PowerStationUnit):
                    elem_errors = element.validate(self)
                elif isinstance(element, Autotransformer):
                    elem_errors = element.validate()
                else:
                    elem_errors = []
                errors.extend(elem_errors)

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert network to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "elements": [self._element_to_dict(e) for e in self.elements.values()]
        }

    def _element_to_dict(self, element: ElementType) -> Dict[str, Any]:
        """Convert element to dictionary."""
        # Get all non-private, non-callable attributes
        result = {"type": element.element_type}
        for key, value in element.__dict__.items():
            if not key.startswith('_') and not callable(value):
                if hasattr(value, 'value'):  # Enum
                    result[key] = value.value
                else:
                    result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Network:
        """Create network from dictionary."""
        network = cls(
            name=data.get("name", ""),
            description=data.get("description", "")
        )

        for elem_data in data.get("elements", []):
            element = cls._element_from_dict(elem_data)
            if element:
                network.add_element(element)

        return network

    @classmethod
    def _element_from_dict(cls, data: Dict[str, Any]) -> Optional[ElementType]:
        """Create element from dictionary."""
        elem_type = data.get("type")

        type_map = {
            "busbar": Busbar,
            "external_grid": ExternalGrid,
            "overhead_line": Line,
            "cable": Line,
            "transformer_2w": Transformer2W,
            "transformer_3w": Transformer3W,
            "autotransformer": Autotransformer,
            "synchronous_generator": SynchronousGenerator,
            "asynchronous_motor": AsynchronousMotor,
            "power_station_unit": PowerStationUnit,
            "grounding_impedance": GroundingImpedance,
            "impedance": Impedance,
        }

        element_class = type_map.get(elem_type)
        if element_class is None:
            return None

        # Filter valid fields for dataclass
        import dataclasses
        if dataclasses.is_dataclass(element_class):
            valid_fields = {f.name for f in dataclasses.fields(element_class)}
            filtered_data = {k: v for k, v in data.items() if k in valid_fields}

            # Handle special cases
            if elem_type in ("cable", "overhead_line"):
                filtered_data["is_cable"] = (elem_type == "cable")

            return element_class(**filtered_data)

        return None

    @classmethod
    def from_json(cls, json_str: str) -> Network:
        """Create network from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def to_json(self, indent: int = 2) -> str:
        """Convert network to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
