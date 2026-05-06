"""kg-inv source list/enable/disable smoke tests."""

from pathlib import Path

import yaml
from click.testing import CliRunner

from src.cli import cli


def _write_sources(p: Path) -> None:
    p.write_text(yaml.safe_dump([
        {"name": "Test source A", "type": "artsy_csv", "enabled": True,
         "local_path": "data/raw/nonexistent.csv"},
        {"name": "Test source B", "type": "match_workbook", "enabled": False,
         "local_path": "data/raw/nonexistent.xlsx"},
    ], sort_keys=False))


def test_source_list_renders(tmp_path: Path):
    p = tmp_path / "sources.yaml"
    _write_sources(p)
    runner = CliRunner()
    result = runner.invoke(cli, ["source", "list", "--sources", str(p)])
    assert result.exit_code == 0, result.output
    assert "Test source A" in result.output
    assert "Test source B" in result.output


def test_source_disable_flips_enabled(tmp_path: Path):
    p = tmp_path / "sources.yaml"
    _write_sources(p)
    runner = CliRunner()
    result = runner.invoke(cli, ["source", "disable", "Test source A",
                                  "--sources", str(p)])
    assert result.exit_code == 0, result.output
    entries = yaml.safe_load(p.read_text())
    assert entries[0]["enabled"] is False


def test_source_enable_flips_back(tmp_path: Path):
    p = tmp_path / "sources.yaml"
    _write_sources(p)
    runner = CliRunner()
    result = runner.invoke(cli, ["source", "enable", "Test source B",
                                  "--sources", str(p)])
    assert result.exit_code == 0, result.output
    entries = yaml.safe_load(p.read_text())
    assert entries[1]["enabled"] is True


def test_source_substring_match_works(tmp_path: Path):
    p = tmp_path / "sources.yaml"
    _write_sources(p)
    runner = CliRunner()
    # 'source A' should match exactly one entry by substring.
    result = runner.invoke(cli, ["source", "disable", "source A",
                                  "--sources", str(p)])
    assert result.exit_code == 0, result.output
    entries = yaml.safe_load(p.read_text())
    assert entries[0]["enabled"] is False
