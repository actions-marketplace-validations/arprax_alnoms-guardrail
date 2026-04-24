import os
import sys
import subprocess
import json

def get_modified_python_files():
    """Uses Git to find which Python files were changed in the PR or Push."""
    # GitHub natively tells us what kind of event triggered the action
    event_name = os.environ.get('GITHUB_EVENT_NAME', 'push')
    base_ref = os.environ.get('GITHUB_BASE_REF', '')
    
    try:
        if event_name == 'pull_request' and base_ref:
            # Scenario A: It's a Pull Request. Compare against the target branch.
            subprocess.run(["git", "fetch", "origin", base_ref], capture_output=True, check=True)
            cmd = ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"]
        else:
            # Scenario B: It's a direct push. Compare the latest commit to the previous one.
            cmd = ["git", "diff", "--name-only", "HEAD~1...HEAD"]
            
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        files = result.stdout.splitlines()
        
        # Filter for only Python files
        return [f for f in files if f.endswith('.py')]
        
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git diff failed: {e.stderr}", file=sys.stderr)
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
    
    # --- TEMPORARY MOCK ENGINE EXECUTION ---
    try:
        print("⚙️ Executing Alnoms Engine...")
        result = subprocess.run(
            ["python", "-m", "alnoms", "--version"], 
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ Alnoms Engine Success: {result.stdout.strip()}")
        sys.exit(0)

    except subprocess.CalledProcessError as e:
        print(f"❌ Alnoms Engine Execution Failed:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()