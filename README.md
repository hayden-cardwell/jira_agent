# JIRA Agent

**An AI-powered tool that helps keep your documentation in sync with your issue tracker.**

## What Does This Do?

This tool monitors your JIRA tickets and assists with maintaining Confluence documentation. Here's the workflow:

1. **Monitors JIRA** - Watches for recently resolved tickets in your projects
2. **Analyzes Ticket Content** - Uses AI (Large Language Models) to understand what was fixed or changed
3. **Searches Confluence** - Finds potentially related documentation articles
4. **Suggests Documentation Changes** - Proposes new articles or updates to existing ones

### Why This Matters

When engineers resolve tickets, the knowledge often stays buried in JIRA. This tool helps bridge that gap by:
- **Identifying documentation opportunities** - Surfaces tickets that might warrant documentation updates
- **Assisting with cross-referencing** - Helps connect resolved tickets to existing documentation
- **Supporting knowledge sharing** - Makes it easier to capture fixes and solutions in your knowledge base
- **Flagging update needs** - Identifies when documentation may need attention based on completed work

### Key Features
- **AI-Powered Analysis** - Uses language models to understand ticket context
- **Smart Search** - Attempts to find relevant Confluence articles
- **Flexible Operation** - Can suggest changes or automatically create/update documentation
- **Safe Demo Mode** - Test with sample data before connecting to your live systems

---

## Quick Start

### For Non-Technical Users
This tool runs as a background service that connects to your JIRA and Confluence systems. Once set up, it will:
- Check JIRA periodically for resolved tickets (configurable interval)
- Process newly resolved tickets
- Suggest or create documentation updates (depending on your configuration)

### For Technical Users

#### Requirements
- Python >= 3.10
- UV (modern Python package manager)
- API tokens for JIRA, Confluence, and OpenAI (or compatible LLM)

#### Installation

1) **Install UV** (see `docs/SETUP.md` for platform-specific commands):
```bash
uv --version  # verify installation
```

2) **Install dependencies**:
```bash
uv sync
```

3) **Configure credentials**:
```bash
cp env.example .env
# Edit .env with your API tokens and settings
```

4) **Run the agent**:
```bash
uv run main.py
```

#### Try It Without Setup (Demo Mode)
Test with included sample data before connecting to your systems:
```bash
export USE_STATIC_TICKETS=true
uv run main.py
```

---

## Configuration Options

The agent is configured through a `.env` file (copy from `env.example`). Here's what you can customize:

### Core Settings (Required)

| Setting | What It Does | Example |
|---------|--------------|---------|
| `OPENAI_API_KEY` | API key for the AI model | `sk-proj-...` |
| `JIRA_SERVER` | Your JIRA URL | `https://company.atlassian.net` |
| `JIRA_EMAIL` | Your JIRA login email | `you@company.com` |
| `JIRA_API_TOKEN` | JIRA API token | `ATATT3x...` |
| `JIRA_PROJECT_KEY` | Which project to monitor | `CSOPS` |

### Confluence Integration (Optional)

| Setting | What It Does | Example |
|---------|--------------|---------|
| `CONFLUENCE_SERVER` | Your Confluence URL | `https://company.atlassian.net` |
| `CONFLUENCE_EMAIL` | Your Confluence email | `you@company.com` |
| `CONFLUENCE_API_TOKEN` | Confluence API token | `ATATT3x...` |
| `CONFLUENCE_SPACE_KEY` | Target space for docs | `TECH` |
| `CONFLUENCE_AUTO_SUBMIT` | Auto-create pages (true/false) | `false` (safer!) |

**💡 Tip**: Set `CONFLUENCE_AUTO_SUBMIT=false` initially to review suggestions before they're published.

### Behavior Settings

| Setting | What It Does | Default |
|---------|--------------|---------|
| `POLL_INTERVAL_SECONDS` | How often to check JIRA | `30` |
| `LOOKBACK_MINUTES` | How far back to scan for tickets | `300` (5 hours) |
| `TESTING_MODE` | Re-process same tickets (for testing) | `false` |
| `USE_STATIC_TICKETS` | Demo mode with sample data | `false` |

### Advanced Settings (Optional)

| Setting | What It Does | Default |
|---------|--------------|---------|
| `OPENAI_BASE_URL` | Use alternative LLM providers | OpenAI API |
| `OPENAI_MODEL` | Which AI model to use | `gpt-4.1-2025-04-14` |
| `PROMPT_TICKET_ANALYZER` | Custom analysis prompt | `ticket_analyzer.prompt` |
| `PROMPT_CONFLUENCE_SEARCH` | Custom search prompt | `confluence_search.prompt` |

