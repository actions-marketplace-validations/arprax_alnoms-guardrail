import os
import sys
import subprocess
import json
import urllib.request

def post_github_comment(report):
    """Formats the Alnoms JSON report and posts it as a GitHub PR comment."""
    token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')
    pr_number = os.environ.get('GITHUB_EVENT_NAME') == 'pull_request' and os.environ.get('GITHUB_REF_NAME').split('/')[0]
    
    # Try to get PR number from the event path if the above fails
    if not pr_number or not pr_number.isdigit():
        try:
            with open(os.environ.get('GITHUB_EVENT_PATH')) as f:
                event_data = json.load(f)
                pr_number = event_data.get('pull_request', {}).get('number')
        except:
            pr_number = None

    if not token or not repo or not pr_number:
        print("ℹ️ Skipping PR comment: Not a Pull Request or GITHUB_TOKEN missing.")
        return

    # --- FORMAT THE MARKDOWN ---
    issues = report.get("issues", [])
    if not issues:
        body = "### ✅ Alnoms Performance Guardrail: Passed\nNo performance bottlenecks detected. Code is clean and scales efficiently."
    else:
        rows = ""
        for issue in issues:
            rows += f"| `{issue['file']}` | `{issue['function']}` | **{issue['complexity']}** | {issue['issue']} |\n"
        
        body = f"""### ❌ Alnoms Performance Guardrail: Bottlenecks Detected

The following performance risks were identified in this Pull Request:

| File | Function | Complexity | Issue |
| :--- | :--- | :--- | :--- |
{rows}

**💡 Recommendation:** Check the local logs or run `alnoms analyze <file> --deep` to investigate and fix these issues before merging.

---
*Built by [Arprax](https://arprax.com)*
"""

    # --- API CALL ---
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
                print("💬 Successfully posted Alnoms report to the Pull Request.")
    except Exception as e:
        print(f"⚠️ Failed to post comment: {str(e)}")

# ... (Keep your get_modified_python_files() function as it is) ...

def main():
    print("🚀 Booting Alnoms Performance Guardrail...")
    fail_threshold = os.environ.get('FAIL_ON', '')
    changed_files = get_modified_python_files()
    
    if not changed_files:
        print("✅ No Python files modified. Skipping.")
        sys.exit(0)

    try:
        cmd = ["python", "-m", "alnoms", "ci"] + changed_files
        if fail_threshold:
            cmd.extend(["--fail-on", fail_threshold])
            
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        report = json.loads(result.stdout)
        
        # 💬 POST THE COMMENT (Success Path)
        post_github_comment(report)
        
        print(f"✅ Alnoms Engine Success. Scanned {report.get('scanned_files', 0)} files.")
        sys.exit(0)

    except subprocess.CalledProcessError as e:
        print(f"❌ Alnoms Performance Guardrail Triggered!", file=sys.stderr)
        try:
            report = json.loads(e.stdout)
            # 💬 POST THE COMMENT (Failure Path)
            post_github_comment(report)
        except:
            print(e.stderr if e.stderr else "Unknown error.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()