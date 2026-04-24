import os
import sys
import subprocess
import json

def main():
    print("🚀 Booting Alnoms Performance Guardrail...")
    
    # 1. Grab inputs from the action.yml environment
    fail_threshold = os.environ.get('FAIL_ON', '')
    github_token = os.environ.get('GITHUB_TOKEN')
    
    # GitHub natively provides the base branch in PRs
    base_ref = os.environ.get('GITHUB_BASE_REF', 'origin/main')
    
    print(f"📊 Threshold: {fail_threshold if fail_threshold else 'Warn Only'}")
    
    try:
        # 2. Execute the Alnoms CLI in headless CI mode
        # Note: This assumes your PyPI package CLI exposes a command like `alnoms-ci`
        print(f"🔍 Scanning diff against {base_ref}...")
        
        # For testing right now, we will just run the module to ensure it installed correctly
        # We will replace this with your actual JSON command in the next step
        result = subprocess.run(
            ["python", "-m", "alnoms", "--help"], 
            capture_output=True,
            text=True,
            check=True
        )
        
        print("✅ Engine executed successfully.")
        
        # 3. Future Step: Parse the JSON from result.stdout and check thresholds
        # If complexity > fail_threshold: sys.exit(1)
        
        sys.exit(0) # Exit 0 means the GitHub Action turns Green (Passed)

    except subprocess.CalledProcessError as e:
        print(f"❌ Alnoms Engine Execution Failed:\n{e.stderr}", file=sys.stderr)
        sys.exit(1) # Exit 1 means the GitHub Action turns Red (Failed)

if __name__ == "__main__":
    main()