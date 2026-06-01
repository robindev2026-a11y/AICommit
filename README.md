# AI Commit - Zero-Dependency Git Assistant

AI Commit is a standalone, lightweight CLI tool that automatically writes structured **Conventional Commit** messages based on your local `git diff` using **Cloudflare Workers AI**.

It requires **zero external python dependencies** (no `pip install` required) and automatically integrates with your active local **Wrangler** login for seamless authentication.

---

## Features

- **Auto-Staging Prompt:** Checks for staged changes. If none are found, prompts you to auto-stage (`git add .`) or analyze unstaged work.
- **Zero-Dependency REST Client:** Uses Python's standard `urllib` package to communicate with Cloudflare's API—no package installs needed.
- **Auto-Credentials Parsing:** Automatically reads your active Cloudflare Account ID and OAuth token from `~/Library/Preferences/.wrangler/config/default.toml` if you are logged in.
- **Conventional Commits:** Enforces standard semantic conventions (`feat:`, `fix:`, `refactor:`, `docs:`, etc.) for clean project histories.
- **Interactive Review CLI:** Let's you accept, edit, regenerate, or push changes directly from a simple console prompt.

---

## Installation & Setup

### 1. Save the Script
Place `ai_commit.py` in a directory of your choice (e.g., `~/Developer/AICommit/`).

### 2. Make it Executable
Open your terminal and make the script runnable:
```bash
chmod +x /path/to/ai_commit.py
```

### 3. Connect Cloudflare Wrangler (OAuth)
Ensure your terminal is authenticated with your Cloudflare account. Simply run:
```bash
npx wrangler login
```
This stores your OAuth credentials locally. `ai_commit.py` will read these files automatically.

*Optional fallback:* If Wrangler is not installed or you are in a CI/CD environment, you can export the variables manually in your shell:
```bash
export CLOUDFLARE_ACCOUNT_ID="your-account-id"
export CLOUDFLARE_API_TOKEN="your-api-token"
```

---

## How to Use

1. Navigate to any git repository on your machine:
   ```bash
   cd /path/to/your/project
   ```

2. Run the script using its path:
   ```bash
   ~/Developer/AICommit/ai_commit.py
   ```

3. Choose from the interactive menu:
   - `[c]` **Accept and commit:** Commits the change with the generated message.
   - `[p]` **Commit and push:** Commits and pushes the change to your active branch.
   - `[e]` **Edit message:** Allows you to rewrite the generated commit message manually in the terminal.
   - `[r]` **Regenerate:** Sends the diff back to the model to try another generation.
   - `[q]` **Abort:** Cancels the commit entirely.

---

## Advanced Configurations

### Changing the LLM Model
By default, the script uses `@cf/meta/llama-3-8b-instruct`. You can override this to any other supported Cloudflare Workers AI model by exporting the `CLOUDFLARE_MODEL` variable:
```bash
export CLOUDFLARE_MODEL="@cf/qwen/qwen1.5-14b-chat"
```
