
import ast
import json
import subprocess
from pathlib import Path


MAX_FILE_BYTES = 1024 * 1024

PYTHON_SUFFIXES = {".py"}
JAVASCRIPT_SUFFIXES = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}


def _result(check: str, status: str, details: str) -> dict:
    return {
        "check": check[:240],
        "status": status,
        "details": details[:1000],
    }


def check_project_source(project_dir: str | Path) -> dict:
    """
    Perform safe syntax and manifest checks.

    Source files are parsed only; uploaded project code is not executed.
    JavaScript/React syntax checks use the application's installed Babel parser.
    """

    project_path = Path(project_dir).resolve()

    if not project_path.is_dir():
        return {
            "status": "ERROR",
            "message": "Project directory was not found.",
            "total_checks": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "results": [],
        }

    results = []
    files_checked = 0

    # Locate Babel parser from this application, not the uploaded project.
    app_root = Path(__file__).resolve().parents[3]
    frontend_dir = app_root / "frontend"
    babel_parser = frontend_dir / "node_modules" / "@babel" / "parser"

    for file_path in project_path.rglob("*"):
        if not file_path.is_file():
            continue

        # Ignore dependencies, virtual environments and generated files.
        relative_parts = file_path.relative_to(project_path).parts
        ignored = {
            "node_modules",
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            "dist",
            "build",
        }

        if any(part in ignored for part in relative_parts):
            continue

        suffix = file_path.suffix.lower()

        if suffix not in PYTHON_SUFFIXES | JAVASCRIPT_SUFFIXES:
            if file_path.name.lower() != "package.json":
                continue

        try:
            if file_path.stat().st_size > MAX_FILE_BYTES:
                results.append(
                    _result(
                        f"Source check: {file_path.name}",
                        "ERROR",
                        "File exceeds the 1 MB safe-check limit.",
                    )
                )
                continue

            source = file_path.read_text(encoding="utf-8")

            if suffix == ".py":
                ast.parse(source, filename=str(file_path))
                results.append(
                    _result(
                        f"Python syntax: {file_path.name}",
                        "PASS",
                        "Python syntax is valid. Code was not executed.",
                    )
                )

            elif suffix in JAVASCRIPT_SUFFIXES:
                if not babel_parser.is_dir():
                    results.append(
                        _result(
                            f"JavaScript syntax: {file_path.name}",
                            "ERROR",
                            "Babel parser was not found in the application's frontend node_modules.",
                        )
                    )
                    continue

                parser_script = r"""
const fs = require('fs');
const parser = require('@babel/parser');

const filename = process.argv[1];
const source = fs.readFileSync(filename, 'utf8');
const ext = filename.split('.').pop().toLowerCase();

const plugins = [];
if (ext === 'jsx') plugins.push('jsx');
if (ext === 'ts' || ext === 'tsx') plugins.push('typescript');
if (ext === 'tsx') plugins.push('jsx');

parser.parse(source, {
  sourceType: 'unambiguous',
  plugins
});

process.stdout.write('Syntax is valid');
"""

                completed = subprocess.run(
                    ["node", "-e", parser_script, str(file_path)],
                    cwd=str(frontend_dir),
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                    shell=False,
                )

                if completed.returncode == 0:
                    results.append(
                        _result(
                            f"JavaScript syntax: {file_path.name}",
                            "PASS",
                            "JavaScript/React syntax parsed successfully.",
                        )
                    )
                else:
                    details = (
                        completed.stderr
                        or completed.stdout
                        or "Parser failed."
                    )
                    results.append(
                        _result(
                            f"JavaScript syntax: {file_path.name}",
                            "FAIL",
                            details,
                        )
                    )

            elif file_path.name.lower() == "package.json":
                manifest = json.loads(source)

                if not isinstance(manifest, dict):
                    raise ValueError(
                        "package.json must contain a JSON object."
                    )

                results.append(
                    _result(
                        f"Package manifest: {file_path.name}",
                        "PASS",
                        "Valid JSON package manifest.",
                    )
                )

            files_checked += 1

        except SyntaxError as exc:
            results.append(
                _result(
                    f"Source syntax: {file_path.name}",
                    "FAIL",
                    f"Syntax error at line {exc.lineno or 'unknown'}.",
                )
            )
            files_checked += 1

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            results.append(
                _result(
                    f"Source validation: {file_path.name}",
                    "FAIL",
                    f"Invalid source or manifest: {type(exc).__name__}.",
                )
            )
            files_checked += 1

        except subprocess.TimeoutExpired:
            results.append(
                _result(
                    f"JavaScript syntax: {file_path.name}",
                    "ERROR",
                    "Syntax parsing exceeded the 10-second limit.",
                )
            )

        except OSError as exc:
            results.append(
                _result(
                    f"Source check: {file_path.name}",
                    "ERROR",
                    f"Unable to read or parse file: {type(exc).__name__}.",
                )
            )

    passed = sum(item["status"] == "PASS" for item in results)
    failed = sum(item["status"] == "FAIL" for item in results)
    errors = sum(item["status"] == "ERROR" for item in results)

    return {
        "status": "CHECKS_COMPLETED",
        "execution_mode": "STATIC_SAFE_CHECKS",
        "total_checks": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "files_checked": files_checked,
        "results": results,
        "note": (
            "Static syntax and manifest checks only. "
            "Application code was not executed, and these results do not "
            "replace runtime tests."
        ),
    }
