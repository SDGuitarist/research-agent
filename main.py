#!/usr/bin/env python3
"""CLI for the research agent."""

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from research_agent import ResearchAgent
from research_agent.errors import ResearchError
from research_agent.modes import ResearchMode


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


def get_auto_save_path(query: str) -> Path:
    """Generate auto-save path for deep mode reports."""
    reports_dir = Path("reports")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_query = sanitize_filename(query)
    filename = f"{timestamp}_{safe_query}.md"
    return reports_dir / filename


def main():
    # Load environment variables from .env file
    load_dotenv()

    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Research agent that searches the web and generates markdown reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Research Modes:
  --quick     Fast research: 3 sources, ~300 word report (~$0.12)
  --standard  Balanced research: 7 sources, ~1000 word report (~$0.20) [default]
  --deep      Thorough research: 10+ sources, 2 search passes, ~2000 word report (~$0.50)
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
        help="The research query",
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
        help="Standard mode: 7 sources, ~1000 words (~$0.20) [default]",
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
        help="Output file path (default: stdout, or auto for --deep)",
    )

    args = parser.parse_args()

    # Determine mode
    if args.quick:
        mode = ResearchMode.quick()
    elif args.deep:
        mode = ResearchMode.deep()
    else:
        mode = ResearchMode.standard()

    # Warn if --max-sources used with mode flag
    if args.max_sources is not None and (args.quick or args.deep or args.standard):
        print(f"Note: --max-sources ignored when using --{mode.name} (uses {mode.max_sources} sources)",
              file=sys.stderr)

    try:
        agent = ResearchAgent(
            mode=mode,
            max_sources=args.max_sources if not (args.quick or args.deep or args.standard) else None,
        )

        report = agent.research(args.query)

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
