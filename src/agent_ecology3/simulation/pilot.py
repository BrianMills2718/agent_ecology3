"""Plan 27 M2: one shared, AES-governed project that resident agents build together.

A run gets its own copy of the pilot sandbox (``git clone`` of the M1 pilot
built by ``scripts/build_aes_pilot.py``); the shared pilot is never touched.
Each agent works in a git worktree of that copy, on its own branch
``agent/<id>``, which is also its writable Codex folder.

``propose_change`` runs four kernel steps, all git and the ``aes`` CLI as
subprocesses:

- **integrate**: commit the agent's edits to tracked library files (authored
  as the agent), merge ``main`` into its branch, and fast-forward ``main`` to
  it. A merge conflict leaves the conflict markers in the agent's folder and
  rejects the change; so does a change to anything but existing library files.
- **judge**: ``aes evidence record`` for every verification subject at the new
  commit (the pilot's committed ``pilot.json`` gives each subject's command),
  commit the observations, then ``aes reconcile --json``.
- **pay**: a criterion that is SUPPORTED now and was not held before pays its
  bounty, split equally among the agents who authored surviving lines (git
  blame at the judged commit) in the files that criterion's observation
  depends on (the observation's own ``dependency_paths``). A criterion that
  stops being SUPPORTED stops being held; regaining it pays again
  (``regained`` is true on that payment).
- **royalty**: each module-level library function the change's added lines
  call or import (resolved through the file's imports) whose current body was
  mostly written by another agent (git blame on the body lines) pays that
  author once per (change, author, function).

Nothing here decides what counts as met: only AES's reconcile standings do.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PILOT_MANIFEST = "pilot.json"
AGENT_EMAIL_DOMAIN = "agents.agent-ecology3.invalid"
KERNEL_NAME = "agent_ecology3 kernel"
KERNEL_EMAIL = "kernel@agent-ecology3.invalid"
DEFAULT_AES_BIN = Path(
    os.environ.get(
        "AE3_AES_BIN",
        str(Path.home() / "code" / "agentic-engineering-system-canonical" / ".venv" / "bin" / "aes"),
    )
)
SUPPORTED = "SUPPORTED"
# Never committed: the shared test environment and Python's own caches.
EXCLUDED = (".venv", "__pycache__/", "*.pyc", ".coverage", ".pytest_cache/")
CONFLICT_MARKER = re.compile(r"^(<{7} |>{7} |={7}$)", re.MULTILINE)
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)


class PilotError(RuntimeError):
    """git or aes failed in a way the run cannot continue past (fail loud)."""


def _git_env(name: str, email: str) -> dict[str, str]:
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
    }


def git(cwd: Path, *args: str, author: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run git with no user hooks and no signing; ``author`` is an agent id or None (kernel)."""
    env = _git_env(author, f"{author}@{AGENT_EMAIL_DOMAIN}") if author else _git_env(KERNEL_NAME, KERNEL_EMAIL)
    proc = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *args],
        cwd=cwd, capture_output=True, text=True, env=env, check=False,
    )
    if check and proc.returncode != 0:
        raise PilotError(f"git {' '.join(args)} failed in {cwd} (exit {proc.returncode}): {(proc.stderr or proc.stdout).strip()[-600:]}")
    return proc


# --- pay rule (pure; unit-tested on recorded reconcile output) -------------

def standings(reconcile: dict[str, Any]) -> dict[str, str]:
    """criterion id -> AES standing, from ``aes reconcile --json``."""
    return {str(c["criterion_id"]): str(c["standing"]) for c in reconcile.get("criteria", [])}


def bounty_decisions(
    after: dict[str, str], held: set[str], ever_paid: set[str]
) -> tuple[list[tuple[str, bool]], list[str]]:
    """Which criteria pay now, and which stop being held.

    Pays (criterion, regained) for each criterion SUPPORTED now and not held;
    ``regained`` is true when it was paid before, lost, and is SUPPORTED again.
    A held criterion that is anything but SUPPORTED now (REFUTED, INSUFFICIENT,
    or supported only by STALE evidence) is released and pays nothing.
    """
    pay = [(c, c in ever_paid) for c, s in sorted(after.items()) if s == SUPPORTED and c not in held]
    released = sorted(c for c in held if after.get(c) != SUPPORTED)
    return pay, released


def split_bounty(amount: int, contributors: list[str]) -> dict[str, int]:
    """Equal whole-scrip shares; the remainder goes one each in the given order."""
    if not contributors or amount <= 0:
        return {}
    base, rest = divmod(amount, len(contributors))
    return {agent: base + (1 if i < rest else 0) for i, agent in enumerate(contributors)}


