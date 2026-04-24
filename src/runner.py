import os
import sys
import subprocess
import json
import urllib.request

def get_modified_python_files():
    """Uses Git to find which Python files were changed, excluding internal scripts."""
    event_name = os.environ.get('GITHUB_EVENT_NAME', 'push')
    base_ref = os.environ.get('GITHUB_BASE_REF', '')
    
    # 🛡️ LIST FILES TO IGNORE
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
    """Formats the Alnoms JSON report and posts it as a GitHub PR comment."""
    token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')
    
    # Try to extract PR number from GITHUB_EVENT_PATH (most reliable)
    pr_number = None
    try:
        event_path = os.environ.get('GITHUB_EVENT_PATH')
        if event_path:
            with open(event_path) as f:
                event_data = json.load(f)
                pr_number = event_data.get('pull_request', {}).get('number')
    except Exception as e:
        print(f"ℹ️ Could not parse PR number from event path: {e}")

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

def main():
    print("🚀 Booting Alnoms Performance Guardrail...")
    
    fail_threshold = os.environ.get('FAIL_ON', '')
    print(f"📊 Threshold: {fail_threshold if fail_threshold else 'Warn Only'}")
    
    changed_files = get_modified_python_files()
    
    if not changed_files:
        print("✅ No Python files modified in this commit. Skipping Alnoms scan.")
        sys.exit(0)

    print(f"🔍 Found {len(changed_files)} Python files to scan: {changed_files}")
    
    try:
        print("⚙️ Executing Alnoms Engine...")
        cmd = ["python", "-m", "alnoms", "ci"] + changed_files
        if fail_threshold:
            cmd.extend(["--fail-on", fail_threshold])
            
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        report = json.loads(result.stdout)
        
        # Post comment to GitHub if on a PR
        post_github_comment(report)
        
        print(f"✅ Alnoms Engine Success. Scanned {report.get('scanned_files', 0)} files.")
        if report.get("issues"):
            print(f"⚠️ Issues detected: {json.dumps(report['issues'], indent=2)}")
        else:
            print("🛡️ No bottlenecks detected. Code is clean.")
        sys.exit(0)

    except subprocess.CalledProcessError as e:
        print(f"❌ Alnoms Performance Guardrail Triggered!", file=sys.stderr)
        try:
            report = json.loads(e.stdout)
            post_github_comment(report) # Post failure report too
            print(json.dumps(report, indent=2), file=sys.stderr)
        except:
            print(e.stderr if e.stderr else "Unknown error in engine execution.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()