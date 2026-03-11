"""Tests for SQLAlchemy models."""

import pytest
from datetime import datetime


# Skip all tests if SQLAlchemy is not installed
pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import (
    Base,
    User,
    Project,
    NetworkVersion,
    CalculationRun,
    RunResult,
    CalculationMode,
    CalculationStatus,
    FaultType,
    Scenario,
)


@pytest.fixture
def engine():
    """Create in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session."""
    with Session(engine) as session:
        yield session


class TestUserModel:
    """Tests for User model."""

    def test_create_user(self, session):
        """Test creating a user."""
        user = User(
            email="test@example.com",
            hashed_password="hashed_password_here",
            full_name="Test User",
        )
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_superuser is False
        assert isinstance(user.created_at, datetime)

    def test_user_unique_email(self, session):
        """Test that email must be unique."""
        user1 = User(email="test@example.com", hashed_password="hash1")
        user2 = User(email="test@example.com", hashed_password="hash2")

        session.add(user1)
        session.commit()

        session.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            session.commit()


class TestProjectModel:
    """Tests for Project model."""

    def test_create_project(self, session):
        """Test creating a project."""
        user = User(email="owner@example.com", hashed_password="hash")
        session.add(user)
        session.commit()

        project = Project(
            name="Test Project",
            description="A test project",
            owner_id=user.id,
        )
        session.add(project)
        session.commit()

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.owner_id == user.id
        assert project.owner == user
        assert project in user.projects

    def test_project_cascade_delete(self, session):
        """Test that deleting user cascades to projects."""
        user = User(email="owner@example.com", hashed_password="hash")
        session.add(user)
        session.commit()

        project = Project(name="Test", owner_id=user.id)
        session.add(project)
        session.commit()

        project_id = project.id
        session.delete(user)
        session.commit()

        # Project should be deleted
        assert session.get(Project, project_id) is None


class TestNetworkVersionModel:
    """Tests for NetworkVersion model."""

    def test_create_network_version(self, session):
        """Test creating a network version with elements."""
        user = User(email="user@example.com", hashed_password="hash")
        project = Project(name="Test", owner_id=user.id)
        session.add_all([user, project])
        session.commit()

        elements = {
            "busbars": [
                {"id": "bus1", "Un": 110.0, "name": "Busbar 1"},
                {"id": "bus2", "Un": 22.0, "name": "Busbar 2"},
            ],
            "external_grids": [
                {"id": "grid1", "bus_id": "bus1", "Sk_max": 2500}
            ],
            "transformers": [
                {"id": "tr1", "bus_hv": "bus1", "bus_lv": "bus2", "Sn": 40}
            ],
        }

        version = NetworkVersion(
            project_id=project.id,
            version_number=1,
            elements=elements,
            created_by_id=user.id,
            comment="Initial version",
        )
        session.add(version)
        session.commit()

        assert version.id is not None
        assert version.version_number == 1
        assert len(version.elements["busbars"]) == 2
        assert version.elements["transformers"][0]["Sn"] == 40

    def test_latest_version_property(self, session):
        """Test Project.latest_version property."""
        user = User(email="user@example.com", hashed_password="hash")
        project = Project(name="Test", owner_id=user.id)
        session.add_all([user, project])
        session.commit()

        v1 = NetworkVersion(
            project_id=project.id,
            version_number=1,
            elements={},
            created_by_id=user.id,
        )
        v2 = NetworkVersion(
            project_id=project.id,
            version_number=2,
            elements={},
            created_by_id=user.id,
        )
        session.add_all([v1, v2])
        session.commit()

        session.refresh(project)
        assert project.latest_version.version_number == 2


class TestCalculationRunModel:
    """Tests for CalculationRun model."""

    def test_create_calculation_run(self, session):
        """Test creating a calculation run."""
        user = User(email="user@example.com", hashed_password="hash")
        project = Project(name="Test", owner_id=user.id)
        session.add_all([user, project])
        session.commit()

        version = NetworkVersion(
            project_id=project.id,
            version_number=1,
            elements={},
            created_by_id=user.id,
        )
        session.add(version)
        session.commit()

        run = CalculationRun(
            project_id=project.id,
            network_version_id=version.id,
            user_id=user.id,
            calculation_mode=CalculationMode.MAX,
            fault_types=["Ik3", "Ik2", "Ik1"],
            fault_buses=["bus1", "bus2"],
            engine_version="1.0.0",
            input_hash="abc123def456",
            status=CalculationStatus.COMPLETED,
        )
        session.add(run)
        session.commit()

        assert run.id is not None
        assert run.calculation_mode == CalculationMode.MAX
        assert "Ik3" in run.fault_types
        assert run.status == CalculationStatus.COMPLETED


