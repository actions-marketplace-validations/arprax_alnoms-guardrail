import os
import sys
import io
import json
import subprocess
import urllib.request
import urllib.parse

TIMEOUT = 60
IGNORE_FILES = {"runner.py", "setup.py", "conftest.py"}

GITHUB_API = "https://api.github.com"

def github_request(path, method="GET", data=None):
    """Minimal GitHub REST API client using urllib."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required for GitHub API calls.")

    url = f"{GITHUB_API}{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        content = resp.read().decode("utf-8")
        return json.loads(content) if content else None

def get_event():
    """Load the GitHub event payload."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.exists(event_path):
        return {}
    with open(event_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_modified_python_files():
    """
    Determine which Python files were modified.

    - For pull_request: use GitHub REST API to list changed files.
    - For push: use git diff HEAD~1...HEAD.
    """
    event_name = os.environ.get("GITHUB_EVENT_NAME", "push")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    event = get_event()

    try:
        if event_name == "pull_request":
            pr_number = event.get("pull_request", {}).get("number")
            if not pr_number:
                print("ℹ️ No PR number found in event payload.", file=sys.stderr)
                return []

            page = 1
            files = []
            while True:
                path = f"/repos/{repo}/pulls/{pr_number}/files?per_page=100&page={page}"
                batch = github_request(path, method="GET")
                if not batch:
                    break
                files.extend(batch)
                if len(batch) < 100:
                    break
                page += 1

            changed = [f["filename"] for f in files]

        else:
            cmd = ["git", "diff", "--name-only", "HEAD~1...HEAD"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=TIMEOUT,
            )
            changed = result.stdout.splitlines()

        py_files = [
            f for f in changed
            if f.endswith(".py") and os.path.basename(f) not in IGNORE_FILES
        ]

        return py_files

    except Exception as e:
        print(f"⚠️ Failed to get modified files: {e}", file=sys.stderr)
        return []


def build_comment(report):
    """Turn the Alnoms JSON report into a Markdown PR comment."""
    decision = report.get("decision", {})
    status = decision.get("status", "PASS")
    reason = decision.get("reason", "No performance regressions detected.")

    # PASS path
    if status == "PASS":
        summary = report.get("summary", {})
        sev = summary.get("by_severity", {})
        worst_comp = summary.get("worst_complexity", "Unknown")
        total = summary.get("total_issues", 0)
        risk = summary.get("risk_level", "LOW")

        return f"""### ✅ Alnoms CI Output: Passed

> {reason}

**Summary**
- System Risk Level: `{risk}`
- Worst Complexity: `{worst_comp}`
- Total Issues: {total} ({sev.get('CRITICAL', 0)} CRITICAL, {sev.get('HIGH', 0)} HIGH, {sev.get('MEDIUM', 0)} MEDIUM)

Code scales efficiently for this change.
"""

    # BLOCK path
    primary = report.get("primary_trigger", {})
    summary = report.get("summary", {})
    issues = report.get("issues", [])

    sev = summary.get("by_severity", {})
    worst_comp = summary.get("worst_complexity", "Unknown")
    total = summary.get("total_issues", 0)
    risk = summary.get("risk_level", "UNKNOWN")

    # Evidence table
    evidence_table = ""
    if len(issues) > 1:
        rows = ""
        for issue in issues[1:]:
            rows += (
                f"| `{issue.get('file', 'unknown')}` "
                f"| `{issue.get('function', 'unknown')}` "
                f"| `{issue.get('severity', 'UNKNOWN')}` "
                f"| `{issue.get('complexity', 'Unknown')}` |\n"
            )

        evidence_table = f"""### 🔍 Additional Evidence
| File | Function | Severity | Complexity |
|------|----------|----------|------------|
{rows}
---
"""

    files_list = " ".join(
        sorted({i.get("file") for i in issues if i.get("file")})
    )

    return f"""❌ **Alnoms Blocked This PR**

> **Verdict:** {reason}

---

### 🚨 Primary Trigger
**Function:** `{primary.get('function', 'unknown')}` (in `{primary.get('file', 'unknown')}`)  
**Severity:** `{primary.get('severity', 'UNKNOWN')}` | **Complexity:** `{primary.get('complexity', 'Unknown')}`  
**Issue:** {primary.get('issue', 'Unknown bottleneck')}

**💡 Suggested Fix**
> {primary.get('suggestion', 'Optimize data structures or loops to reduce complexity.')}

---

### 📊 Impact Summary
- **System Risk Level:** `{risk}`
- **Worst Complexity:** `{worst_comp}`
- **Total Issues:** {total} ({sev.get('CRITICAL', 0)} CRITICAL, {sev.get('HIGH', 0)} HIGH, {sev.get('MEDIUM', 0)} MEDIUM)

---

{evidence_table.strip()}

### 🔬 Deep Analysis (Optional)

```bash
alnoms analyze {files_list} --deep
```
*Alnoms CI Guardrail · Built by [Arprax](https://arprax.com)*
"""

def post_github_comment(report):
    """Post a single authoritative comment to the PR (if this is a PR)."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    event = get_event()
    pr_number = event.get("pull_request", {}).get("number")

    if not repo or not pr_number:
        print("ℹ️ Skipping PR comment: Not a Pull Request.")
        return

    body = build_comment(report)
    path = f"/repos/{repo}/issues/{pr_number}/comments"

    try:
        github_request(path, method="POST", data={"body": body})
        print("💬 Posted Alnoms CI report as PR comment.")
    except Exception as e:
        print(f"⚠️ Failed to post PR comment: {e}", file=sys.stderr)

def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("🚀 Booting Alnoms Performance Guardrail...")
    fail_threshold = os.environ.get("FAIL_ON", "")

    changed_files = get_modified_python_files()

    if not changed_files:
        print("✅ No Python files modified. Skipping scan.")
        sys.exit(0)

    print(f"🔍 Found {len(changed_files)} Python files to scan: {changed_files}")

    cmd = ["python", "-m", "alnoms", "ci"] + changed_files
    if fail_threshold:
        cmd.extend(["--fail-on", fail_threshold])

    try:
        print("⚙️ Executing Alnoms Engine...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=TIMEOUT,
        )
        report = json.loads(result.stdout)

        print(json.dumps(report, indent=2))
        post_github_comment(report)

        scanned = report.get("metadata", {}).get("scanned_files", 0)
        print(f"✅ Alnoms Engine Success. Scanned {scanned} files.")

        if report.get("decision", {}).get("status") == "BLOCK":
            print("❌ Alnoms Performance Guardrail Triggered! Blocking PR.", file=sys.stderr)
            sys.exit(1)

        sys.exit(0)

    except subprocess.CalledProcessError as e:
        print("❌ Alnoms Engine failed.", file=sys.stderr)
        try:
            report = json.loads(e.stdout or "{}")
            print(json.dumps(report, indent=2), file=sys.stderr)
            post_github_comment(report)
        except Exception:
            print(e.stderr or "Unknown error in engine execution.", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"❌ Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
