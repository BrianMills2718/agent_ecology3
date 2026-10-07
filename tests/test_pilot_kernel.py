"""Plan 27 M2: propose_change / integrate / judge / pay with scripted agents (no model calls).

The integration tests drive the real ``aes`` CLI and real git on a tiny
fixture project built the same way as the M1 pilot (``aes init`` plus the
builder's own ``build_proposal``): a package ``tinydb`` with two stubbed
functions and one test module each. A scripted agent is a test that writes
files into the agent's worktree and calls the kernel's ``propose_change``.
The pay rule is also unit-tested on recorded ``aes reconcile --json`` output.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from agent_ecology3.config import AppConfig
from agent_ecology3.simulation.pilot import (
    DEFAULT_AES_BIN,
    PilotProject,
    bounty_decisions,
    split_bounty,
    standings,
)
from agent_ecology3.simulation.resident import ResidentKernel
from agent_ecology3.world import World
from scripts import build_aes_pilot as builder

FIXTURES = Path(__file__).resolve().parent / "fixtures"
needs_aes = pytest.mark.skipif(not DEFAULT_AES_BIN.exists(), reason=f"aes CLI not installed at {DEFAULT_AES_BIN}")

STUB_UTILS = '''"""Small helpers."""


def double(x):
    """Return twice x."""
    pass


def pop(d, key):
    """Remove key from d and return its value."""
    pass
'''
STUB_CORE = '''"""Core."""
from tinydb.utils import double


def quad(x):
    """Return four times x."""
    pass
'''
TEST_UTILS = "from tinydb.utils import double\n\n\ndef test_double():\n    assert double(2) == 4\n    assert double(5) == 10\n"
TEST_CORE = "from tinydb.core import quad\n\n\ndef test_quad():\n    assert quad(3) == 12\n"


def _run(cmd: list[str], cwd: Path) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
           "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, check=False)
    assert proc.returncode == 0, f"{' '.join(cmd)}: {proc.stdout}\n{proc.stderr}"
    return proc.stdout


def build_fixture_pilot(dest: Path) -> Path:
    """A two-criterion AES pilot: tinydb/utils.py double(), tinydb/core.py quad()."""
    aes = str(DEFAULT_AES_BIN)
    git = ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false"]
    (dest / "tinydb").mkdir(parents=True)
    (dest / "tests").mkdir()
    (dest / "tinydb" / "__init__.py").write_text("")
    (dest / "tinydb" / "utils.py").write_text(STUB_UTILS)
    (dest / "tinydb" / "core.py").write_text(STUB_CORE)
    (dest / "tests" / "__init__.py").write_text("")
    (dest / "tests" / "conftest.py").write_text("")
    (dest / "tests" / "test_utils.py").write_text(TEST_UTILS)
    (dest / "tests" / "test_core.py").write_text(TEST_CORE)
    (dest / ".gitignore").write_text("__pycache__\n.venv\n")
    _run([*git, "init", "--quiet", "-b", "main"], dest)
    _run([*git, "add", "."], dest)
    _run([*git, "commit", "--quiet", "-m", "stubs"], dest)
    # The shared test environment: this interpreter's venv (it has pytest).
    (dest / ".venv").symlink_to(Path(sys.prefix))
    _run([aes, "init", "--project-id", "ae3-fixture", "--actor", "test agents", "--outcome", "fixture works",
          "--governed-root", "tinydb/", "--governed-root", "tests/"], dest)
    _run([*git, "add", ".aes"], dest)
    _run([*git, "commit", "--quiet", "-m", "aes init"], dest)
    proposal, manifest = builder.build_proposal(dest)
    (dest / "pilot.json").write_text(json.dumps(manifest, indent=2) + "\n")
    _run([*git, "add", "pilot.json"], dest)
    _run([*git, "commit", "--quiet", "-m", "manifest"], dest)
    _run([aes, "plan", "prepare"], dest)
    proposal_path = dest / ".git" / "proposal.json"
    proposal_path.write_text(json.dumps(proposal))
    _run([aes, "plan", "validate", str(proposal_path)], dest)
    _run([aes, "plan", "accept", str(proposal_path)], dest)
    _run([*git, "add", ".aes"], dest)
    _run([*git, "commit", "--quiet", "-m", "plan"], dest)
    assert manifest["subjects"][0]["command"] == builder.test_command("tests/test_core.py")
    return dest


@pytest.fixture(scope="module")
def fixture_pilot(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if not DEFAULT_AES_BIN.exists():
        pytest.skip(f"aes CLI not installed at {DEFAULT_AES_BIN}")
    return build_fixture_pilot(tmp_path_factory.mktemp("pilot") / "tinydb")


# --- pay rule on recorded `aes reconcile --json` output (no CLI) ----------

def _recorded(name: str) -> dict[str, str]:
    return standings(json.loads((FIXTURES / "aes_pilot" / name).read_text()))


def test_pay_rule_on_recorded_reconcile() -> None:
    """SUPPORTED pays once; REFUTED, INSUFFICIENT and stale evidence pay nothing; regain pays again."""
    stubs = _recorded("reconcile_stubs.json")              # 7 INSUFFICIENT (no evidence yet)
    refuted = _recorded("reconcile_stubs_recorded.json")   # 7 REFUTED (stubs recorded)
    met = _recorded("reconcile_reference_recorded.json")   # 7 SUPPORTED (reference recorded)
    stale = _recorded("reconcile_reference_stale.json")    # reference evidence gone STALE -> INSUFFICIENT
    assert set(stubs.values()) == {"INSUFFICIENT"} and set(refuted.values()) == {"REFUTED"}
    assert set(met.values()) == {"SUPPORTED"} and set(stale.values()) == {"INSUFFICIENT"}
    held: set[str] = set()
    ever: set[str] = set()
    assert bounty_decisions(stubs, held, ever) == ([], [])
    assert bounty_decisions(refuted, held, ever) == ([], [])
    pay, released = bounty_decisions(met, held, ever)
    assert pay == [(c, False) for c in sorted(met)] and released == []
    held |= {c for c, _ in pay}
    ever |= held
    assert bounty_decisions(met, held, ever) == ([], [])          # still supported: no second payment
    pay, released = bounty_decisions(stale, held, ever)
    assert pay == [] and released == sorted(met)                   # stale evidence: released, unpaid
    held -= set(released)
    pay, _ = bounty_decisions(met, held, ever)
    assert pay == [(c, True) for c in sorted(met)]                 # lost and regained: pays again


def test_split_bounty_is_exact() -> None:
    assert split_bounty(30, ["alpha_2", "alpha_1"]) == {"alpha_2": 15, "alpha_1": 15}
    assert split_bounty(30, ["a", "b", "c", "d"]) == {"a": 8, "b": 8, "c": 7, "d": 7}
    assert sum(split_bounty(31, ["a", "b", "c"]).values()) == 31
    assert split_bounty(30, []) == {}


# --- scripted agents through the kernel, real git and real aes ------------

def _setup(pilot_src: Path, tmp_path: Path) -> tuple[World, ResidentKernel]:
    cfg = AppConfig()
    cfg.principals.count = 2
    cfg.llm.enable_bootstrap_loop_llm = False
    cfg.dashboard.enabled = False
    cfg.logging.logs_dir = str(tmp_path / "logs")
    cfg.mint.enabled = False
    world = World(AppConfig.model_validate(cfg.model_dump()), run_id="pilot_test")
    run = tmp_path / "run"
    pilot = PilotProject.create(
        pilot_src, run / "pilot_project", {pid: run / "agents" / pid / "work" for pid in world.principal_ids},
        bounty_scrip=30, royalty_scrip=world.config.mint.royalty_scrip,
    )
    kernel = ResidentKernel(world, run / "agents", actions_per_turn=4, pilot=pilot)
    kernel.turn = 1
    return world, kernel


def _edit(kernel: ResidentKernel, agent: str, path: str, old: str, new: str) -> None:
    file = kernel.agents[agent].workdir / "work" / path
    text = file.read_text()
    assert old in text, f"{old!r} not in {path}"
    file.write_text(text.replace(old, new, 1))


def _propose(kernel: ResidentKernel, agent: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """One scripted propose_change; returns the outcome and the events it logged."""
    before = len(kernel.world.logger.read_recent(100_000))
    kernel.agents[agent].actions_this_turn = 0
    outcome = asyncio.run(kernel.act(kernel.agents[agent], {"action_type": "propose_change", "content": "scripted"}))
    return outcome, kernel.world.logger.read_recent(100_000)[before:]


def _of(events: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [e for e in events if e.get("event_type") == kind]


def _standing(events: list[dict[str, Any]]) -> dict[str, tuple[str, str]]:
    (judged,) = _of(events, "aes_judged")
    return {row["criterion_id"]: (row["before"], row["after"]) for row in judged["standings"]}


IMPLEMENT_DOUBLE = ("    pass\n", "    return x * 2\n")
IMPLEMENT_QUAD = ("    pass\n", "    return double(double(x))\n")


@needs_aes
def test_pays_contributor_on_supported_and_nothing_on_refuted(fixture_pilot: Path, tmp_path: Path) -> None:
    world, kernel = _setup(fixture_pilot, tmp_path)
    _edit(kernel, "alpha_1", "tinydb/utils.py", *IMPLEMENT_DOUBLE)
    outcome, events = _propose(kernel, "alpha_1")
    assert outcome["success"] is True, outcome
    assert [e["event_type"] for e in events][:2] == ["change_submitted", "change_integrated"]
    (integrated,) = _of(events, "change_integrated")
    assert integrated["files"] == ["tinydb/utils.py"] and integrated["principal_id"] == "alpha_1"
    assert _standing(events) == {"SC-UTILS": ("INSUFFICIENT", "SUPPORTED"), "SC-CORE": ("INSUFFICIENT", "REFUTED")}
    # The standings are AES's own: an independent reconcile of the run copy agrees.
    assert standings(kernel.pilot.reconcile()) == {"SC-UTILS": "SUPPORTED", "SC-CORE": "REFUTED"}
    paid = [(e["principal_id"], e["criterion_id"], e["share"]) for e in _of(events, "bounty_paid")]
    assert paid == [("alpha_1", "SC-UTILS", 30)]                    # nothing for REFUTED SC-CORE
    assert _of(events, "bounty_paid")[0]["commit"] == integrated["commit"]
    assert world.ledger.get_scrip("alpha_1") == 130 and world.ledger.get_scrip("alpha_2") == 100
    assert [e["action_type"] for e in _of(events, "resident_action")] == ["propose_change"]


@needs_aes
def test_royalty_on_cross_author_call_and_split_bounty(fixture_pilot: Path, tmp_path: Path) -> None:
    world, kernel = _setup(fixture_pilot, tmp_path)
    _edit(kernel, "alpha_1", "tinydb/utils.py", *IMPLEMENT_DOUBLE)
    _edit(kernel, "alpha_1", "tinydb/utils.py", "value.\"\"\"\n    pass\n", "value.\"\"\"\n    return d.pop(key)\n")
    _propose(kernel, "alpha_1")
    # alpha_2's folder is behind main; its proposal merges main in first. Its
    # change also calls a dict method named like alpha_1's utils.pop and a
    # builtin: neither is an imported library function, so neither pays.
    _edit(kernel, "alpha_2", "tinydb/core.py", "    pass\n",
          "    cache = {}\n    cache.pop('k', None)\n    assert any([True])\n    return double(double(x))\n")
    outcome, events = _propose(kernel, "alpha_2")
    assert outcome["success"] is True, outcome
    royalties = [(e["principal_id"], e["solver"], e["function"], e["amount"], e["source"]) for e in _of(events, "royalty_paid")]
    assert royalties == [("alpha_1", "alpha_2", "double", 3, "pilot_function_call")]
    assert _standing(events)["SC-CORE"] == ("REFUTED", "SUPPORTED")
    paid = sorted((e["principal_id"], e["criterion_id"], e["share"]) for e in _of(events, "bounty_paid"))
    # SC-CORE's observation depends on core.py (alpha_2) and utils.py (alpha_1): equal split.
    assert paid == [("alpha_1", "SC-CORE", 15), ("alpha_2", "SC-CORE", 15)]
    assert world.ledger.get_scrip("alpha_1") == 100 + 30 + 3 + 15
    assert world.ledger.get_scrip("alpha_2") == 100 + 15
    _check_views(world)


def _check_views(world: World) -> None:
    """The feed, matrix and Living view show the shared-project events in plain words."""
    from agent_ecology3.dashboard.server import _agent_graph, _resident_action_rows
    from agent_ecology3.viz.world_substrate_view import PROJECT, build_profile, build_projection

    events = world.logger.read_recent(100_000)
    rows = [(r["principal_id"], r["action"], r["description"]) for r in _resident_action_rows(events, {})]
    texts = [d for _, _, d in rows]
    assert any(d.startswith("proposed a change (\u201cscripted\u201d): integrated into the shared project") for d in texts)
    assert any(a == "aes_judged" and "SC-UTILS: insufficient \u2192 supported" in d for _, a, d in rows)
    assert any(a == "aes_judged" and "SC-CORE: refuted \u2192 supported" in d for _, a, d in rows)
    assert ("alpha_1", "bounty_paid") in [(p, a) for p, a, _ in rows]
    assert any(p == "alpha_1" and a == "royalty" and "function double" in d for p, a, d in rows)
    state = world.get_state_summary(event_limit=10)
    graph = _agent_graph(events, state)
    edges = {e["id"]: e["label"] for e in graph["graph"]["edges"]}
    assert edges["builds_on:alpha_2->alpha_1"] == "builds on ×1"
    assert edges["co_contributed:alpha_1->alpha_2"] == "co-contributed ×1"
    assert graph["summary"]["builds_on"] == 1 and graph["summary"]["bounties_met"] == 2
    bundle = build_projection(events, run_id="t", principals=["alpha_1", "alpha_2"], task_ids=[], starting_scrip=100)
    profile = build_profile(bundle, principals=["alpha_1", "alpha_2"], task_ids=[])
    assert PROJECT in profile["entities"]
    rules = [e["rule_id"] for e in bundle["events"]]
    assert "ae3.project.integrated.alpha_2" in rules and "ae3.aes.bounty.alpha_1" in rules
    final = bundle["events"][-1]["changes"]
    assert bundle["projection_final_hash"]
    scrip = {}
    for event in bundle["events"]:
        for change in event["changes"]:
            if change["path"].endswith("member.scrip"):
                scrip[change["path"].split(".")[1]] = change["after"]
    assert scrip == {"alpha_1": 148, "alpha_2": 115} and final


@needs_aes
def test_breaking_a_supported_criterion_pays_nothing_and_regain_pays_again(fixture_pilot: Path, tmp_path: Path) -> None:
    world, kernel = _setup(fixture_pilot, tmp_path)
    _edit(kernel, "alpha_1", "tinydb/utils.py", *IMPLEMENT_DOUBLE)
    _propose(kernel, "alpha_1")
    _propose(kernel, "alpha_2")  # nothing new: only brings its folder up to date
    _edit(kernel, "alpha_2", "tinydb/utils.py", "return x * 2", "return x * 3")
    outcome, events = _propose(kernel, "alpha_2")
    assert outcome["success"] is True
    assert _standing(events)["SC-UTILS"] == ("SUPPORTED", "REFUTED")
    (judged,) = _of(events, "aes_judged")
    assert judged["released"] == ["SC-UTILS"]
    assert _of(events, "bounty_paid") == []
    assert "sc-utils: supported -> refuted" in outcome["message"].lower()
    assert world.ledger.get_scrip("alpha_2") == 100
    _edit(kernel, "alpha_2", "tinydb/utils.py", "return x * 3", "return x + x")
    outcome, events = _propose(kernel, "alpha_2")
    assert _standing(events)["SC-UTILS"] == ("REFUTED", "SUPPORTED")
    paid = [(e["principal_id"], e["share"], e["regained"]) for e in _of(events, "bounty_paid")]
    # The surviving line is alpha_2's now: the regained bounty is its alone.
    assert paid == [("alpha_2", 30, True)]


@needs_aes
def test_conflicting_change_is_rejected_then_resolved(fixture_pilot: Path, tmp_path: Path) -> None:
    world, kernel = _setup(fixture_pilot, tmp_path)
    _edit(kernel, "alpha_1", "tinydb/utils.py", *IMPLEMENT_DOUBLE)
    _edit(kernel, "alpha_2", "tinydb/utils.py", "    pass\n", "    return 2 * x\n")
    assert _propose(kernel, "alpha_1")[0]["success"] is True
    outcome, events = _propose(kernel, "alpha_2")
    assert outcome["success"] is False and outcome["error_code"] == "change_rejected"
    (rejected,) = _of(events, "change_rejected")
    assert "conflict" in rejected["reason"] and rejected["files"] == ["tinydb/utils.py"]
    assert _of(events, "change_integrated") == [] and _of(events, "aes_judged") == []
    work = kernel.agents["alpha_2"].workdir / "work" / "tinydb" / "utils.py"
    assert "<<<<<<<" in work.read_text()
    assert kernel.pilot.branch_state("alpha_2")["merging"] is True
    assert "conflict markers" in kernel.observation(kernel.agents["alpha_2"])
    from agent_ecology3.dashboard.server import _resident_action_rows
    (row,) = [r for r in _resident_action_rows(world.logger.read_recent(100_000), {})
              if r["principal_id"] == "alpha_2" and r["action"] == "propose_change"]
    assert row["description"].startswith("proposed a change (\u201cscripted\u201d): rejected \u2014 conflict with main")
    assert row["success"] is False
    outcome, _ = _propose(kernel, "alpha_2")                           # markers still there
    assert outcome["error_code"] == "change_rejected" and "conflict markers" in outcome["error"]
    work.write_text(STUB_UTILS.replace("    pass\n", "    return x * 2  # agreed\n"))
    outcome, events = _propose(kernel, "alpha_2")
    assert outcome["success"] is True, outcome
    assert "Left in your folder" not in outcome["message"]          # main's side of the merge is not "ignored"
    assert _of(events, "bounty_paid") == []                         # SC-UTILS already held


@needs_aes
def test_only_library_edits_are_proposed(fixture_pilot: Path, tmp_path: Path) -> None:
    """An agent cannot change the tests that judge it: such edits stay in its folder."""
    world, kernel = _setup(fixture_pilot, tmp_path)
    folder = kernel.agents["alpha_1"].workdir / "work"
    (folder / "tests" / "test_utils.py").write_text("def test_double():\n    assert True\n")
    (folder / "scratch.py").write_text("print('mine')\n")
    outcome, events = _propose(kernel, "alpha_1")
    assert outcome["success"] is False and "nothing to propose" in outcome["error"]
    assert "tests/test_utils.py" in outcome["error"] and "scratch.py" in outcome["error"]
    assert _of(events, "aes_judged") == []
    main_test = (kernel.pilot.root / "tests" / "test_utils.py").read_text()
    assert main_test == TEST_UTILS
    # Its Codex folder is the worktree; the Codex home stays a sibling it cannot write.
    assert folder == kernel.agents["alpha_1"].workdir / "work"
    assert (folder / ".git").is_file()
