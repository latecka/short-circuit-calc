"""Calculations API endpoints."""

import hashlib
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DBSession, CurrentUser
from app.models import (
    Project,
    NetworkVersion,
    CalculationRun,
    RunResult,
    CalculationMode,
    CalculationStatus,
    FaultType,
)
from app.schemas import (
    CalculationRequest,
    CalculationRunResponse,
    CalculationRunDetailResponse,
    CalculationListResponse,
    RunResultResponse,
    ImpedanceSchema,
)
from app.engine.network import Network
from app.engine.iec60909 import IEC60909Calculator

router = APIRouter(prefix="/calculations", tags=["calculations"])

ENGINE_VERSION = "1.0.0"


def _result_to_response(result: RunResult) -> RunResultResponse:
    """Convert RunResult model to response schema."""
    return RunResultResponse(
        id=result.id,
        bus_id=result.bus_id,
        fault_type=result.fault_type.value,
        Ik=result.Ik,
        ip=result.ip,
        R_X_ratio=result.R_X_ratio,
        c_factor=result.c_factor,
        Zk=ImpedanceSchema(**result.Zk),
        Z1=ImpedanceSchema(**result.Z1),
        Z2=ImpedanceSchema(**result.Z2),
        Z0=ImpedanceSchema(**result.Z0) if result.Z0 else None,
        correction_factors=result.correction_factors or {},
        warnings=result.warnings or [],
        assumptions=result.assumptions or [],
    )


def _run_to_response(run: CalculationRun, include_results: bool = False):
    """Convert CalculationRun model to response schema."""
    base = {
        "id": run.id,
        "project_id": run.project_id,
        "network_version_id": run.network_version_id,
        "user_id": run.user_id,
        "calculation_mode": run.calculation_mode.value,
        "fault_types": run.fault_types,
        "fault_buses": run.fault_buses,
        "engine_version": run.engine_version,
        "status": run.status.value,
        "error_message": run.error_message,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "result_count": len(run.results),
    }
    if include_results:
        return CalculationRunDetailResponse(
            **base,
            results=[_result_to_response(r) for r in run.results],
        )
    return CalculationRunResponse(**base)


def _build_network_from_elements(elements: dict) -> Network:
    """Build Network object from stored elements."""
    from app.engine.elements import (
        Busbar,
        ExternalGrid,
        Line,
        Transformer2W,
        Transformer3W,
        SynchronousGenerator,
        AsynchronousMotor,
        Impedance,
        GroundingImpedance,
        NeutralGrounding,
        InputMode,
    )
    from app.engine.autotransformer import Autotransformer
    from app.engine.psu import PowerStationUnit

    network = Network()

    # Add busbars
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
        grid = ExternalGrid(
            id=grid_data["id"],
            name=grid_data.get("name"),
            bus_id=grid_data["bus_id"],
            Sk_max=grid_data["Sk_max"],
            Sk_min=grid_data.get("Sk_min", grid_data["Sk_max"]),
            rx_ratio=grid_data.get("rx_ratio", 0.1),
            c_max=grid_data.get("c_max", 1.1),
            c_min=grid_data.get("c_min", 1.0),
            Z0_Z1_ratio=grid_data.get("Z0_Z1_ratio", 1.0),
            X0_X1_ratio=grid_data.get("X0_X1_ratio", 1.0),
            R0_X0_ratio=grid_data.get("R0_X0_ratio"),
        )
        network.add_element(grid)

    # Add lines
    for line_data in elements.get("lines", []):
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
            parallel_lines=line_data.get("parallel_lines", 1),
            is_cable=line_data.get("type") == "cable",
            in_service=line_data.get("in_service", True),
        )
        network.add_element(line)

    # Add 2-winding transformers
    for tr_data in elements.get("transformers_2w", []):
        ng_hv = NeutralGrounding(tr_data.get("neutral_grounding_hv", "isolated"))
        ng_lv = NeutralGrounding(tr_data.get("neutral_grounding_lv", "isolated"))
        tr = Transformer2W(
            id=tr_data["id"],
            name=tr_data.get("name"),
            bus_hv=tr_data["bus_hv"],
            bus_lv=tr_data["bus_lv"],
            Sn=tr_data["Sn"],
            Un_hv=tr_data["Un_hv"],
            Un_lv=tr_data["Un_lv"],
            uk_percent=tr_data["uk_percent"],
            Pkr=tr_data.get("Pkr", 0),
            vector_group=tr_data["vector_group"],
            tap_position=tr_data.get("tap_position", 0),
            neutral_grounding_hv=ng_hv,
            neutral_grounding_lv=ng_lv,
            in_service=tr_data.get("in_service", True),
        )
        network.add_element(tr)

    # Add 3-winding transformers
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
            vector_group_hv_mv=tr_data.get("vector_group_hv_mv", "YNyn0"),
            vector_group_hv_lv=tr_data.get("vector_group_hv_lv", "YNd11"),
            in_service=tr_data.get("in_service", True),
        )
        network.add_element(tr)

    # Add autotransformers
    for at_data in elements.get("autotransformers", []):
        ng = NeutralGrounding(at_data.get("neutral_grounding", "grounded"))
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
            vector_group=at_data.get("vector_group", "YNa0"),
            has_tertiary_delta=at_data.get("has_tertiary_delta", False),
            tertiary_Sn=at_data.get("tertiary_Sn"),
            neutral_grounding=ng,
            Z0_source=at_data.get("Z0_source", "derived"),
            Z0_measured_r=at_data.get("Z0_measured_r"),
            Z0_measured_x=at_data.get("Z0_measured_x"),
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

    return network