class TestRunResultModel:
    """Tests for RunResult model."""

    def test_create_run_result(self, session):
        """Test creating a run result."""
        user = User(email="user@example.com", hashed_password="hash")
        project = Project(name="Test", owner_id=user.id)
        session.add_all([user, project])
        session.commit()

        version = NetworkVersion(
            project_id=project.id,
            version_number=1,
            elements={},
            created_by_id=user.id,
        )
        session.add(version)
        session.commit()

        run = CalculationRun(
            project_id=project.id,
            network_version_id=version.id,
            user_id=user.id,
            calculation_mode=CalculationMode.MAX,
            fault_types=["Ik3"],
            fault_buses=["bus1"],
            engine_version="1.0.0",
            input_hash="abc123",
        )
        session.add(run)
        session.commit()

        result = RunResult(
            run_id=run.id,
            bus_id="bus1",
            fault_type=FaultType.IK3,
            Ik=12.345,
            ip=26.789,
            R_X_ratio=0.1,
            c_factor=1.1,
            Zk={"r": 0.5, "x": 5.0},
            Z1={"r": 0.5, "x": 5.0},
            Z2={"r": 0.5, "x": 5.0},
            Z0={"r": 1.0, "x": 10.0},
            correction_factors={"KT": 0.95},
            warnings=["Motor excluded from calculation"],
            assumptions=["Z2 = Z1 assumed"],
        )
        session.add(result)
        session.commit()

        assert result.id is not None
        assert result.Ik == 12.345
        assert result.fault_type == FaultType.IK3
        assert result.Zk["x"] == 5.0
        assert "KT" in result.correction_factors

    def test_run_results_cascade(self, session):
        """Test that deleting run cascades to results."""
        user = User(email="user@example.com", hashed_password="hash")
        project = Project(name="Test", owner_id=user.id)
        session.add_all([user, project])
        session.commit()

        version = NetworkVersion(
            project_id=project.id,
            version_number=1,
            elements={},
            created_by_id=user.id,
        )
        session.add(version)
        session.commit()

        run = CalculationRun(
            project_id=project.id,
            network_version_id=version.id,
            user_id=user.id,
            engine_version="1.0.0",
            input_hash="abc",
        )
        session.add(run)
        session.commit()

        result = RunResult(
            run_id=run.id,
            bus_id="bus1",
            fault_type=FaultType.IK3,
            Ik=10.0,
            ip=20.0,
            R_X_ratio=0.1,
            c_factor=1.1,
            Zk={"r": 1, "x": 1},
            Z1={"r": 1, "x": 1},
            Z2={"r": 1, "x": 1},
        )
        session.add(result)
        session.commit()

        result_id = result.id
        session.delete(run)
        session.commit()

        assert session.get(RunResult, result_id) is None


class TestScenarioModel:
    """Tests for Scenario model element filtering and breaker state mapping."""

    def test_breaker_states_disable_line(self, session):
        user = User(email="scenario1@example.com", hashed_password="hash")
        session.add(user)
        session.commit()
        project = Project(name="Scenario Test", owner_id=user.id)
        session.add(project)
        session.commit()

        scenario = Scenario(
            project_id=project.id,
            name="S1",
            element_states={"breakers": {"L1": False}},
        )
        session.add(scenario)
        session.commit()

        assert scenario.is_element_active("lines", "L1") is False
        assert scenario.is_element_active("lines", "L2") is True

    def test_breaker_states_require_all_transformer_sides_closed(self, session):
        user = User(email="scenario2@example.com", hashed_password="hash")
        session.add(user)
        session.commit()
        project = Project(name="Scenario Test", owner_id=user.id)
        session.add(project)
        session.commit()

        scenario = Scenario(
            project_id=project.id,
            name="S2",
            element_states={"breakers": {"T1_HV": True, "T1_LV": False}},
        )
        session.add(scenario)
        session.commit()

        assert scenario.is_element_active("transformers_2w", "T1") is False

        scenario.element_states = {"breakers": {"T1_HV": True, "T1_LV": True}}
        assert scenario.is_element_active("transformers_2w", "T1") is True

    def test_get_active_elements_uses_breaker_states(self, session):
        user = User(email="scenario3@example.com", hashed_password="hash")
        session.add(user)
        session.commit()
        project = Project(name="Scenario Test", owner_id=user.id)
        session.add(project)
        session.commit()

        scenario = Scenario(
            project_id=project.id,
            name="S3",
            element_states={"breakers": {"L1": False, "T1_HV": True, "T1_LV": False}},
        )

        elements = {
            "busbars": [{"id": "B1"}, {"id": "B2"}],
            "lines": [{"id": "L1"}, {"id": "L2"}],
            "transformers_2w": [{"id": "T1"}, {"id": "T2"}],
        }
        filtered = scenario.get_active_elements(elements)

        assert [e["id"] for e in filtered["lines"]] == ["L2"]
        assert [e["id"] for e in filtered["transformers_2w"]] == ["T2"]
