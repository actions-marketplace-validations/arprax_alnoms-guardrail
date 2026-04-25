import os
import sys
import io
import subprocess
import json
import urllib.request

def get_modified_python_files():
    """Uses Git to find which Python files were changed, excluding internal scripts."""
    event_name = os.environ.get('GITHUB_EVENT_NAME', 'push')
    base_ref = os.environ.get('GITHUB_BASE_REF', '')
    
    # 🛡️ Files to skip (infrastructure and runner itself)
    IGNORE_FILES = ['runner.py', 'setup.py', 'conftest.py']

    try:
        if event_name == 'pull_request' and base_ref:
            subprocess.run(["git", "fetch", "origin", base_ref], capture_output=True, check=True, timeout=30)
            cmd = ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"]
        else:
            cmd = ["git", "diff", "--name-only", "HEAD~1...HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        files = result.stdout.splitlines()
        
        return [
            f for f in files 
            if f.endswith('.py') and not any(ignored in f for ignored in IGNORE_FILES)
        ]
    except Exception as e:
        print(f"⚠️ Git diff failed: {str(e)}", file=sys.stderr)
        return []

def post_github_comment(report):
    """Formats the Alnoms JSON report and posts it as an authoritative GitHub PR comment."""
    token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')
    
    # Extract PR number from the GitHub Event JSON path (safest method)
    pr_number = None
    try:
        event_path = os.environ.get('GITHUB_EVENT_PATH')
        if event_path:
            with open(event_path) as f:
                event_data = json.load(f)
                pr_number = event_data.get('pull_request', {}).get('number')
    except Exception as e:
        print(f"ℹ️ Could not parse PR number: {e}")

    if not token or not repo or not pr_number:
        print("ℹ️ Skipping PR comment: Not a Pull Request or GITHUB_TOKEN missing.")
        return

    issues = report.get("issues", [])
    if not issues:
        body = "### ✅ Alnoms CI Output: Passed\nNo performance regressions detected. Code scales efficiently."
    else:
        rows = ""
        suggestions = ""
        for issue in issues:
            rows += f"| `{issue['file']}` | `{issue['function']}` | Non-linear scaling (likely {issue['complexity']}) |\n"
            if issue.get('suggestion'):
                suggestions += f"- **{issue['function']}**: {issue['suggestion']}\n"
        
        # Fallback if no specific suggestion is provided by the engine
        if not suggestions:
            suggestions = "- Review the flagged functions and optimize data structures or loops to reduce complexity.\n"

        # Use the first flagged file for the copy-paste deep analysis command
        target_file = issues[0]['file']

        body = f"""❌ **Alnoms Blocked This PR**

        ### Performance Regression Detected
        A high-risk performance pattern was identified in this change.

        | File | Function | Detected Behavior |
        | :--- | :--- | :--- |
        {rows}
        ---

        ### 📊 Estimated Impact
        - Input growth 10× → runtime may increase ~20–50×  
        - Degrades performance significantly at scale  
        - Risk of increased compute cost in production  

        ---

        ### ⛔ Decision
        **This PR is blocked due to a potential performance regression.**

        ---

        ### 💡 Suggested Fix
        {suggestions.strip()}

        ---

        ### 🔍 Deep Analysis (Optional)
        For detailed runtime behavior and validation, run the following locally:

        ```bash
        alnoms analyze {target_file} --deep
        ```
        ---
        *Alnoms CI Guardrail · Built by [Arprax](https://arprax.com)*
        """

    # --- API CALL (Inside post_github_comment) ---
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    data = json.dumps({"body": body}).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            if response.getcode() == 201:
                print("💬 Successfully posted authoritative Alnoms Blocked report.")
    except Exception as e:
        print(f"⚠️ Failed to post comment: {str(e)}")

def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("🚀 Booting Alnoms Performance Guardrail...")
    fail_threshold = os.environ.get('FAIL_ON', '')

    changed_files = get_modified_python_files()

    if not changed_files:
        print("✅ No Python files modified. Skipping scan.")
        sys.exit(0)

    print(f"🔍 Found {len(changed_files)} Python files to scan: {changed_files}")

    try:
        print("⚙️ Executing Alnoms Engine...")
        cmd = ["python", "-m", "alnoms", "ci"] + changed_files
        if fail_threshold:
            cmd.extend(["--fail-on", fail_threshold])
            
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        report = json.loads(result.stdout)
        
        post_github_comment(report)
        print(f"✅ Alnoms Engine Success. Scanned {report.get('scanned_files', 0)} files.")
        sys.exit(0)

    except subprocess.CalledProcessError as e:
        print(f"❌ Alnoms Performance Guardrail Triggered!", file=sys.stderr)
        try:
            report = json.loads(e.stdout)
            post_github_comment(report)
            print(json.dumps(report, indent=2), file=sys.stderr)
        except Exception:
            print(e.stderr if e.stderr else "Unknown error in engine execution.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()