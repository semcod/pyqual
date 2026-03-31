# AI Fix Tools

pyqual's fix stage accepts **any shell command** via `run:`. This means every AI coding agent with a CLI can be plugged in as the auto-fix engine. When quality gates fail (`when: metrics_fail`), pyqual passes the detected errors to the AI tool, which edits files in-place, and the pipeline re-checks gates in the next iteration.

## How It Works

```
┌─────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐    ┌────────┐
│ analyze │───▶│ validate │───▶│  test   │───▶│  gates   │───▶│  pass? │
└─────────┘    └──────────┘    └─────────┘    └──────────┘    └────┬───┘
                                                                   │
                                              ┌────────┐     no   │  yes
                                              │ verify │◀─────────┤─────▶ done
                                              └────┬───┘          │
                                                   │         ┌────▼────┐
                                                   └────────▶│ AI fix  │
                                                             └─────────┘
```

1. **prefact** analyzes failures → writes `.pyqual/errors.json` and `TODO.md`
2. **AI fix stage** reads errors, edits code in-place
3. **verify** re-validates; pipeline loops up to `max_iterations`

All examples below follow the same pattern — only the `run:` command changes.

---

## Claude Code

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) — Anthropic's agentic coding CLI. Supports non-interactive mode with `-p` (print/prompt).

### Install & Auth

```bash
npm install -g @anthropic-ai/claude-code
claude auth login
# or set ANTHROPIC_API_KEY in .env
```

### pyqual.yaml

```yaml
pipeline:
  name: claude-code-fix
  metrics:
    cc_max: 15
    coverage_min: 80
    vallm_pass_min: 90

  stages:
    - name: analyze
      tool: code2llm
      when: first_iteration

    - name: validate
      tool: vallm

    - name: test
      tool: pytest

    - name: prefact
      tool: prefact
      when: metrics_fail
      optional: true

    - name: fix
      run: |
        PROMPT="Fix all quality gate failures in this Python project."
        [ -f .pyqual/errors.json ] && PROMPT="$PROMPT\n\nGate errors:\n$(cat .pyqual/errors.json)"
        [ -f TODO.md ] && PROMPT="$PROMPT\n\nTODO items:\n$(cat TODO.md)"
        claude -p "$PROMPT" \
          --model sonnet \
          --allowedTools "Edit,Read,Write,Bash(git diff),Bash(python),Bash(pytest)" \
          --output-format text
      when: metrics_fail
      timeout: 1800

    - name: verify
      tool: pytest
      when: after_fix

  loop:
    max_iterations: 3
    on_fail: report

  env:
    ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
```

### Key Flags

| Flag | Purpose |
|------|---------|
| `-p "..."` | Non-interactive prompt mode (required for CI) |
| `--model` | Model selection (`sonnet`, `opus`, or the alias supported by your Claude Code account) |
| `--allowedTools` | Restrict which tools Claude Code can use |
| `--output-format text` | Machine-friendly output |
| `--max-turns N` | Limit agentic turns (cost control) |

### Variant: Focused File Fix

```yaml
    - name: fix
      run: |
        claude -p "Fix the failing tests and quality issues in $(cat .pyqual/errors.json)" \
          --model sonnet \
          --allowedTools "Edit,Read,Bash(pytest)" \
          --max-turns 10 \
          --output-format text
      when: metrics_fail
      timeout: 900
```

### Fallback Behavior

If Claude Code exits non-zero or hits a usage limit, the example `pyqual.yaml`
falls back to `llx fix . --apply --errors .pyqual/errors.json --verbose` so the
pipeline still attempts an automated repair instead of failing immediately.

---

## OpenAI Codex CLI

