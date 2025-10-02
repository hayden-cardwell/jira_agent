# JIRA Agent

Minimal agent that analyzes recently resolved JIRA tickets with an LLM and optionally drafts Confluence documentation updates.

## Features
- Analyze ticket context using few-shot prompts
- Search Confluence for related articles and include context
- Propose new article drafts or updates to existing pages
- Static demo mode using bundled sample ticket data

## Requirements
- Python >= 3.10
- UV (package and environment manager)

## Quickstart
1) Install UV (see `docs/SETUP.md` for platform-specific commands) and verify:
```bash
uv --version
```

2) Install dependencies:
```bash
uv sync
```

3) Configure environment:
```bash
cp env.example .env
# Edit .env with your credentials and settings
```

4) Run the agent:
```bash
uv run main.py
```

### Static demo mode
To run against the included sample ticket instead of live JIRA:
```bash
export USE_STATIC_TICKETS=true
uv run main.py
```

## Configuration
Set the following in `.env` (see `env.example`):

- JIRA_SERVER: Atlassian JIRA base URL (e.g., `https://your-company.atlassian.net`)
- JIRA_EMAIL: Your account email
- JIRA_API_TOKEN: API token for JIRA
- TESTING_MODE: `true|false` (affects polling de-duplication)
- JIRA_PROJECT_KEY: Project key to poll in live mode (e.g., `CSOPS`)

- CONFLUENCE_SERVER: Confluence base URL (same tenant as JIRA for Cloud)
- CONFLUENCE_EMAIL: Your account email
- CONFLUENCE_API_TOKEN: API token for Confluence
- CONFLUENCE_SPACE_KEY: Space key for page operations
- CONFLUENCE_AUTO_SUBMIT: `true|false` to auto-create/update pages

- OPENAI_API_KEY: API key for the LLM provider via the OpenAI SDK
- OPENAI_BASE_URL: Base URL for the API (defaults to OpenAI if unset)
- OPENAI_MODEL: Chat model name (default `gpt-5-mini-2025-08-07`)

- USE_STATIC_TICKETS: `true|false` to process bundled sample ticket(s)
- POLL_INTERVAL_SECONDS: Polling interval for live mode (default 30)
- LOOKBACK_MINUTES: How far back to look for resolved tickets (default 300)

Notes:
- Live mode requires valid JIRA credentials and network access.
- Confluence operations require credentials and a valid `CONFLUENCE_SPACE_KEY`. When `CONFLUENCE_AUTO_SUBMIT=false`, the agent will only log suggestions.

## Project layout
```
.
├── main.py                         # Entry point
├── src/jira_agent
│   ├── core/main.py                # Agent orchestration
│   ├── atlassian/jira.py           # JIRA client wrapper
│   ├── atlassian/confluence.py     # Confluence client wrapper
│   ├── agent/llm.py                # LLM provider abstraction
│   └── prompts/                    # Prompt templates and examples
├── docs/SETUP.md                   # Detailed setup guide
├── env.example                     # Example environment configuration
└── pyproject.toml                  # Dependencies and project config
```

## Example: verify connectivity (optional)
```bash
uv run python -c "from dotenv import load_dotenv; load_dotenv(); print('Env loaded')"
```

If you encounter connection issues, double-check `.env` values and see `docs/SETUP.md` Troubleshooting.


