from __future__ import annotations

from pathlib import Path


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def _pinned_requirements() -> dict[str, str]:
    requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
    pins: dict[str, str] = {}
    for line in requirements.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        name, version = line.split("==", 1)
        pins[name.split("[", 1)[0].lower()] = version
    return pins


def test_python_dependency_advisory_floor_versions() -> None:
    pins = _pinned_requirements()

    assert _version_tuple(pins["fastapi"]) >= (0, 136, 3)
    assert _version_tuple(pins["starlette"]) >= (1, 0, 1)
    assert _version_tuple(pins["pytest"]) >= (9, 0, 3)
