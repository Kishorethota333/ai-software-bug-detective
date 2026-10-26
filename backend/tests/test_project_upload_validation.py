import io
import uuid
import zipfile
from types import SimpleNamespace

from openpyxl import load_workbook
import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def upload_client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "PROJECT_UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)
    email = f"zip-test-{uuid.uuid4().hex}@example.com"
    registration = client.post(
        "/api/auth/register",
        json={"name": "ZIP Test", "email": email, "password": "test-password-123"},
    )
    assert registration.status_code == 201, registration.text
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    return client, headers, tmp_path


def make_zip(files):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        for name, content in files:
            archive.writestr(name, content)
    return payload.getvalue()


def upload(client, headers, payload):
    return client.post(
        "/api/projects/upload-source",
        headers=headers,
        files={"file": ("project.zip", payload, "application/zip")},
    )


def test_upload_source_requires_authentication(upload_client):
    client, _, _ = upload_client

    response = upload(client, None, make_zip([("project/main.py", "pass")]))

    assert response.status_code == 401


def test_upload_warns_for_generated_files_and_removes_sensitive_files(upload_client):
    client, headers, upload_dir = upload_client
    payload = make_zip(
        [
            ("project/src/main.py", "print('safe source')"),
            ("project/node_modules/pkg/index.js", "module.exports = 1"),
            ("project/.pytest_cache/v/cache/nodeids", "[]"),
            ("project/.env", "DO_NOT_RETURN_OR_RETAIN"),
            ("project/.ssh/id_rsa", "PRIVATE_KEY_CONTENT"),
        ]
    )

    response = upload(client, headers, payload)

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["file_count"] == 5
    assert result["source_file_count"] == 1
    assert {"name": "node_modules/", "count": 1} in result["unnecessary_items"]
    assert {"name": ".pytest_cache/", "count": 1} in result["unnecessary_items"]
    assert result["security_warnings"] == [
        {"name": ".env", "count": 1},
        {"name": "id_rsa", "count": 1},
    ]
    assert "DO_NOT_RETURN_OR_RETAIN" not in response.text
    assert "PRIVATE_KEY_CONTENT" not in response.text

    stored_zip = upload_dir / f'{result["upload_id"]}.zip'
    with zipfile.ZipFile(stored_zip) as archive:
        names = archive.namelist()
        assert "project/.env" not in names
        assert "project/.ssh/id_rsa" not in names
        assert "project/src/main.py" in names
        assert b"DO_NOT_RETURN_OR_RETAIN" not in stored_zip.read_bytes()
        assert b"PRIVATE_KEY_CONTENT" not in stored_zip.read_bytes()
    assert not list(upload_dir.glob("*.uploading.zip"))
    assert not list(upload_dir.glob("*.sanitized.zip"))


def test_upload_does_not_overwrite_an_existing_final_destination(upload_client, monkeypatch):
    client, headers, upload_dir = upload_client
    staging_id = uuid.uuid4().hex
    existing_id = uuid.uuid4().hex
    final_id = uuid.uuid4().hex
    existing_path = upload_dir / f"{existing_id}.zip"
    existing_path.write_bytes(b"existing unrelated upload")
    upload_ids = iter((staging_id, existing_id, final_id))

    def next_upload_id():
        return SimpleNamespace(hex=next(upload_ids))

    monkeypatch.setattr(
        main,
        "uuid",
        SimpleNamespace(uuid4=next_upload_id),
    )

    response = upload(client, headers, make_zip([("project/main.py", "pass")]))

    assert response.status_code == 200, response.text
    assert response.json()["upload_id"] == final_id
    assert existing_path.read_bytes() == b"existing unrelated upload"
    assert (upload_dir / f"{final_id}.zip").is_file()
    assert not list(upload_dir.glob("*.uploading.zip"))
    assert not list(upload_dir.glob("*.sanitized.zip"))


def test_upload_cleans_staging_files_when_atomic_publish_fails(
    upload_client, monkeypatch
):
    client, headers, upload_dir = upload_client

    def fail_replace(_source, _destination):
        raise PermissionError("simulated Windows rename denial")

    monkeypatch.setattr(main.os, "replace", fail_replace)

    response = upload(client, headers, make_zip([("project/main.py", "pass")]))

    assert response.status_code == 500
    assert "Support reference:" in response.json()["detail"]
    assert not list(upload_dir.glob("*.zip"))
    assert not list(upload_dir.glob("*.uploading.zip"))
    assert not list(upload_dir.glob("*.sanitized.zip"))


def test_upload_rejects_archive_without_recognizable_source(upload_client):
    client, headers, _ = upload_client
    response = upload(client, headers, make_zip([("project/README.md", "documentation")]))

    assert response.status_code == 400
    assert response.json()["detail"] == "The ZIP does not contain recognizable project source files."


def test_upload_rejects_invalid_zip(upload_client):
    client, headers, _ = upload_client
    response = upload(client, headers, b"not a zip archive")

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded file is not a valid ZIP archive."


