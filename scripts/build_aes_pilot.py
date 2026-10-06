"""Build the Plan 27 pilot: a stubbed tinydb sandbox governed by AES.

The sandbox is a git repository OUTSIDE agent_ecology3 (default
``~/.local/state/agent_ecology3/pilots/tinydb``). No library code is ever
written into agent_ecology3. Steps, all reproducible:

1. Cache a bare clone of Commit0's tinydb fork (commit-0/tinydb, MIT) beside
   the sandbox, and check both pinned commits exist.
2. Shallow-fetch the stubbed ``base_commit`` into a new repository, so ``main``
   starts at exactly that commit and the reference implementation (an ancestor
   in Commit0's history) is not reachable from the sandbox.
3. Create ``.venv`` with uv (pytest, pytest-cov, pyyaml pinned).
4. ``aes init`` (governed roots tinydb/ and tests/); the pre-commit gate
   (``aes hooks install``) is installed after the plan is accepted.
5. Derive the target mechanically from ``git ls-files``: one success criterion
   per ``tests/test_<m>.py``, each with one evidence requirement and one
   verification subject whose locator is that test module; one planned
   artifact per tracked governed file. Accept it through
   ``aes plan prepare/validate/accept``.
6. Write ``pilot.json``: the command each verification subject is recorded
   with (AES has no command field on a verification subject, so the command
   lives here and is passed to ``aes evidence record --command``).

``--stub-check DIR`` does the same without restoring anything, so every
criterion must come out REFUTED (the tests really fail on the stubs).

``--reference-check DIR`` clones the built sandbox into DIR (a throwaway copy),
restores the reference implementation of tinydb/ from the cached clone,
records evidence for every verification subject, and prints ``aes status``.
The sandbox itself stays stubbed.

Usage:
    uv run python scripts/build_aes_pilot.py                 # build (refuses if it exists)
    uv run python scripts/build_aes_pilot.py --rebuild       # remove and rebuild the sandbox
    uv run python scripts/build_aes_pilot.py --status        # print aes status of the sandbox
    uv run python scripts/build_aes_pilot.py --reference-check ~/code/.scratch/ae3/pilot-reference
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

LIBRARY = "tinydb"
SOURCE_URL = "https://github.com/commit-0/tinydb"
UPSTREAM = "https://github.com/msiemens/tinydb"
LICENCE = "MIT"
BASE_COMMIT = "ed761a72c8c1e1cb24ca4dbcc089f35c5264d357"  # Commit0 stubbed bodies
REFERENCE_COMMIT = "429b27a513f0ad301632379e55667dd99865fb16"  # full implementation
PROJECT_ID = f"ae3-pilot-{LIBRARY}"
ACTOR = "agent_ecology3 agents"
OUTCOME = f"{LIBRARY} works as its own tests specify"
GOVERNED_ROOTS = ["tinydb/", "tests/"]
TEST_PACKAGES = ["pytest==9.1.1", "pytest-cov==7.1.0", "pyyaml==6.0.3"]
PILOT_MANIFEST = "pilot.json"
PROPOSAL_ID = "PLAN-001-TEST-MODULES"
# Fixed identity and dates so the sandbox commits are the same on every build.
GIT_ENV = {
    "GIT_AUTHOR_NAME": "agent_ecology3 pilot builder",
    "GIT_AUTHOR_EMAIL": "pilot-builder@agent-ecology3.invalid",
    "GIT_COMMITTER_NAME": "agent_ecology3 pilot builder",
    "GIT_COMMITTER_EMAIL": "pilot-builder@agent-ecology3.invalid",
    "GIT_AUTHOR_DATE": "2026-10-06T00:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-10-06T00:00:00+00:00",
}

STATE_ROOT = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "agent_ecology3" / "pilots"
DEFAULT_DEST = STATE_ROOT / LIBRARY
DEFAULT_CACHE = STATE_ROOT / "_sources" / f"{LIBRARY}.git"
DEFAULT_AES = Path(
    os.environ.get(
        "AE3_AES_BIN",
        str(Path.home() / "code" / "agentic-engineering-system-canonical" / ".venv" / "bin" / "aes"),
    )
)

_T0 = time.monotonic()


def log(message: str) -> None:
    print(f"[{time.monotonic() - _T0:6.1f}s] {message}", flush=True)


def run(cmd: list[str], cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full_env = {**os.environ, **GIT_ENV, **(env or {})}
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=full_env, check=False)
    if check and proc.returncode != 0:
        raise SystemExit(
            f"command failed (exit {proc.returncode}): {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}"
        )
    return proc


def module_name(test_path: str) -> str:
    """tests/test_tables.py -> tables."""
    return Path(test_path).stem.removeprefix("test_")


def test_command(test_path: str) -> list[str]:
    """Exact command a verification subject is recorded with (cwd = sandbox root)."""
    return [
        ".venv/bin/python", "-m", "pytest", "-p", "no:cacheprovider",
        "-o", "addopts=", "-q", test_path,
    ]


def ensure_cache(cache: Path) -> None:
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        log(f"cloning {SOURCE_URL} into {cache}")
        run(["git", "clone", "--bare", "--quiet", SOURCE_URL, str(cache)])
    for sha in (BASE_COMMIT, REFERENCE_COMMIT):
        if run(["git", "--git-dir", str(cache), "cat-file", "-e", f"{sha}^{{commit}}"], check=False).returncode:
            log(f"fetching missing {sha[:8]} into cache")
            run(["git", "--git-dir", str(cache), "fetch", "--quiet", "origin", sha])
    # Allow a shallow fetch of a pinned commit by id from this local cache.
    run(["git", "--git-dir", str(cache), "config", "uploadpack.allowAnySHA1InWant", "true"])


def build_proposal(dest: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive the AES proposal and pilot manifest from the tracked governed files."""
    files = run(["git", "ls-files", *GOVERNED_ROOTS], cwd=dest).stdout.split()
    tests = sorted(f for f in files if f.startswith("tests/test_") and f.endswith(".py"))
    if not tests:
        raise SystemExit("no tests/test_*.py modules found")
    normative, criteria, subjects, components = [], [], [], []
    manifest_subjects = []
    sc_for_test: dict[str, str] = {}
    for path in tests:
        key = module_name(path).upper()
        ni, sc, er, vs = f"NI-{key}", f"SC-{key}", f"ER-{key}-01", f"VS-{key}"
        sc_for_test[path] = sc
        normative.append({
            "id": ni, "kind": "behavior", "outcome_refs": ["OUT-001"],
            "statement": f"{LIBRARY} behaves as {path} specifies.",
        })
        criteria.append({
            "id": sc, "statement": f"Every test in {path} passes.", "target_refs": [ni],
            "disproof": f"Any test in {path} fails or errors.",
            "evidence_requirements": [{
                "id": er, "kind": "deterministic_test",
                "requirement": f"{path} runs to exit 0 at the recorded commit.",
            }],
        })
        subjects.append({
            "id": vs, "criterion_refs": [sc], "evidence_requirement_refs": [er],
            "proof_kind": "deterministic_test", "proof_role": "direct", "locator": path,
            "purpose": f"run {path}",
        })
        manifest_subjects.append({
            "verification_subject": vs, "criterion": sc, "test_module": path,
            "command": test_command(path),
        })
    all_ni = [n["id"] for n in normative]
    all_sc = [c["id"] for c in criteria]
    artifacts = []
    source_ids, support_test_ids = [], []
    for path in files:
        art_id = "ART-" + re.sub(r"[^A-Za-z0-9]+", "-", path).strip("-").upper()
        if path.startswith("tests/"):
            refs = [sc_for_test[path]] if path in sc_for_test else all_sc
            kind = "test"
            if path not in sc_for_test:
                support_test_ids.append(art_id)
        else:
            refs = all_ni
            kind = "source" if path.endswith(".py") else "configuration"
            source_ids.append(art_id)
        artifacts.append({
            "id": art_id, "locator": {"exact_path": path}, "kind": kind,
            "purpose": f"{LIBRARY} file {path} (tracked at base commit)",
            "semantic_justification_refs": refs,
        })
    components.append({
        "id": "CMP-LIBRARY", "responsibility": f"the {LIBRARY} package source",
        "target_refs": all_ni, "planned_artifact_refs": source_ids,
    })
    components.append({
        "id": "CMP-TEST-SUPPORT", "responsibility": "shared test fixtures and package marker",
        "target_refs": all_sc, "planned_artifact_refs": support_test_ids,
    })
    for path in tests:
        key = module_name(path).upper()
        components.append({
            "id": f"CMP-{key}", "responsibility": f"the behaviour {path} specifies",
            "target_refs": [f"NI-{key}"],
            "planned_artifact_refs": [a["id"] for a in artifacts if a["locator"]["exact_path"] == path],
        })
    proposal = {
        "schema_version": "aes.v0_2.proposal.probe0",
        "proposal_id": PROPOSAL_ID,
        "title": f"One success criterion per {LIBRARY} test module",
        "rationale": (
            "Mechanically derived by agent_ecology3 scripts/build_aes_pilot.py: each "
            "tests/test_<module>.py is one criterion with one verification subject that runs "
            "exactly that module; every tracked governed file is a planned artifact."
        ),
        "closes_gaps": [],
        "target_delta": {"add": {
            "normative_items": normative, "success_criteria": criteria,
            "components": components, "planned_artifacts": artifacts,
            "verification_subjects": subjects,
        }},
    }
    manifest = {
        "schema_version": "ae3-pilot/v1",
        "library": LIBRARY, "licence": LICENCE, "source": SOURCE_URL, "upstream": UPSTREAM,
        "base_commit": BASE_COMMIT, "reference_commit": REFERENCE_COMMIT,
        "project_id": PROJECT_ID, "governed_roots": GOVERNED_ROOTS,
        "subjects": manifest_subjects,
    }
    return proposal, manifest


