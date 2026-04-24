import os
import sys
import subprocess
import json

def get_modified_python_files():
    """Uses Git to find which Python files were changed in the PR or Push."""
    event_name = os.environ.get('GITHUB_EVENT_NAME', 'push')
    base_ref = os.environ.get('GITHUB_BASE_REF', '')
    
    try:
        # We add a 30-second timeout to prevent the runner from hanging indefinitely
        if event_name == 'pull_request' and base_ref:
            # Scenario A: It's a Pull Request. Compare against the target branch.
            subprocess.run(["git", "fetch", "origin", base_ref], capture_output=True, check=True, timeout=30)
            cmd = ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"]
        else:
            # Scenario B: It's a direct push. Compare the latest commit to the previous one.
            cmd = ["git", "diff", "--name-only", "HEAD~1...HEAD"]
            
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        files = result.stdout.splitlines()
        
        return [f for f in files if f.endswith('.py')]
        
    except subprocess.TimeoutExpired:
        print("⚠️ Git diff timed out. The history might be too large or deep.", file=sys.stderr)
        return []
    except Exception as e:
        print(f"⚠️ Git diff failed: {str(e)}", file=sys.stderr)
        return []

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
        
        # Build the command: python -m alnoms ci file1.py file2.py --fail-on O(N^3)
        cmd = ["python", "-m", "alnoms", "ci"] + changed_files
        if fail_threshold:
            cmd.extend(["--fail-on", fail_threshold])
            
        # timeout=60 added here because scanning multiple files can take longer than a git diff
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        
        # Parse the JSON output from your engine
        report = json.loads(result.stdout)
        
        print(f"✅ Alnoms Engine Success. Scanned {report.get('scanned_files', 0)} files.")
        if report.get("issues"):
            # We use indent=2 for a cleaner terminal output in the GitHub log
            print(f"⚠️ Issues detected: {json.dumps(report['issues'], indent=2)}")
        else:
            print("🛡️ No bottlenecks detected. Code is clean.")
            
        sys.exit(0)

    except subprocess.TimeoutExpired:
        print("❌ Error: Alnoms Engine timed out (exceeded 60s).", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Alnoms Performance Guardrail Triggered!", file=sys.stderr)
        try:
            # Engine failure usually contains the JSON report in stdout
            report = json.loads(e.stdout)
            print(json.dumps(report, indent=2), file=sys.stderr)
        except:
            print(e.stderr if e.stderr else "Unknown error in engine execution.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()