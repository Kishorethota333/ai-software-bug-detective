import subprocess

from app.config.settings import settings
from app.test_runner import local_runner


def test_runner_uses_configured_timeout_without_starting_docker(
    tmp_path, monkeypatch
):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_sample.py").write_text(
        "def test_sample(): pass\n",
        encoding="utf-8",
    )
    captured = {}

    def fake_run(command, **kwargs):
        captured["timeout"] = kwargs["timeout"]
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="1 passed",
            stderr="",
        )

    monkeypatch.setattr(settings, "test_runner_timeout_seconds", 17)
    monkeypatch.setattr(local_runner.shutil, "which", lambda _name: "docker")
    monkeypatch.setattr(local_runner.subprocess, "run", fake_run)

    result = local_runner.run_project_tests(tmp_path)

    assert captured["timeout"] == 17
    assert result["status"] == "PASSED"
    assert result["runtime_executed"] is True


def test_runner_uses_static_checks_when_docker_is_unavailable(
    tmp_path, monkeypatch
):
    (tmp_path / "main.py").write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setattr(local_runner.shutil, "which", lambda _name: None)

    result = local_runner.run_project_tests(tmp_path)

    assert result["execution_mode"] == "STATIC_SAFE_CHECKS"
    assert result["runtime_executed"] is False
    assert result["passed"] == 1
    assert "runtime tests were not executed" in result["message"]
