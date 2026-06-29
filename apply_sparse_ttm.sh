#!/usr/bin/env bash
# apply_sparse_ttm.sh
# Idempotent one-shot patch script.
# Safe to re-run — checks before modifying.
# Run from repo root: bash apply_sparse_ttm.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "Verifying repo structure..."
for f in generate.py src/pipeline.py src/prompt_engine.py src/comfy_client.py src/job_queue.py config/pipeline.yaml; do
  [ -f "$f" ] || { echo "ERROR: $f not found. Run from repo root."; exit 1; }
done

echo "All source files present."
echo "NOTE: All patched files are now managed via git. This script is for reference."
echo "To apply the full patch from this branch:"
echo "  git fetch origin feat/sparse-ttm-batch-scaling"
echo "  git checkout feat/sparse-ttm-batch-scaling"
echo "  python generate.py --dry-run --sparse-keyframes"
echo ""
echo "To merge to main:"
echo "  gh pr merge --merge --delete-branch"
