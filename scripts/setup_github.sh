#!/usr/bin/env bash
# Run this AFTER the repo is created and pushed.
# Usage: ./scripts/setup_github.sh
set -euo pipefail

REPO="Monotoba/specforge"

echo "=== Configuring GitHub repo: $REPO ==="

# ── 1. Create the 'pypi' deployment environment ──────────────────────────────
echo ""
echo "1. Creating 'pypi' deployment environment..."
curl -s -X PUT \
  -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO/environments/pypi" \
  -d '{"wait_timer":0,"reviewers":[],"deployment_branch_policy":null}' > /dev/null
echo "   ✓ pypi environment created"

# ── 2. Add environment protection: restrict to tag pushes only ────────────────
echo ""
echo "2. Restricting 'pypi' environment to tag deployments..."
curl -s -X PUT \
  -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO/environments/pypi" \
  -d '{"deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}' > /dev/null

# Add tag pattern v*.*.*
curl -s -X POST \
  -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO/environments/pypi/deployment-branch-policies" \
  -d '{"name":"v*","type":"tag"}' > /dev/null 2>&1 || echo "   (tag policy may already exist)"
echo "   ✓ pypi environment restricted to v* tags"

# ── 3. Branch protection on main ─────────────────────────────────────────────
echo ""
echo "3. Adding branch protection to 'main'..."
curl -s -X PUT \
  -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO/branches/main/protection" \
  -d '{"required_status_checks":{"strict":true,"contexts":["test (3.11)","test (3.12)","build"]},"enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null}' > /dev/null
echo "   ✓ main branch protected (CI must pass)"

# ── 4. Enable security features ──────────────────────────────────────────────
echo ""
echo "4. Enabling vulnerability alerts and Dependabot..."
curl -s -X PUT \
  -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO/vulnerability-alerts" > /dev/null 2>&1 || true
curl -s -X PUT \
  -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO/automated-security-fixes" > /dev/null 2>&1 || true
echo "   ✓ vulnerability alerts enabled"

# ── 5. Tag and push v0.21.0 to trigger the release workflow ──────────────────
echo ""
echo "5. Creating release tag v0.21.0..."
cd "$(git rev-parse --show-toplevel)"
if git tag | grep -q "^v0.21.0$"; then
  echo "   (tag v0.21.0 already exists)"
else
  git tag -a v0.21.0 -m "Release 0.21.0 — initial public release"
  echo "   ✓ tag v0.21.0 created locally"
fi

echo ""
echo "=== Done! ==="
echo ""
echo "Next steps:"
echo ""
echo "  1. Push the tag to trigger the release workflow:"
echo "     git push origin v0.21.0"
echo ""
echo "  2. Configure PyPI trusted publishing (one-time, on pypi.org):"
echo "     https://pypi.org/manage/account/publishing/"
echo ""
echo "     Fill in:"
echo "       PyPI project name : specforge"
echo "       Owner             : Monotoba"
echo "       Repository        : specforge"
echo "       Workflow filename : release.yml"
echo "       Environment name  : pypi"
echo ""
echo "  3. The release workflow will publish automatically when a v*.*.* tag is pushed."
