
from pathlib import Path
import re
import shutil
import subprocess


DOCKER_IMAGE = "ai-bug-detective-python-runner:latest"
DEFAULT_TIMEOUT_SECONDS = 120


def run_static_fallback(project_path: Path) -> dict:
    """
    Safe fallback when Docker is unavailable.
    Performs static source checks only.
    Never executes uploaded project code on the host.
    """
    try:
        from app.test_runner.source_checker import check_project_source

        result = check_project_source(project_path)

        results = result.get("results", [])

        output = "\n".join(
            f'{item.get("status", "")}: '
            f'{item.get("check", "")} - '
            f'{item.get("details", "")}'
            for item in results
        )

        return {
            "status": "DOCKER_UNAVAILABLE",
            "message": (
                "Docker is unavailable. Static source checks completed; "
                "runtime tests were not executed."
            ),
            "total": result.get("total_checks", 0),
            "passed": result.get("passed", 0),
            "failed": result.get("failed", 0),
            "errors": result.get("errors", 0),
            "skipped": 0,
            "runtime_executed": False,
            "execution_mode": "STATIC_SAFE_CHECKS",
            "output": output[-12000:],
        }

    except (ImportError, OSError, ValueError) as exc:
        return {
            "status": "ERROR",
            "message": "Static fallback could not complete.",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "runtime_executed": False,
            "execution_mode": "STATIC_SAFE_CHECKS",
            "output": str(exc)[:2000],
        }


def run_project_tests(
    project_dir: str | Path,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """
    Run project pytest tests inside an isolated Docker container.

    If Docker is unavailable, run safe static source checks instead.
    Uploaded code is never executed directly on the host.
    """

    project_path = Path(project_dir).resolve()

    # 1. Validate the project directory.
    if not project_path.is_dir():
        return {
            "status": "ERROR",
            "message": "Project directory was not found.",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "runtime_executed": False,
            "execution_mode": "NOT_EXECUTED",
            "output": "",
        }

    # 2. If Docker is unavailable, use the safe static-check fallback.
    if shutil.which("docker") is None:
        return run_static_fallback(project_path)

    # 3. Check whether the uploaded project contains tests.
    if not (project_path / "tests").is_dir():
        return {
            "status": "NO_TESTS_FOUND",
            "message": (
                "No tests directory was found in the project. "
                "Runtime tests were not executed."
            ),
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "runtime_executed": False,
            "execution_mode": "DOCKER_ISOLATED",
            "output": "",
        }

    # 4. Run tests inside the isolated Docker container.
    command = [
        "docker",
        "run",
        "--rm",
        "--network", "none",
        "--memory", "512m",
        "--cpus", "1",
        "--pids-limit", "128",
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", "65534:65534",
        "--mount",
        f"type=bind,source={project_path},target=/workspace,readonly",
        "--workdir", "/workspace",
        DOCKER_IMAGE,
        "python", "-m", "pytest", "-q", "tests",
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(1, min(timeout_seconds, 300)),
            check=False,
            shell=False,
        )

        output = (
            (completed.stdout or "")
            + "\n"
            + (completed.stderr or "")
        ).strip()

        passed = 0
        failed = 0
        errors = 0
        skipped = 0

        # Parse pytest summary counts.
        for line in output.splitlines():
            if not any(
                marker in line
                for marker in (
                    " passed",
                    " failed",
                    " error",
                    " errors",
                    " skipped",
                )
            ):
                continue

            counts = {
                name: int(value)
                for value, name in re.findall(
                    r"(\d+)\s+(passed|failed|errors?|skipped)",
                    line,
                )
            }

            if counts:
                passed = counts.get("passed", 0)
                failed = counts.get("failed", 0)
                errors = counts.get("error", counts.get("errors", 0))
                skipped = counts.get("skipped", 0)

        total = passed + failed + errors + skipped

        if completed.returncode == 0:
            status = "PASSED"
        elif total > 0:
            status = "FAILED"
        else:
            status = "ERROR"

        return {
            "status": status,
            "message": "Docker test execution completed.",
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "exit_code": completed.returncode,
            "runtime_executed": True,
            "execution_mode": "DOCKER_ISOLATED",
            "output": output[-12000:],
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT",
            "message": "Tests exceeded the execution time limit.",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "runtime_executed": False,
            "execution_mode": "DOCKER_ISOLATED",
            "output": "",
        }

    except OSError as exc:
        return {
            "status": "ERROR",
            "message": "Unable to start the Docker test runner.",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "runtime_executed": False,
            "execution_mode": "DOCKER_ISOLATED",
            "output": str(exc)[:2000],
        }