# --- the project ----------------------------------------------------------

@dataclass
class Integration:
    turn: int
    agent: str
    commit: str
    files: list[str]


@dataclass
class AgentBranch:
    agent: str
    path: Path
    last_rejection: str | None = None
    last_seen_integration: int = 0


@dataclass
class PilotProject:
    """A run's own copy of the pilot, with one worktree per agent."""

    root: Path
    manifest: dict[str, Any]
    aes_bin: Path
    agents: list[str]
    bounty_scrip: int = 30
    royalty_scrip: int = 3
    # A test run that hangs (an agent's infinite loop) is killed and recorded as a failure.
    test_timeout_seconds: int = 120
    branches: dict[str, AgentBranch] = field(default_factory=dict)
    base_commit: str = ""
    last_reconcile: dict[str, Any] = field(default_factory=dict)
    held: set[str] = field(default_factory=set)
    ever_paid: set[str] = field(default_factory=set)
    integrations: list[Integration] = field(default_factory=list)
    judge_seconds: list[float] = field(default_factory=list)

    # -- setup --
    @classmethod
    def create(
        cls, sandbox: Path, run_copy: Path, agent_dirs: dict[str, Path], *,
        aes_bin: Path = DEFAULT_AES_BIN, bounty_scrip: int = 30, royalty_scrip: int = 3,
    ) -> PilotProject:
        """Clone ``sandbox`` into ``run_copy`` and add a worktree per agent at ``agent_dirs[id]``."""
        sandbox = sandbox.expanduser().resolve()
        if not (sandbox / PILOT_MANIFEST).is_file():
            raise PilotError(f"{sandbox} has no {PILOT_MANIFEST}; build it with scripts/build_aes_pilot.py")
        if run_copy.exists():
            raise PilotError(f"{run_copy} exists; a run copy is made fresh")
        if not aes_bin.exists():
            raise PilotError(f"aes not found at {aes_bin} (set AE3_AES_BIN)")
        run_copy.parent.mkdir(parents=True, exist_ok=True)
        git(run_copy.parent, "clone", "--quiet", "--no-local", f"file://{sandbox}", str(run_copy))
        exclude = run_copy / ".git" / "info" / "exclude"
        exclude.write_text(exclude.read_text(encoding="utf-8") + "\n" + "\n".join(EXCLUDED) + "\n", encoding="utf-8")
        venv = (sandbox / ".venv").resolve()
        project = cls(
            root=run_copy, manifest=json.loads((run_copy / PILOT_MANIFEST).read_text(encoding="utf-8")),
            aes_bin=aes_bin, agents=list(agent_dirs), bounty_scrip=bounty_scrip, royalty_scrip=royalty_scrip,
        )
        if venv.is_dir():
            (run_copy / ".venv").symlink_to(venv)
        project.base_commit = project.head()
        for agent, path in agent_dirs.items():
            if path.exists() and any(path.iterdir()):
                raise PilotError(f"agent folder {path} is not empty")
            if path.exists():
                path.rmdir()
            path.parent.mkdir(parents=True, exist_ok=True)
            git(run_copy, "worktree", "add", "--quiet", "-b", f"agent/{agent}", str(path), "main")
            if venv.is_dir():
                (path / ".venv").symlink_to(venv)
            project.branches[agent] = AgentBranch(agent=agent, path=path)
        project.last_reconcile = project.reconcile()
        return project

    @property
    def library_roots(self) -> list[str]:
        """Governed roots agents may change: every governed root except tests/."""
        return [r for r in self.manifest.get("governed_roots", []) if not r.startswith("tests")]

    def head(self, ref: str = "HEAD", cwd: Path | None = None) -> str:
        return git(cwd or self.root, "rev-parse", ref).stdout.strip()

    def reconcile(self) -> dict[str, Any]:
        """``aes reconcile --json``; it exits 1 on a REFUTED criterion but still prints the report."""
        proc = subprocess.run([str(self.aes_bin), "reconcile", "--json", "--root", str(self.root)],
                              cwd=self.root, capture_output=True, text=True, check=False)
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise PilotError(f"aes reconcile --json failed (exit {proc.returncode}): {(proc.stderr or proc.stdout)[-600:]}") from exc
        return report if isinstance(report, dict) else {}

    # -- what an agent sees --
    def branch_state(self, agent: str) -> dict[str, Any]:
        branch = self.branches[agent]
        counts = git(branch.path, "rev-list", "--left-right", "--count", f"main...agent/{agent}").stdout.split()
        behind, ahead = (int(counts[0]), int(counts[1])) if len(counts) == 2 else (0, 0)
        status = git(branch.path, "status", "--porcelain", "--untracked-files=no").stdout.splitlines()
        merging = git(branch.path, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0
        return {"ahead": ahead, "behind": behind, "changed_files": len(status), "merging": merging,
                "last_rejection": branch.last_rejection}

    def subject_for(self, criterion: str) -> dict[str, Any] | None:
        return next((s for s in self.manifest.get("subjects", []) if s.get("criterion") == criterion), None)

    def observation_text(self, agent: str, turn: int) -> str:
        """Compact pilot section of an agent's turn prompt."""
        after = standings(self.last_reconcile)
        open_rows, met = [], []
        for criterion, standing in sorted(after.items()):
            subject = self.subject_for(criterion) or {}
            if standing == SUPPORTED:
                met.append(criterion)
            else:
                open_rows.append(f"- {criterion}: {subject.get('test_module', '?')} ({standing.lower()})")
        state = self.branch_state(agent)
        branch = self.branches[agent]
        mine = (
            f"Your folder (branch agent/{agent}): {state['changed_files']} changed file(s) not yet proposed, "
            f"{state['ahead']} commit(s) ahead of main, {state['behind']} behind."
        )
        if state["merging"]:
            mine += " A merge with main is in progress there: resolve the conflict markers, then propose_change again."
        if branch.last_rejection:
            mine += f" Your last proposal was rejected: {branch.last_rejection}"
        recent = [i for i in self.integrations[branch.last_seen_integration:] if i.agent != agent]
        branch.last_seen_integration = len(self.integrations)
        recent_lines = [f"- turn {i.turn}: {i.agent} integrated {', '.join(i.files) or '(no files)'} ({i.commit[:7]})"
                        for i in recent[-8:]]
        return (
            f"\nShared project ({self.manifest.get('library', 'pilot')}): main is at {self.head()[:7]}. "
            f"Open bounties, {self.bounty_scrip} scrip each when AES records the criterion as met "
            f"({len(open_rows)} open):\n" + ("\n".join(open_rows) or "- none")
            + f"\nMet now: {', '.join(met) or 'none'}.\n" + mine
            + ("\nIntegrated by others since your last turn:\n" + "\n".join(recent_lines) if recent_lines else "")
        )

    # -- integrate --
    def propose(self, agent: str) -> dict[str, Any]:
        """Commit, merge main in, and fast-forward main. Returns status integrated or rejected."""
        branch = self.branches[agent]
        path = branch.path
        roots = self.library_roots
        merging = git(path, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0
        # Only edits to tracked library files are proposed; anything else stays in the folder.
        # Agents cannot stage (their sandbox cannot write the git directory), so a
        # staged-only entry is main's side of a merge in progress, not the agent's edit.
        ignored = [line[3:] for line in git(path, "status", "--porcelain").stdout.splitlines()
                   if (line[:2] == "??" or line[1] != " ") and not any(line[3:].startswith(r) for r in roots)]
        git(path, "add", "-u", "--", *roots)
        staged = git(path, "diff", "--cached", "--name-only").stdout.split()
        for name in staged:
            text = (path / name).read_text(encoding="utf-8", errors="replace") if (path / name).is_file() else ""
            if CONFLICT_MARKER.search(text):
                return self._reject(agent, f"{name} still has merge conflict markers (<<<<<<< / >>>>>>>); edit them out and propose again", staged, ignored)
        if staged or merging:
            message = "Resolve merge with main" if merging else f"{agent}: change"
            git(path, "commit", "--quiet", "--no-verify", "-m", message, author=agent)
        if self.head("main") != git(path, "merge-base", "main", f"agent/{agent}").stdout.strip():
            merge = git(path, "merge", "--no-edit", "--quiet", "main", author=agent, check=False)
            if merge.returncode != 0:
                conflicted = git(path, "diff", "--name-only", "--diff-filter=U").stdout.split()
                return self._reject(
                    agent,
                    f"conflict with main in {', '.join(conflicted) or 'some files'}. Your folder now holds the merge with "
                    "conflict markers; keep both sides' intent, remove the markers, then propose_change again",
                    conflicted, ignored,
                )
        changes = git(path, "diff", "--name-status", "main", f"agent/{agent}").stdout.splitlines()
        if not changes:
            return self._reject(agent, "nothing to propose: your branch has no edits to library files that main lacks "
                                "(your folder is now up to date with main)", [], ignored)
        bad = [c for c in changes if not c.startswith("M\t") or not any(c.split("\t")[-1].startswith(r) for r in roots)]
        if bad:
            return self._reject(
                agent,
                "only edits to existing files under " + ", ".join(roots) + " are accepted; this change also has "
                + "; ".join(b.replace("\t", " ") for b in bad[:5])
                + ". Restore those files from main (for example: git show main:<path> > <path>)",
                [b.split("\t")[-1] for b in bad], ignored,
            )
        files = sorted(c.split("\t")[-1] for c in changes)
        previous = self.head("main")
        git(self.root, "merge", "--ff-only", "--quiet", f"agent/{agent}")
        commit = self.head("main")
        branch.last_rejection = None
        return {"status": "integrated", "commit": commit, "previous_commit": previous, "files": files, "ignored": ignored}

    def _reject(self, agent: str, reason: str, files: list[str], ignored: list[str]) -> dict[str, Any]:
        self.branches[agent].last_rejection = reason
        return {"status": "rejected", "reason": reason, "files": files, "ignored": ignored}

    def record_integration(self, turn: int, agent: str, commit: str, files: list[str]) -> None:
        self.integrations.append(Integration(turn=turn, agent=agent, commit=commit, files=files))

    # -- judge --
    def judge(self, commit: str) -> dict[str, Any]:
        """Record every verification subject at ``commit`` (main's head), commit the observations, reconcile."""
        if self.head() != commit:
            raise PilotError(f"main moved: expected {commit[:8]}, at {self.head()[:8]}")
        started = time.monotonic()
        before = standings(self.last_reconcile)
        observations: dict[str, str] = {}
        for subject in self.manifest.get("subjects", []):
            vs = subject["verification_subject"]
            proc = subprocess.run(
                [str(self.aes_bin), "evidence", "record", vs, "--depends-on", "tests/conftest.py",
                 "--command", "timeout", "--kill-after=5", str(self.test_timeout_seconds), *subject["command"]],
                cwd=self.root, capture_output=True, text=True, check=False,
            )
            obs = self._observation_for(vs, commit)
            if obs is None:
                raise PilotError(f"aes evidence record {vs} wrote no observation (exit {proc.returncode}): {(proc.stderr or proc.stdout)[-600:]}")
            observations[subject["criterion"]] = obs
        git(self.root, "add", ".aes")
        git(self.root, "commit", "--quiet", "--no-verify", "-m", f"AES evidence for {commit[:8]}")
        evidence_commit = self.head()
        report = self.reconcile()
        self.last_reconcile = report
        after = standings(report)
        seconds = round(time.monotonic() - started, 2)
        self.judge_seconds.append(seconds)
        return {"commit": commit, "evidence_commit": evidence_commit, "before": before, "after": after,
                "observation_ids": observations, "seconds": seconds}

    def _observation_for(self, vs: str, commit: str) -> str | None:
        folder = self.root / ".aes" / "observations"
        for path in sorted(folder.glob(f"*-{commit[:8]}.yaml")) if folder.is_dir() else []:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if vs in (data.get("subject_refs") or []) and str(data.get("subject_revision")) == commit:
                return str(data["observation_id"])
        return None

    def dependency_paths(self, observation_id: str) -> list[str]:
        data = yaml.safe_load((self.root / ".aes" / "observations" / f"{observation_id}.yaml").read_text(encoding="utf-8"))
        return [str(p) for p in (data or {}).get("dependency_paths") or []]

    # -- pay --
    def blame_authors(self, commit: str, file: str) -> list[str]:
        """Author name per line of ``file`` at ``commit``; non-agent authors become ''."""
        proc = git(self.root, "blame", "--line-porcelain", commit, "--", file, check=False)
        if proc.returncode != 0:
            return []
        authors: list[str] = []
        name = ""
        for line in proc.stdout.splitlines():
            if line.startswith("author "):
                name = line[7:]
            elif line.startswith("author-mail "):
                mail = line[12:].strip("<>")
                if not (mail.endswith("@" + AGENT_EMAIL_DOMAIN) and name in self.agents):
                    name = ""
            elif line.startswith("\t"):
                authors.append(name)
        return authors

    def contributors(self, commit: str, observation_id: str) -> list[str]:
        """Agents with surviving lines (blame at ``commit``) in the observation's library dependency files."""
        lines: Counter[str] = Counter()
        for path in self.dependency_paths(observation_id):
            if any(path.startswith(r) for r in self.library_roots):
                lines.update(a for a in self.blame_authors(commit, path) if a)
        return sorted(lines, key=lambda a: (-lines[a], a))

    def settle(self, judged: dict[str, Any]) -> dict[str, Any]:
        """Apply the pay rule to a judgement: payments per criterion and released criteria."""
        pay, released = bounty_decisions(judged["after"], self.held, self.ever_paid)
        for criterion in released:
            self.held.discard(criterion)
        payments = []
        for criterion, regained in pay:
            observation = judged["observation_ids"].get(criterion)
            payees = self.contributors(judged["commit"], observation) if observation else []
            shares = split_bounty(self.bounty_scrip, payees)
            if not shares:
                continue  # no agent-authored line behind it: nobody to pay; it stays open to pay later
            self.held.add(criterion)
            self.ever_paid.add(criterion)
            payments.append({"criterion_id": criterion, "shares": shares, "regained": regained,
                             "observation_id": observation})
        return {"payments": payments, "released": released}

    # -- royalty --
    def _module_file(self, commit: str, importer: str, module: str | None, level: int) -> str | None:
        """Library file a ``from <module> import`` in ``importer`` names, or None outside the library."""
        if level:
            parts = importer.split("/")[:-level]
        else:
            parts = []
        parts += [p for p in (module or "").split(".") if p]
        if not parts:
            return None
        known = set(git(self.root, "ls-tree", "-r", "--name-only", commit, "--", *self.library_roots).stdout.split())
        for candidate in ("/".join(parts) + ".py", "/".join(parts) + "/__init__.py"):
            if candidate in known:
                return candidate
        return None

    def _top_level_body(self, commit: str, file: str, name: str) -> tuple[int, int] | None:
        """(first, last) body line of the module-level function ``name`` in ``file``; docstring excluded."""
        try:
            tree = ast.parse(git(self.root, "show", f"{commit}:{file}").stdout)
        except SyntaxError:
            return None
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name and node.body:
                body = node.body
                if len(body) > 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    body = body[1:]  # the docstring is the stub's, not the implementer's
                return body[0].lineno, node.end_lineno or body[-1].lineno
        return None

    def royalties(self, previous: str, commit: str, payer: str) -> list[dict[str, Any]]:
        """Library functions the change's added lines call or import whose body another agent mostly wrote.

        Resolved statically and conservatively: a bare call ``f()`` counts when
        ``f`` is imported from a library module or is a module-level function of
        the same file; ``mod.f()`` counts when ``mod`` is an imported library
        module; ``from <library module> import f`` on an added line counts.
        Method calls on objects (``x.pop()``) are not resolved, so builtins and
        dict methods never pay a royalty by name alone.
        """
        diff = git(self.root, "diff", "-U0", previous, commit, "--", *self.library_roots).stdout
        added: dict[str, set[int]] = {}
        current = None
        for line in diff.splitlines():
            if line.startswith("+++ "):
                current = line[6:] if line.startswith("+++ b/") else None
            elif current and (match := HUNK.match(line)):
                start, count = int(match.group(1)), int(match.group(2) or 1)
                added.setdefault(current, set()).update(range(start, start + count))
        targets: dict[tuple[str, str], str] = {}
        for file, lines in added.items():
            if not file.endswith(".py") or not lines:
                continue
            try:
                tree = ast.parse(git(self.root, "show", f"{commit}:{file}").stdout)
            except SyntaxError:
                continue
            functions: dict[str, tuple[str, str]] = {
                n.name: (file, n.name) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            modules: dict[str, str] = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    source = self._module_file(commit, file, node.module, node.level)
                    for alias in node.names:
                        bound = alias.asname or alias.name
                        submodule = self._module_file(commit, file, f"{node.module or ''}.{alias.name}".strip("."), node.level)
                        if submodule:
                            modules[bound] = submodule
                        elif source:
                            functions[bound] = (source, alias.name)
                            if node.lineno in lines:
                                targets.setdefault((source, alias.name), file)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or node.lineno not in lines:
                    continue
                func = node.func
                if isinstance(func, ast.Name) and func.id in functions:
                    targets.setdefault(functions[func.id], file)
                elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in modules:
                    targets.setdefault((modules[func.value.id], func.attr), file)
        paid: list[dict[str, Any]] = []
        for (target_file, name), used_in in sorted(targets.items()):
            if name.startswith("__"):
                continue
            span = self._top_level_body(commit, target_file, name)
            if span is None:
                continue  # a class, constant or missing name: no function body to credit
            authors = self.blame_authors(commit, target_file)[span[0] - 1:span[1]]
            counted = Counter(a for a in authors if a)
            if not counted:
                continue
            author, lines_by_author = counted.most_common(1)[0]
            if author == payer or lines_by_author * 2 <= len(authors):
                continue
            paid.append({"author": author, "function": name, "file": target_file, "used_in": used_in})
        return paid
