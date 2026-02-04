# Research Agent

A Python CLI tool that performs web searches and generates markdown reports using Claude.

## Features

- Searches the web using DuckDuckGo
- Fetches pages concurrently with async HTTP
- Extracts clean content using trafilatura
- Summarizes content in parallel chunks
- Generates structured markdown reports with citations

## Installation

```bash
git clone https://github.com/SDGuitarist/research-agent.git
cd research-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file with your Anthropic API key:

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

Get an API key at https://console.anthropic.com/settings/keys

## Usage

```bash
# Standard research (default) — 7 sources, ~1000 word report
python main.py "What are the best practices for Python async programming?"

# Quick research — 3 sources, ~300 word report
python main.py "Quick summary of Python decorators" --quick

# Deep research — 10+ sources, 2 search passes, ~2000 word report
python main.py "Comprehensive analysis of Kubernetes security" --deep

# Save to file
python main.py "Kubernetes security basics" -o report.md
```

## Research Modes

| Mode | Sources | Search Passes | Report Length | Cost |
|------|---------|---------------|---------------|------|
| `--quick` | 3 | 1 | ~300 words | ~$0.12 |
| `--standard` | 7 | 1 | ~1000 words | ~$0.20 |
| `--deep` | 10+ | 2 | ~2000 words | ~$0.50 |

**Deep mode** performs a two-pass search: after the first pass, it analyzes the results and generates a refined follow-up query to fill gaps and explore unexplored angles. Reports are automatically saved to the `reports/` folder with timestamped filenames.

```bash
# Deep mode auto-saves to reports/
python main.py "GraphQL vs REST" --deep
# -> reports/2026-02-03_183703056652_graphql_vs_rest.md

# Override auto-save location
python main.py "GraphQL vs REST" --deep -o custom_report.md
```

## How It Works

1. **Search** — Queries DuckDuckGo for relevant sources
2. **Fetch** — Downloads pages concurrently with httpx
3. **Extract** — Pulls clean text using trafilatura (with readability-lxml fallback)
4. **Summarize** — Processes content chunks in parallel with Claude
5. **Synthesize** — Generates a structured report with citations

## Example Output

```markdown
# Best Practices for Python Error Handling

Python error handling is essential for creating robust applications...

## Core Mechanisms

### Try-Except Blocks
The foundation of Python error handling... [Source 1]

## Sources

- [Source 1] Real Python - https://realpython.com/python-exceptions/
- [Source 2] Python Docs - https://docs.python.org/3/tutorial/errors.html
```

## Cost

Costs vary by research mode (using Claude Sonnet for summarization and synthesis):

- **Quick**: ~$0.12 per query
- **Standard**: ~$0.20 per query
- **Deep**: ~$0.50 per query

## License

MIT
