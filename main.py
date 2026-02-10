#!/usr/bin/env python3
"""CLI for the research agent."""

import argparse
import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from research_agent import ResearchAgent
from research_agent.errors import ResearchError
from research_agent.modes import ResearchMode

RESEARCH_LOG_PATH = Path("research_log.md")


def sanitize_filename(query: str, max_length: int = 50) -> str:
    """
    Sanitize a query string for use in a filename.

    - Lowercase
    - Replace spaces with underscores
    - Remove non-alphanumeric chars except underscores
    - Truncate to max_length
    """
    # Lowercase and replace spaces
    sanitized = query.lower().replace(" ", "_")
    # Keep only alphanumeric and underscores
    sanitized = re.sub(r"[^a-z0-9_]", "", sanitized)
    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    # Strip leading/trailing underscores
    sanitized = sanitized.strip("_")
    # Truncate
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rsplit("_", 1)[0]
    return sanitized or "research"


def append_research_log(query: str, mode: ResearchMode, report: str) -> None:
    """Append a brief entry to the research log."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        # Extract first non-empty, non-heading line as summary
        summary_lines = []
        for line in report.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("**Note:**"):
                summary_lines.append(line)
                if len(summary_lines) >= 2:
                    break
        summary = " ".join(summary_lines)[:200] + "..." if summary_lines else "No summary available"

        entry = f"\n## {timestamp} — \"{query}\"\n- Mode: {mode.name}\n- {summary}\n"

        with open(RESEARCH_LOG_PATH, "a") as f:
            f.write(entry)
    except OSError:
        pass  # Non-fatal — don't fail the pipeline for logging


def get_auto_save_path(query: str) -> Path:
    """Generate auto-save path for standard and deep mode reports."""
    reports_dir = REPORTS_DIR
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S%f")  # Microseconds prevent collisions
    safe_query = sanitize_filename(query)
    filename = f"{safe_query}_{timestamp}.md"
    return reports_dir / filename


REPORTS_DIR = Path("reports")

# Regex patterns for extracting date from report filenames
# Old format: 2026-02-03_183703056652_query_name.md (timestamp first)
_OLD_FORMAT = re.compile(r"^(\d{4}-\d{2}-\d{2})_\d{6,}_(.+)\.md$")
# New format: query_name_2026-02-03_183703056652.md (query first)
_NEW_FORMAT = re.compile(r"^(.+)_(\d{4}-\d{2}-\d{2})_\d{6,}\.md$")


def list_reports() -> None:
    """Print a table of saved reports sorted newest-first."""
    if not REPORTS_DIR.is_dir():
        print("No reports directory found.")
        return

    md_files = sorted(REPORTS_DIR.glob("*.md"))
    if not md_files:
        print("No saved reports.")
        return

    # Parse each filename for date and query name
    dated = []  # (date_str, query_name, filename)
    undated = []  # filenames that don't match either pattern

    for f in md_files:
        name = f.name
        old_match = _OLD_FORMAT.match(name)
        new_match = _NEW_FORMAT.match(name)

        if old_match:
            dated.append((old_match.group(1), old_match.group(2), name))
        elif new_match:
            dated.append((new_match.group(2), new_match.group(1), name))
        else:
            undated.append(name)

    # Sort dated reports newest-first
    dated.sort(key=lambda x: x[0], reverse=True)

    total = len(dated) + len(undated)
    print(f"Saved reports ({total}):")
    for date_str, query_name, _ in dated:
        print(f"  {date_str}  {query_name}")

    if undated:
        print(f"  -- {len(undated)} reports with non-standard names --")
        for name in sorted(undated):
            print(f"  {name}")


def show_costs() -> None:
    """Print estimated costs for all research modes and exit."""
    modes = [ResearchMode.quick(), ResearchMode.standard(), ResearchMode.deep()]
    print("Estimated costs per query:")
    for m in modes:
        default = "  [default]" if m.name == "standard" else ""
        print(f"  {m.name:<10} {m.cost_estimate}  "
              f"({m.max_sources} sources, ~{m.word_target} words){default}")


def main():
    # Load environment variables from .env file
    load_dotenv()

    _quick = ResearchMode.quick()
    _standard = ResearchMode.standard()
    _deep = ResearchMode.deep()

    parser = argparse.ArgumentParser(
        description="Research agent that searches the web and generates markdown reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Research Modes:
  --quick     Fast research: {_quick.max_sources} sources, ~{_quick.word_target} word report ({_quick.cost_estimate})
  --standard  Balanced research: {_standard.max_sources} sources, ~{_standard.word_target} word report ({_standard.cost_estimate}) [default]
              Auto-saves to reports/ folder
  --deep      Thorough research: {_deep.max_sources}+ sources, 2 search passes, ~{_deep.word_target} word report ({_deep.cost_estimate})
              Auto-saves to reports/ folder

Examples:
  python main.py "What are Python async best practices?"
  python main.py "Quick summary of React hooks" --quick
  python main.py "Comprehensive analysis of Kubernetes security" --deep
  python main.py "Compare React vs Vue" --standard -o comparison.md
        """,
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="The research query",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List saved reports and exit",
    )

    # Mode flags (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: 3 sources, ~300 words (~$0.12)",
    )
    mode_group.add_argument(
        "--standard",
        action="store_true",
        help="Standard mode: 7 sources, ~1000 words (~$0.20), auto-saves [default]",
    )
    mode_group.add_argument(
        "--deep",
        action="store_true",
        help="Deep mode: 10+ sources, 2 passes, ~2000 words (~$0.50), auto-saves",
    )

    parser.add_argument(
        "--max-sources", "-n",
        type=int,
        default=None,
        help="Maximum sources (ignored when using mode flags)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file path (default: stdout, or auto for --standard/--deep)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--cost",
        action="store_true",
        help="Show estimated costs for all modes and exit",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open saved report after generation (macOS)",
    )

    args = parser.parse_args()

    # --list: show saved reports and exit (highest priority)
    if args.list:
        list_reports()
        sys.exit(0)

    # --cost: show costs and exit (no API keys needed)
    if args.cost:
        show_costs()
        sys.exit(0)

    # Require query for research
    if args.query is None:
        parser.print_help()
        sys.exit(2)

    # Configure logging (after parsing so --verbose is available)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(name)s: %(message)s",
    )

    # Determine mode
    mode_flag_used = args.quick or args.deep or args.standard
    if args.quick:
        mode = ResearchMode.quick()
    elif args.deep:
        mode = ResearchMode.deep()
    else:
        mode = ResearchMode.standard()

    # Warn if --max-sources used with mode flag
    if args.max_sources is not None and mode_flag_used:
        print(f"Note: --max-sources ignored when using --{mode.name} (uses {mode.max_sources} sources)",
              file=sys.stderr)

    try:
        agent = ResearchAgent(
            mode=mode,
            max_sources=args.max_sources if not mode_flag_used else None,
        )

        report = agent.research(args.query)

        # Append to research log
        append_research_log(args.query, mode, report)

        # Determine output path
        output_path = args.output
        if output_path is None and mode.auto_save:
            # Deep mode auto-save
            output_path = get_auto_save_path(args.query)

        # Save to file if we have an output path
        if output_path:
            # Create directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report)
            print(f"\n\nReport saved to: {output_path}")
            if args.open:
                subprocess.run(["open", str(output_path)])
        elif args.open:
            print("Warning: --open ignored — no file saved. Use -o to specify output path.",
                  file=sys.stderr)

    except ResearchError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except OSError as e:
        # Handle file system errors (disk full, permissions, etc.)
        print(f"\nFile error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
