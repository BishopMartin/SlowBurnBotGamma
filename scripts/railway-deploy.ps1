# Deploy this repo to Railway.
#
# Works after either:
#   - `npx @railway/cli@latest login` (interactive, stores session), or
#   - `$env:RAILWAY_TOKEN = "railway_..."` from https://railway.com/account/tokens (CI/scripts).
#
# Usage (PowerShell, from repo root):
#   .\scripts\railway-deploy.ps1

$ErrorActionPreference = "Stop"
$ProjectId = if ($env:RAILWAY_PROJECT_ID) { $env:RAILWAY_PROJECT_ID } else { "7ea1c94f-861d-49d6-a428-6771c62ce371" }
$ServiceName = if ($env:RAILWAY_SERVICE_NAME) { $env:RAILWAY_SERVICE_NAME } else { "SlowBurnBotGamma" }

Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "Linking project $ProjectId ..."
npx --yes @railway/cli@latest link -p $ProjectId
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Linking service '$ServiceName' (avoids 'multiple services' error on up) ..."
npx --yes @railway/cli@latest service link $ServiceName
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Deploying (detached, CI log stream) ..."
npx --yes @railway/cli@latest up --detach --ci -p $ProjectId -m "deploy: $(Get-Date -Format o)"
exit $LASTEXITCODE
