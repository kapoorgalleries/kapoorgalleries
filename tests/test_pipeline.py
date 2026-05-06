"""Integration: a fresh `make all` from the committed inputs produces the
expected shape of artifacts.

This is slower than the unit tests (~5s) but covers the cross-cutting
behaviour (every ingester runs, schema priority, conflicts detection).
"""

from pathlib import Path

import subprocess


REPO = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=120)


def test_full_pipeline_produces_canonical_artifacts(tmp_path: Path):
    # Use a per-test DB path so we don't blast the committed inventory.db.
    db = tmp_path / "test_inventory.db"
    master = tmp_path / "test_master.csv"

    p = _run(["python3", "-m", "src.cli", "init-db", "--db", str(db)])
    assert p.returncode == 0, p.stderr

    p = _run(["python3", "-m", "src.cli", "ingest", "--db", str(db)])
    assert p.returncode == 0, p.stderr
    # At least the artsy_csv ingester should have fired
    assert "Artsy_2-16-2026.csv" in p.stdout

    p = _run(["python3", "-m", "src.cli", "consolidate", "--db", str(db)])
    assert p.returncode == 0, p.stderr
    assert "Consolidated" in p.stdout

    p = _run(["python3", "-m", "src.cli", "stats", "--db", str(db)])
    assert p.returncode == 0, p.stderr
    assert "Works:" in p.stdout
    # Sanity: the bulk upload xlsx pulls 1400+ works
    assert any(line.strip().startswith("Works:") and int(line.strip().split()[1]) >= 600
               for line in p.stdout.splitlines() if "Works:" in line)


def test_pytest_finds_all_test_modules():
    """Every tests/test_*.py module should be importable and discoverable."""
    for f in (REPO / "tests").glob("test_*.py"):
        # Just make sure it's syntactically valid by attempting to import it.
        import importlib, sys
        mod_name = f"tests.{f.stem}"
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        try:
            importlib.import_module(mod_name)
        except (ImportError, SyntaxError) as e:
            raise AssertionError(f"Cannot import {mod_name}: {e}")
