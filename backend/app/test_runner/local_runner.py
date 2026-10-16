
from pathlib import Path
import shutil
import subprocess


DOCKER_IMAGE = "ai-bug-detective-python-runner:latest"
DEFAULT_TIMEOUT_SECONDS = 120


def run_project_tests(
    project_dir: str | Path,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """
    Prepare isolated pytest execution for uploaded projects.

    Uploaded code is never executed directly on the host.
    Docker must be installed and the runner image must exist.
    """

    project_path = Path(project_dir).resolve()

    if not project_path.is_dir():
        return {
            "status": "ERROR",
            "message": "Project directory was not found.",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "output": "",
        }

    if shutil.which("docker") is None:
        return {
            "status": "DOCKER_UNAVAILABLE",
            "message": (
                "Docker is unavailable. "
                "Only static source checks can run on this system."
            ),
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "output": "",
        }

    if not (project_path / "tests").is_dir():
        return {
            "status": "NO_TESTS_FOUND",
            "message": "No tests directory was found in the project.",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "output": "",
        }

    command = [
        "docker", "run", "--rm",
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

        # Parse the summary from pytest's final output line.
        passed = failed = errors = skipped = 0

        for line in output.splitlines():
            if " passed" not in line and not any(
                marker in line
                for marker in (" failed", " error", " skipped")
            ):
                continue

            import re

            counts = {
                name: int(value or 0)
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
        elif total:
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
            "output": "",
        }

    except OSError:
        return {
            "status": "ERROR",
            "message": "Unable to start the Docker test runner.",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "output": "",
        }
