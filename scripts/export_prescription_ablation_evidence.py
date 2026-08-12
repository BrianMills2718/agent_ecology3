#!/usr/bin/env python3
"""Export the frozen Evaluation 04 evidence from ignored runtime logs."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from llm_client.observability.query import get_llm_call_receipts
from llm_client.observability.replay import get_call_record


RUN_REVISION = "03be7c4"
PREFLIGHT_TRACE_ID = "ae3/preflight_1786496281479803236/event_0/payer/alpha_1"
PAID_RUN_IDS = (
    "run_20260812_005820",
    "run_20260812_011048",
    "run_20260812_011449",
    "run_20260812_012034",
    "run_20260812_012401",
)
LLM_OFF_RUN_IDS = (
    "run_20260812_012834",
    "run_20260812_012844",
    "run_20260812_012855",
)
MATRIX_FILES = (
    "prescribed_1786496300.jsonl",
    "prescribed_1786496300_run_ids.txt",
    "prescribed_valid_1786497048.jsonl",
    "prescribed_valid_1786497048_run_ids.txt",
    "prescribed_1024_1786497289.jsonl",
    "prescribed_1024_1786497289_run_ids.txt",
    "prescribed_1024_1786497289_summary.json",
    "llm_off_1786498114.jsonl",
    "llm_off_1786498114_run_ids.txt",
    "llm_off_1786498114_summary.json",
)
INPUT_FILES = (
    "config/config.prescription_ablation.yaml",
    "config/prompts/loop_prompt_variant.txt",
    "config/prompts/loop_prompt_minimal.txt",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _gzip_copy(source: Path, destination: Path) -> None:
    with source.open("rb") as source_handle, destination.open("wb") as raw_output:
        with gzip.GzipFile(fileobj=raw_output, mode="wb", mtime=0) as compressed:
            shutil.copyfileobj(source_handle, compressed)


def _write_gzip_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("wb") as raw_output:
        with gzip.GzipFile(fileobj=raw_output, mode="wb", mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8") as text_output:
                for record in records:
                    text_output.write(json.dumps(record, sort_keys=True) + "\n")


def _events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _trace_records(root: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    audit = {
        "ae3_attempt_events": 0,
        "matching_receipt_rows": 0,
        "missing_receipt_events": 0,
        "records_with_messages": 0,
        "records_with_nonempty_response_text": 0,
        "tool_call_records_with_empty_response_text": 0,
    }

    for run_id in PAID_RUN_IDS:
        events = _events(root / "logs" / run_id / "events.jsonl")
        decisions = {
            event.get("llm_trace_id"): event
            for event in events
            if event.get("event_type") == "loop_decision" and event.get("llm_trace_id")
        }
        for event in events:
            if event.get("event_type") not in {"llm_syscall", "llm_syscall_error"}:
                continue
            audit["ae3_attempt_events"] += 1
            trace_id = event["trace_id"]
            receipts = get_llm_call_receipts(trace_id=trace_id)
            if not receipts:
                audit["missing_receipt_events"] += 1
            for receipt in receipts:
                audit["matching_receipt_rows"] += 1
                call_id = int(receipt.receipt_id.rsplit("-", 1)[1])
                call_record = get_call_record(call_id)
                messages_present = bool(call_record.get("messages"))
                response_present = bool(call_record.get("response"))
                if messages_present:
                    audit["records_with_messages"] += 1
                if response_present:
                    audit["records_with_nonempty_response_text"] += 1
                if receipt.finish_reason == "tool_calls" and not response_present:
                    audit["tool_call_records_with_empty_response_text"] += 1
                records.append(
                    {
                        "run_id": run_id,
                        "trace_id": trace_id,
                        "ae3_attempt_event": event,
                        "ae3_loop_decision": decisions.get(trace_id),
                        "receipt": receipt.model_dump(mode="json"),
                        "retained_call_record": call_record,
                        "custody_check": {
                            "messages_present": messages_present,
                            "response_text_present": response_present,
                            "raw_tool_call_envelope_retained": False
                            if receipt.finish_reason == "tool_calls" and not response_present
                            else None,
                        },
                    }
                )

    preflight_receipts = get_llm_call_receipts(trace_id=PREFLIGHT_TRACE_ID)
    for receipt in preflight_receipts:
        call_id = int(receipt.receipt_id.rsplit("-", 1)[1])
        records.append(
            {
                "run_id": "preflight",
                "trace_id": PREFLIGHT_TRACE_ID,
                "receipt": receipt.model_dump(mode="json"),
                "retained_call_record": get_call_record(call_id),
            }
        )
    return records, audit


def export(root: Path) -> Path:
    evidence = root / "docs" / "evaluations" / "evidence" / "04_prescription_ablation"
    if evidence.exists():
        raise SystemExit(f"Refusing to overwrite existing evidence: {evidence}")
    evidence.mkdir(parents=True)
    (evidence / "events").mkdir()
    (evidence / "inputs").mkdir()
    (evidence / "matrices").mkdir()

    observed_head = subprocess.check_output(
        ["git", "rev-parse", "--short=7", "HEAD"], cwd=root, text=True
    ).strip()
    if observed_head != RUN_REVISION:
        raise SystemExit(f"Expected run revision {RUN_REVISION}, observed {observed_head}")

    for relative in INPUT_FILES:
        source = root / relative
        shutil.copyfile(source, evidence / "inputs" / source.name)
    for filename in MATRIX_FILES:
        shutil.copyfile(
            root / "logs" / "plan4_prescription_ablation" / filename,
            evidence / "matrices" / filename,
        )
    for run_id in (*PAID_RUN_IDS, *LLM_OFF_RUN_IDS):
        _gzip_copy(
            root / "logs" / run_id / "events.jsonl",
            evidence / "events" / f"{run_id}.events.jsonl.gz",
        )

    trace_records, custody_audit = _trace_records(root)
    _write_gzip_jsonl(evidence / "trace_records.jsonl.gz", trace_records)
    inventory = {
        "schema_version": "ae3_evaluation_04_evidence_v1",
        "classification": "inconclusive",
        "classification_reasons": [
            "More than one paid run failed the frozen validity thresholds.",
            "The shared client retained rendered messages but not raw tool-call envelopes.",
        ],
        "run_revision": RUN_REVISION,
        "run_worktree_was_clean": True,
        "model": "minimax/minimax-m3",
        "minimal_condition_started": False,
        "stop_reason": "Frozen invalid-run limit reached during the prescribed control.",
        "preflight": {
            "trace_id": PREFLIGHT_TRACE_ID,
            "cost_usd": 0.0001023,
        },
        "paid_runs": [
            {"run_id": PAID_RUN_IDS[0], "role": "excluded_horizon_pilot", "valid": False},
            {"run_id": PAID_RUN_IDS[1], "role": "retained_output_cap_pilot", "valid": False},
            {"run_id": PAID_RUN_IDS[2], "role": "prescribed_replicate_1", "valid": True},
            {"run_id": PAID_RUN_IDS[3], "role": "prescribed_replicate_2", "valid": True},
            {"run_id": PAID_RUN_IDS[4], "role": "prescribed_replicate_3", "valid": False},
        ],
        "llm_off_runs": list(LLM_OFF_RUN_IDS),
        "actual_paid_cost_usd": 0.0744073,
        "trace_custody_audit": custody_audit,
    }
    _write_json(evidence / "run_inventory.json", inventory)

    readme = """# Evaluation 04 evidence\n\nThis bundle preserves the inputs, matrix outputs, compressed raw AE3 events,\nand matching shared-client call records for the inconclusive prescription\nablation. `run_inventory.json` is the compact index. `SHA256SUMS` covers every\nother file in this directory.\n\nThe trace archive intentionally exposes the observed custody gap: rendered\nmessages were retained, while successful tool-call rows generally have an empty\nresponse text field and no raw tool-call envelope. AE3's normalized decisions\nremain in the paired loop-decision events.\n"""
    (evidence / "README.md").write_text(readme)

    manifest_lines = []
    for path in sorted(evidence.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            manifest_lines.append(f"{_sha256(path)}  {path.relative_to(evidence)}")
    (evidence / "SHA256SUMS").write_text("\n".join(manifest_lines) + "\n")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Agent Ecology 3 worktree root",
    )
    args = parser.parse_args()
    print(export(args.repo.resolve()))


if __name__ == "__main__":
    main()
