#!/usr/bin/env bash
# Deploy the public replay (Plan 26 M4) to brianmills.dev/agent-ecology/ from a committed revision.
#
#   scripts/deploy_public_replay.sh [revision, default origin/main]
#
# Release checks, in order; any failure stops before anything is published:
#   1. the replay's tests (no model calls);
#   2. the leak check on the committed files (bank sentences, hidden test inputs,
#      tokens, home paths, Codex folders, email addresses: every count must be 0);
#   3. wrangler deploy (Cloudflare Worker "agent-ecology-replay", static assets only);
#   4. the live index.html and snapshot.json match the committed bytes, and the
#      leak check run on the files fetched from the live site is 0.
# Needs: ~/.secrets/api_keys.env with CLOUDFLARE_API_KEY and CLOUDFLARE_EMAIL; the bank
# file (BANK, default the run5 bank) to check against. Prints counts and timings per step.
set -euo pipefail
REV=${1:-origin/main}
BANK=${BANK:-$HOME/.cache/agent_ecology3/codeflow_bank_a16_p40_s25201.jsonl}
URL=https://brianmills.dev/agent-ecology/
repo=$(cd "$(dirname "$0")/.." && pwd)
git -C "$repo" fetch -q origin
commit=$(git -C "$repo" rev-parse "$REV")
stage="$repo/worktrees/deploy-replay-${commit:0:12}"
git -C "$repo" worktree add -q --detach "$stage" "$commit"
trap 'git -C "$repo" worktree remove --force "$stage" >/dev/null 2>&1 || true' EXIT
assets="$stage/deploy/cloudflare/agent-ecology/assets/agent-ecology"
t=$SECONDS
echo "== 1. tests at ${commit:0:12}"
(cd "$stage" && uv run -q pytest tests/test_public_replay.py -p no:cacheprovider 2>&1 | tail -1)
echo "== 2. leak check on committed files ($((SECONDS - t))s)"
(cd "$stage" && uv run -q python scripts/build_public_replay.py check "$assets" --bank "$BANK")
echo "== 3. deploy ($((SECONDS - t))s)"
pages="$stage/deploy/cloudflare/agent-ecology"
(cd "$pages" && npm install --silent --no-audit --no-fund >/dev/null 2>&1)
set -a; . "$HOME/.secrets/api_keys.env"; set +a
export CLOUDFLARE_API_KEY CLOUDFLARE_EMAIL
wlog=$(mktemp)
(cd "$pages" && node_modules/.bin/wrangler deploy >"$wlog" 2>&1) \
  || { echo "deploy FAILED:" >&2; tail -25 "$wlog" >&2; exit 1; }
grep -E "Current Version|brianmills.dev" "$wlog" || tail -5 "$wlog"
echo "== 4. verify live ($((SECONDS - t))s)"
live=$(mktemp -d)
for f in index.html snapshot.json living.html; do
  want=$(sha256sum < "$assets/$f" | cut -c1-16)
  for _ in $(seq 1 20); do
    curl -s -m 30 "$URL$f?v=$RANDOM" -o "$live/$f"
    got=$(sha256sum < "$live/$f" | cut -c1-16)
    [[ "$got" == "$want" ]] && break
    sleep 3
  done
  [[ "$got" == "$want" ]] || { echo "live $f does not match the committed build" >&2; exit 3; }
  echo "live $f matches ${commit:0:12} ($(wc -c < "$live/$f") bytes)"
done
(cd "$stage" && uv run -q python scripts/build_public_replay.py check "$live" --bank "$BANK")
echo "deployed ${commit:0:12} to $URL in $((SECONDS - t))s"