@router.post("", response_model=CalculationRunResponse, status_code=status.HTTP_201_CREATED)
def run_calculation(
    data: CalculationRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Run short-circuit calculation."""
    # Get network version
    version = db.query(NetworkVersion).filter(
        NetworkVersion.id == data.network_version_id
    ).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Network version not found",
        )

    # Check project ownership
    project = db.query(Project).filter(
        Project.id == version.project_id,
        Project.owner_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Calculate input hash
    input_data = {
        "elements": version.elements,
        "mode": data.calculation_mode.value,
        "fault_types": [ft.value for ft in data.fault_types],
        "fault_buses": data.fault_buses,
    }
    input_hash = hashlib.sha256(
        json.dumps(input_data, sort_keys=True).encode()
    ).hexdigest()

    # Create calculation run
    calc_mode = CalculationMode.MAX if data.calculation_mode.value == "max" else CalculationMode.MIN
    run = CalculationRun(
        project_id=project.id,
        network_version_id=version.id,
        user_id=current_user.id,
        calculation_mode=calc_mode,
        fault_types=[ft.value for ft in data.fault_types],
        fault_buses=data.fault_buses,
        engine_version=ENGINE_VERSION,
        input_hash=input_hash,
        status=CalculationStatus.RUNNING,
    )
    db.add(run)
    db.commit()

    try:
        # Build network from elements
        network = _build_network_from_elements(version.elements or {})

        # Validate requested buses exist
        for bus_id in data.fault_buses:
            if bus_id not in network.busbars:
                raise ValueError(f"Bus '{bus_id}' not found in network")

        # Create calculator
        is_max = data.calculation_mode == "max"
        calculator = IEC60909Calculator(network, is_max=is_max)

        # Run calculations
        for fault_type in data.fault_types:
            for bus_id in data.fault_buses:
                try:
                    result_data = calculator.calculate(bus_id, fault_type.value)

                    # Map fault type to enum
                    ft_enum = FaultType.IK3
                    if fault_type.value == "Ik2":
                        ft_enum = FaultType.IK2
                    elif fault_type.value == "Ik1":
                        ft_enum = FaultType.IK1

                    result = RunResult(
                        run_id=run.id,
                        bus_id=bus_id,
                        fault_type=ft_enum,
                        Ik=result_data["Ik"],
                        ip=result_data["ip"],
                        R_X_ratio=result_data["R_X_ratio"],
                        c_factor=result_data["c_factor"],
                        Zk=result_data["Zk"],
                        Z1=result_data["Z1"],
                        Z2=result_data["Z2"],
                        Z0=result_data.get("Z0"),
                        correction_factors=result_data.get("correction_factors", {}),
                        warnings=result_data.get("warnings", []),
                        assumptions=result_data.get("assumptions", []),
                    )
                    db.add(result)

                except Exception as e:
                    # Log error but continue with other calculations
                    result = RunResult(
                        run_id=run.id,
                        bus_id=bus_id,
                        fault_type=ft_enum,
                        Ik=0.0,
                        ip=0.0,
                        R_X_ratio=0.0,
                        c_factor=1.0,
                        Zk={"r": 0, "x": 0},
                        Z1={"r": 0, "x": 0},
                        Z2={"r": 0, "x": 0},
                        warnings=[f"Calculation failed: {str(e)}"],
                    )
                    db.add(result)

        run.status = CalculationStatus.COMPLETED
        run.completed_at = datetime.utcnow()

    except Exception as e:
        run.status = CalculationStatus.FAILED
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(run)

    return _run_to_response(run)


@router.get("", response_model=CalculationListResponse)
def list_calculations(
    db: DBSession,
    current_user: CurrentUser,
    project_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List calculation runs."""
    query = db.query(CalculationRun).filter(CalculationRun.user_id == current_user.id)

    if project_id:
        query = query.filter(CalculationRun.project_id == project_id)

    total = query.count()
    runs = (
        query.order_by(CalculationRun.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return CalculationListResponse(
        items=[_run_to_response(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{run_id}", response_model=CalculationRunDetailResponse)
def get_calculation(
    run_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get calculation run with results."""
    run = db.query(CalculationRun).filter(
        CalculationRun.id == run_id,
        CalculationRun.user_id == current_user.id,
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calculation not found",
        )

    return _run_to_response(run, include_results=True)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calculation(
    run_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Delete a calculation run."""
    run = db.query(CalculationRun).filter(
        CalculationRun.id == run_id,
        CalculationRun.user_id == current_user.id,
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calculation not found",
        )

    db.delete(run)
    db.commit()
