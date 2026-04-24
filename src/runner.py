import os
import sys
import subprocess
import json

def get_modified_python_files(base_ref):
    """Uses Git to find which Python files were changed in the PR."""
    try:
        # Fetch origin to ensure we have the base branch history
        subprocess.run(["git", "fetch", "origin", base_ref], capture_output=True, check=True)
        
        # Get the diff
        result = subprocess.run(
            ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        files = result.stdout.splitlines()
        # Filter for only Python files
        return [f for f in files if f.endswith('.py')]
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git diff failed (might be a direct push, not a PR): {e.stderr}", file=sys.stderr)
        return []

def main():
    print("🚀 Booting Alnoms Performance Guardrail...")
    
    fail_threshold = os.environ.get('FAIL_ON', '')
    # In GitHub Actions PRs, this env var holds the target branch (e.g., 'main')
    base_ref = os.environ.get('GITHUB_BASE_REF', 'main') 
    
    print(f"📊 Threshold: {fail_threshold if fail_threshold else 'Warn Only'}")
    
    changed_files = get_modified_python_files(base_ref)
    
    if not changed_files:
        print("✅ No Python files modified in this PR. Skipping Alnoms scan.")
        sys.exit(0)

    print(f"🔍 Found {len(changed_files)} Python files to scan: {changed_files}")
    
    # --- TEMPORARY MOCK ENGINE EXECUTION ---
    # Once you update your PyPI package to accept file lists, we will pass `changed_files` here.
    try:
        print("⚙️ Executing Alnoms Engine...")
        result = subprocess.run(
            ["python", "-m", "alnoms", "--version"], # We will change this to the real scan command next
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