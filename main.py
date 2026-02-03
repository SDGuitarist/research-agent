#!/usr/bin/env python3
"""CLI for the research agent."""

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from research_agent import ResearchAgent
from research_agent.errors import ResearchError


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
Examples:
  python main.py "What are Python async best practices?"
  python main.py "Compare React vs Vue in 2024" --max-sources 10
  python main.py "Kubernetes security" -o report.md
        """,
    )
    parser.add_argument(
        "query",
        help="The research query",
    )
    parser.add_argument(
        "--max-sources", "-n",
        type=int,
        default=5,
        help="Maximum number of sources to research (default: 5)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file path (default: print to stdout)",
    )

    args = parser.parse_args()

    try:
        agent = ResearchAgent(
            max_sources=args.max_sources,
        )

        report = agent.research(args.query)

        if args.output:
            args.output.write_text(report)
            print(f"\nReport saved to: {args.output}")
        else:
            print("\n" + "=" * 60)
            print("RESEARCH REPORT")
            print("=" * 60 + "\n")
            print(report)

    except ResearchError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
