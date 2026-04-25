import os
import sys
import json
import subprocess
import urllib.request

# -----------------------------
# CONFIG
# -----------------------------
IGNORE_FILES = {'runner.py', 'setup.py', 'conftest.py'}
TIMEOUT = int(os.environ.get("ALNOMS_TIMEOUT", 60))


# -----------------------------
# GET MODIFIED FILES
# -----------------------------
def get_modified_python_files():
    """Find modified Python files using GitHub event payload or git fallback."""
    try:
        event_path = os.environ.get('GITHUB_EVENT_PATH')
        files = []

        # ✅ Preferred: GitHub event payload
        if event_path and os.path.exists(event_path):
            with open(event_path) as f:
                event_data = json.load(f)

            # Pull Request
            if "pull_request" in event_data:
                files = [
                    f["filename"]
                    for f in event_data.get("pull_request", {}).get("files", [])
                ]

        # ⚠️ Fallback: git diff
        if not files:
            cmd = ["git", "diff", "--name-only", "HEAD~1...HEAD"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=TIMEOUT
            )
            files = result.stdout.splitlines()

        # ✅ Filter Python files safely
        return [
            f for f in files
            if f.endswith(".py") and os.path.basename(f) not in IGNORE_FILES
        ]

    except Exception as e:
        print(f"⚠️ Failed to get modified files: {e}", file=sys.stderr)
        return []


# -----------------------------
# FORMAT COMMENT
# -----------------------------
def build_comment(report):
    issues = report.get("issues", [])

    if not issues:
        return """### ✅ Alnoms CI Output: Passed
No performance regressions detected. Code scales efficiently."""

    rows = ""
    seen_suggestions = set()
    suggestions = ""

    for issue in issues:
        file = issue.get("file", "unknown")
        function = issue.get("function", "unknown")
        complexity = issue.get("complexity", "non-linear")

        rows += f"| `{file}` | `{function}` | Likely {complexity} scaling |\n"

        suggestion = issue.get("suggestion")
        if suggestion and suggestion not in seen_suggestions:
            seen_suggestions.add(suggestion)
            suggestions += f"- {suggestion}\n"

    if not suggestions:
        suggestions = "- Optimize loops or data structures to reduce complexity.\n"

    files_list = ", ".join(sorted({i.get("file", "") for i in issues}))

    body = f"""❌ **Alnoms Blocked This PR**

### Performance Regression Detected

A high-risk non-linear scaling pattern was identified in this change.

| File | Function | Detected Behavior |
|------|----------|------------------|
{rows}
---

### 📊 Estimated Impact

- Input growth 10× → runtime may increase ~20–50×  
- Significant degradation under moderate to large workloads  
- Increased compute cost risk in production environments  

---

### ⛔ Decision

**This PR is blocked due to a performance regression.**

---

### 💡 Suggested Fix

{suggestions.strip()}

---

### 🔍 Deep Analysis (Optional)

To inspect full runtime behavior and validate scaling:

```bash
alnoms analyze {files_list} --deep
```
---
*Alnoms CI Guardrail · Built by Arprax*
"""
    return body


# -----------------------------
# POST COMMENT
# -----------------------------
def post_github_comment(report):
    token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')
    pr_number = None

    try:
        event_path = os.environ.get('GITHUB_EVENT_PATH')
        if event_path:
            with open(event_path) as f:
                event_data = json.load(f)
                pr_number = event_data.get('pull_request', {}).get('number')
    except Exception:
        pass

    if not token or not repo or not pr_number:
        print("ℹ️ Skipping PR comment: Not a PR or missing token.")
        return

    body = build_comment(report)

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }

    data = json.dumps({"body": body}).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            if response.getcode() == 201:
                print("💬 Posted Alnoms CI report.")
    except Exception as e:
        print(f"⚠️ Failed to post comment: {e}")


# -----------------------------
# MAIN
# -----------------------------
def main():
    print("🚀 Booting Alnoms Performance Guardrail...")

    fail_threshold = os.environ.get("FAIL_ON", "")
    changed_files = get_modified_python_files()

    if not changed_files:
        print("✅ No Python files modified. Skipping scan.")
        sys.exit(0)

    print(f"🔍 Scanning files: {changed_files}")

    try:
        cmd = ["python", "-m", "alnoms", "ci"] + changed_files

        if fail_threshold:
            cmd += ["--fail-on", fail_threshold]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT
        )

        try:
            report = json.loads(result.stdout)
        except json.JSONDecodeError:
            print("❌ Failed to parse Alnoms output", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            sys.exit(1)

        post_github_comment(report)

        if result.returncode != 0:
            print("❌ Performance regression detected.", file=sys.stderr)
            sys.exit(1)

        print("✅ No performance issues detected.")
        sys.exit(0)

    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()