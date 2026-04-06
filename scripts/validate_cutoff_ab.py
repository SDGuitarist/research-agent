#!/usr/bin/env python3
"""A/B validation: compare gate decisions at relevance_cutoff=3 vs cutoff=4.

Runs real queries through search → fetch → extract → summarize → score pipeline,
then replays the same scored data at both cutoffs to compare gate decisions.
Scores once per query to avoid double-spending API credits.

Usage:
    python3 scripts/validate_cutoff_ab.py
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from anthropic import AsyncAnthropic
from research_agent.modes import ResearchMode
from research_agent.search import search
from research_agent.fetch import fetch_urls
from research_agent.extract import extract_all
from research_agent.cascade import cascade_recover
from research_agent.summarize import summarize_all
from research_agent.relevance import score_source, _aggregate_by_source
from research_agent.sanitize import sanitize_content

# Queries from the plan's A/B test table + 3 high-risk additions
QUERIES = [
    ("Specific technical", "Python asyncio semaphore patterns"),
    ("Specific factual", "SpaceX Starship launch dates 2026"),
    ("Broad technical", "machine learning trends"),
    ("Niche topic", "post-quantum cryptography standards"),
    ("Current events", "recent AI regulation EU"),
    ("Comparison", "React vs Vue 2026"),
    ("Local/specific", "best coffee shops Portland Oregon"),
    ("How-to", "how to deploy FastAPI on AWS Lambda"),
    ("Industry", "renewable energy market growth"),
    ("Emerging tech", "WebAssembly server-side use cases"),
    ("Aggregator-heavy", "best project management tools 2026"),
    ("Person-specific", "John Smith CEO XYZ Corp"),
    ("Very recent events", "latest AI model releases April 2026"),
]


@dataclass
class QueryResult:
    query_type: str
    query: str
    source_scores: list[dict]
    decision_at_3: str
    decision_at_4: str
    survived_at_3: int
    survived_at_4: int
    total_scored: int
    flipped: bool


async def score_all_sources(query, summaries, client, mode):
    """Score all summaries and return per-source aggregated scores."""
    safe_query = sanitize_content(query)
    scored = []
    for s in summaries:
        result = await score_source(
            safe_query, s, client,
            model=mode.relevance_model,
            temperature=mode.planning_temperature,
        )
        scored.append(result)
    return _aggregate_by_source(summaries, scored)


def gate_decision(source_scores, cutoff, mode):
    """Replay gate logic at a given cutoff without re-scoring."""
    surviving = sum(1 for src in source_scores if src["score"] >= cutoff)
    total = len(source_scores)

    if surviving >= mode.min_sources_full_report:
        return "full_report", surviving
    elif surviving >= mode.min_sources_short_report:
        return "short_report", surviving
    elif total > 0 and surviving == 0:
        return "no_new_findings", surviving
    else:
        return "insufficient_data", surviving


async def run_query(query_type, query, client, mode):
    """Run a single query through search → score pipeline."""
    print(f"  [{query_type}] \"{query}\"")

    try:
        results = search(query, max_results=mode.pass1_sources)
    except Exception as e:
        print(f"    Search failed: {e}")
        return None

    if not results:
        print(f"    No search results")
        return None

    pages = await fetch_urls([r.url for r in results])
    contents = extract_all(pages)

    fetched_urls = {c.url for c in contents}
    failed_urls = [r.url for r in results if r.url not in fetched_urls]
    if failed_urls:
        recovered = await cascade_recover(failed_urls, results)
        contents.extend(recovered)

    if not contents:
        print(f"    No content extracted")
        return None

    summaries = await summarize_all(
        client, contents, model=mode.model,
        temperature=mode.summarize_temperature,
    )

    if not summaries:
        print(f"    No summaries generated")
        return None

    agg_scores = await score_all_sources(query, summaries, client, mode)
    score_list = [{"url": s["url"], "score": s["score"], "title": s["title"]} for s in agg_scores]

    decision_3, survived_3 = gate_decision(agg_scores, 3, mode)
    decision_4, survived_4 = gate_decision(agg_scores, 4, mode)
    flipped = decision_3 != decision_4

    status = "FLIP!" if flipped else "ok"
    print(f"    Sources: {len(agg_scores)} | Scores: {[s['score'] for s in score_list]}")
    print(f"    cutoff=3: {decision_3} ({survived_3} survived) | cutoff=4: {decision_4} ({survived_4} survived) [{status}]")

    return QueryResult(
        query_type=query_type, query=query, source_scores=score_list,
        decision_at_3=decision_3, decision_at_4=decision_4,
        survived_at_3=survived_3, survived_at_4=survived_4,
        total_scored=len(agg_scores), flipped=flipped,
    )


async def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = AsyncAnthropic(api_key=api_key)
    mode = ResearchMode.standard()

    print("=== Cycle 28 A/B Validation: relevance_cutoff 3 vs 4 ===")
    print(f"Mode: standard | Scoring model: {mode.relevance_model} | Summarize model: {mode.model}")
    print(f"Queries: {len(QUERIES)}")
    print()

    results = []
    for query_type, query in QUERIES:
        try:
            result = await run_query(query_type, query, client, mode)
            if result:
                results.append(result)
        except Exception as e:
            print(f"    ERROR: {e}")
        print()

    flips = [r for r in results if r.flipped]
    print("=" * 60)
    print(f"RESULTS: {len(results)} queries completed, {len(flips)} decision flips")
    print()

    if flips:
        print("DECISION FLIPS:")
        for f in flips:
            print(f"  [{f.query_type}] \"{f.query}\"")
            print(f"    cutoff=3: {f.decision_at_3} ({f.survived_at_3} survived)")
            print(f"    cutoff=4: {f.decision_at_4} ({f.survived_at_4} survived)")
            print(f"    Scores: {[s['score'] for s in f.source_scores]}")
    else:
        print("NO DECISION FLIPS — cutoff raise from 3->4 is safe for standard mode.")

    # Write durable artifact
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = {
        "test": "Cycle 28 A/B Validation: relevance_cutoff 3 vs 4",
        "timestamp": timestamp,
        "mode": "standard",
        "scoring_model": mode.relevance_model,
        "queries_run": len(results),
        "decision_flips": len(flips),
        "conclusion": "SAFE" if not flips else "INVESTIGATE",
        "results": [
            {
                "type": r.query_type,
                "query": r.query,
                "scores": [s["score"] for s in r.source_scores],
                "total_sources": r.total_scored,
                "cutoff_3": {"decision": r.decision_at_3, "survived": r.survived_at_3},
                "cutoff_4": {"decision": r.decision_at_4, "survived": r.survived_at_4},
                "flipped": r.flipped,
            }
            for r in results
        ],
    }

    out_path = Path("docs/validation")
    out_path.mkdir(parents=True, exist_ok=True)
    json_path = out_path / "2026-04-05-cycle-28-cutoff-ab-results.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nResults saved to {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
