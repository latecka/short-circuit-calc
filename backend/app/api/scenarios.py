"""Scenarios API endpoints."""

import hashlib
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DBSession, CurrentUser
from app.models import Project, NetworkVersion, Scenario, CalculationRun, RunResult, CalculationMode, CalculationStatus, FaultType
from app.schemas.scenario import (
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioResponse,
    ScenarioListResponse,
    ScenarioRunRequest,
    ScenarioRunResponse,
)
from app.engine.iec60909 import ShortCircuitCalculator
from app.engine.network import Network
from app.engine.elements import (
    Busbar, ExternalGrid, Line, Transformer2W, Transformer3W,
    SynchronousGenerator, AsynchronousMotor, Impedance, GroundingImpedance,
    InputMode,
)
from app.engine.autotransformer import Autotransformer
from app.engine.psu import PowerStationUnit

router = APIRouter(prefix="/projects/{project_id}/scenarios", tags=["scenarios"])


def _get_project_or_404(db: DBSession, project_id: str, user_id: str) -> Project:
    """Get project owned by user or raise 404."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user_id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def _get_scenario_or_404(db: DBSession, project_id: str, scenario_id: str, user_id: str) -> Scenario:
    """Get scenario belonging to user's project or raise 404."""
    scenario = db.query(Scenario).join(Project).filter(
        Scenario.id == scenario_id,
        Scenario.project_id == project_id,
        Project.owner_id == user_id,
    ).first()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )
    return scenario


def _scenario_to_response(scenario: Scenario) -> ScenarioResponse:
    """Convert Scenario model to response schema."""
    return ScenarioResponse(
        id=scenario.id,
        project_id=scenario.project_id,
        name=scenario.name,
        description=scenario.description,
        calculation_mode=scenario.calculation_mode.value,
        element_states=scenario.element_states or {},
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
    )


