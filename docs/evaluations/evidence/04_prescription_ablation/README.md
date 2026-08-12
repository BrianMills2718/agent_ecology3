# Evaluation 04 evidence

This bundle preserves the inputs, matrix outputs, compressed raw AE3 events,
and matching shared-client call records for the inconclusive prescription
ablation. `run_inventory.json` is the compact index. `SHA256SUMS` covers every
other file in this directory.

The trace archive intentionally exposes the observed custody gap: rendered
messages were retained, while successful tool-call rows generally have an empty
response text field and no raw tool-call envelope. AE3's normalized decisions
remain in the paired loop-decision events.
