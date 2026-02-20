"""JSONL event logging."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SummarySnapshot:
    timestamp: str
    event_number: int
    action_count: int
    principal_count: int
    artifact_count: int
    total_scrip: int


class EventLogger:
    """Append-only JSONL logger with per-run directories."""

    def __init__(
        self,
        *,
        logs_dir: str,
        run_id: str,
        event_file_name: str = "events.jsonl",
        summary_file_name: str = "summary.jsonl",
    ) -> None:
        self.logs_dir = Path(logs_dir)
        self.run_id = run_id
        self.run_dir = self.logs_dir / run_id
        self.output_path = self.run_dir / event_file_name
        self.summary_path = self.run_dir / summary_file_name
        self.sequence = 0

        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text("", encoding="utf-8")
        self.summary_path.write_text("", encoding="utf-8")

        latest = self.logs_dir / "latest"
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(self.run_id)

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def log(self, event_type: str, data: dict[str, Any]) -> None:
        self.sequence += 1
        payload = {
            "timestamp": self._timestamp(),
            "sequence": self.sequence,
            "event_type": event_type,
            **data,
        }
        with self.output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def log_summary(self, summary: SummarySnapshot) -> None:
        with self.summary_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(summary.__dict__, ensure_ascii=True) + "\n")

    def read_recent(self, n: int = 50) -> list[dict[str, Any]]:
        if n <= 0:
            return []
        if not self.output_path.exists():
            return []
        lines = self.output_path.read_text(encoding="utf-8").splitlines()
        result: list[dict[str, Any]] = []
        for raw in lines[-n:]:
            try:
                result.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return result

    def read_slice(self, offset: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        if not self.output_path.exists() or limit <= 0:
            return []
        lines = self.output_path.read_text(encoding="utf-8").splitlines()
        selected = lines[offset : offset + limit]
        out: list[dict[str, Any]] = []
        for raw in selected:
            try:
                out.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return out