def make_venv(dest: Path) -> None:
    log("creating .venv with uv")
    run(["uv", "venv", "--quiet", ".venv"], cwd=dest)
    run(["uv", "pip", "install", "--quiet", "--python", ".venv/bin/python", *TEST_PACKAGES], cwd=dest)


def build(dest: Path, cache: Path, aes: Path) -> None:
    ensure_cache(cache)
    dest.mkdir(parents=True)
    log(f"shallow-fetching base {BASE_COMMIT[:8]} into {dest}")
    run(["git", "init", "--quiet", "-b", "main"], cwd=dest)
    run(["git", "fetch", "--quiet", "--depth", "1", f"file://{cache}", BASE_COMMIT], cwd=dest)
    run(["git", "checkout", "--quiet", "-B", "main", BASE_COMMIT], cwd=dest)
    if run(["git", "cat-file", "-e", f"{REFERENCE_COMMIT}^{{commit}}"], cwd=dest, check=False).returncode == 0:
        raise SystemExit("reference commit is reachable in the sandbox; refusing")
    exclude = dest / ".git" / "info" / "exclude"
    exclude.write_text(exclude.read_text() + "\n.venv/\n.coverage\n", encoding="utf-8")
    make_venv(dest)

    log("aes init")
    init = [str(aes), "init", "--project-id", PROJECT_ID, "--actor", ACTOR, "--outcome", OUTCOME]
    for root in GOVERNED_ROOTS:
        init += ["--governed-root", root]
    run(init, cwd=dest)
    run(["git", "add", ".aes"], cwd=dest)
    run(["git", "commit", "--quiet", "-m", f"Initialize AES ({PROJECT_ID})"], cwd=dest)

    proposal, manifest = build_proposal(dest)
    (dest / PILOT_MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    run(["git", "add", PILOT_MANIFEST], cwd=dest)
    run(["git", "commit", "--quiet", "-m", "Pilot manifest: test command per verification subject"], cwd=dest)

    log("aes plan prepare / validate / accept")
    run([str(aes), "plan", "prepare"], cwd=dest)
    proposal_path = dest / ".git" / f"{PROPOSAL_ID}.json"  # outside the work tree
    proposal_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    print(run([str(aes), "plan", "validate", str(proposal_path)], cwd=dest).stdout.strip())
    print(run([str(aes), "plan", "accept", str(proposal_path)], cwd=dest).stdout.strip())
    run(["git", "add", ".aes"], cwd=dest)
    run(["git", "commit", "--quiet", "-m", f"Plan {PROPOSAL_ID}"], cwd=dest)
    # The pre-commit gate goes in only now: before the plan, every existing
    # library file is an orphan and the gate would refuse the init commit.
    log("aes hooks install")
    run([str(aes), "hooks", "install"], cwd=dest)
    run(["git", "add", ".githooks"], cwd=dest)
    run(["git", "commit", "--quiet", "-m", "Install the AES pre-commit gate"], cwd=dest)
    head = run(["git", "rev-parse", "HEAD"], cwd=dest).stdout.strip()
    log(f"built {dest} at {head}")


def status(dest: Path, aes: Path) -> int:
    proc = run([str(aes), "status"], cwd=dest, check=False)
    print(proc.stdout.rstrip())
    if proc.stderr.strip():
        print(proc.stderr.rstrip(), file=sys.stderr)
    return proc.returncode


def evidence_check(dest: Path, copy: Path, cache: Path, aes: Path, restore_reference: bool) -> int:
    """Record every subject in a throwaway copy of the sandbox.

    With ``restore_reference`` the copy first gets tinydb/ from the reference
    commit (the oracle must say yes); without it the stubs are recorded as they
    are (the oracle must say no: every criterion REFUTED).
    """
    if copy.exists():
        raise SystemExit(f"{copy} exists; choose a new directory")
    ensure_cache(cache)
    log(f"cloning sandbox into throwaway copy {copy}")
    run(["git", "clone", "--quiet", "--no-local", f"file://{dest}", str(copy)])
    if restore_reference:
        archive = subprocess.run(
            ["git", "--git-dir", str(cache), "archive", REFERENCE_COMMIT, "tinydb"],
            capture_output=True, check=True,
        ).stdout
        subprocess.run(["tar", "-x", "-C", str(copy)], input=archive, check=True)
        run(["git", "add", "tinydb"], cwd=copy)
        run(["git", "commit", "--quiet", "-m", f"Reference check: restore tinydb/ from {REFERENCE_COMMIT[:8]}"], cwd=copy)
    make_venv(copy)
    manifest = json.loads((copy / PILOT_MANIFEST).read_text(encoding="utf-8"))
    for subject in manifest["subjects"]:
        proc = run(
            [str(aes), "evidence", "record", subject["verification_subject"],
             "--depends-on", "tests/conftest.py", "--command", *subject["command"]],
            cwd=copy, check=False,
        )
        log(f"recorded {subject['verification_subject']}: exit {proc.returncode} {proc.stdout.strip().splitlines()[-1:]}")
        if proc.returncode:
            print(proc.stderr, file=sys.stderr)
    run(["git", "add", ".aes"], cwd=copy)
    run(["git", "commit", "--quiet", "-m", "Evidence check: observations"], cwd=copy)
    return status(copy, aes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="sandbox path (outside agent_ecology3)")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="bare clone of the Commit0 fork")
    parser.add_argument("--aes", type=Path, default=DEFAULT_AES, help="aes executable (env AE3_AES_BIN)")
    parser.add_argument("--rebuild", action="store_true", help="remove an existing pilot sandbox first")
    parser.add_argument("--status", action="store_true", help="only print aes status of the sandbox")
    parser.add_argument("--reference-check", type=Path, metavar="DIR", help="throwaway copy: restore the reference, record every subject")
    parser.add_argument("--stub-check", type=Path, metavar="DIR", help="throwaway copy: record every subject on the stubs")
    args = parser.parse_args()
    dest = args.dest.expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[1]
    if dest == repo_root or repo_root in dest.parents:
        raise SystemExit(f"refusing: sandbox {dest} is inside agent_ecology3")
    if not args.aes.exists():
        raise SystemExit(f"aes not found at {args.aes}; set --aes or AE3_AES_BIN")
    if args.status:
        return status(dest, args.aes)
    if args.reference_check or args.stub_check:
        copy = (args.reference_check or args.stub_check).expanduser().resolve()
        return evidence_check(dest, copy, args.cache, args.aes, restore_reference=bool(args.reference_check))
    if dest.exists():
        if not args.rebuild:
            raise SystemExit(f"{dest} exists; pass --rebuild to replace it")
        manifest = dest / PILOT_MANIFEST
        if not manifest.exists() or json.loads(manifest.read_text())["project_id"] != PROJECT_ID:
            raise SystemExit(f"refusing to remove {dest}: it is not a {PROJECT_ID} sandbox")
        log(f"removing existing sandbox {dest}")
        shutil.rmtree(dest)
    build(dest, args.cache, args.aes)
    return status(dest, args.aes)


if __name__ == "__main__":
    sys.exit(main())
