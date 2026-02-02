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
# Basic usage
python main.py "What are the best practices for Python async programming?"

# Save to file
python main.py "Kubernetes security basics" -o report.md

# Use more sources
python main.py "React vs Vue comparison" --max-sources 10
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

~$0.10-0.15 per query using Claude Sonnet for both summarization and synthesis.

## License

MIT
