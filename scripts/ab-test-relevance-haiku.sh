#!/usr/bin/env bash
# A/B test: Haiku for relevance scoring (Tier 2)
# Runs the same 9 baseline queries with RELEVANCE_MODEL set to Haiku.
# Compare output reports against reports/*_2026-03-05_*.md (Sonnet-scored).
set -euo pipefail

export RELEVANCE_MODEL="claude-haiku-4-5-20251001"

QUERIES=(
  "the lodge at torrey pines"
  "best restaurants"
  "how do zoning laws affect short-term rentals in san diego"
  "pendry san diego branding and marketing initiatives"
  "hotel del coronado guest programs and events for 2026"
  "luxury hospitality market trends in san diego for 2026"
  "grant writing as a side hustle"
  "macroeconomic implications of ai and job displacement"
  "ai in filmmaking current trends best practices and limitations"
)

echo "=== A/B Test: Haiku Relevance Scoring ==="
echo "Model override: $RELEVANCE_MODEL"
echo "Queries: ${#QUERIES[@]}"
echo ""

for q in "${QUERIES[@]}"; do
  echo "--- Running: $q ---"
  python3 main.py --standard "$q" -v 2>&1 | tee -a reports/ab-test-haiku-relevance.log
  echo ""
  echo "--- Done: $q ---"
  echo ""
done

echo "=== All queries complete ==="
echo "Compare new reports against reports/*_2026-03-05_*.md"
