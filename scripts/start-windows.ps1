$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$ImageName = "pm-mvp:local"
$ContainerName = "pm-mvp"
$VolumeName = "pm-mvp-data"
$HostPort = if ($env:HOST_PORT) { $env:HOST_PORT } else { "8000" }

Set-Location $RootDir

Write-Host "[start-windows] Building Docker image..."
docker build -t $ImageName .

Write-Host "[start-windows] Removing existing container if present..."
docker rm -f $ContainerName *> $null

Write-Host "[start-windows] Starting container on http://localhost:$HostPort"
docker run -d --name $ContainerName --env-file .env -v ${VolumeName}:/app/backend/data -p ${HostPort}:8000 $ImageName *> $null

Write-Host "[start-windows] Started."
