# ntulearn-mcp

An MCP server that wraps the Blackboard Learn REST API for NTULearn (NTU Singapore's LMS), letting Claude Desktop interact with your courses, content, announcements, and grades.

## Setup

### 1. Install `uv` (if not already installed)

```powershell
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

### 2. Install dependencies

```bash
cd ntulearn-mcp
uv sync
```

### 3. Get your BbRouter cookie

The server authenticates using your browser session cookie. Here's how to get it:

1. Open **https://ntulearn.ntu.edu.sg** in Chrome or Firefox and log in
2. Open DevTools (`F12`) → **Application** tab → **Cookies** → `https://ntulearn.ntu.edu.sg`
3. Find the cookie named **`BbRouter`**
4. Copy the **Value** field (it looks like `expires:1234567890,...`)
5. Paste it into your `.env` file (see below)

The cookie is valid for your browser session. If you see "BbRouter cookie has expired" errors, repeat these steps.

### 4. Configure `.env`

Copy the example and fill in your cookie:

```bash
cp .env.example .env
```

Edit `.env`:

```env
NTULEARN_BASE_URL=https://ntulearn.ntu.edu.sg
NTULEARN_COOKIE=expires:1234567890,...   # paste your BbRouter value here
NTULEARN_DOWNLOAD_DIR=./downloads
```

### 5. Test it

```bash
uv run ntulearn-mcp
```

The server starts and listens on stdio. You won't see output unless it errors — that's expected.

## Register with Claude Desktop

Add this to your `claude_desktop_config.json` (found at `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "ntulearn": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\YourName\\path\\to\\ntulearn-mcp",
        "run",
        "ntulearn-mcp"
      ],
      "env": {
        "NTULEARN_COOKIE": "expires:1234567890,..."
      }
    }
  }
}
```

Alternatively, keep `NTULEARN_COOKIE` in your `.env` file and omit the `env` block — the server loads `.env` automatically from the project directory.

Restart Claude Desktop after editing the config.

## Available Tools

| Tool | Description |
|------|-------------|
| `list_courses` | List enrolled courses (active by default) |
| `get_course_contents` | Top-level content tree for a course |
| `get_folder_children` | Children of a folder/lesson |
| `search_course_content` | Recursively search a course's content tree |
| `get_file_download_url` | Extract download URL from a content item |
| `download_file` | Download a file to your local downloads folder |
| `get_announcements` | Course announcements |
| `get_gradebook` | Gradebook columns and your scores |

## Manual testing with `mcp dev`

```bash
# Interactive tool inspector in the browser
uv run mcp dev src/ntulearn_mcp/server.py
```

This opens a web UI where you can call each tool and inspect the responses.

## Example prompts for Claude

- "List all my NTULearn courses"
- "Show me the content tree for course _12345_1"
- "Search for 'assignment' in course _12345_1"
- "Download the lecture slides from content item _67890_1 in course _12345_1"
- "What are the latest announcements in my courses?"
- "Show me my grades for course _12345_1"

## Project structure

```
ntulearn-mcp/
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
└── src/
    └── ntulearn_mcp/
        ├── __init__.py
        ├── server.py      # MCP server entrypoint & tool handlers
        ├── client.py      # Blackboard REST API async HTTP client
        ├── parsers.py     # HTML body → download URL extraction
        └── models.py      # Pydantic models (for reference/validation)
```

## Roadmap

- **Phase 2**: Playwright-based auto-authentication (auto-refresh the BbRouter cookie)
- Caching layer (avoid re-fetching unchanged content trees)
- Test suite
