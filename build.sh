#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "=== Installing Python Dependencies ==="
pip install -r requirements.txt

echo "=== Installing Playwright Chromium ==="
playwright install chromium

echo "=== Build Completed Successfully ==="
