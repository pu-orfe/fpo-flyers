#!/usr/bin/env zsh
# Create or update the main-branch ruleset from .github/rulesets/main.json.
#
# The ruleset requires the CI jobs (lint, test) to pass before main moves, and
# blocks force-pushes and deletion. The GitHub Actions app may bypass it so
# generate.yml can still push feed-hash and keepalive commits.
#
# Usage: scripts/apply-ruleset.sh [--dry-run]
#   REPO=owner/name overrides the repository (default: the current gh repo).
# Requires: gh (authenticated, repo admin), jq. Safe to re-run: an existing
# ruleset with the same name is updated in place.
set -euo pipefail

# Captured here: inside a zsh function, $0 is the function's name.
script_file="$0"
script_dir="$(cd "$(dirname "$script_file")" && pwd)"

usage() { sed -n '2,12p' "$script_file" | sed 's/^# \{0,1\}//'; }

dry_run=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) dry_run=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in gh jq; do
  command -v "$tool" >/dev/null || { echo "missing required tool: $tool" >&2; exit 1; }
done

ruleset="$script_dir/../.github/rulesets/main.json"
[[ -f "$ruleset" ]] || { echo "ruleset not found: $ruleset" >&2; exit 1; }
name="$(jq -er '.name' "$ruleset")"

repo="${REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
[[ "$repo" == */* ]] || { echo "invalid repository: $repo" >&2; exit 1; }

existing_id="$(gh api "repos/$repo/rulesets" --jq ".[] | select(.name == $(jq -n --arg n "$name" '$n')) | .id")"

if [[ -z "$existing_id" ]]; then
  method=POST api_path="repos/$repo/rulesets"
else
  method=PUT api_path="repos/$repo/rulesets/$existing_id"
fi

if (( dry_run )); then
  echo "[dry-run] would $method $api_path with:"
  jq . "$ruleset"
  exit 0
fi

gh api --method "$method" "$api_path" --input "$ruleset" \
  --jq '"\(.name): id=\(.id) enforcement=\(.enforcement)"'
