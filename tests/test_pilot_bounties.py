"""Plan 27 M1: the dashboard's bounty board reads AES gaps correctly.

Fixtures are real ``aes reconcile --json`` output from the tinydb pilot built by
scripts/build_aes_pilot.py on 2026-10-06: ``reconcile_stubs.json`` is the fresh
sandbox (7 INSUFFICIENT); ``reconcile_stubs_recorded.json`` is a throwaway copy
after ``--stub-check`` recorded every subject on the stubs (7 REFUTED).
``pilot_manifest.json`` is that sandbox's pilot.json. No AES run happens here.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

from fastapi.testclient import TestClient

from agent_ecology3.dashboard.server import create_app, pilot_bounties

FIXTURES = Path(__file__).parent / "fixtures" / "aes_pilot"
MODULES = ["middlewares", "operations", "queries", "storages", "tables", "tinydb", "utils"]


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _reconcile_gap_ids(report: dict) -> set[str]:
    ids = {g["id"] for c in report["components"] for g in c["gaps"]}
    return ids | {g["id"] for g in report["unassigned_gaps"]}


def test_stub_board_lists_every_criterion_once_with_its_test_module() -> None:
    report, manifest = _load("reconcile_stubs.json"), _load("pilot_manifest.json")
    board = pilot_bounties(report, manifest)
    # Gaps appear under several components in the report; the board counts each once.
    assert sum(len(c["gaps"]) for c in report["components"]) > len(_reconcile_gap_ids(report))
    assert board["gap_count"] == len(_reconcile_gap_ids(report)) == 7
    assert {b["gap_id"] for b in board["bounties"]} == _reconcile_gap_ids(report)
    by_criterion = {b["criterion_id"]: b for b in board["bounties"]}
    assert set(by_criterion) == {f"SC-{m.upper()}" for m in MODULES}
    for module in MODULES:
        bounty = by_criterion[f"SC-{module.upper()}"]
        assert bounty["test_module"] == f"tests/test_{module}.py"
        assert bounty["standing"] == "INSUFFICIENT"
        assert "NO_CURRENT_SUPPORT" in bounty["why"]
        assert f"CMP-{module.upper()}" in bounty["components"]
        assert bounty["command"].endswith(f"-o addopts= -q tests/test_{module}.py")
    assert board["standing_counts"] == {"INSUFFICIENT": 7}


def test_recorded_stubs_show_refuted_with_the_refuting_observation() -> None:
    board = pilot_bounties(_load("reconcile_stubs_recorded.json"), _load("pilot_manifest.json"))
    assert board["gap_count"] == 7
    assert {b["standing"] for b in board["bounties"]} == {"REFUTED"}
    tables = next(b for b in board["bounties"] if b["criterion_id"] == "SC-TABLES")
    assert tables["why"].startswith("REFUTED: refuted by OBS-TABLES-")


def test_all_supported_report_has_no_bounties() -> None:
    report = _load("reconcile_stubs.json")
    for component in report["components"]:
        component["gaps"] = []
    for criterion in report["criteria"]:
        criterion["standing"], criterion["missing"] = "SUPPORTED", []
    board = pilot_bounties(report, None)
    assert board["gap_count"] == 0 and board["bounties"] == []
    assert board["standing_counts"] == {"SUPPORTED": 7}


def _fake_aes(tmp_path: Path, fixture: str, exit_code: int) -> Path:
    script = tmp_path / "aes"
    script.write_text(f"#!/bin/sh\ncat '{FIXTURES / fixture}'\nexit {exit_code}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_endpoint_reads_pilot_and_tolerates_reconcile_exit_1(tmp_path: Path) -> None:
    pilot = tmp_path / "pilot"
    pilot.mkdir()
    (pilot / "pilot.json").write_text((FIXTURES / "pilot_manifest.json").read_text(), encoding="utf-8")
    app = create_app(pilot_path=str(pilot), aes_bin=str(_fake_aes(tmp_path, "reconcile_stubs_recorded.json", 1)))
    payload = TestClient(app).get("/pilot-bounties").json()
    assert payload["success"] and payload["configured"] and payload["standalone"]
    assert payload["reconcile_exit"] == 1 and payload["gap_count"] == 7


def test_endpoint_reports_unparseable_reconcile_loudly(tmp_path: Path) -> None:
    script = tmp_path / "aes"
    script.write_text("#!/bin/sh\necho 'no project here' >&2\nexit 2\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    payload = TestClient(create_app(pilot_path=str(tmp_path), aes_bin=str(script))).get("/pilot-bounties").json()
    assert payload["success"] is False and "exit 2" in payload["error"] and "no project here" in payload["error"]


def test_env_var_selects_pilot_and_absent_pilot_is_reported(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AE3_PILOT_PATH", raising=False)
    payload = TestClient(create_app()).get("/pilot-bounties").json()
    assert payload == {"success": False, "configured": False, "error": "no pilot: pass --pilot PATH or set AE3_PILOT_PATH"}
    monkeypatch.setenv("AE3_PILOT_PATH", str(tmp_path))
    monkeypatch.setenv("AE3_AES_BIN", str(_fake_aes(tmp_path, "reconcile_stubs.json", 0)))
    payload = TestClient(create_app()).get("/pilot-bounties").json()
    assert payload["success"] and payload["gap_count"] == 7
    # Without pilot.json the board still lists the gaps, just without test modules.
    assert all(b["test_module"] is None for b in payload["bounties"])


def test_page_has_bounty_tab_with_styled_tooltips() -> None:
    html = TestClient(create_app()).get("/").text
    assert 'id="bountiesTab"' in html and 'id="bountyRefresh"' in html
    assert html.count('class="tab tip"') == 1
    assert ".tip[data-tip]:hover::after" in html
