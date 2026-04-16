# Deploy from CI/script: requires RAILWAY_TOKEN in env (see .env.example).
# Interactive: run `npx @railway/cli@latest login` once in a normal terminal (browser OAuth);
# Cursor agent cannot complete `railway login` (non-interactive).
# Usage (PowerShell, from repo root):
#   $env:RAILWAY_TOKEN = "railway_..."   # or: Get-Content .env | ForEach-Object { if ($_ -match '^([^#][^=]+)=(.*)$') { Set-Item -Path env:$($matches[1]) -Value $matches[2].Trim() } }
#   .\scripts\railway-deploy.ps1
#
# Or one line after creating .env with RAILWAY_TOKEN set:
#   Get-Content .env | Where-Object { $_ -match '^\s*RAILWAY_TOKEN=' } | ForEach-Object { Invoke-Expression "`$env:$($_.Split('=',2)[0].Trim())='$($_.Split('=',2)[1].Trim())'" }; .\scripts\railway-deploy.ps1

$ErrorActionPreference = "Stop"
$ProjectId = if ($env:RAILWAY_PROJECT_ID) { $env:RAILWAY_PROJECT_ID } else { "7ea1c94f-861d-49d6-a428-6771c62ce371" }

if (-not $env:RAILWAY_TOKEN -or $env:RAILWAY_TOKEN.Trim().Length -eq 0) {
    Write-Error "RAILWAY_TOKEN is not set. Create a token at https://railway.com/account/tokens and set `$env:RAILWAY_TOKEN or add it to a .env file (see .env.example)."
    exit 1
}

Set-Location (Join-Path $PSScriptRoot "..")
Write-Host "Linking to Railway project $ProjectId ..."
npx --yes @railway/cli@latest link -p $ProjectId
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Deploying (detached, CI log stream) ..."
npx --yes @railway/cli@latest up --detach --ci -p $ProjectId -m "deploy: $(Get-Date -Format o)"
exit $LASTEXITCODE
