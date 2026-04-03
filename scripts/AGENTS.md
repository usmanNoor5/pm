# Scripts Agent Guide

This folder contains container lifecycle scripts:

- Linux: `start-linux.sh`, `stop-linux.sh`
- macOS: `start-mac.sh`, `stop-mac.sh`
- Windows PowerShell: `start-windows.ps1`, `stop-windows.ps1`

Behavior:
- Start scripts build image `pm-mvp:local` and run container `pm-mvp`.
- Stop scripts remove container `pm-mvp` if present.
- Start scripts support optional host port override via `HOST_PORT` (default `8000`).