---

## How It Works (Technical Overview)

### Architecture

```
JIRA Tickets → AI Analysis → Confluence Documentation
     ↓             ↓                    ↓
  Monitor      Understand          Update/Create
  Changes      Context             Knowledge Base
```

### Workflow

1. **Polling** - Agent checks JIRA periodically for recently resolved tickets
2. **Context Gathering** - Retrieves full ticket details (summary, description, comments, resolution)
3. **Confluence Search** - AI generates search queries to find potentially related documentation
4. **Analysis** - LLM analyzes ticket + related docs to determine if updates may be needed
5. **Action** - Either logs suggestions or (if configured) creates/updates Confluence pages

### Project Structure

```
.
├── main.py                         # Entry point
├── src/jira_agent/
│   ├── core/main.py                # Agent orchestration and workflow
│   ├── atlassian/
│   │   ├── jira.py                 # JIRA API integration
│   │   └── confluence.py           # Confluence API integration
│   ├── agent/llm.py                # AI/LLM provider abstraction
│   ├── prompts/templates.py        # Prompt loading and formatting
│   └── data/static_tickets/        # Sample data for demo mode
├── prompts/                        # Customizable AI prompts
│   ├── ticket_analyzer.prompt      # How to analyze tickets
│   └── confluence_search.prompt    # How to search for docs
├── docs/SETUP.md                   # Detailed setup instructions
└── pyproject.toml                  # Python dependencies
```

---

## Customization

### Adjusting AI Behavior

The agent's intelligence comes from carefully crafted prompts in the `prompts/` directory:

- **`ticket_analyzer.prompt`** - Controls how tickets are analyzed and what documentation changes are suggested
- **`confluence_search.prompt`** - Determines how the agent searches for relevant documentation

You can edit these files directly to:
- Change the analysis criteria
- Adjust the tone of generated content
- Add domain-specific instructions
- Include few-shot examples for better results

### Using Alternative AI Models

The agent supports any OpenAI-compatible API:
- OpenAI GPT models (default)
- Azure OpenAI
- Anthropic Claude (via compatibility layers)
- Self-hosted models (Ollama, vLLM, etc.)

Just configure `OPENAI_BASE_URL` and `OPENAI_MODEL` in your `.env` file.

---

## Troubleshooting

### Connection Issues
```bash
# Verify environment variables loaded correctly
uv run python -c "from dotenv import load_dotenv; load_dotenv(); print('Env loaded')"
```

### Common Problems

**"Failed to connect to JIRA"**
- Double-check your `JIRA_SERVER` URL (include `https://`)
- Verify API token has proper permissions
- Ensure your IP isn't blocked

**"No tickets found"**
- Increase `LOOKBACK_MINUTES` to scan further back
- Verify `JIRA_PROJECT_KEY` matches your project
- Check that tickets are actually marked as "resolved"

**"Confluence page not found"**
- Ensure `CONFLUENCE_SPACE_KEY` is correct
- Verify API token has write access to the space
- Check page titles match exactly (case-sensitive)

For detailed troubleshooting, see `docs/SETUP.md`.

---

## Use Cases

### For Engineering Teams
- Help document bug fixes and their root causes
- Track workarounds and solutions in your knowledge base
- Assist in keeping runbooks and troubleshooting guides current

### For Support Teams
- Surface customer issues that may need documentation
- Help build a searchable database of solutions
- Potentially reduce repetitive support tickets

### For Product Teams
- Help document feature changes and updates
- Assist in maintaining product documentation
- Track technical decisions and their rationale

---

## Security & Privacy

- **API Tokens**: Stored locally in `.env`, never committed to version control
- **Data**: Ticket content is sent to your configured LLM provider for analysis
- **Permissions**: Respects JIRA and Confluence permissions of the configured API user
- **Safe Mode**: `CONFLUENCE_AUTO_SUBMIT=false` allows review before publishing

---

## Contributing & Support

This is a work-in-progress tool. For questions, issues, or contributions:
- Review the code in `src/jira_agent/`
- Check `docs/SETUP.md` for detailed documentation
- Test changes in `USE_STATIC_TICKETS` mode before production

---

## License

See the LICENSE file in this repository.