def test_upload_reports_safe_error_and_cleans_staged_zip(upload_client, monkeypatch, caplog):
    client, headers, upload_dir = upload_client

    def fail_zip_test(_archive):
        raise OSError("private filesystem details")

    monkeypatch.setattr(main.zipfile.ZipFile, "testzip", fail_zip_test)
    response = upload(client, headers, make_zip([("project/main.py", "pass")]))

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "Support reference:" in detail
    assert "private filesystem details" not in detail
    assert list(upload_dir.iterdir()) == []
    assert "ZIP upload storage/read failure" in caplog.text
    assert "private filesystem details" in caplog.text


def test_upload_rejects_corrupted_zip_integrity(upload_client):
    client, headers, _ = upload_client
    payload = make_zip([("project/main.py", "print('integrity')")])
    damaged = bytearray(payload)
    content_offset = damaged.index(b"print('integrity')")
    damaged[content_offset] ^= 1

    response = upload(client, headers, bytes(damaged))

    assert response.status_code == 400
    assert response.json()["detail"] == "The ZIP archive is corrupted."


def test_upload_rejects_path_traversal_with_windows_separators(upload_client):
    client, headers, _ = upload_client
    response = upload(client, headers, make_zip([("..\\outside.py", "print('unsafe')")]))

    assert response.status_code == 400
    assert response.json()["detail"].startswith("ZIP contains unsafe file paths.")


def test_upload_enforces_entry_count_and_size_limits(upload_client, monkeypatch):
    client, headers, _ = upload_client
    monkeypatch.setattr(main, "MAX_PROJECT_FILES", 1)
    too_many_files = make_zip(
        [("project/one.py", "pass"), ("project/two.py", "pass")]
    )
    response = upload(client, headers, too_many_files)
    assert response.status_code == 400
    assert response.json()["detail"] == "ZIP contains too many files."

    monkeypatch.setattr(main, "MAX_PROJECT_FILES", 5000)
    monkeypatch.setattr(main, "MAX_PROJECT_ZIP_SIZE", 10)
    response = upload(client, headers, make_zip([("project/main.py", "print('large')")]))
    assert response.status_code == 413
    assert response.json()["detail"] == "ZIP file must be 500 MB or smaller."


def test_directory_records_do_not_count_against_file_limit(upload_client, monkeypatch):
    client, headers, _ = upload_client
    monkeypatch.setattr(main, "MAX_PROJECT_FILES", 1)
    payload = make_zip(
        [
            ("project/", ""),
            ("project/src/", ""),
            ("project/src/main.py", "pass"),
        ]
    )

    response = upload(client, headers, payload)

    assert response.status_code == 200, response.text
    assert response.json()["file_count"] == 1


def test_upload_enforces_expanded_size_limit(upload_client, monkeypatch):
    client, headers, _ = upload_client
    monkeypatch.setattr(main, "MAX_PROJECT_UNPACKED_SIZE", 4)
    response = upload(client, headers, make_zip([("project/main.py", "12345")]))

    assert response.status_code == 400
    assert response.json()["detail"] == "Uncompressed project size exceeds 200 MB."


def test_large_safe_check_file_is_reported_as_skipped(upload_client):
    client, headers, upload_dir = upload_client
    payload = make_zip(
        [
            ("project/main.py", "pass"),
            ("project/generated.py", "x" * (1024 * 1024 + 1)),
        ]
    )
    upload_response = upload(client, headers, payload)
    assert upload_response.status_code == 200, upload_response.text
    upload_id = upload_response.json()["upload_id"]

    checks_response = client.post(
        f"/api/projects/{upload_id}/run-tests",
        headers=headers,
    )

    assert checks_response.status_code == 200, checks_response.text
    checks = checks_response.json()
    assert checks["passed"] == 1
    assert checks["failed"] == 0
    assert checks["errors"] == 0
    assert checks["skipped"] == 1
    skipped_results = [
        item for item in checks["results"] if item["status"] == "SKIPPED"
    ]
    assert len(skipped_results) == 1
    assert "1 MB safe-check limit" in skipped_results[0]["details"]

    report_response = client.get(
        f"/api/projects/{upload_id}/test-report",
        headers=headers,
    )
    assert report_response.status_code == 200, report_response.text
    report = report_response.json()
    assert report["overall_status"] == "STATIC_CHECKS_INCOMPLETE"
    assert report["summary"]["skipped"] == 1
    assert len(report["skipped_checks"]) == 1

    excel_response = client.get(
        f"/api/projects/{upload_id}/test-report/excel",
        headers=headers,
    )
    assert excel_response.status_code == 200
    workbook = load_workbook(io.BytesIO(excel_response.content), read_only=True)
    assert workbook["Summary"]["A11"].value == "Skipped"
    assert workbook["Summary"]["B11"].value == 1
    assert workbook["Skipped Checks"]["A2"].value == "Source check: project/generated.py"
    workbook.close()


UPLOAD_ID_ENDPOINTS = (
    ("post", "analyze-source"),
    ("post", "generate-test-cases"),
    ("post", "run-tests"),
    ("post", "execute-tests"),
    ("get", "test-report"),
    ("get", "test-report/excel"),
)


