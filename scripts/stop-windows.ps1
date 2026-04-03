$ErrorActionPreference = "Stop"

$ContainerName = "pm-mvp"

Write-Host "[stop-windows] Stopping container..."
docker rm -f $ContainerName *> $null
Write-Host "[stop-windows] Done."
