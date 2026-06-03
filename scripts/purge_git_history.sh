#!/usr/bin/env bash
# Helper to remove sensitive files from Git history using git-filter-repo.
# WARNING: This rewrites history. Coordinate with your team before pushing.

set -euo pipefail

if ! command -v git >/dev/null 2>&1; then
  echo "git is required"
  exit 1
fi

if command -v git-filter-repo >/dev/null 2>&1; then
  echo "Using git-filter-repo to remove .env and db.sqlite3 from history"
  git filter-repo --invert-paths --path .env --path db.sqlite3 --force
  echo "Done. Review the rewritten history, then push with --force where appropriate."
  exit 0
fi

cat <<'EOF'
git-filter-repo is not installed. Install it and rerun this script, or use BFG.

Install git-filter-repo (example for Debian/Ubuntu):
  sudo apt-get install git-filter-repo

Or install via pip:
  pip install git-filter-repo

If you prefer BFG:
  1. Download BFG jar: https://rtyley.github.io/bfg-repo-cleaner/
  2. Run:
     java -jar bfg.jar --delete-files .env --delete-files db.sqlite3
     git reflog expire --expire=now --all && git gc --prune=now --aggressive

After rewriting history, ensure all collaborators re-clone or follow the rebase instructions.
EOF