@router.get("", response_model=ScenarioListResponse)
def list_scenarios(
    project_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """List all scenarios for a project. Auto-creates default scenario if none exist."""
    project = _get_project_or_404(db, project_id, current_user.id)

    scenarios = db.query(Scenario).filter(
        Scenario.project_id == project_id,
    ).order_by(Scenario.created_at).all()

    # Auto-create default scenario if none exist
    if not scenarios:
        default_scenario = Scenario(
            project_id=project_id,
            name="Základný scenár",
            description="Všetky prvky aktívne",
            calculation_mode=CalculationMode.MAX,
            element_states={},
        )
        db.add(default_scenario)
        db.commit()
        db.refresh(default_scenario)
        scenarios = [default_scenario]

    return ScenarioListResponse(
        items=[_scenario_to_response(s) for s in scenarios],
        total=len(scenarios),
    )


@router.post("", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def create_scenario(
    project_id: str,
    data: ScenarioCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a new scenario."""
    project = _get_project_or_404(db, project_id, current_user.id)

    # Get element_states from copy_from scenario if specified
    element_states = data.element_states
    if data.copy_from:
        source_scenario = _get_scenario_or_404(db, project_id, data.copy_from, current_user.id)
        element_states = source_scenario.element_states.copy() if source_scenario.element_states else {}

    scenario = Scenario(
        project_id=project_id,
        name=data.name,
        description=data.description,
        calculation_mode=CalculationMode(data.calculation_mode),
        element_states=element_states,
    )

    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return _scenario_to_response(scenario)


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    project_id: str,
    scenario_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get a scenario by ID."""
    scenario = _get_scenario_or_404(db, project_id, scenario_id, current_user.id)
    return _scenario_to_response(scenario)


@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    project_id: str,
    scenario_id: str,
    data: ScenarioUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Update a scenario."""
    scenario = _get_scenario_or_404(db, project_id, scenario_id, current_user.id)

    if data.name is not None:
        scenario.name = data.name
    if data.description is not None:
        scenario.description = data.description
    if data.calculation_mode is not None:
        scenario.calculation_mode = CalculationMode(data.calculation_mode)
    if data.element_states is not None:
        scenario.element_states = data.element_states

    scenario.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(scenario)

    return _scenario_to_response(scenario)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(
    project_id: str,
    scenario_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Delete a scenario."""
    scenario = _get_scenario_or_404(db, project_id, scenario_id, current_user.id)

    db.delete(scenario)
    db.commit()


@router.post("/{scenario_id}/run", response_model=ScenarioRunResponse)
def run_scenario(
    project_id: str,
    scenario_id: str,
    data: ScenarioRunRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Run calculation for a scenario."""
    scenario = _get_scenario_or_404(db, project_id, scenario_id, current_user.id)
    project = _get_project_or_404(db, project_id, current_user.id)

    # Get latest network version
    version = db.query(NetworkVersion).filter(
        NetworkVersion.project_id == project_id,
    ).order_by(NetworkVersion.version_number.desc()).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No network version found. Save network first.",
        )

    # Filter elements based on scenario
    all_elements = version.elements or {}
    active_elements = scenario.get_active_elements(all_elements)

    # Build network from filtered elements
    try:
        network = _build_network_from_elements(active_elements)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to build network: {str(e)}",
        )

    # Get fault buses
    fault_buses = data.fault_buses
    if not fault_buses:
        fault_buses = [bus.id for bus in network.get_elements_by_type(Busbar)]

    if not fault_buses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No buses in filtered network",
        )

    # Compute input hash
    input_data = {
        "elements": active_elements,
        "mode": scenario.calculation_mode.value,
        "fault_types": data.fault_types,
        "fault_buses": fault_buses,
    }
    input_hash = hashlib.sha256(json.dumps(input_data, sort_keys=True).encode()).hexdigest()

    # Create calculation run
    run = CalculationRun(
        project_id=project_id,
        network_version_id=version.id,
        user_id=current_user.id,
        scenario_id=scenario.id,
        calculation_mode=scenario.calculation_mode,
        fault_types=data.fault_types,
        fault_buses=fault_buses,
        engine_version="1.0.0",
        input_hash=input_hash,
        status=CalculationStatus.RUNNING,
    )
    db.add(run)
    db.commit()

    # Run calculation
    try:
        calculator = ShortCircuitCalculator(network)
        calc_result = calculator.calculate(
            fault_types=data.fault_types,
            fault_buses=fault_buses,
            mode=scenario.calculation_mode.value,
        )

        if not calc_result.is_success:
            run.status = CalculationStatus.FAILED
            run.error_message = "; ".join(calc_result.errors)
        else:
            run.status = CalculationStatus.COMPLETED

            # Store results
            for result in calc_result.results:
                run_result = RunResult(
                    run_id=run.id,
                    bus_id=result.bus_id,
                    fault_type=FaultType(result.fault_type),
                    Ik=result.Ik,
                    ip=result.ip,
                    R_X_ratio=result.R_X_ratio,
                    c_factor=result.c_factor,
                    Zk=result.Zk.to_dict(),
                    Z1=result.Z1.to_dict(),
                    Z2=result.Z2.to_dict(),
                    Z0=result.Z0.to_dict() if result.Z0 else None,
                    correction_factors=result.correction_factors,
                    warnings=result.warnings,
                    assumptions=result.assumptions,
                )
                db.add(run_result)

    except Exception as e:
        run.status = CalculationStatus.FAILED
        run.error_message = str(e)

    run.completed_at = datetime.utcnow()
    db.commit()

    return ScenarioRunResponse(
        run_id=run.id,
        scenario_id=scenario.id,
        status=run.status.value,
        message="Calculation completed" if run.status == CalculationStatus.COMPLETED else run.error_message or "Calculation failed",
    )


def _build_network_from_elements(elements: dict) -> Network:
    """Build Network object from elements dictionary."""
    network = Network(name="scenario_network")

    def _first(data: dict, keys: list[str], default=None):
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
        return default

    # Add busbars first
    for bus_data in elements.get("busbars", []):
        bus = Busbar(
            id=bus_data["id"],
            name=bus_data.get("name"),
            Un=bus_data["Un"],
            is_reference=bus_data.get("is_reference", False),
        )
        network.add_element(bus)

    # Add external grids
    for grid_data in elements.get("external_grids", []):
        sk_max = _first(grid_data, ["Sk_max", "s_sc_max_mva", "sk_max_mva", "sk3max_mva"])
        if sk_max is None:
            raise ValueError(f"External grid {grid_data.get('id', '')} is missing Sk_max/s_sc_max_mva")
        sk_min = _first(grid_data, ["Sk_min", "s_sc_min_mva", "sk_min_mva", "sk3min_mva"], sk_max)

        grid = ExternalGrid(
            id=grid_data["id"],
            name=grid_data.get("name"),
            bus_id=grid_data["bus_id"],
            Sk_max=sk_max,
            Sk_min=sk_min,
            rx_ratio=_first(grid_data, ["rx_ratio", "rx_max", "rx"], 0.1),
            c_max=_first(grid_data, ["c_max", "c"], 1.1),
            c_min=grid_data.get("c_min", 1.0),
            Z0_Z1_ratio=grid_data.get("Z0_Z1_ratio", 1.0),
            X0_X1_ratio=grid_data.get("X0_X1_ratio", 1.0),
            R0_X0_ratio=grid_data.get("R0_X0_ratio"),
        )
        network.add_element(grid)

    # Add lines
    for line_data in elements.get("lines", []):
        parallel_lines = int(_first(line_data, ["parallel_lines", "parallel_cables", "parallel", "n_parallel"], 1))
        line = Line(
            id=line_data["id"],
            name=line_data.get("name"),
            bus_from=line_data["bus_from"],
            bus_to=line_data["bus_to"],
            length=line_data["length"],
            r1_per_km=line_data["r1_per_km"],
            x1_per_km=line_data["x1_per_km"],
            r0_per_km=line_data.get("r0_per_km", line_data["r1_per_km"] * 3),
            x0_per_km=line_data.get("x0_per_km", line_data["x1_per_km"] * 3),
            parallel_lines=max(parallel_lines, 1),
            is_cable=line_data.get("type") == "cable",
            in_service=line_data.get("in_service", True),
        )
        network.add_element(line)

    # Add 2W transformers
    for tr_data in elements.get("transformers_2w", []):
        uk_percent = _first(tr_data, ["uk_percent", "vk_percent", "uk"])
        if uk_percent is None:
            raise ValueError(f"Transformer {tr_data.get('id', '')} is missing uk_percent/vk_percent")

        pkr = tr_data.get("Pkr")
        if pkr is None and tr_data.get("vkr_percent") is not None:
            pkr = (tr_data["vkr_percent"] / 100.0) * tr_data["Sn"] * 1000.0

        tr = Transformer2W(
            id=tr_data["id"],
            name=tr_data.get("name"),
            bus_hv=tr_data["bus_hv"],
            bus_lv=tr_data["bus_lv"],
            Sn=tr_data["Sn"],
            Un_hv=tr_data["Un_hv"],
            Un_lv=tr_data["Un_lv"],
            uk_percent=uk_percent,
            Pkr=pkr if pkr is not None else 0,
            vector_group=tr_data.get("vector_group", "Dyn11"),
            tap_position=tr_data.get("tap_position", 0),
            neutral_grounding_hv=tr_data.get("neutral_grounding_hv", "isolated"),
            neutral_grounding_lv=tr_data.get("neutral_grounding_lv", "isolated"),
            grounding_impedance_hv_id=tr_data.get("grounding_impedance_hv_id"),
            grounding_impedance_lv_id=tr_data.get("grounding_impedance_lv_id"),
            in_service=tr_data.get("in_service", True),
        )
        network.add_element(tr)

    # Add 3W transformers
    for tr_data in elements.get("transformers_3w", []):
        tr = Transformer3W(
            id=tr_data["id"],
            name=tr_data.get("name"),
            bus_hv=tr_data["bus_hv"],
            bus_mv=tr_data["bus_mv"],
            bus_lv=tr_data["bus_lv"],
            Sn_hv=tr_data["Sn_hv"],
            Sn_mv=tr_data.get("Sn_mv", tr_data["Sn_hv"]),
            Sn_lv=tr_data.get("Sn_lv", tr_data["Sn_hv"]),
            Un_hv=tr_data["Un_hv"],
            Un_mv=tr_data["Un_mv"],
            Un_lv=tr_data["Un_lv"],
            uk_hv_mv_percent=tr_data["uk_hv_mv_percent"],
            uk_hv_lv_percent=tr_data["uk_hv_lv_percent"],
            uk_mv_lv_percent=tr_data["uk_mv_lv_percent"],
            Pkr_hv_mv=tr_data.get("Pkr_hv_mv", 0),
            Pkr_hv_lv=tr_data.get("Pkr_hv_lv", 0),
            Pkr_mv_lv=tr_data.get("Pkr_mv_lv", 0),
            in_service=tr_data.get("in_service", True),
        )
        network.add_element(tr)

    # Add autotransformers
    for at_data in elements.get("autotransformers", []):
        at = Autotransformer(
            id=at_data["id"],
            name=at_data.get("name"),
            bus_hv=at_data["bus_hv"],
            bus_lv=at_data["bus_lv"],
            Sn=at_data["Sn"],
            Un_hv=at_data["Un_hv"],
            Un_lv=at_data["Un_lv"],
            uk_percent=at_data["uk_percent"],
            Pkr=at_data.get("Pkr", 0),
            neutral_grounding=at_data.get("neutral_grounding", "grounded"),
            has_tertiary_delta=at_data.get("has_tertiary_delta", False),
            tertiary_Sn=at_data.get("tertiary_Sn"),
            in_service=at_data.get("in_service", True),
        )
        network.add_element(at)

    # Add generators
    for gen_data in elements.get("generators", []):
        gen = SynchronousGenerator(
            id=gen_data["id"],
            name=gen_data.get("name"),
            bus_id=gen_data["bus_id"],
            Sn=gen_data["Sn"],
            Un=gen_data["Un"],
            Xd_pp=gen_data["Xd_pp"],
            Ra=gen_data.get("Ra", 0),
            cos_phi=gen_data.get("cos_phi", 0.85),
            connection=gen_data.get("connection", "direct"),
            in_service=gen_data.get("in_service", True),
        )
        network.add_element(gen)

    # Add motors
    for motor_data in elements.get("motors", []):
        mode = InputMode(motor_data.get("input_mode", "power"))
        motor = AsynchronousMotor(
            id=motor_data["id"],
            name=motor_data.get("name"),
            bus_id=motor_data["bus_id"],
            Un=motor_data["Un"],
            input_mode=mode,
            Pn=motor_data.get("Pn"),
            eta=motor_data.get("eta"),
            cos_phi=motor_data.get("cos_phi"),
            In=motor_data.get("In"),
            Ia_In=motor_data["Ia_In"],
            pole_pairs=motor_data.get("pole_pairs", 1),
            include_in_sc=motor_data.get("include_in_sc", True),
            in_service=motor_data.get("in_service", True),
        )
        network.add_element(motor)

    # Add impedances
    for imp_data in elements.get("impedances", []):
        imp = Impedance(
            id=imp_data["id"],
            name=imp_data.get("name"),
            bus_from=imp_data["bus_from"],
            bus_to=imp_data["bus_to"],
            R=imp_data["R"],
            X=imp_data["X"],
            R0=imp_data.get("R0"),
            X0=imp_data.get("X0"),
            in_service=imp_data.get("in_service", True),
        )
        network.add_element(imp)

    # Add grounding impedances
    for gi_data in elements.get("grounding_impedances", []):
        gi = GroundingImpedance(
            id=gi_data["id"],
            name=gi_data.get("name"),
            R=gi_data["R"],
            X=gi_data["X"],
        )
        network.add_element(gi)

    # Add PSUs
    for psu_data in elements.get("psus", []):
        psu = PowerStationUnit(
            id=psu_data["id"],
            name=psu_data.get("name"),
            generator_id=psu_data["generator_id"],
            transformer_id=psu_data["transformer_id"],
            has_oltc=psu_data.get("has_oltc", True),
            generator_winding=psu_data.get("generator_winding"),
        )
        network.add_element(psu)

    return network