def request_upload_endpoints(client, upload_id, headers=None):
    responses = []
    for method, endpoint in UPLOAD_ID_ENDPOINTS:
        request = getattr(client, method)
        responses.append(
            request(
                f"/api/projects/{upload_id}/{endpoint}",
                headers=headers,
            )
        )
    return responses


def test_upload_id_endpoints_allow_owner_access(upload_client, monkeypatch):
    client, headers, _ = upload_client
    uploaded = upload(client, headers, make_zip([("project/main.py", "pass")]))
    assert uploaded.status_code == 200, uploaded.text
    upload_id = uploaded.json()["upload_id"]

    async def fake_analyze(_context):
        return {
            "provider": "test",
            "test_cases": [
                {
                    "scenario": "Verify source is accepted",
                    "input_data": "",
                    "expected_result": "Source is accepted",
                }
            ],
        }

    monkeypatch.setattr(main, "analyze", fake_analyze)
    monkeypatch.setattr(
        main,
        "run_project_tests",
        lambda _workspace: {
            "execution_mode": "DOCKER_UNAVAILABLE",
            "status": "NOT_RUN",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 1,
            "output": "",
            "message": "Docker unavailable",
        },
    )

    responses = request_upload_endpoints(client, upload_id, headers)
    assert [response.status_code for response in responses] == [200] * len(
        UPLOAD_ID_ENDPOINTS
    )


def test_upload_id_endpoints_require_authentication(upload_client):
    client, headers, _ = upload_client
    uploaded = upload(client, headers, make_zip([("project/main.py", "pass")]))
    assert uploaded.status_code == 200, uploaded.text

    responses = request_upload_endpoints(client, uploaded.json()["upload_id"])
    assert [response.status_code for response in responses] == [401] * len(
        UPLOAD_ID_ENDPOINTS
    )


def test_upload_id_endpoints_hide_other_users_upload(upload_client):
    client, owner_headers, _ = upload_client
    uploaded = upload(client, owner_headers, make_zip([("project/main.py", "pass")]))
    assert uploaded.status_code == 200, uploaded.text

    registration = client.post(
        "/api/auth/register",
        json={
            "name": "Other User",
            "email": f"other-{uuid.uuid4().hex}@example.com",
            "password": "test-password-123",
        },
    )
    assert registration.status_code == 201, registration.text
    other_headers = {
        "Authorization": f"Bearer {registration.json()['access_token']}"
    }

    responses = request_upload_endpoints(
        client,
        uploaded.json()["upload_id"],
        other_headers,
    )
    assert [response.status_code for response in responses] == [404] * len(
        UPLOAD_ID_ENDPOINTS
    )


def test_legacy_upload_without_owner_record_is_inaccessible(upload_client):
    client, headers, upload_dir = upload_client
    legacy_id = "d" * 32
    (upload_dir / f"{legacy_id}.zip").write_bytes(
        make_zip([("project/main.py", "pass")])
    )

    responses = request_upload_endpoints(client, legacy_id, headers)
    assert [response.status_code for response in responses] == [404] * len(
        UPLOAD_ID_ENDPOINTS
    )


def test_project_detail_and_bug_analysis_require_resource_ownership(
    upload_client, monkeypatch
):
    client, owner_headers, _ = upload_client
    project_response = client.post(
        "/api/projects",
        headers=owner_headers,
        json={"name": "Owned project"},
    )
    assert project_response.status_code == 201, project_response.text
    project_id = project_response.json()["id"]

    bug_response = client.post(
        "/api/bugs",
        headers=owner_headers,
        json={"title": "Owned bug", "project_id": project_id},
    )
    assert bug_response.status_code == 201, bug_response.text
    bug_id = bug_response.json()["id"]

    other_registration = client.post(
        "/api/auth/register",
        json={
            "name": "Other User",
            "email": f"project-other-{uuid.uuid4().hex}@example.com",
            "password": "test-password-123",
        },
    )
    assert other_registration.status_code == 201, other_registration.text
    other_headers = {
        "Authorization": f"Bearer {other_registration.json()['access_token']}"
    }

    async def fake_analyze(_context):
        return {
            "root_cause": "Test root cause",
            "confidence": 0.9,
            "severity": "MEDIUM",
            "affected_component": "Test component",
            "possible_causes": "Test cause",
            "suggested_fix": "Test fix",
            "recommended_actions": "Test action",
            "provider": "test",
            "test_cases": [],
        }

    monkeypatch.setattr(main, "analyze", fake_analyze)

    assert client.get(f"/api/projects/{project_id}").status_code == 401
    assert client.post(f"/api/bugs/{bug_id}/analyze").status_code == 401
    assert (
        client.get(
            f"/api/projects/{project_id}",
            headers=owner_headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/bugs/{bug_id}/analyze",
            headers=owner_headers,
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/projects/{project_id}",
            headers=other_headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/bugs/{bug_id}/analyze",
            headers=other_headers,
        ).status_code
        == 403
    )
