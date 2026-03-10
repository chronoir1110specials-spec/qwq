New-Item -ItemType Directory -Force -Path .\offline_wheels | Out-Null
pip download -r .\requirements-core.txt -d .\offline_wheels
pip download -r .\requirements-pipeline.txt -d .\offline_wheels
Write-Host "Offline wheels downloaded to .\offline_wheels"
