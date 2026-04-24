#!/usr/bin/env bash
set -euo pipefail

echo "Installing Alnoms..."
pip install alnoms

echo "Running Alnoms CI..."
RESULT=$(alnoms-ci)

echo "result=$RESULT" >> "$GITHUB_OUTPUT"