[Codex CLI](https://github.com/openai/codex) — OpenAI's agentic coding CLI. Auto-edits files in `full-auto` mode.

### Install & Auth

```bash
npm install -g @openai/codex
# Set OPENAI_API_KEY in .env
```

### pyqual.yaml

```yaml
pipeline:
  name: codex-fix
  metrics:
    cc_max: 15
    coverage_min: 80

  stages:
    - name: validate
      tool: vallm

    - name: test
      tool: pytest

    - name: prefact
      tool: prefact
      when: metrics_fail
      optional: true

    - name: fix
      run: |
        PROMPT="Fix all quality issues in this project."
        [ -f .pyqual/errors.json ] && PROMPT="$PROMPT Errors: $(cat .pyqual/errors.json)"
        [ -f TODO.md ] && PROMPT="$PROMPT TODO: $(cat TODO.md)"
        codex --approval-mode full-auto \
          --model o4-mini \
          --quiet \
          "$PROMPT"
      when: metrics_fail
      timeout: 1800

    - name: verify
      tool: pytest
      when: after_fix

  loop:
    max_iterations: 3
    on_fail: report

  env:
    OPENAI_API_KEY: ${OPENAI_API_KEY}
```

### Key Flags

| Flag | Purpose |
|------|---------|
| `--approval-mode full-auto` | No human approval needed (CI mode) |
| `--model` | Model selection (`o4-mini`, `o3`, `gpt-4.1`) |
| `--quiet` | Suppress interactive UI |

---

## Google Gemini CLI

[Gemini CLI](https://github.com/google-gemini/gemini-cli) — Google's agentic coding CLI with tool use.

### Install & Auth

```bash
npm install -g @anthropic-ai/gemini-cli
# or: go install github.com/google-gemini/gemini-cli@latest
# Set GEMINI_API_KEY in .env
```

### pyqual.yaml

```yaml
pipeline:
  name: gemini-fix
  metrics:
    cc_max: 15
    coverage_min: 80

  stages:
    - name: validate
      tool: vallm

    - name: test
      tool: pytest

    - name: prefact
      tool: prefact
      when: metrics_fail
      optional: true

    - name: fix
      run: |
        PROMPT="Fix all quality gate failures."
        [ -f .pyqual/errors.json ] && PROMPT="$PROMPT\n\nErrors:\n$(cat .pyqual/errors.json)"
        [ -f TODO.md ] && PROMPT="$PROMPT\n\nTODO:\n$(cat TODO.md)"
        echo "$PROMPT" | gemini -y \
          --model gemini-2.5-pro
      when: metrics_fail
      timeout: 1800

    - name: verify
      tool: pytest
      when: after_fix

  loop:
    max_iterations: 3

  env:
    GEMINI_API_KEY: ${GEMINI_API_KEY}
```

### Key Flags

| Flag | Purpose |
|------|---------|
| `-y` | Auto-approve all tool calls (non-interactive / CI mode) |
| `--model` | Model selection (`gemini-2.5-pro`, `gemini-2.5-flash`) |
| `--sandbox` | Run in sandboxed environment |

---

## aider

[aider](https://aider.chat) — AI pair programming in your terminal. Supports many LLM backends.

### Install & Auth

```bash
pip install aider-chat
# Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or OPENROUTER_API_KEY in .env
```

### pyqual.yaml (built-in preset)

```yaml
pipeline:
  name: aider-fix
  metrics:
    cc_max: 15
    coverage_min: 80

  stages:
    - name: validate
      tool: vallm

    - name: test
      tool: pytest

    - name: prefact
      tool: prefact
      when: metrics_fail
      optional: true

    - name: fix
      tool: aider
      when: metrics_fail
      timeout: 1800

    - name: verify
      tool: pytest
      when: after_fix

  loop:
    max_iterations: 3

  env:
    ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
```

### pyqual.yaml (custom command)

```yaml
    - name: fix
      run: |
        ERRORS=""
        [ -f .pyqual/errors.json ] && ERRORS="$(cat .pyqual/errors.json)"
        [ -f TODO.md ] && ERRORS="$ERRORS\n$(cat TODO.md)"
        aider --yes-always \
          --model anthropic/claude-sonnet-4-5-20250514 \
          --no-auto-commits \
          --message "Fix these quality issues: $ERRORS"
      when: metrics_fail
      timeout: 1800
```

### Key Flags

| Flag | Purpose |
|------|---------|
| `--yes-always` | Auto-approve all changes (CI mode) |
| `--model` | Any litellm-compatible model string |
| `--no-auto-commits` | Let pyqual control git commits |
| `--message "..."` | Non-interactive prompt |
| `--file path` | Scope to specific files |

### Variant: With OpenRouter

```yaml
    - name: fix
      run: |
        aider --yes-always \
          --model openrouter/qwen/qwen3-coder-next \
          --no-auto-commits \
          --message "Fix: $(cat .pyqual/errors.json 2>/dev/null || cat TODO.md)"
      when: metrics_fail

  env:
    OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
```

---

## llx fix

[llx](https://pypi.org/project/llx/) — pyqual's native AI fix tool. Uses aider under the hood with MCP orchestration.

### Install

```bash
pip install llx[full]
```

### pyqual.yaml (built-in preset)

```yaml
    - name: fix
      tool: llx-fix
      when: metrics_fail
      timeout: 1800
```

### pyqual.yaml (custom command)

```yaml
    - name: fix
      run: llx fix . --apply --errors .pyqual/errors.json --verbose
      when: metrics_fail
      timeout: 1800
```

### pyqual.yaml (MCP service)

```yaml
    - name: fix
      run: >
        pyqual mcp-fix
          --workdir .
          --issues .pyqual/errors.json
          --output .pyqual/llx_mcp.json
          --endpoint http://localhost:8000/sse
      when: metrics_fail
      timeout: 1800

  env:
    PYQUAL_LLX_MCP_URL: http://localhost:8000/sse
```

### Key Flags

| Flag | Purpose |
|------|---------|
| `--apply` | Apply fixes in-place (no dry-run) |
| `--errors <path>` | Path to gate failure JSON |
| `--verbose` | Show detailed fix progress |
| `--model <model>` | Override model selection |
| `--tier balanced\|fast\|quality` | Trade-off speed vs quality |

---

## Cursor CLI (Background Agent)

[Cursor](https://docs.cursor.com/cli) — AI-first IDE with a CLI mode for headless usage.

### pyqual.yaml

```yaml
    - name: fix
      run: |
        PROMPT="Fix all quality gate failures."
        [ -f .pyqual/errors.json ] && PROMPT="$PROMPT Errors: $(cat .pyqual/errors.json)"
        cursor agent "$PROMPT"
      when: metrics_fail
      timeout: 1800
```

> **Note:** Cursor CLI agent mode requires an active Cursor subscription and may require the IDE to be running. Verify headless support for your version.

---

## Windsurf CLI

[Windsurf](https://docs.windsurf.com/windsurf/cli) — Agentic IDE with shell invocation.

### pyqual.yaml

```yaml
    - name: fix
      run: |
        PROMPT="Fix all quality gate failures."
        [ -f .pyqual/errors.json ] && PROMPT="$PROMPT Errors: $(cat .pyqual/errors.json)"
        windsurf --prompt "$PROMPT" --headless
      when: metrics_fail
      timeout: 1800
```

> **Note:** Windsurf headless mode availability depends on your subscription tier.

---

## Cline (via CLI wrapper)

[Cline](https://github.com/cline/cline) — Autonomous coding agent (VS Code extension). Can be invoked headlessly via the `cline` CLI.

### pyqual.yaml

```yaml
    - name: fix
      run: |
        PROMPT="Fix all quality gate failures in this project."
        [ -f .pyqual/errors.json ] && PROMPT="$PROMPT\n$(cat .pyqual/errors.json)"
        cline --task "$PROMPT" \
          --model claude-sonnet-4-5-20250514 \
          --auto-approve
      when: metrics_fail
      timeout: 1800
```

---

## Generic Pattern: Any LLM CLI

If your AI tool has a CLI that can edit files, it works with pyqual. The pattern is always:

```yaml
    - name: fix
      run: |
        # 1. Build prompt from pyqual error artifacts
        PROMPT="Fix quality issues in this project."
        [ -f .pyqual/errors.json ] && PROMPT="$PROMPT\nErrors:\n$(cat .pyqual/errors.json)"
        [ -f TODO.md ] && PROMPT="$PROMPT\nTODO:\n$(cat TODO.md)"

        # 2. Invoke AI tool in non-interactive mode
        your-ai-tool --auto --no-confirm --message "$PROMPT"
      when: metrics_fail
      timeout: 1800
```

### Requirements for Any AI Fix Tool

| Requirement | Why |
|-------------|-----|
| **Non-interactive mode** | pyqual runs in a pipeline — no human to approve |
| **File editing capability** | The tool must write changes to disk |
| **Deterministic exit code** | 0 = success, non-zero = failure |
| **Stdin/file prompt input** | Must accept error context from pyqual artifacts |

---

## Comparison Table

| Tool | Install | Model | Non-interactive Flag | Auto-approve | Cost |
|------|---------|-------|---------------------|--------------|------|
| **Claude Code** | `npm i -g @anthropic-ai/claude-code` | Sonnet 4.5, Opus 4 | `-p "..."` | `--allowedTools` | API usage |
| **Codex CLI** | `npm i -g @openai/codex` | o4-mini, o3, GPT-4.1 | positional arg | `--approval-mode full-auto` | API usage |
| **Gemini CLI** | `npm i -g @google/gemini-cli` | Gemini 2.5 Pro/Flash | pipe to stdin | `-y` | API usage |
| **aider** | `pip install aider-chat` | Any (litellm) | `--message "..."` | `--yes-always` | API usage |
| **llx fix** | `pip install llx[full]` | Configurable | `--apply` | Built-in | API usage |
| **Cursor** | IDE install | Varies | `cursor agent "..."` | Subscription | Subscription |
| **Windsurf** | IDE install | Varies | `--prompt --headless` | Subscription | Subscription |
| **Cline** | VS Code ext / CLI | Any | `--task "..."` | `--auto-approve` | API usage |

---

## Tips

### Cost Control

```yaml
    - name: fix
      run: |
        claude -p "$(cat .pyqual/errors.json)" \
          --model claude-sonnet-4-5-20250514 \
          --max-turns 5 \
          --output-format text
      when: metrics_fail
      timeout: 600    # short timeout = cost cap
```

### Scope to Changed Files Only

```yaml
    - name: fix
      run: |
        FILES=$(git diff --name-only HEAD~1 -- '*.py' | tr '\n' ' ')
        [ -z "$FILES" ] && exit 0
        aider --yes-always --model anthropic/claude-sonnet-4-5-20250514 \
          --no-auto-commits --file $FILES \
          --message "Fix quality issues: $(cat .pyqual/errors.json)"
      when: metrics_fail
```

### Chain Two Tools (Fallback)

```yaml
    - name: fix_quick
      run: |
        aider --yes-always --model openrouter/qwen/qwen3-coder-next \
          --no-auto-commits \
          --message "Fix: $(cat .pyqual/errors.json 2>/dev/null || echo 'see TODO.md')"
      when: metrics_fail
      timeout: 600

    - name: fix_heavy
      run: |
        claude -p "Fix remaining quality failures: $(cat .pyqual/errors.json)" \
          --model claude-sonnet-4-5-20250514 \
          --output-format text
      when: metrics_fail    # runs only if gates still fail after fix_quick
      timeout: 1800
```

### Dry-Run Testing

Test any AI fix command manually before putting it in the pipeline:

```bash
# See what errors pyqual would pass to the fix stage
pyqual run --max-iterations 1
cat .pyqual/errors.json

# Test your fix command manually
claude -p "Fix: $(cat .pyqual/errors.json)" --model claude-sonnet-4-5-20250514 --output-format text
```

---

## API Keys & Token Storage

Every AI fix tool requires an API key. pyqual reads keys from **environment variables**, which can be set via `.env`, `pyqual.yaml env:`, or CI secrets.

### Where Tokens Are Stored

| Method | File / Location | When to Use |
|--------|-----------------|-------------|
| `.env` file | `.env` in project root | Local development |
| `pyqual.yaml env:` | `env:` section with `${VAR}` refs | Reference (never hardcode keys!) |
| CI secrets | GitHub Settings → Secrets | GitHub Actions / CI |
| Shell export | `export ANTHROPIC_API_KEY=...` | One-off terminal sessions |
| `claude auth login` | `~/.claude/` (OAuth session) | Local Claude Code (no API key needed) |

### Required Keys Per Tool

| Tool | Environment Variable | How to Get |
|------|---------------------|------------|
| **Claude Code** | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) → API Keys |
| **Codex CLI** | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/api-keys) |
| **Gemini CLI** | `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/apikey) |
| **aider** | Any of the above, or `OPENROUTER_API_KEY` | Depends on model backend |
| **llx fix** | `OPENROUTER_API_KEY` (default) | [openrouter.ai](https://openrouter.ai/keys) |

### Local Setup (.env)

```bash
# Create .env in project root (gitignored!)
cat >> .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENROUTER_API_KEY=sk-or-v1-...
LLM_MODEL=openrouter/qwen/qwen3-coder-next
EOF

# Verify .env is in .gitignore
grep -q '.env' .gitignore || echo '.env' >> .gitignore
```

pyqual automatically loads `.env` via `python-dotenv` at startup.

### Claude Code: OAuth vs API Key

Claude Code supports **two auth methods**:

**1. OAuth login (interactive, local dev):**
```bash
claude auth login
# Opens browser, stores session in ~/.claude/
# No API key needed — uses your Anthropic account/subscription
```

**2. API key (headless, CI):**
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
claude -p "hello" --output-format text
# Uses API key directly — required for CI/GitHub Actions
```

For `pyqual run` in CI, you **must** use the API key method.

### GitHub Actions Setup

**Step 1: Add secrets to your repository:**

GitHub repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret name | Value |
|-------------|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` (for llx fallback) |

**Step 2: Reference in workflow:**

```yaml
# .github/workflows/pyqual.yml
name: pyqual quality gates
on: [push, pull_request]

jobs:
  quality-loop:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
      with: {fetch-depth: 0}

    - uses: actions/setup-python@v5
      with: {python-version: "3.11"}

    - uses: actions/setup-node@v4
      with: {node-version: "20"}

    - name: Install pyqual + tools
      run: |
        pip install pyqual[all]
        npm install -g @anthropic-ai/claude-code

    - name: Run quality gate loop
      run: pyqual run --config pyqual.yaml
      env:
        LLM_MODEL: ${{ secrets.LLM_MODEL || 'openrouter/qwen/qwen3-coder-next' }}
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}

    - name: Upload metrics
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: pyqual-metrics
        path: .pyqual/
```

### pyqual.yaml env: Section

Reference environment variables with `${VAR}` syntax — **never hardcode keys**:

```yaml
  env:
    LLM_MODEL: openrouter/qwen/qwen3-coder-next
    # These read from shell environment / .env / CI secrets at runtime:
    ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
```

---

## Setup Stage: Auto-Install Dependencies

Add a `setup` stage to `pyqual.yaml` that checks and installs all tools the pipeline needs. Runs once on the first iteration.

```yaml
  stages:
    # Verify/install all tool dependencies before pipeline starts
    - name: setup
      run: |
        set -e
        echo "=== pyqual dependency check ==="
        # Python tools (pip)
        for pkg in code2llm vallm prefact llx pytest-cov goal; do
          if python -m pip show "$pkg" >/dev/null 2>&1; then
            echo "  ✓ $pkg"
          else
            echo "  ✗ $pkg — installing…"
            pip install -q "$pkg" || echo "  ⚠ $pkg install failed (optional)"
          fi
        done
        # Node tools (claude)
        if command -v claude >/dev/null 2>&1; then
          echo "  ✓ claude $(claude --version 2>/dev/null)"
        else
          echo "  ✗ claude — installing…"
          npm install -g --prefix="$HOME/.local" @anthropic-ai/claude-code 2>/dev/null \
            && echo "  ✓ claude installed" \
            || echo "  ⚠ claude install failed (fix stage will use llx fallback)"
        fi
        # Verify API keys
        if [ -n "$ANTHROPIC_API_KEY" ]; then
          echo "  ✓ ANTHROPIC_API_KEY is set"
        else
          echo "  ⚠ ANTHROPIC_API_KEY not set — Claude Code fix stage will not work"
        fi
        echo "=== setup done ==="
      when: first_iteration
      timeout: 300

    - name: analyze
      tool: code2llm
      when: first_iteration
    # ... rest of pipeline
```

This ensures that even a bare CI runner or a fresh developer checkout has everything needed to run the full quality loop.
