#!/bin/bash
set -euo pipefail
mode="${1:-all}"
scratch="$(mktemp -d "${TMPDIR:-/tmp}/taf-jcvi-smoke.XXXXXXXX")"
trap 'status=$?; if ((status)); then printf >&2 "jcvi-smoke failed: mode=%s status=%s\n" "$mode" "$status"; tail -n 60 "$scratch/run.log" >&2 2>/dev/null || true; fi; rm -rf -- "$scratch"; exit "$status"' EXIT
export HOME="$scratch/home" TMPDIR="$scratch/tmp" MPLCONFIGDIR="$scratch/mpl" XDG_CACHE_HOME="$scratch/cache"
mkdir -p "$HOME" "$TMPDIR" "$MPLCONFIGDIR" "$XDG_CACHE_HOME"
cd "$scratch"
python /opt/jcvi/share/testdata/smoke.py "$mode" >"$scratch/run.log" 2>&1
echo "jcvi-smoke $mode PASS"
