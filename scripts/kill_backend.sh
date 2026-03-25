#!/usr/bin/env bash
# Stop locally running uvicorn backend (Windows-compatible)
powershell.exe -command "
  Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force -ErrorAction SilentlyContinue }
"
echo "Backend stopped."
