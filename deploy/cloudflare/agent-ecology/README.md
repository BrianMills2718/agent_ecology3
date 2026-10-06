# Public replay at brianmills.dev/agent-ecology/

A static, read-only replay of one finished agent_ecology3 run (Plan 26 M4):
the activity feed, the Interactions matrix and the World Substrate living view.
No server code, no API, no controls that act. Cloudflare Worker
`agent-ecology-replay`, static assets only (`wrangler.jsonc`).

- **Build** (redaction by allow-list, then a leak check that refuses to write):
  `uv run python scripts/build_public_replay.py build <run_dir> --bank <bank.jsonl>`
  writes `assets/agent-ecology/{index.html,snapshot.json,living.html}`.
  What is withheld and why: the docstring of `scripts/build_public_replay.py`.
- **Test** (no model calls): `uv run pytest tests/test_public_replay.py`.
- **Deploy** from a committed revision, with release checks and live verification:
  `scripts/deploy_public_replay.sh [origin/main]`.
- **Browser check** (page errors, phone-width sideways scroll, a styled tooltip on
  every control): `npm install && node check_page.cjs https://brianmills.dev/agent-ecology/`.

Roll back by redeploying an earlier commit: `scripts/deploy_public_replay.sh <commit>`.
