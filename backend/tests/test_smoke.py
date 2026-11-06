import io
import uuid
import zipfile

import pytest
from openpyxl import load_workbook
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.config.database import Base
from app.models import (
    Project,
    ProjectUpload,
    TestCase as CaseRecord,
    TestExecutionHistory as ExecutionHistoryRecord,
    User,
)


@pytest.fixture
def client(isolated_database):
    with TestClient(main.app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_core_workflow(client):
    email = f"test-{uuid.uuid4().hex[:10]}@example.com"
    registered = client.post("/api/auth/register", json={"name":"Test Developer", "email":email, "password":"correct-horse-battery"})
    assert registered.status_code == 201, registered.text
    token = registered.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    project = client.post("/api/projects", headers=headers, json={"name":"Test Project", "description":"test", "technology":"FastAPI"})
    assert project.status_code == 201, project.text
    bug = client.post("/api/bugs", headers=headers, json={"title":"API returns 500 error", "project_id":project.json()["id"], "error_message":"Internal Server Error 500"})
    assert bug.status_code == 201, bug.text
    analysis = client.post(f"/api/bugs/{bug.json()['id']}/analyze", headers=headers)
    assert analysis.status_code == 200, analysis.text
    assert analysis.json()["root_cause"]
    cases = client.get("/api/test-cases", headers=headers, params={"bug_id":bug.json()["id"]})
    assert cases.status_code == 200 and len(cases.json()) >= 1
    initial_case_ids = {case["id"] for case in cases.json()}
    repeated_analysis = client.post(
        f"/api/bugs/{bug.json()['id']}/analyze",
        headers=headers,
    )
    assert repeated_analysis.status_code == 200, repeated_analysis.text
    repeated_cases = client.get(
        "/api/test-cases",
        headers=headers,
        params={"bug_id": bug.json()["id"]},
    )
    assert {case["id"] for case in repeated_cases.json()} == initial_case_ids
    workbook_response = client.get("/api/test-cases/excel", headers=headers)
    assert workbook_response.status_code == 200
    workbook = load_workbook(io.BytesIO(workbook_response.content), read_only=True)
    sheet = workbook["Test Cases"]
    all_cases_response = client.get("/api/test-cases", headers=headers)
    all_cases = all_cases_response.json()
    assert sheet.max_row == len(all_cases) + 1
    assert [cell.value for cell in sheet[1]] == [
        "Test Case ID",
        "Bug ID",
        "Scenario",
        "Input",
        "Expected Result",
        "Type",
        "Priority",
        "Marked Executed",
    ]
    exported_scenarios = {
        row[2]
        for row in sheet.iter_rows(min_row=2, values_only=True)
    }
    assert exported_scenarios == {case["scenario"] for case in all_cases}
    workbook.close()


def test_project_test_report_excel_treats_untrusted_strings_as_text(
    client, tmp_path, monkeypatch
):
    registration = client.post(
        "/api/auth/register",
        json={
            "name": "Report Owner",
            "email": f"report-{uuid.uuid4().hex}@example.com",
            "password": "test-password-123",
        },
    )
    headers = {
        "Authorization": "Bearer " + registration.json()["access_token"]
    }
    formula = '=HYPERLINK("https://example.invalid","click")'
    report = {
        "upload_id": "a" * 32,
        "report_type": "STATIC_SOURCE_CHECKS",
        "overall_status": "STATIC_CHECKS_PASSED",
        "summary": {
            "total_checks": 1,
            "passed": 1,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "files_checked": 1,
        },
        "failed_checks": [],
        "error_checks": [],
        "skipped_checks": [],
        "all_results": [
            {"check": formula, "status": "PASS", "details": formula}
        ],
    }
    report_dir = tmp_path / "project-uploads"
    report_dir.mkdir()
    monkeypatch.setattr(main, "PROJECT_UPLOAD_DIR", report_dir)
    monkeypatch.setattr(
        main,
        "get_project_test_report",
        lambda *_args, **_kwargs: report,
    )

    response = client.get(
        f"/api/projects/{report['upload_id']}/test-report/excel",
        headers=headers,
    )

    assert response.status_code == 200
    workbook = load_workbook(io.BytesIO(response.content), read_only=True)
    sheet = workbook["Test Results"]
    assert sheet["A2"].value == formula
    assert sheet["A2"].data_type == "s"
    assert sheet["C2"].value == formula
    assert sheet["C2"].data_type == "s"
    workbook.close()


def test_project_delete_detaches_and_preserves_upload_history():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = session_factory()
    try:
        user = User(
            name="Project Owner",
            email=f"project-delete-{uuid.uuid4().hex}@example.com",
            password_hash="test-hash",
        )
        project = Project(name="Project with source artifacts", owner=user)
        db.add_all([user, project])
        db.flush()

        upload_id = uuid.uuid4().hex
        db.add_all([
            ProjectUpload(
                upload_id=upload_id,
                owner_id=user.id,
                project_id=project.id,
            ),
            CaseRecord(
                project_id=project.id,
                upload_id=upload_id,
                scenario="Preserved source case",
                input_data="input",
                expected_result="result",
                priority="MEDIUM",
                test_type="FUNCTIONAL",
                executed=False,
            ),
            ExecutionHistoryRecord(
                upload_id=upload_id,
                project_id=project.id,
                initiated_by=user.id,
                status="PASSED",
                execution_mode="STATIC_SAFE_CHECKS",
                total=1,
                passed=1,
                failed=0,
                errors=0,
                skipped=0,
                duration_seconds=0,
                runtime_executed=False,
                output="",
                error_message="",
                failure_reason="",
            ),
        ])
        db.commit()
        project_id = project.id

        main.delete_project(project_id, db, user)

        assert db.get(Project, project_id) is None
        assert db.get(ProjectUpload, upload_id).project_id is None
        source_case = db.query(CaseRecord).filter_by(upload_id=upload_id).one()
        assert source_case.project_id is None
        history = db.query(ExecutionHistoryRecord).filter_by(upload_id=upload_id).one()
        assert history.project_id is None
    finally:
        db.close()
        engine.dispose()


def test_execute_tests_uses_configured_file_limit(
    client, tmp_path, monkeypatch
):
    upload_dir = tmp_path / "project-uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(main, "PROJECT_UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(main.settings, "test_runner_max_files", 1)

    registration = client.post(
        "/api/auth/register",
        json={
            "name": "Execution Limit Owner",
            "email": f"execution-limit-{uuid.uuid4().hex}@example.com",
            "password": "test-password-123",
        },
    )
    headers = {
        "Authorization": "Bearer " + registration.json()["access_token"]
    }
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as project_zip:
        project_zip.writestr("src/one.py", "pass")
        project_zip.writestr("src/two.py", "pass")
    uploaded = client.post(
        "/api/projects/upload-source",
        headers=headers,
        files={"file": ("source.zip", archive.getvalue(), "application/zip")},
    )
    assert uploaded.status_code == 200, uploaded.text

    response = client.post(
        f"/api/projects/{uploaded.json()['upload_id']}/execute-tests",
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "ZIP contains too many files."


def test_execution_history_is_persisted_and_exported(
    client, tmp_path, monkeypatch
):
    upload_dir = tmp_path / "project-uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(main, "PROJECT_UPLOAD_DIR", upload_dir)

    registration = client.post(
        "/api/auth/register",
        json={
            "name": "Execution Owner",
            "email": f"execution-{uuid.uuid4().hex}@example.com",
            "password": "test-password-123",
        },
    )
    headers = {
        "Authorization": "Bearer " + registration.json()["access_token"]
    }
    project = client.post(
        "/api/projects",
        headers=headers,
        json={"name": "Execution history project"},
    )
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as project_zip:
        project_zip.writestr("tests/test_example.py", "def test_example(): pass")
    uploaded = client.post(
        "/api/projects/upload-source",
        headers=headers,
        data={"project_id": str(project.json()["id"])},
        files={"file": ("source.zip", archive.getvalue(), "application/zip")},
    )
    assert uploaded.status_code == 200, uploaded.text
    upload_id = uploaded.json()["upload_id"]

    monkeypatch.setattr(
        main,
        "run_project_tests",
        lambda _path: {
            "status": "PASSED",
            "execution_mode": "DOCKER_ISOLATED",
            "runtime_executed": True,
            "total": 3,
            "passed": 2,
            "failed": 1,
            "errors": 0,
            "skipped": 0,
            "output": "2 passed, 1 failed",
            "message": "Docker test execution completed.",
        },
    )
    executed = client.post(
        f"/api/projects/{upload_id}/execute-tests",
        headers=headers,
    )
    assert executed.status_code == 200, executed.text

    history = client.get(
        f"/api/projects/{upload_id}/execution-history",
        headers=headers,
        params={"status_filter": "passed", "limit": 1},
    )
    assert history.status_code == 200, history.text
    assert len(history.json()) == 1
    assert history.json()[0]["id"] == executed.json()["execution_id"]
    assert history.json()[0]["project_id"] == project.json()["id"]
    assert history.json()[0]["failed"] == 1
    assert history.json()[0]["runtime_executed"] is True

    excel = client.get(
        f"/api/projects/{upload_id}/execution-history/excel",
        headers=headers,
    )
    assert excel.status_code == 200
    workbook = load_workbook(io.BytesIO(excel.content), read_only=True)
    assert workbook["Execution History"].max_row == 2
    workbook.close()

    other_registration = client.post(
        "/api/auth/register",
        json={
            "name": "Other User",
            "email": f"other-{uuid.uuid4().hex}@example.com",
            "password": "test-password-123",
        },
    )
    other_headers = {
        "Authorization": "Bearer " + other_registration.json()["access_token"]
    }
    forbidden = client.get(
        f"/api/projects/{upload_id}/execution-history",
        headers=other_headers,
    )
    assert forbidden.status_code == 404
