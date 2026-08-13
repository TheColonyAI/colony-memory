"""The two places that state the version must agree.

`pyproject.toml` decides what PyPI receives; `colony_memory/_version.py` decides
what `colony_memory.__version__` reports at runtime. Nothing links them, so a
release that bumps one and not the other publishes a wheel whose own
`__version__` lies about which wheel it is. That has happened before in a
sibling package (`colony-chat-hermes` shipped 0.3.1 reporting 0.2.2), and it is
invisible: every test passes, the upload succeeds, and the mismatch only
surfaces when someone reports a bug against the wrong version.

0.1.2 is a metadata-only release, which is exactly the kind most likely to bump
one file and forget the other.
"""

from __future__ import annotations

import pathlib
import re

try:
    import tomllib  # 3.11+
except ImportError:  # 3.10, the floor declared in requires-python
    tomllib = None  # type: ignore[assignment]

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    raw = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if tomllib is not None:
        return tomllib.loads(raw)["project"]["version"]
    m = re.search(r'^version = "([^"]+)"', raw, re.M)
    assert m, "no version line in pyproject.toml"
    return m.group(1)


def test_declared_versions_agree() -> None:
    from colony_memory import __version__

    assert __version__ == _pyproject_version(), (
        f"colony_memory.__version__ is {__version__} but pyproject.toml says "
        f"{_pyproject_version()} — the wheel would misreport itself"
    )


def test_the_version_is_actually_readable() -> None:
    """Guards the check above: if the parse silently returned None on both
    sides, they would be 'equal' and this file would certify nothing."""
    v = _pyproject_version()
    assert re.fullmatch(r"\d+\.\d+\.\d+", v), f"unparsed version {v!r}"
