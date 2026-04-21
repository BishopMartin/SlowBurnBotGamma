pre-push: auto-increments frontend/lib/version.ts (1.43 -> 1.44) and commits "chore: bump app version".

One-time per clone:
  git config core.hooksPath githooks

Skip once:
  SKIP_VERSION_BUMP=1 git push   (Unix / Git Bash)
  $env:SKIP_VERSION_BUMP=1; git push   (PowerShell)

Manual bump (no commit):
  cd frontend && npm run bump-version
