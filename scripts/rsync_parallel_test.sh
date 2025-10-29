#!/usr/bin/env bash
set -euo pipefail

# rsync parallel sharding test harness (macOS-focused)
# - Supports methods: top-level, count-balanced, size-balanced (size-tiers TBD)
# - Defaults to dry-run to ensure safety; require --dry-run=false for real runs

usage() {
  cat <<'EOF'
Usage: rsync_parallel_test.sh \
  --src SRC --dst DST \
  --method {top-level|count-balanced|size-balanced} \
  --shards {3|4} \
  --log-dir DIR [--dry-run {true|false}] [--bwlimit RATE] [--extra "FLAGS"] [--baseline]

Examples:
  rsync_parallel_test.sh --src /Volumes/Source --dst /Volumes/Dest \
    --method count-balanced --shards 4 --log-dir logs/rsync-test \
    --extra "-AX --exclude .DS_Store --exclude '._*'"

Notes (macOS):
  - Install Homebrew tools: brew install rsync coreutils parallel
  - Ensure PATH precedence for rsync 3.x and GNU tools (gsplit/gstat)
    ARM64: export PATH="/opt/homebrew/opt/rsync/bin:/opt/homebrew/bin:$PATH"
    Intel: export PATH="/usr/local/opt/rsync/bin:/usr/local/bin:$PATH"
  - Checksum sampling uses: shasum -a 256
EOF
}

# Defaults
SRC=""
DST=""
METHOD=""
SHARDS=""
LOG_DIR=""
DRY_RUN=true
BWLIMIT=""
EXTRA=""
BASELINE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src) SRC=${2:-}; shift 2 ;;
    --dst) DST=${2:-}; shift 2 ;;
    --method) METHOD=${2:-}; shift 2 ;;
    --shards) SHARDS=${2:-}; shift 2 ;;
    --log-dir) LOG_DIR=${2:-}; shift 2 ;;
    --dry-run) DRY_RUN=${2:-}; shift 2 ;;
    --bwlimit) BWLIMIT=${2:-}; shift 2 ;;
    --extra) EXTRA=${2:-}; shift 2 ;;
    --baseline) BASELINE=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

[[ -z "$SRC" || -z "$DST" || -z "$METHOD" || -z "$SHARDS" || -z "$LOG_DIR" ]] && { usage; exit 2; }

if [[ "$SHARDS" != "3" && "$SHARDS" != "4" ]]; then
  echo "Error: --shards must be 3 or 4" >&2
  exit 2
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Warning: This script is tuned for macOS (Darwin). Proceeding anyway..." >&2
fi

# Dep checks (best-effort)
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1" >&2; return 1; }; }
MISSING=0
for bin in rsync find gsplit gstat python3; do
  if ! need "$bin"; then MISSING=1; fi
done
if [[ $MISSING -eq 1 ]]; then
  echo "Install missing deps. Recommended: brew install rsync coreutils" >&2
fi

mkdir -p "$LOG_DIR"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "Workdir: $WORKDIR"

# Build base rsync flags
BASE_FLAGS=(-a --partial --partial-dir=.rsync-partial --info=stats2 --numeric-ids)
[[ -n "$BWLIMIT" ]] && BASE_FLAGS+=(--bwlimit "$BWLIMIT")

if [[ "$DRY_RUN" == "true" ]]; then
  BASE_FLAGS+=(--dry-run)
fi

# Append optional flags
if [[ -n "$EXTRA" ]]; then
  # shellcheck disable=SC2206
  EXTRA_ARR=($EXTRA)
else
  EXTRA_ARR=()
fi

# Baseline run (single rsync) for comparison
if [[ "$BASELINE" == true ]]; then
  echo "Running baseline rsync..."
  RSYNC_LOG="$LOG_DIR/baseline.log"
  rsync "${BASE_FLAGS[@]}" "${EXTRA_ARR[@]}" --log-file "$RSYNC_LOG" \
    "$SRC"/ "$DST"/
  echo "Baseline complete. Log: $RSYNC_LOG"
fi

cd "$SRC"

make_shards_top_level() {
  # Use ls for top-level directories to avoid BSD find maxdepth issues
  ls -1 -d */ 2>/dev/null | sed 's:/$::' | gsplit -n l/"$SHARDS" -d - "$WORKDIR/tl."
}

make_shards_count_balanced() {
  # List all files; split into N parts by count
  find . -type f -print | sed 's:^\./::' | gsplit -n l/"$SHARDS" -d - "$WORKDIR/files."
}

make_shards_size_balanced() {
  # Generate size + path (paths relative to SRC)
  # gstat prints size via %z; strip leading ./ from find
  find . -type f -print0 | sed -e 's:^\./::' | tr '\0' '\n' | while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    sz=$(gstat -f '%z' -- "$p" 2>/dev/null || echo 0)
    printf '%s %s\n' "$sz" "$p"
  done >"$WORKDIR/sizes.txt"

  python3 - "$SHARDS" "$WORKDIR" <<'PY'
import sys, heapq, os
N = int(sys.argv[1])
wd = sys.argv[2]
bins = [(0, i, []) for i in range(N)]
with open(os.path.join(wd, 'sizes.txt'), 'r') as f:
    for line in f:
        line=line.rstrip('\n')
        if not line:
            continue
        sz_s, name = line.split(' ', 1)
        try:
            sz = int(sz_s)
        except ValueError:
            sz = 0
        total, i, arr = heapq.heappop(bins)
        arr.append(name)
        heapq.heappush(bins, (total+sz, i, arr))
for total, i, arr in sorted(bins, key=lambda x: x[1]):
    with open(os.path.join(wd, f'files.{i:02d}'), 'w') as out:
        out.write('\n'.join(arr))
PY
}

case "$METHOD" in
  top-level) make_shards_top_level ; PREFIX="tl" ;;
  count-balanced) make_shards_count_balanced ; PREFIX="files" ;;
  size-balanced) make_shards_size_balanced ; PREFIX="files" ;;
  *) echo "Unknown --method: $METHOD" >&2; exit 2 ;;
esac

# Launch parallel rsyncs
declare -a PIDS=()
for i in $(seq -f '%02g' 0 $((SHARDS-1))); do
  LIST="$WORKDIR/${PREFIX}.${i}"
  [[ -s "$LIST" ]] || { echo "Shard $i is empty; skipping"; continue; }
  LOG="$LOG_DIR/shard_${i}.log"
  echo "Starting shard $i with list $LIST"
  rsync "${BASE_FLAGS[@]}" "${EXTRA_ARR[@]}" --relative --files-from="$LIST" --log-file "$LOG" . "$DST"/ &
  PIDS+=($!)
done

EXIT_SUM=0
for idx in "${!PIDS[@]}"; do
  pid=${PIDS[$idx]}
  if wait "$pid"; then
    :
  else
    code=$?
    echo "Shard index $idx failed with exit code $code" >&2
    EXIT_SUM=$((EXIT_SUM+code))
  fi
done

if [[ $EXIT_SUM -ne 0 ]]; then
  echo "One or more shards failed. Check logs in $LOG_DIR" >&2
  exit 1
fi

echo "All shards completed successfully. Logs in $LOG_DIR"

# TODO: Add checksum sampling and JSON summary aggregation per advisory order

