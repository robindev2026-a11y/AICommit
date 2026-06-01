#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import urllib.request
import urllib.error
import re

# Cloudflare Workers AI Config
DEFAULT_MODEL = "@cf/meta/llama-3-8b-instruct"
API_URL_TEMPLATE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"

def run_cmd(cmd):
    """Helper to run a shell command and return stdout."""
    try:
        res = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: '{cmd}'\nDetails: {e.stderr.strip()}")
        sys.exit(1)

def get_git_diff():
    """Retrieves the staged diff, or unstaged diff if no files are staged."""
    staged_files = run_cmd("git diff --name-only --cached")
    if staged_files:
        print("Analyzing staged changes...")
        return run_cmd("git diff --cached")
    
    unstaged_files = run_cmd("git diff --name-only")
    if unstaged_files:
        print("No staged changes found. Analyzing unstaged changes...")
        response = input("Would you like to stage all changes (git add .) first? (y/n): ").strip().lower()
        if response == 'y':
            run_cmd("git add .")
            print("Staged all changes.")
            return run_cmd("git diff --cached")
        else:
            return run_cmd("git diff")
            
    print("No changes detected in the git repository.")
    sys.exit(0)

def auto_detect_wrangler_token():
    """Tries to extract the oauth_token from the local Wrangler config file."""
    config_path = os.path.expanduser("~/Library/Preferences/.wrangler/config/default.toml")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                for line in f:
                    if line.strip().startswith("oauth_token"):
                        # Extract the token inside double quotes
                        parts = line.split('"')
                        if len(parts) >= 2:
                            return parts[1].strip()
        except Exception as e:
            print(f"Warning: Could not read local wrangler config at {config_path}: {e}")
    return None

def auto_detect_account_id():
    """Runs wrangler whoami to extract the active account ID."""
    print("Auto-detecting Cloudflare Account ID via wrangler...")
    try:
        res = subprocess.run("npx wrangler whoami", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in res.stdout.split("\n"):
            if "Account ID" in line or "Account Name" in line:
                continue
            if "│" in line:
                parts = [p.strip() for p in line.split("│") if p.strip()]
                for part in parts:
                    # Match a 32-character hexadecimal account ID
                    if len(part) == 32 and re.match(r"^[0-9a-fA-F]{32}$", part):
                        return part
    except Exception as e:
        print(f"Warning: Could not query wrangler account: {e}")
    return None

def generate_commit_message_cloudflare(diff, account_id, api_token, model_name):
    """Sends the diff to Cloudflare Workers AI to generate a Conventional Commit message."""
    print(f"Generating commit message via Cloudflare Workers AI (model: {model_name})...")
    
    system_prompt = (
        "You are an expert developer assistant. Generate a concise Conventional Commit message "
        "based on the git diff provided by the user.\n\n"
        "Format:\n"
        "<type>(<scope>): <subject>\n\n"
        "[optional bulleted body]\n\n"
        "Rules:\n"
        "1. <type> must be one of: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.\n"
        "2. <scope> is optional and represents the module/feature area affected.\n"
        "3. <subject> must be in the imperative, present tense, lowercase, and no period at the end.\n"
        "4. Keep the subject line under 72 characters.\n"
        "5. Provide a short bulleted body if there are major changes.\n"
        "6. Return ONLY the final commit message text, with no markdown code blocks or extra explanations."
    )

    url = API_URL_TEMPLATE.format(account_id=account_id, model=model_name)
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Git Diff:\n{diff}"}
        ]
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("success"):
                return res_data["result"]["response"].strip()
            else:
                errors = res_data.get("errors", [])
                err_msg = errors[0].get("message", "Unknown error") if errors else "Unknown error"
                print(f"Cloudflare API error: {err_msg}")
                sys.exit(1)
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            errors = err_body.get("errors", [])
            err_msg = errors[0].get("message", "HTTP status error") if errors else "HTTP status error"
        except Exception:
            err_msg = f"HTTP Error {e.code}"
        print(f"Cloudflare HTTP Error: {err_msg}")
        sys.exit(1)
    except Exception as e:
        print(f"Error generating commit message: {e}")
        sys.exit(1)

def main():
    # 1. Check if git repository
    if not os.path.exists(".git"):
        print("Error: Not a git repository (could not locate .git).")
        sys.exit(1)

    # 2. Get credentials (auto-detected or environment variables)
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or auto_detect_account_id()
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN") or auto_detect_wrangler_token()
    
    if not account_id or not api_token:
        print("\nError: Could not retrieve Cloudflare credentials.")
        print("Please check that wrangler is logged in (`npx wrangler whoami`) or manually export credentials:")
        print("  export CLOUDFLARE_ACCOUNT_ID='your_account_id'")
        print("  export CLOUDFLARE_API_TOKEN='your_api_token'")
        sys.exit(1)

    # Allow custom model overrides
    model_name = os.environ.get("CLOUDFLARE_MODEL", DEFAULT_MODEL)

    # 3. Retrieve git diff
    diff = get_git_diff()
    if not diff:
        print("No diff content to analyze.")
        sys.exit(0)

    # Snipping large diffs
    if len(diff) > 20000:
        print("Warning: Git diff is very large. Snipping to first 20,000 characters...")
        diff = diff[:20000] + "\n\n[Diff truncated...]"

    # 4. Generate message
    commit_msg = generate_commit_message_cloudflare(diff, account_id, api_token, model_name)
    
    # 5. Interactive prompt
    while True:
        print("\n--- Proposed Commit Message ---")
        print(commit_msg)
        print("--------------------------------")
        print("\nOptions:")
        print("[c] Accept and commit")
        print("[p] Accept, commit, and push")
        print("[e] Edit message")
        print("[r] Regenerate")
        print("[q] Abort")
        
        choice = input("Select an option: ").strip().lower()
        
        if choice == 'c' or choice == 'p':
            temp_file = ".git/AI_COMMIT_MSG"
            with open(temp_file, "w") as f:
                f.write(commit_msg)
            
            staged = run_cmd("git diff --name-only --cached")
            if not staged:
                run_cmd("git add .")
                
            print("Committing changes...")
            run_cmd(f"git commit -F {temp_file}")
            os.remove(temp_file)
            print("Commit successful!")
            
            if choice == 'p':
                print("Pushing to remote...")
                branch = run_cmd("git branch --show-current")
                run_cmd(f"git push origin {branch}")
                print("Push successful!")
            break
            
        elif choice == 'e':
            print("Enter your new commit message (Press Enter when done, use empty line or Ctrl+D to finish multiline):")
            lines = []
            while True:
                try:
                    line = input()
                    if line == "" and len(lines) > 0 and lines[-1] == "":
                        break
                    lines.append(line)
                except EOFError:
                    break
            commit_msg = "\n".join(lines).strip()
            
        elif choice == 'r':
            commit_msg = generate_commit_message_cloudflare(diff, account_id, api_token, model_name)
            
        elif choice == 'q':
            print("Commit aborted.")
            sys.exit(0)
            
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
