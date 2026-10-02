param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$source = Join-Path $Root "config\profiles"
if (-not (Test-Path $source)) {
    throw "Profile source folder not found: $source"
}

foreach ($agent in @("maf", "langgraph")) {
    $destination = Join-Path $Root "src\agents\$agent\profiles"
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Copy-Item -Path (Join-Path $source "*.json") -Destination $destination -Force
}

Write-Host "Synced config\profiles into src\agents\maf\profiles and src\agents\langgraph\profiles."
